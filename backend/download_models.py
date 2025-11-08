"""
Script to pre-download all required models while internet is available.
Run this once with a stable network connection.
"""

import os
import sys

print("="*60)
print("Pre-downloading models for offline use")
print("="*60)

# Set environment for better caching
os.environ["TRANSFORMERS_CACHE"] = os.path.expanduser("~/.cache/huggingface")
os.environ["HF_HOME"] = os.path.expanduser("~/.cache/huggingface")

print("\n1. Downloading HuggingFace AudioSet model...")
try:
    from transformers import pipeline
    classifier = pipeline(
        'audio-classification',
        model='MIT/ast-finetuned-audioset-10-10-0.4593'
    )
    print("✓ AudioSet model downloaded successfully")
except Exception as e:
    print(f"✗ Failed to download AudioSet model: {e}")
    sys.exit(1)

print("\n2. Downloading Silero VAD model...")
try:
    import torch
    model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad', trust_repo=True)
    print("✓ Silero VAD model downloaded successfully")
except Exception as e:
    print(f"✗ Failed to download Silero VAD: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("All models downloaded successfully!")
print("You can now run the Flask app offline.")
print("="*60)
