
from flask import Flask, request, jsonify
import os
import torch
from transformers import pipeline
import logging
import torchaudio
from torchaudio.transforms import Resample
from datetime import datetime, timedelta
import json
import numpy as np
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Set offline mode BEFORE any imports that might use HuggingFace
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    logging.info(f"✓ Gemini API configured with model: {GEMINI_MODEL}")
else:
    gemini_model = None
    logging.warning("⚠️ GEMINI_API_KEY not found in .env - Gemini features disabled")

# Global variable for audio classifier (lazy loaded)
audio_classifier = None
_classifier_loaded = False


def get_audio_classifier():
    """Lazy load the audio classifier from cache only"""
    global audio_classifier, _classifier_loaded
    if _classifier_loaded:
        return audio_classifier
    
    _classifier_loaded = True
    try:
        logging.info("Attempting to load AudioSet classifier with low_cpu_mem_usage...")
        from transformers import AutoFeatureExtractor, ASTForAudioClassification
        
        # Load model with low memory mode to work around page file issues
        feature_extractor = AutoFeatureExtractor.from_pretrained(
            "MIT/ast-finetuned-audioset-10-10-0.4593",
            local_files_only=True
        )
        model = ASTForAudioClassification.from_pretrained(
            "MIT/ast-finetuned-audioset-10-10-0.4593",
            local_files_only=True,
            low_cpu_mem_usage=True,  # Reduces peak memory usage during loading
            torch_dtype=torch.float32
        )
        
        audio_classifier = pipeline(
            "audio-classification",
            model=model,
            feature_extractor=feature_extractor,
            device=-1,  # CPU
            top_k=10
        )
        logging.info("✓ Successfully loaded audio classifier")
    except Exception as e:
        logging.warning(f"✗ Could not load HF model, using DSP fallback: {e}")
        import traceback
        traceback.print_exc()
        audio_classifier = None
    
    return audio_classifier

'''def get_audio_classifier():
    """Lazy load the audio classifier from cache only"""
    global audio_classifier, _classifier_loaded
    if _classifier_loaded:
        return audio_classifier
    
    _classifier_loaded = True
    try:
        logging.info("Attempting to load AudioSet classifier from cache...")
        audio_classifier = pipeline(
            "audio-classification",
            model="MIT/ast-finetuned-audioset-10-10-0.4593",
            device=0 if torch.cuda.is_available() else -1,
            top_k=10,
            local_files_only=True
        )
        logging.info("✓ Successfully loaded audio classifier from cache")
    except Exception as e:
        logging.warning(f"✗ Could not load HF model, using DSP fallback: {e}")
        audio_classifier = None
    
    return audio_classifier'''

# Map model labels to our classes (case-insensitive match). These are heuristic; adjust after empirical tests.
LABEL_MAP = {
    "cheering": ["Cheering", "Whoop"],
    "applause": ["Applause", "Clapping"],
    "chatter": ["Speech", "Chatter", "Conversation", "Babble"],
    "booing": [
        "Boo", "Booing",  # Direct negative reactions
        "Grunt", "Groan", "Gasp", "Sigh",  # Disappointment sounds
        "Wail", "Moan", "Screaming"  # Distress sounds
    ],
    "music_only": ["Music", "Musical instrument", "Electronic music"]
}

def aggregate_probs(preds):
    result = {k: 0.0 for k in LABEL_MAP}
    for pred in preds:
        plabel = pred['label'].lower()
        for k, labels in LABEL_MAP.items():
            if any(plabel == l.lower() for l in labels):
                result[k] += float(pred['score'])
    total = sum(result.values())
    if total > 0:
        for k in result:
            result[k] /= total
    return result

# Enthusiasm score weights (tune during testing)
# Updated weights for better discrimination:
# - W2: Reduced applause (0.8→0.7) - often background noise
# - W3: Increased chatter penalty (0.5→0.6) - talking = not engaged
# - W4: Increased booing penalty (1.2→1.5) - more severe negative signal
W1, W2, W3, W4 = 1.0, 0.7, 0.6, 1.5
SCORE_HISTORY = []
WINDOW_SIZE = 5

