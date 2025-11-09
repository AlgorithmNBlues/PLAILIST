import requests

url = "http://127.0.0.1:5000/classify-audio"

# Test multiple audio files
audio_files = [
    "07065073.wav",
    "crowd-cheer-and-applause-406644.mp3",
    "crowd-disappointment-reaction-352718.mp3"
]

for audio_file in audio_files:
    print(f"\n{'='*60}")
    print(f"Testing: {audio_file}")
    print('='*60)
    try:
        with open(audio_file, 'rb') as f:
            files = {'audio': f}
            response = requests.post(url, files=files)
            print(response.json())
    except FileNotFoundError:
        print(f"Error: File '{audio_file}' not found")
    except Exception as e:
        print(f"Error: {e}")
