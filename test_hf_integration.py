"""
Quick test to verify HF model integration in Flask app context
"""
import sys
sys.path.insert(0, 'backend')

# Import the app module
from backend.app import get_audio_classifier, aggregate_probs, calculate_enthusiasm_score
import soundfile as sf
import numpy as np

print("="*60)
print("Testing HF Integration")
print("="*60)

# Test 1: Load classifier
print("\n1. Loading classifier...")
classifier = get_audio_classifier()
if classifier is None:
    print("✗ Classifier failed to load")
    sys.exit(1)
print("✓ Classifier loaded")

# Test 2: Process test files
test_files = [
    ("crowd-cheer-and-applause-406644.mp3", "Cheering/Applause"),
    ("crowd-disappointment-reaction-352718.mp3", "Disappointment")
]

for filename, expected_type in test_files:
    print(f"\n2. Processing {filename} ({expected_type})...")
    try:
        # Load audio
        max_samples = 30 * 44100
        audio_data, sr = sf.read(filename, dtype='float32', frames=max_samples)
        
        # Convert to mono
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Resample to 16kHz
        if sr != 16000:
            step = int(sr / 16000)
            audio_data = audio_data[::step]
            sr = 16000
        
        # Run inference
        preds = classifier(audio_data.astype(np.float32), sampling_rate=sr)
        probs = aggregate_probs(preds)
        score = calculate_enthusiasm_score(probs)
        
        print(f"   Probabilities: {probs}")
        print(f"   Enthusiasm Score: {score:.2f}")
        print(f"   ✓ Processed successfully")
        
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Integration test complete")
print("="*60)