def calculate_enthusiasm_score(probs):
    return (probs.get('cheering', 0)*W1 + 
            probs.get('applause', 0)*W2 - 
            probs.get('chatter', 0)*W3 -
            probs.get('booing', 0)*W4)  # Booing is more negative than chatter

def detect_trend():
    if len(SCORE_HISTORY) < WINDOW_SIZE:
        return 'unknown'
    window = SCORE_HISTORY[-WINDOW_SIZE:]
    diffs = [window[i+1] - window[i] for i in range(len(window)-1)]
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff > 0.05:
        return 'rising'
    elif avg_diff < -0.05:
        return 'falling'
    else:
        return 'stable'

# ---------- Party State & Gemini Integration ----------

# Party session tracking
PARTY_STATE = {
    "start_time": None,
    "current_song": None,
    "song_history": [],
    "prediction_tracker": [],
    "last_gemini_call": None
}

def calculate_party_stage(elapsed_minutes, avg_enthusiasm_5min, current_trend):
    """Determine party phase based on time and energy"""
    if elapsed_minutes < 30 or avg_enthusiasm_5min < 0.3:
        return "early"
    elif 30 <= elapsed_minutes < 120 and avg_enthusiasm_5min > 0.6:
        return "peak"
    elif elapsed_minutes >= 120 or (current_trend == "falling" and avg_enthusiasm_5min < 0.5):
        return "late"
    else:
        return "mid"

def interpret_enthusiasm_score(score):
    """Convert numeric score to human-readable interpretation"""
    if score > 0.7:
        return "Highly engaged - crowd is loving it"
    elif score > 0.4:
        return "Good energy - crowd enjoying"
    elif score > 0.1:
        return "Moderate interest - maintaining attention"
    elif score > -0.2:
        return "Neutral - crowd chatting/ambient"
    elif score > -0.7:
        return "Losing interest - attention dropping"
    else:
        return "Negative reaction - crowd disappointed/unhappy"

def build_gemini_context():
    """Construct rich context for Gemini API"""
    if not SCORE_HISTORY:
        return None
    
    # Initialize party start time if not set
    if PARTY_STATE["start_time"] is None:
        PARTY_STATE["start_time"] = datetime.now()
    
    elapsed_minutes = (datetime.now() - PARTY_STATE["start_time"]).seconds // 60
    current_score = SCORE_HISTORY[-1] if SCORE_HISTORY else 0.0
    current_trend = detect_trend()
    
    # Calculate historical averages
    avg_30s = np.mean(SCORE_HISTORY[-6:]) if len(SCORE_HISTORY) >= 6 else current_score
    avg_1min = np.mean(SCORE_HISTORY[-12:]) if len(SCORE_HISTORY) >= 12 else current_score
    avg_5min = np.mean(SCORE_HISTORY[-60:]) if len(SCORE_HISTORY) >= 60 else current_score
    score_variance = np.var(SCORE_HISTORY[-12:]) if len(SCORE_HISTORY) >= 12 else 0.0
    
    party_stage = calculate_party_stage(elapsed_minutes, avg_5min, current_trend)
    
    context = {
        "crowd_state": {
            "enthusiasm_score": round(float(current_score), 2),
            "trend": current_trend,
            "interpretation": interpret_enthusiasm_score(current_score),
            "confidence": "high" if len(SCORE_HISTORY) >= 10 else "low"
        },
        "temporal_context": {
            "score_history_30s": [round(float(s), 2) for s in SCORE_HISTORY[-6:]],
            "avg_score_30s": round(float(avg_30s), 2),
            "avg_score_1min": round(float(avg_1min), 2),
            "avg_score_5min": round(float(avg_5min), 2),
            "score_variance": round(float(score_variance), 3),
            "samples_collected": len(SCORE_HISTORY)
        },
        "party_context": {
            "stage": party_stage,
            "elapsed_minutes": elapsed_minutes,
            "start_time": PARTY_STATE["start_time"].isoformat(),
            "total_songs_played": len(PARTY_STATE["song_history"]),
            "current_song": PARTY_STATE["current_song"]
        },
        "song_history": PARTY_STATE["song_history"][-5:] if PARTY_STATE["song_history"] else []
    }
    
    return context

