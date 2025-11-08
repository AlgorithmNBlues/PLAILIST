"""
Test Gemini Integration - Simulates a party with crowd reactions
"""
import requests
import json
import time

SERVER_URL = "http://127.0.0.1:5000"

def test_audio(filename):
    """Analyze an audio file"""
    with open(filename, 'rb') as f:
        files = {'audio': (filename, f, 'audio/mpeg' if filename.endswith('.mp3') else 'audio/wav')}
        response = requests.post(f"{SERVER_URL}/classify-audio", files=files, timeout=30)
        return response.json()

def get_gemini_recommendation():
    """Get song recommendations from Gemini"""
    response = requests.post(f"{SERVER_URL}/gemini-recommend", timeout=30)
    return response.json()

def start_song(title, artist, genre, predicted_score=None):
    """Start tracking a new song"""
    data = {
        "song": {
            "title": title,
            "artist": artist,
            "genre": genre,
            "predicted_score": predicted_score
        }
    }
    response = requests.post(f"{SERVER_URL}/update-song", json=data)
    return response.json()

def end_song():
    """End current song and move to history"""
    data = {"action": "end_song"}
    response = requests.post(f"{SERVER_URL}/update-song", json=data)
    return response.json()

def get_party_state():
    """Get current party state"""
    response = requests.get(f"{SERVER_URL}/party-state")
    return response.json()

def reset_party():
    """Reset party state"""
    response = requests.post(f"{SERVER_URL}/reset-party")
    return response.json()

print("="*70)
print("🎵 AI DJ ASSISTANT - GEMINI INTEGRATION TEST")
print("="*70)

# Reset to clean state
print("\n1. Resetting party state...")
result = reset_party()
print(f"   ✓ {result['status']}")

# Simulate Song 1: High energy track
print("\n2. Starting Song 1: 'Energy Boost' by DJ Awesome (Electronic)")
start_song("Energy Boost", "DJ Awesome", "Electronic", predicted_score=0.70)

print("   Simulating crowd reactions (analyzing audio samples)...")
test_files = [
    "crowd-cheer-and-applause-406644.mp3",
    "crowd-cheer-and-applause-406644.mp3",  # Play twice for more data
]

for i, filename in enumerate(test_files, 1):
    print(f"   [{i}/{len(test_files)}] Analyzing {filename}...")
    result = test_audio(filename)
    print(f"       Score: {result['enthusiasm_score']:.2f}, Trend: {result['trend']}")
    time.sleep(1)

print("   Ending song...")
song_result = end_song()
print(f"   ✓ Song outcome: {song_result['song_record']['outcome']}")
print(f"     Avg score: {song_result['song_record']['avg_reaction_score']}")

# Simulate Song 2: Moderate track
print("\n3. Starting Song 2: 'Chill Vibes' by Artist B (Pop)")
start_song("Chill Vibes", "Artist B", "Pop", predicted_score=0.40)

print("   Simulating mixed reactions...")
result = test_audio("07065073.wav")  # Chatter
print(f"   Score: {result['enthusiasm_score']:.2f}, Trend: {result['trend']}")
time.sleep(1)

end_song()

# Simulate Song 3: Bad choice
print("\n4. Starting Song 3: 'Wrong Choice' by Artist C (Rock)")
start_song("Wrong Choice", "Artist C", "Rock", predicted_score=0.60)

print("   Simulating negative reaction...")
result = test_audio("crowd-disappointment-reaction-352718.mp3")
print(f"   Score: {result['enthusiasm_score']:.2f}, Trend: {result['trend']}")
time.sleep(1)

end_song()

# Get party state
print("\n5. Current party state:")
state = get_party_state()
print(f"   Party stage: {state['party_stage']}")
print(f"   Elapsed time: {state['elapsed_minutes']} minutes")
print(f"   Songs played: {state['total_songs_played']}")
print(f"   Current score: {state['current_score']}")
print(f"   Current trend: {state['current_trend']}")
print(f"   5-min average: {state['avg_score_5min']}")

# Call Gemini for recommendations
print("\n6. 🤖 Asking Gemini AI for song recommendations...")
print("   (This may take a few seconds...)")

try:
    recommendation = get_gemini_recommendation()
    
    if 'error' in recommendation:
        print(f"   ✗ Error: {recommendation['error']}")
        if 'message' in recommendation:
            print(f"     {recommendation['message']}")
    else:
        print("\n" + "="*70)
        print("🎯 GEMINI RECOMMENDATIONS")
        print("="*70)
        
        analysis = recommendation['recommendation']['analysis']
        print(f"\n📊 CROWD ANALYSIS:")
        print(f"   Mood: {analysis['crowd_mood']}")
        print(f"   Energy: {analysis['energy_trajectory']}")
        print(f"   Reasoning: {analysis['recommendations_reasoning']}")
        
        action = recommendation['recommendation']['action']
        print(f"\n🎬 RECOMMENDED ACTION:")
        print(f"   Strategy: {action['recommendation']}")
        print(f"   Urgency: {action['urgency']}")
        print(f"   Confidence: {action['confidence']:.0%}")
        
        print(f"\n🎵 NEXT SONGS:")
        for song in recommendation['recommendation']['next_songs']:
            print(f"\n   {song['priority']}. {song['title']} by {song['artist']}")
            print(f"      Genre: {song['genre']}")
            print(f"      Why: {song['reasoning']}")
            print(f"      Expected impact: {song['predicted_impact']['enthusiasm_delta']}")
            print(f"      Expected score: {song['predicted_impact']['expected_score']}")
        
        if recommendation['recommendation'].get('warnings'):
            print(f"\n⚠️  WARNINGS:")
            for warning in recommendation['recommendation']['warnings']:
                print(f"   - {warning}")
        
        if recommendation['recommendation'].get('tips'):
            print(f"\n💡 TIPS:")
            for tip in recommendation['recommendation']['tips']:
                print(f"   - {tip}")

except Exception as e:
    print(f"   ✗ Error calling Gemini: {e}")

print("\n" + "="*70)
print("✓ Test complete!")
print("="*70)

# Final state
print("\nFinal song history:")
state = get_party_state()
for i, song in enumerate(state['song_history'], 1):
    print(f"{i}. {song['title']} - {song['outcome']} (avg: {song['avg_reaction_score']})")
