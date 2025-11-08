"""
Test client - testing with smaller files first
"""
import requests

SERVER_URL = 'http://127.0.0.1:5000'

# Test with small MP3 files first
audio_files = [
    'crowd-cheer-and-applause-406644.mp3',
    'crowd-disappointment-reaction-352718.mp3',
]

for audio_file in audio_files:
    print("\n" + "="*60)
    print(f"Testing: {audio_file}")
    print("="*60)
    
    try:
        with open(audio_file, 'rb') as f:
            files = {'audio': (audio_file, f, 'audio/mpeg')}
            response = requests.post(f'{SERVER_URL}/classify-audio', files=files, timeout=30)
            
        if response.status_code == 200:
            result = response.json()
            print(f"Probabilities: {result['probs']}")
            print(f"Enthusiasm Score: {result['enthusiasm_score']}")
            print(f"Trend: {result['trend']}")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
