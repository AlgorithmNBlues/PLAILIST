
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
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

app = Flask(__name__, 
            template_folder='../frontend',
            static_folder='../frontend/static')

# Enable CORS for frontend communication
CORS(app, resources={r"/*": {"origins": "*"}})

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

# Simplified party session tracking
PARTY_STATE = {
    "start_time": None,
    "playlist": [],  # Queue of songs to play
    "last_gemini_call": None,
    "gemini_call_count": 0
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
    """Construct rich context for Gemini API - focused on continuous vibe monitoring"""
    if not SCORE_HISTORY:
        return None
    
    # Initialize party start time if not set
    if PARTY_STATE["start_time"] is None:
        PARTY_STATE["start_time"] = datetime.now()
    
    elapsed_minutes = (datetime.now() - PARTY_STATE["start_time"]).seconds // 60
    current_score = SCORE_HISTORY[-1] if SCORE_HISTORY else 0.0
    current_trend = detect_trend()
    
    # Calculate historical averages - focus on last 90 seconds (6 samples)
    avg_90s = np.mean(SCORE_HISTORY[-6:]) if len(SCORE_HISTORY) >= 6 else current_score
    avg_3min = np.mean(SCORE_HISTORY[-12:]) if len(SCORE_HISTORY) >= 12 else current_score
    avg_5min = np.mean(SCORE_HISTORY[-20:]) if len(SCORE_HISTORY) >= 20 else current_score
    score_variance = np.var(SCORE_HISTORY[-6:]) if len(SCORE_HISTORY) >= 6 else 0.0
    
    party_stage = calculate_party_stage(elapsed_minutes, avg_5min, current_trend)
    
    context = {
        "crowd_state": {
            "enthusiasm_score": round(float(current_score), 2),
            "trend": current_trend,
            "interpretation": interpret_enthusiasm_score(current_score),
            "confidence": "high" if len(SCORE_HISTORY) >= 6 else "low"
        },
        "temporal_context": {
            "score_history_90s": [round(float(s), 2) for s in SCORE_HISTORY[-6:]],
            "avg_score_90s": round(float(avg_90s), 2),
            "avg_score_3min": round(float(avg_3min), 2),
            "avg_score_5min": round(float(avg_5min), 2),
            "score_variance": round(float(score_variance), 3),
            "samples_collected": len(SCORE_HISTORY)
        },
        "party_context": {
            "stage": party_stage,
            "elapsed_minutes": elapsed_minutes,
            "start_time": PARTY_STATE["start_time"].isoformat(),
            "playlist_size": len(PARTY_STATE["playlist"]),
            "current_playlist": PARTY_STATE["playlist"][-5:] if PARTY_STATE["playlist"] else []
        }
    }
    
    return context

def call_gemini_api(context):
    """Query Gemini for song recommendations"""
    if not gemini_model:
        return {"error": "Gemini API not configured"}
    
    try:
        prompt = f"""You are an expert AI DJ assistant analyzing a live party in real-time. The DJ is playing music continuously while analyzing crowd reactions every 30 seconds. You are called every 90 seconds to recommend 2-3 songs to ADD to the playlist queue.

CROWD STATE:
- Current enthusiasm: {context['crowd_state']['enthusiasm_score']:.2f} (scale: -1.5 to +1.0)
- Trend: {context['crowd_state']['trend']}
- Interpretation: {context['crowd_state']['interpretation']}
- Data confidence: {context['crowd_state']['confidence']}

TEMPORAL CONTEXT (Last 90 seconds):
- Score history: {context['temporal_context']['score_history_90s']}
- Average (90s): {context['temporal_context']['avg_score_90s']:.2f}
- Average (3min): {context['temporal_context']['avg_score_3min']:.2f}
- Average (5min): {context['temporal_context']['avg_score_5min']:.2f}
- Score stability (variance): {context['temporal_context']['score_variance']:.3f}

PARTY CONTEXT:
- Stage: {context['party_context']['stage']}
- Time elapsed: {context['party_context']['elapsed_minutes']} minutes
- Playlist queue size: {context['party_context']['playlist_size']}
- Current playlist (last 5 songs): {json.dumps(context['party_context']['current_playlist'], indent=2) if context['party_context']['current_playlist'] else "Empty"}

TASK: Based on the crowd vibe over the last 90 seconds, recommend 2-3 songs to APPEND to the playlist queue. These songs should maintain or improve the party energy flow without disrupting the current momentum.

Provide your response in the following JSON format:
{{
  "analysis": {{
    "crowd_mood": "Brief assessment of current crowd mood and energy",
    "energy_trajectory": "Description of energy trend over last 90 seconds",
    "recommendations_reasoning": "Why these specific songs will work right now"
  }},
  "action": {{
    "recommendation": "maintain_energy | increase_energy | wind_down | change_genre",
    "urgency": "low | normal | high",
    "confidence": 0.0-1.0,
    "songs_to_add": 2 or 3
  }},
  "next_songs": [
    {{
      "title": "Song Name",
      "artist": "Artist Name",
      "genre": "Genre",
      "reasoning": "Why this song fits the current vibe",
      "predicted_impact": {{
        "enthusiasm_delta": "+0.10 to +0.15",
        "expected_score": 0.75
      }},
      "priority": 1
    }}
  ],
  "warnings": ["warning1", "warning2"] (if any concerns about crowd energy),
  "tips": ["tip1", "tip2"] (general DJ advice)
}}

IMPORTANT: 
- Return ONLY valid JSON, no markdown formatting or extra text.
- Recommend 2 songs for normal situations, 3 songs if urgency is high or energy needs boosting.
- Consider the last 5 songs in the playlist to avoid repetition and maintain variety."""

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
        
        # Initialize party start time if not set
        if PARTY_STATE["start_time"] is None:
            PARTY_STATE["start_time"] = datetime.now()
        
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
    """Get song recommendations from Gemini based on crowd analysis (called every 90+ seconds)"""
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
        
        # Check if enough time has passed since last Gemini call (90 seconds minimum)
        if PARTY_STATE["last_gemini_call"]:
            elapsed = (datetime.now() - PARTY_STATE["last_gemini_call"]).total_seconds()
            if elapsed < 90:
                return jsonify({
                    'message': f'Too soon to call Gemini again. Wait {int(90 - elapsed)} more seconds.',
                    'elapsed_seconds': int(elapsed),
                    'required_interval': 90
                }), 429  # Too Many Requests
        
        # Build context from current state
        context = build_gemini_context()
        if not context:
            return jsonify({'error': 'Failed to build context'}), 500
        
        # Call Gemini API
        logging.info(f"Calling Gemini API for recommendations (call #{PARTY_STATE['gemini_call_count'] + 1})...")
        recommendation = call_gemini_api(context)
        
        if "error" in recommendation:
            return jsonify(recommendation), 500
        
        # Update party state
        PARTY_STATE["gemini_call_count"] += 1
        
        # Add recommended songs to playlist queue
        if "next_songs" in recommendation:
            for song in recommendation["next_songs"]:
                PARTY_STATE["playlist"].append({
                    "title": song.get("title"),
                    "artist": song.get("artist"),
                    "genre": song.get("genre"),
                    "added_at": datetime.now().isoformat(),
                    "predicted_score": song.get("predicted_impact", {}).get("expected_score"),
                    "reasoning": song.get("reasoning")
                })
            logging.info(f"Added {len(recommendation['next_songs'])} songs to playlist queue")
        
        # Return full recommendation with updated playlist
        result = {
            'context': context,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat(),
            'gemini_call_count': PARTY_STATE["gemini_call_count"],
            'playlist_size': len(PARTY_STATE["playlist"]),
            'songs_added': len(recommendation.get("next_songs", []))
        }
        
        logging.info(f"Gemini recommendation generated successfully (call #{PARTY_STATE['gemini_call_count']})")
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error in gemini_recommend: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/add-to-playlist', methods=['POST'])
def add_to_playlist():
    """Add songs to the playlist queue (simplified - no per-song tracking)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Expect a list of songs to add
        songs = data.get('songs', [])
        if not songs:
            return jsonify({'error': 'No songs provided'}), 400
        
        added_count = 0
        for song in songs:
            PARTY_STATE["playlist"].append({
                "title": song.get("title"),
                "artist": song.get("artist"),
                "genre": song.get("genre"),
                "added_at": datetime.now().isoformat(),
                "source": song.get("source", "manual")
            })
            added_count += 1
            logging.info(f"Added to playlist: {song.get('title')} by {song.get('artist')}")
        
        return jsonify({
            'status': 'Songs added to playlist',
            'songs_added': added_count,
            'playlist_size': len(PARTY_STATE["playlist"]),
            'playlist': PARTY_STATE["playlist"][-10:]  # Return last 10 songs
        })
        
    except Exception as e:
        logging.error(f"Error in add_to_playlist: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/party-state', methods=['GET'])
def get_party_state():
    """Get current party state and statistics (simplified for continuous monitoring)"""
    try:
        if PARTY_STATE["start_time"]:
            elapsed_minutes = (datetime.now() - PARTY_STATE["start_time"]).seconds // 60
        else:
            elapsed_minutes = 0
        
        # Calculate recent averages
        avg_90s = np.mean(SCORE_HISTORY[-6:]) if len(SCORE_HISTORY) >= 6 else (np.mean(SCORE_HISTORY) if SCORE_HISTORY else 0)
        avg_5min = np.mean(SCORE_HISTORY[-20:]) if len(SCORE_HISTORY) >= 20 else (np.mean(SCORE_HISTORY) if SCORE_HISTORY else 0)
        
        # Calculate time since last Gemini call
        seconds_since_gemini = None
        if PARTY_STATE["last_gemini_call"]:
            seconds_since_gemini = int((datetime.now() - PARTY_STATE["last_gemini_call"]).total_seconds())
        
        state = {
            "party_active": PARTY_STATE["start_time"] is not None,
            "elapsed_minutes": elapsed_minutes,
            "current_score": round(float(SCORE_HISTORY[-1]), 2) if SCORE_HISTORY else 0.0,
            "current_trend": detect_trend(),
            "party_stage": calculate_party_stage(elapsed_minutes, avg_5min, detect_trend()),
            "avg_score_90s": round(float(avg_90s), 2),
            "avg_score_5min": round(float(avg_5min), 2),
            "score_history_90s": [round(float(s), 2) for s in SCORE_HISTORY[-6:]],
            "total_samples": len(SCORE_HISTORY),
            "playlist_size": len(PARTY_STATE["playlist"]),
            "playlist": PARTY_STATE["playlist"][-10:],  # Last 10 songs in queue
            "gemini_call_count": PARTY_STATE["gemini_call_count"],
            "seconds_since_gemini_call": seconds_since_gemini,
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
        PARTY_STATE["playlist"] = []
        PARTY_STATE["last_gemini_call"] = None
        PARTY_STATE["gemini_call_count"] = 0
        SCORE_HISTORY.clear()
        
        logging.info("Party state reset")
        return jsonify({'status': 'Party state reset successfully'})
        
    except Exception as e:
        logging.error(f"Error in reset_party: {e}")
        return jsonify({'error': str(e)}), 500

# ---------- Frontend Routes ----------

@app.route('/')
def session_home():
    """
    Serve the main party session page (home.html) directly - no login needed
    """
    try:
        # Direct file read for faster loading
        import os
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'home.html')
        with open(frontend_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error serving home.html: {e}")
        return f'''
        <!doctype html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error loading Plailist</h1>
            <p>Could not find home.html: {str(e)}</p>
            <p>Template folder: {app.template_folder}</p>
        </body>
        </html>
        ''', 500

@app.route('/session')
def session_alias():
    """Alias for / route - redirect to main page"""
    return session_home()

@app.route('/audio', methods=['POST'])
def process_audio():
    """
    Unified audio processing endpoint for frontend
    
    Flow:
    1. Receive audio from frontend
    2. Call /classify-audio internally
    3. Check if 90s passed, call /gemini-recommend if needed
    4. Return vibe + songs + score to frontend
    """
    try:
        logging.info("Frontend audio request received")
        
        # Get audio data
        audio_bytes = None
        if request.data:
            audio_bytes = request.data
        elif 'file' in request.files:
            f = request.files['file']
            audio_bytes = f.read()
        elif 'audio' in request.files:
            f = request.files['audio']
            audio_bytes = f.read()
        else:
            return jsonify({'error': 'No audio provided'}), 400
        
        # Save audio temporarily and classify
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        try:
            # Classify audio
            with open(tmp_path, 'rb') as f:
                files = {'audio': ('audio.mp3', f, 'audio/mpeg')}
                # Use internal request context to call classify_audio
                from werkzeug.datastructures import FileStorage
                
                # Reopen file for internal call
                with open(tmp_path, 'rb') as audio_file:
                    # Simulate the classify_audio endpoint logic
                    method_used = 'DSP'
                    classifier = get_audio_classifier()
                    
                    if classifier is not None:
                        logging.info("Using HuggingFace classifier")
                        try:
                            import numpy as np
                            import soundfile as sf
                            
                            max_samples = 5 * 44100
                            audio_data, sr = sf.read(tmp_path, dtype='float32', frames=max_samples)
                            
                            if len(audio_data.shape) > 1:
                                audio_data = np.mean(audio_data, axis=1)
                            
                            if sr != 16000:
                                step = int(sr / 16000)
                                audio_data = audio_data[::step]
                                sr = 16000
                            
                            if len(audio_data) > 80000:
                                audio_data = audio_data[:80000]
                            
                            preds = classifier(audio_data.astype(np.float32), sampling_rate=sr)
                            probs = aggregate_probs(preds)
                            method_used = 'HuggingFace'
                        except Exception as e:
                            logging.error(f"HF classifier failed: {e}, falling back to DSP")
                            probs = analyze_audio_dsp(tmp_path)
                    else:
                        logging.info("Using DSP fallback analysis")
                        probs = analyze_audio_dsp(tmp_path)
                    
                    enthusiasm_score = calculate_enthusiasm_score(probs)
                    SCORE_HISTORY.append(enthusiasm_score)
                    if len(SCORE_HISTORY) > WINDOW_SIZE:
                        SCORE_HISTORY.pop(0)
                    trend = detect_trend()
                    
                    if PARTY_STATE["start_time"] is None:
                        PARTY_STATE["start_time"] = datetime.now()
                    
                    classification_result = {
                        'probs': probs,
                        'enthusiasm_score': round(enthusiasm_score, 2),
                        'trend': trend,
                        'method': method_used
                    }
            
            # Check if we should call Gemini (90s interval)
            should_call_gemini = False
            gemini_result = None
            
            if PARTY_STATE["last_gemini_call"]:
                elapsed = (datetime.now() - PARTY_STATE["last_gemini_call"]).total_seconds()
                should_call_gemini = elapsed >= 90
            else:
                should_call_gemini = True  # First call
            
            if should_call_gemini and gemini_model:
                logging.info("Calling Gemini for recommendations...")
                context = build_gemini_context()
                if context:
                    recommendation = call_gemini_api(context)
                    
                    if "error" not in recommendation:
                        PARTY_STATE["gemini_call_count"] += 1
                        
                        # Add songs to playlist
                        if "next_songs" in recommendation:
                            for song in recommendation["next_songs"]:
                                PARTY_STATE["playlist"].append({
                                    "title": song.get("title"),
                                    "artist": song.get("artist"),
                                    "genre": song.get("genre"),
                                    "added_at": datetime.now().isoformat(),
                                    "predicted_score": song.get("predicted_impact", {}).get("expected_score"),
                                    "reasoning": song.get("reasoning")
                                })
                        
                        gemini_result = recommendation
            
            # Map to frontend vibe format
            vibe = "Energetic and Upbeat"  # Default
            if gemini_result and gemini_result.get('action'):
                action = gemini_result['action'].get('recommendation', '')
                if action == "increase_energy":
                    vibe = "Rising Energy"
                elif action == "wind_down":
                    vibe = "Slowing Down"
                elif action == "maintain_energy":
                    if enthusiasm_score > 0.5:
                        vibe = "Energetic and Upbeat"
                    else:
                        vibe = "Calm and Mellow"
            else:
                # Determine vibe from score
                if enthusiasm_score > 0.6:
                    vibe = "Energetic and Upbeat"
                elif enthusiasm_score < 0:
                    vibe = "Calm and Mellow"
                elif trend == "rising":
                    vibe = "Rising Energy"
                elif trend == "falling":
                    vibe = "Slowing Down"
            
            # Prepare response
            response = {
                'vibe': vibe,
                'score': round(enthusiasm_score, 2),
                'trend': trend,
                'method': method_used,
                'gemini_called': gemini_result is not None,
                'songs': []
            }
            
            # Add songs from Gemini if available
            if gemini_result and "next_songs" in gemini_result:
                response['songs'] = [
                    {'title': s.get('title'), 'artist': s.get('artist')}
                    for s in gemini_result['next_songs']
                ]
            
            # Add current playlist
            response['current_playlist'] = [
                {'title': s.get('title'), 'artist': s.get('artist')}
                for s in PARTY_STATE["playlist"][-10:]
            ]
            
            logging.info(f"Frontend response: vibe={vibe}, score={enthusiasm_score:.2f}, songs={len(response['songs'])}")
            return jsonify(response), 200
            
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except Exception as e:
        logging.error(f"Error in /audio endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("🎧 PLAILIST - AI DJ Party System")
    print("=" * 70)
    print("\n🌐 Server starting on http://127.0.0.1:5000\n")
    print("📱 Frontend URL:")
    print("   • Main App:  http://127.0.0.1:5000/")
    print("\n🤖 API Endpoints:")
    print("   • GET  /health              - Health check")
    print("   • POST /classify-audio     - Analyze audio crowd reaction")
    print("   • POST /gemini-recommend   - Get AI song recommendations (90s interval)")
    print("   • POST /audio              - Frontend unified endpoint")
    print("   • POST /add-to-playlist    - Add songs to playlist queue")
    print("   • GET  /party-state        - Get party statistics and playlist")
    print("   • POST /reset-party        - Reset party session")
    print("\n" + "=" * 70)
    if gemini_model:
        print("✅ Gemini AI integration ENABLED")
    else:
        print("⚠️  Gemini AI integration DISABLED (no API key)")
    print("=" * 70)
    print("\n� Architecture:")
    print("   → Frontend calls /audio with recorded audio")
    print("   → Server classifies audio (HuggingFace or DSP)")
    print("   → Every 90s: Gemini recommends 2-3 songs")
    print("   → Vibe meter updates in real-time")
    print("   → Playlist queue grows automatically")
    print("\n" + "=" * 70 + "\n")
    app.run(host='127.0.0.1', port=5000, debug=False)
