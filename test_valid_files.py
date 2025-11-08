"""
Test with only valid audio files (skipping corrupted arin.mp3)
"""
import requests
import json

SERVER_URL = "http://127.0.0.1:5000/classify-audio"

test_files = [
    "07065073.wav",
    "crowd-cheer-and-applause-406644.mp3",
    "crowd-disappointment-reaction-352718.mp3"
]

for filename in test_files:
    print("\n" + "="*60)
    print(f"Testing: {filename}")
    print("="*60)
    
    try:
        with open(filename, 'rb') as f:
            files = {'audio': (filename, f, 'audio/mpeg' if filename.endswith('.mp3') else 'audio/wav')}
            response = requests.post(SERVER_URL, files=files, timeout=30)
            result = response.json()
            print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*60)
print("Note: arin.mp3 is corrupted (incomplete MP4 file, only 47KB)")
print("It has invalid headers and cannot be decoded by any audio library")
print("="*60)