def call_gemini_api(context):
    """Query Gemini for song recommendations"""
    if not gemini_model:
        return {"error": "Gemini API not configured"}
    
    try:
        prompt = f"""You are an expert AI DJ assistant analyzing a live party. Based on the crowd analysis below, recommend the next 3 songs to play and provide strategic advice.

CROWD STATE:
- Current enthusiasm: {context['crowd_state']['enthusiasm_score']:.2f} (scale: -1.5 to +1.0)
- Trend: {context['crowd_state']['trend']}
- Interpretation: {context['crowd_state']['interpretation']}
- Data confidence: {context['crowd_state']['confidence']}

TEMPORAL CONTEXT:
- Last 30 seconds scores: {context['temporal_context']['score_history_30s']}
- Average (30s): {context['temporal_context']['avg_score_30s']:.2f}
- Average (1min): {context['temporal_context']['avg_score_1min']:.2f}
- Average (5min): {context['temporal_context']['avg_score_5min']:.2f}
- Score stability (variance): {context['temporal_context']['score_variance']:.3f}

PARTY CONTEXT:
- Stage: {context['party_context']['stage']}
- Time elapsed: {context['party_context']['elapsed_minutes']} minutes
- Songs played: {context['party_context']['total_songs_played']}

SONG HISTORY:
{json.dumps(context['song_history'], indent=2) if context['song_history'] else "No songs played yet"}

Based on this analysis, provide your response in the following JSON format:
{{
  "analysis": {{
    "crowd_mood": "Brief assessment of crowd mood and energy",
    "energy_trajectory": "Description of energy trend",
    "recommendations_reasoning": "Why these recommendations make sense"
  }},
  "action": {{
    "recommendation": "maintain_energy | increase_energy | wind_down | change_genre",
    "urgency": "low | normal | high",
    "confidence": 0.0-1.0
  }},
  "next_songs": [
    {{
      "title": "Song Name",
      "artist": "Artist Name",
      "genre": "Genre",
      "reasoning": "Why this song",
      "predicted_impact": {{
        "enthusiasm_delta": "+0.10 to +0.15",
        "expected_score": 0.75
      }},
      "priority": 1
    }}
  ],
  "warnings": ["warning1", "warning2"],
  "tips": ["tip1", "tip2"]
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or extra text."""

        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=GEMINI_TEMPERATURE,
                max_output_tokens=2000
            )
        )
        
        # Parse JSON from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        PARTY_STATE["last_gemini_call"] = datetime.now()
        
        return result
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse Gemini response as JSON: {e}")
        logging.error(f"Raw response: {response.text}")
        return {"error": "Invalid JSON response from Gemini", "raw": response.text[:500]}
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        return {"error": str(e)}

# ---------- Health check endpoint ----------

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Server is running'})    

# ---------- Lightweight DSP-based analysis (fallback) ----------

SILERO_VAD = None
SILERO_UTILS = None

def _maybe_load_silero():
    global SILERO_VAD, SILERO_UTILS
    if SILERO_VAD is not None:
        return
    try:
        # Force offline mode for torch.hub as well
        torch.hub.set_dir(os.path.expanduser("~/.cache/torch/hub"))
        SILERO_VAD, SILERO_UTILS = torch.hub.load(
            'snakers4/silero-vad',
            'silero_vad',
            trust_repo=True,
            skip_validation=True  # Skip online validation
        )
        logging.info("✓ Loaded Silero VAD from cache")
    except Exception as e:
        logging.warning(f"✗ Silero VAD not available (will skip speech detection): {e}")

