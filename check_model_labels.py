"""
Check what labels the HF model predicts for disappointment audio
to see if we're missing important labels in LABEL_MAP
"""
import sys
sys.path.insert(0, 'backend')

from backend.app import get_audio_classifier
import soundfile as sf
import numpy as np

print("Loading classifier...")
classifier = get_audio_classifier()

if classifier is None:
    print("❌ Classifier failed to load")
    sys.exit(1)

print("\n" + "="*60)
print("Analyzing: crowd-disappointment-reaction-352718.mp3")
print("="*60)

# Load audio
audio_data, sr = sf.read("crowd-disappointment-reaction-352718.mp3", dtype='float32')
if len(audio_data.shape) > 1:
    audio_data = np.mean(audio_data, axis=1)
if sr != 16000:
    step = int(sr / 16000)
    audio_data = audio_data[::step]
    sr = 16000

# Get ALL predictions (not just top 10)
preds = classifier(audio_data.astype(np.float32), sampling_rate=sr, top_k=None)

# Sort by score
preds_sorted = sorted(preds, key=lambda x: x['score'], reverse=True)

print("\nTop 20 predictions:")
print("-" * 60)
for i, pred in enumerate(preds_sorted[:20], 1):
    print(f"{i:2d}. {pred['label']:30s} {pred['score']:.4f}")

print("\n" + "="*60)
print("Looking for negative emotion labels...")
print("="*60)

negative_keywords = ['boo', 'gasp', 'grunt', 'groan', 'sigh', 'cry', 'wail', 'scream', 'shout']
for pred in preds_sorted:
    if any(kw in pred['label'].lower() for kw in negative_keywords):
        print(f"  {pred['label']:30s} {pred['score']:.4f}")
