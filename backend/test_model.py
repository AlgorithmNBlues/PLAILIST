"""
Test script to verify HuggingFace model can load and run inference.
This isolates whether the issue is with model loading or Flask environment.
"""

import os
import sys
import traceback

# Set offline mode
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

print("="*60)
print("Testing HuggingFace Model Load & Inference")
print("="*60)

print("\n1. Testing model loading...")
try:
    from transformers import pipeline
    import torch
    
    print(f"   PyTorch version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    
    classifier = pipeline(
        "audio-classification",
        model="MIT/ast-finetuned-audioset-10-10-0.4593",
        device=0 if torch.cuda.is_available() else -1,
        top_k=10,
        local_files_only=True
    )
    print("✓ Model loaded successfully")
except Exception as e:
    print(f"✗ Model loading failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n2. Loading audio file...")
test_file = "07065073.wav"
if not os.path.exists(test_file):
    print(f"✗ Test file {test_file} not found")
    sys.exit(1)

try:
    import soundfile as sf
    import numpy as np
    
    # Load only first 30 seconds to avoid memory issues
    max_samples = 30 * 44100  # 30 seconds at 44.1kHz
    audio_data, sr = sf.read(test_file, frames=max_samples)
    print(f"   Loaded {len(audio_data)} samples at {sr} Hz")
    
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Resample to 16kHz if needed using simple decimation
    if sr != 16000:
        step = int(sr / 16000)
        audio_data = audio_data[::step]
        sr = 16000
        print(f"   Resampled to {sr} Hz ({len(audio_data)} samples)")
    
    print("\n3. Testing inference...")
    predictions = classifier(audio_data.astype(np.float32), sampling_rate=sr)
    print("✓ Inference successful")
    print(f"\nTop predictions:")
    for pred in predictions[:5]:
        print(f"  {pred['label']}: {pred['score']:.3f}")
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("All tests passed! Model is working correctly.")
print("="*60)