def _load_audio_mono_16k(path):
    """Load audio file and convert to mono 16kHz using multiple fallback methods"""
    # Try soundfile first (works for both WAV and MP3 with proper backend)
    try:
        import soundfile as sf
        import numpy as np
        logging.info(f"Attempting to load {path} with soundfile...")
        
        # Load only first 30 seconds to avoid memory issues
        max_samples = 30 * 44100  # 30 seconds at max expected sample rate
        wav_np, sr = sf.read(path, dtype='float32', frames=max_samples)
        
        # Convert to mono if stereo
        if len(wav_np.shape) > 1:
            wav_np = np.mean(wav_np, axis=1)
        
        # Resample to 16kHz using simple decimation (memory efficient)
        if sr != 16000:
            step = int(sr / 16000)
            wav_np = wav_np[::step]
            sr = 16000
        
        wav = torch.from_numpy(wav_np).float()
        logging.info(f"✓ Loaded audio with soundfile: shape={wav.shape}, sr={sr}")
        return wav, sr
        
    except Exception as e1:
        logging.warning(f"soundfile failed: {e1}, trying torchaudio with soundfile backend...")
        
        # Fallback to torchaudio with soundfile backend (avoids torchcodec requirement)
        try:
            import numpy as np
            
            # Use soundfile backend which handles more formats
            wav, sr = torchaudio.backend.soundfile_backend.load(path)
            
            # Convert to mono if stereo
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0, keepdim=False)
            else:
                wav = wav.squeeze(0)
            
            # Limit to 30 seconds
            max_samples = 30 * sr
            if wav.shape[0] > max_samples:
                wav = wav[:max_samples]
            
            # Resample to 16kHz if needed
            if sr != 16000:
                resampler = Resample(orig_freq=sr, new_freq=16000)
                wav = resampler(wav)
                sr = 16000
            
            logging.info(f"✓ Loaded audio with torchaudio: shape={wav.shape}, sr={sr}")
            return wav, sr
            
        except Exception as e2:
            logging.warning(f"torchaudio failed: {e2}, trying scipy...")
            
            # Final fallback to scipy for WAV files only
            try:
                from scipy.io import wavfile
                sr, wav_np = wavfile.read(path)
                wav = torch.from_numpy(wav_np).float()
                
                if len(wav.shape) > 1 and wav.shape[1] > 1:
                    wav = wav.mean(dim=1)
                
                # Normalize to [-1, 1]
                if wav.abs().max() > 1.0:
                    wav = wav / 32768.0
                
                if sr != 16000:
                    from scipy.signal import resample
                    target_len = int(len(wav) * 16000 / sr)
                    wav = torch.from_numpy(resample(wav.numpy(), target_len)).float()
                    sr = 16000
                
                logging.info(f"✓ Loaded audio with scipy: shape={wav.shape}, sr={sr}")
                return wav, sr
                
            except Exception as e3:
                logging.error(f"All audio loading methods failed. soundfile: {e1}, pydub: {e2}, scipy: {e3}")
                raise ValueError(f"Cannot load audio file {path}")

def _zero_crossing_rate(wav: torch.Tensor):
    x = wav.detach().cpu().numpy()
    zero_crossings = ((x[:-1] * x[1:]) < 0).sum()
    return float(zero_crossings) / max(1, x.shape[0])

def analyze_audio_dsp(path):
    try:
        wav, sr = _load_audio_mono_16k(path)
        duration = wav.shape[0] / sr if sr else 0.0
        rms = torch.sqrt(torch.mean(wav ** 2)).item()
        zcr = _zero_crossing_rate(wav)
    except Exception as e:
        logging.error(f"Error loading audio file: {e}")
        # Return safe defaults if audio loading fails
        return {
            'cheering': 0.0,
            'applause': 0.0,
            'chatter': 0.5,
            'music_only': 0.5
        }

    # Speech ratio via Silero (if available)
    _maybe_load_silero()
    speech_ratio = 0.0
    if SILERO_VAD is not None and SILERO_UTILS is not None and duration > 0:
        (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = SILERO_UTILS
        try:
            timestamps = get_speech_timestamps(wav.cpu(), SILERO_VAD, sampling_rate=sr)
            voiced = sum([ts['end'] - ts['start'] for ts in timestamps]) / sr if timestamps else 0.0
            speech_ratio = float(voiced / duration) if duration > 0 else 0.0
        except Exception as e:
            logging.warning(f"Silero VAD failed, continuing without speech ratio: {e}")

    # Improved heuristic thresholds (more aggressive for crowd sounds)
    RMS_SILENCE = 0.005
    RMS_MEDIUM = 0.02   # Lowered from 0.05
    RMS_HIGH = 0.08
    ZCR_MEDIUM = 0.04   # Lowered from 0.08
    ZCR_HIGH = 0.1

    probs = {k: 0.0 for k in LABEL_MAP}
    
    # Detect low-frequency rumble (booing has more low-freq energy)
    # This is a crude heuristic - real detection needs spectral analysis
    low_freq_indicator = zcr < 0.02  # Very low ZCR suggests low-frequency dominance

    if rms < RMS_SILENCE:
        # Silence or very low energy
        probs['music_only'] = 1.0
    else:
        # Base probability on speech ratio (talking vs crowd noise)
        if speech_ratio > 0.6:
            # High speech content = people talking
            probs['chatter'] = speech_ratio
            probs['music_only'] = 1.0 - speech_ratio
        elif speech_ratio > 0.3:
            # Moderate speech = could be talking or crowd
            probs['chatter'] = speech_ratio * 0.7
            probs['cheering'] = (1.0 - speech_ratio) * 0.5
            probs['applause'] = (1.0 - speech_ratio) * 0.3
        else:
            # Low speech ratio + energy = likely crowd noise or music
            if rms > RMS_MEDIUM and zcr > ZCR_MEDIUM:
                # High energy + high ZCR + low speech = cheering/applause
                energy_factor = min(1.0, rms / RMS_HIGH)
                probs['cheering'] = energy_factor * 0.6
                probs['applause'] = energy_factor * 0.4
            elif rms > RMS_MEDIUM and low_freq_indicator:
                # High energy + very low ZCR = booing/disappointment (crude heuristic)
                probs['booing'] = 0.7
                probs['chatter'] = 0.3
            elif rms > RMS_MEDIUM:
                # High energy but lower ZCR = could be music or crowd
                probs['music_only'] = 0.4
                probs['cheering'] = 0.3
                probs['applause'] = 0.3
            else:
                # Low energy, low speech = background music
                probs['music_only'] = 0.8
                probs['chatter'] = 0.2

        # Ensure non-negativity
        for k in probs:
            probs[k] = max(0.0, probs[k])

    # Normalize to sum to 1
    s = sum(probs.values())
    if s == 0:
        probs['music_only'] = 1.0
    else:
        for k in probs:
            probs[k] /= s

    return probs

@app.route('/classify-audio', methods=['POST'])
def classify_audio():
    temp_path = None
    try:
        logging.info("="*60)
        logging.info("Received classification request")
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        logging.info(f"File received: {audio_file.filename}")
        
        # Save with original extension to handle MP3/WAV correctly
        filename = audio_file.filename or 'audio.wav'
        ext = os.path.splitext(filename)[1]
        temp_path = f'temp{ext}'
        audio_file.save(temp_path)
        logging.info(f"Saved to: {temp_path}")
        
        method_used = 'DSP'  # Default to DSP
        classifier = get_audio_classifier()
        if classifier is not None:
            logging.info("Using HuggingFace classifier")
            try:
                # Load audio using the same multi-fallback loader as DSP
                import numpy as np
                
                logging.info(f"Loading audio file for HF inference...")
                
                # Try soundfile first
                try:
                    import soundfile as sf
                    max_samples = 5 * 44100
                    audio_data, sr = sf.read(temp_path, dtype='float32', frames=max_samples)
                    
                    # Convert to mono if stereo
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    
                    # Resample to 16kHz using simple decimation
                    if sr != 16000:
                        step = int(sr / 16000)
                        audio_data = audio_data[::step]
                        sr = 16000
                    
                    logging.info(f"✓ Loaded with soundfile: {len(audio_data)} samples at {sr} Hz")
                    
                except Exception as sf_err:
                    logging.warning(f"soundfile failed: {sf_err}, trying torchaudio...")
                    
                    # Fallback to torchaudio for MP4/M4A
                    wav, sr = torchaudio.load(temp_path)
                    
                    # Convert to mono
                    if wav.shape[0] > 1:
                        wav = wav.mean(dim=0)
                    else:
                        wav = wav.squeeze(0)
                    
                    # Limit to 5 seconds
                    max_samples = 5 * sr
                    if wav.shape[0] > max_samples:
                        wav = wav[:max_samples]
                    
                    # Resample to 16kHz
                    if sr != 16000:
                        resampler = Resample(orig_freq=sr, new_freq=16000)
                        wav = resampler(wav)
                        sr = 16000
                    
                    audio_data = wav.numpy()
                    logging.info(f"✓ Loaded with torchaudio: {len(audio_data)} samples at {sr} Hz")
                
                # Ensure max 5 seconds at 16kHz (80000 samples)
                if len(audio_data) > 80000:
                    audio_data = audio_data[:80000]
                    logging.info(f"Truncated to {len(audio_data)} samples")
                
                logging.info("Starting inference...")
                preds = classifier(audio_data.astype(np.float32), sampling_rate=sr)
                logging.info("Inference completed successfully")
                probs = aggregate_probs(preds)
                method_used = 'HuggingFace'  # Mark success
                logging.info(f"HF predictions: {probs}")
            except MemoryError as e:
                logging.error(f"HF classifier ran out of memory: {e}, falling back to DSP")
                probs = analyze_audio_dsp(temp_path)
            except Exception as e:
                logging.error(f"HF classifier failed: {e}, falling back to DSP")
                import traceback
                traceback.print_exc()
                probs = analyze_audio_dsp(temp_path)
        else:
            logging.info("Using DSP fallback analysis")
            probs = analyze_audio_dsp(temp_path)
        
        logging.info(f"Final probabilities: {probs}")
        
        enthusiasm_score = calculate_enthusiasm_score(probs)
        SCORE_HISTORY.append(enthusiasm_score)
        if len(SCORE_HISTORY) > WINDOW_SIZE:
            SCORE_HISTORY.pop(0)
        trend = detect_trend()
        
        # Track reaction for current song
        if PARTY_STATE["current_song"] is not None:
            PARTY_STATE["current_song"]["reactions"].append(enthusiasm_score)
        
        result = {
            'probs': probs,
            'enthusiasm_score': round(enthusiasm_score, 2),
            'trend': trend,
            'method': method_used
        }
        logging.info(f"Returning result: {result}")
        logging.info("="*60)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"FATAL ERROR in classify_audio: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logging.info(f"Cleaned up: {temp_path}")
            except Exception as e:
                logging.warning(f"Could not remove temp file: {e}")

# ---------- Gemini Integration Endpoints ----------

@app.route('/gemini-recommend', methods=['POST'])
def gemini_recommend():
    """Get song recommendations from Gemini based on crowd analysis"""
    try:
        if not gemini_model:
            return jsonify({
                'error': 'Gemini API not configured',
                'message': 'Please set GEMINI_API_KEY in .env file'
            }), 503
        
        if not SCORE_HISTORY:
            return jsonify({
                'error': 'No crowd data available',
                'message': 'Please analyze some audio first using /classify-audio'
            }), 400
        
        # Build context from current state
        context = build_gemini_context()
        if not context:
            return jsonify({'error': 'Failed to build context'}), 500
        
        # Call Gemini API
        logging.info("Calling Gemini API for recommendations...")
        recommendation = call_gemini_api(context)
        
        if "error" in recommendation:
            return jsonify(recommendation), 500
        
        # Return full recommendation
        result = {
            'context': context,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        }
        
        logging.info(f"Gemini recommendation generated successfully")
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error in gemini_recommend: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/update-song', methods=['POST'])
def update_song():
    """Update current playing song and track its performance"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # If starting a new song
        if 'song' in data:
            song = data['song']
            PARTY_STATE["current_song"] = {
                "title": song.get("title"),
                "artist": song.get("artist"),
                "genre": song.get("genre"),
                "start_time": datetime.now().isoformat(),
                "reactions": [],
                "predicted_score": song.get("predicted_score")
            }
            logging.info(f"Started tracking: {song.get('title')} by {song.get('artist')}")
            return jsonify({'status': 'Song tracking started', 'song': PARTY_STATE["current_song"]})
        
        # If ending a song (moving to history)
        if data.get('action') == 'end_song':
            if PARTY_STATE["current_song"]:
                current = PARTY_STATE["current_song"]
                
                # Calculate performance metrics
                if current["reactions"]:
                    avg_score = np.mean(current["reactions"])
                    peak_score = np.max(current["reactions"])
                    min_score = np.min(current["reactions"])
                    
                    # Determine outcome
                    if avg_score > 0.6:
                        outcome = "success"
                    elif avg_score > 0.3:
                        outcome = "moderate"
                    else:
                        outcome = "poor"
                    
                    # Calculate prediction accuracy if available
                    prediction_accuracy = None
                    if current.get("predicted_score"):
                        prediction_accuracy = abs(current["predicted_score"] - avg_score)
                    
                    # Add to history
                    song_record = {
                        "title": current["title"],
                        "artist": current["artist"],
                        "genre": current["genre"],
                        "played_at": current["start_time"],
                        "avg_reaction_score": round(float(avg_score), 2),
                        "peak_reaction": round(float(peak_score), 2),
                        "min_reaction": round(float(min_score), 2),
                        "outcome": outcome,
                        "predicted_score": current.get("predicted_score"),
                        "prediction_accuracy": round(float(prediction_accuracy), 2) if prediction_accuracy else None
                    }
                    
                    PARTY_STATE["song_history"].append(song_record)
                    logging.info(f"Song ended: {current['title']} - Outcome: {outcome}, Avg: {avg_score:.2f}")
                    
                    # Reset current song
                    PARTY_STATE["current_song"] = None
                    
                    return jsonify({'status': 'Song ended and added to history', 'song_record': song_record})
                else:
                    return jsonify({'error': 'No reactions recorded for current song'}), 400
            else:
                return jsonify({'error': 'No current song to end'}), 400
        
        return jsonify({'error': 'Invalid action'}), 400
        
    except Exception as e:
        logging.error(f"Error in update_song: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/party-state', methods=['GET'])
def get_party_state():
    """Get current party state and statistics"""
    try:
        if PARTY_STATE["start_time"]:
            elapsed_minutes = (datetime.now() - PARTY_STATE["start_time"]).seconds // 60
        else:
            elapsed_minutes = 0
        
        avg_5min = np.mean(SCORE_HISTORY[-60:]) if len(SCORE_HISTORY) >= 60 else (np.mean(SCORE_HISTORY) if SCORE_HISTORY else 0)
        
        state = {
            "party_active": PARTY_STATE["start_time"] is not None,
            "elapsed_minutes": elapsed_minutes,
            "current_song": PARTY_STATE["current_song"],
            "total_songs_played": len(PARTY_STATE["song_history"]),
            "current_score": round(float(SCORE_HISTORY[-1]), 2) if SCORE_HISTORY else 0.0,
            "current_trend": detect_trend(),
            "party_stage": calculate_party_stage(elapsed_minutes, avg_5min, detect_trend()),
            "avg_score_5min": round(float(avg_5min), 2),
            "total_samples": len(SCORE_HISTORY),
            "song_history": PARTY_STATE["song_history"][-10:],  # Last 10 songs
            "gemini_enabled": gemini_model is not None,
            "last_gemini_call": PARTY_STATE["last_gemini_call"].isoformat() if PARTY_STATE["last_gemini_call"] else None
        }
        
        return jsonify(state)
        
    except Exception as e:
        logging.error(f"Error in get_party_state: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset-party', methods=['POST'])
def reset_party():
    """Reset party state (for testing or new session)"""
    try:
        PARTY_STATE["start_time"] = None
        PARTY_STATE["current_song"] = None
        PARTY_STATE["song_history"] = []
        PARTY_STATE["prediction_tracker"] = []
        PARTY_STATE["last_gemini_call"] = None
        SCORE_HISTORY.clear()
        
        logging.info("Party state reset")
        return jsonify({'status': 'Party state reset successfully'})
        
    except Exception as e:
        logging.error(f"Error in reset_party: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("Starting Flask server on http://127.0.0.1:5000")
    print("=" * 50)
    print("Endpoints:")
    print("  GET  /health              - Health check")
    print("  POST /classify-audio     - Analyze audio crowd reaction")
    print("  POST /gemini-recommend   - Get AI song recommendations")
    print("  POST /update-song        - Update current/end song tracking")
    print("  GET  /party-state        - Get party statistics")
    print("  POST /reset-party        - Reset party session")
    print("=" * 50)
    if gemini_model:
        print("✓ Gemini AI integration ENABLED")
    else:
        print("✗ Gemini AI integration DISABLED (no API key)")
    print("=" * 50)
    app.run(host='127.0.0.1', port=5000, debug=False)
