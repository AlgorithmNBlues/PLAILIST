"""
Integrated AI DJ Workflow v2 - Continuous Vibe Monitoring

Simplified architecture:
1. Initialize party with seed songs → add to playlist
2. Start continuous loop:
   - Analyze audio every 30 seconds
   - Call Gemini every 90 seconds to append songs
   - Display current vibe and playlist
"""

import requests
import time
import os
from datetime import datetime
from playlist_initializer import PlaylistInitializer

# Configuration
FLASK_SERVER = "http://127.0.0.1:5000"
CSV_DIRECTORY = "PLAILIST-dj-attendee-fingerprint"
AUDIO_INTERVAL = 30  # Analyze audio every 30 seconds
GEMINI_INTERVAL = 90  # Call Gemini every 90 seconds

# Demo audio files for testing
DEMO_AUDIO_FILES = [
    "crowd-cheer-and-applause-406644.mp3",
    "crowd-disappointment-reaction-352718.mp3"
]

class ContinuousDJSystem:
    def __init__(self):
        self.initializer = PlaylistInitializer(CSV_DIRECTORY)
        self.last_gemini_call = None
        self.audio_file_index = 0
        
    def check_servers(self):
        """Check if Flask server is running and demo audio files exist"""
        print("🔍 Checking system status...")
        
        # Check Flask server
        try:
            response = requests.get(f"{FLASK_SERVER}/health", timeout=3)
            if response.status_code == 200:
                print("✅ Flask AI DJ server: RUNNING")
                flask_ok = True
            else:
                print(f"⚠️  Flask server returned status {response.status_code}")
                flask_ok = False
        except:
            print("❌ Flask server: NOT RUNNING")
            print("   Start with: python backend/app.py")
            flask_ok = False
        
        # Check CSV files
        csv_ok = True
        for csv_file in ['spotify_tracks_arin.csv', 'spotify_tracks_atharva.csv', 'spotify_tracks_jayanth.csv']:
            filepath = os.path.join(CSV_DIRECTORY, csv_file)
            if os.path.exists(filepath):
                print(f"✅ CSV data: {csv_file} found")
            else:
                print(f"❌ CSV data: {csv_file} NOT FOUND")
                csv_ok = False
        
        # Check demo audio files
        audio_ok = True
        for audio_file in DEMO_AUDIO_FILES:
            if os.path.exists(audio_file):
                print(f"✅ Demo audio: {audio_file} found")
            else:
                print(f"❌ Demo audio: {audio_file} NOT FOUND")
                audio_ok = False
        
        print()
        return flask_ok and csv_ok and audio_ok
    
    def initialize_party(self):
        """Initialize party with fingerprint data and seed songs"""
        print("\n" + "="*70)
        print("🎉 INITIALIZING PARTY")
        print("="*70 + "\n")
        
        # Reset party state
        try:
            response = requests.post(f"{FLASK_SERVER}/reset-party")
            if response.status_code == 200:
                print("✅ Party state reset")
        except Exception as e:
            print(f"⚠️  Could not reset party state: {e}")
        
        # Fetch and analyze fingerprints
        print("📡 Fetching user fingerprints...")
        data = self.initializer.fetch_fingerprints()
        if not data:
            print("❌ Failed to fetch fingerprints")
            return False
        
        print("\n📊 Analyzing group preferences...")
        self.initializer.analyze_group_preferences()
        self.initializer.print_summary()
        
        # Generate seed playlist
        seed_songs = self.initializer.generate_seed_playlist(5)
        
        # Add seed songs to playlist
        print(f"\n📝 Adding {len(seed_songs)} seed songs to playlist...")
        try:
            # Format songs for the API
            formatted_songs = []
            for song in seed_songs:
                formatted_songs.append({
                    "title": song["title"],
                    "artist": song["artist"],
                    "genre": song["genre"],
                    "source": "seed"
                })
            
            response = requests.post(
                f"{FLASK_SERVER}/add-to-playlist",
                json={"songs": formatted_songs}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Added {result['songs_added']} songs to playlist")
                print(f"   Playlist size: {result['playlist_size']}")
            else:
                print(f"⚠️  Failed to add songs: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding songs to playlist: {e}")
            return False
        
        print("\n✅ Initialization complete! Starting continuous monitoring...\n")
        return True
    
    def get_next_demo_audio(self):
        """Get next demo audio file (rotate between applause and disappointment)"""
        audio_file = DEMO_AUDIO_FILES[self.audio_file_index % len(DEMO_AUDIO_FILES)]
        self.audio_file_index += 1
        return audio_file
    
    def analyze_audio(self, audio_file):
        """Send audio file to Flask for classification"""
        try:
            with open(audio_file, 'rb') as f:
                files = {'audio': (audio_file, f, 'audio/mpeg')}
                response = requests.post(f"{FLASK_SERVER}/classify-audio", files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    score = result.get('enthusiasm_score', 0)
                    trend = result.get('trend', 'unknown')
                    method = result.get('method', 'unknown')
                    
                    # Determine audio type from filename
                    if "cheer" in audio_file or "applause" in audio_file:
                        audio_type = "👏 Applause"
                    else:
                        audio_type = "👎 Disappointment"
                    
                    # Color coding for terminal output
                    if score > 0.6:
                        emoji = "🔥"
                        status = "EXCELLENT"
                        color = "\033[92m"  # Green
                    elif score > 0.3:
                        emoji = "✅"
                        status = "GOOD"
                        color = "\033[92m"
                    elif score > 0:
                        emoji = "😐"
                        status = "MODERATE"
                        color = "\033[93m"  # Yellow
                    elif score > -0.5:
                        emoji = "⚠️"
                        status = "LOW"
                        color = "\033[93m"
                    else:
                        emoji = "😞"
                        status = "NEGATIVE"
                        color = "\033[91m"  # Red
                    
                    reset_color = "\033[0m"
                    
                    print(f"   {audio_type} → {color}{emoji} Score: {score:.2f} ({status}){reset_color} | Trend: {trend}")
                    return result
                else:
                    print(f"   ❌ Classification failed: {response.text}")
                    return None
        except Exception as e:
            print(f"   ❌ Error analyzing audio: {e}")
            return None
    
    def call_gemini(self):
        """Request Gemini recommendations (respects 90s interval)"""
        try:
            response = requests.post(f"{FLASK_SERVER}/gemini-recommend")
            
            if response.status_code == 200:
                result = response.json()
                recommendation = result.get('recommendation', {})
                
                print("\n" + "="*70)
                print(f"🤖 GEMINI AI RECOMMENDATIONS (Call #{result['gemini_call_count']})")
                print("="*70)
                
                # Analysis
                analysis = recommendation.get('analysis', {})
                print(f"\n📊 Crowd Analysis:")
                print(f"   Mood: {analysis.get('crowd_mood', 'N/A')}")
                print(f"   Trajectory: {analysis.get('energy_trajectory', 'N/A')}")
                
                # Action
                action = recommendation.get('action', {})
                print(f"\n🎯 DJ Action:")
                print(f"   Strategy: {action.get('recommendation', 'N/A').upper()}")
                print(f"   Urgency: {action.get('urgency', 'N/A').upper()}")
                print(f"   Songs to add: {action.get('songs_to_add', 2)}")
                
                # Recommended songs
                next_songs = recommendation.get('next_songs', [])
                print(f"\n🎵 Songs Added to Playlist ({len(next_songs)}):")
                for i, song in enumerate(next_songs, 1):
                    print(f"   {i}. {song.get('title')} - {song.get('artist')} ({song.get('genre')})")
                    print(f"      → {song.get('reasoning', 'N/A')}")
                
                # Warnings and tips
                warnings = recommendation.get('warnings', [])
                if warnings:
                    print(f"\n⚠️  Warnings:")
                    for warning in warnings:
                        print(f"   - {warning}")
                
                tips = recommendation.get('tips', [])
                if tips:
                    print(f"\n💡 Tips:")
                    for tip in tips:
                        print(f"   - {tip}")
                
                print("="*70 + "\n")
                
                self.last_gemini_call = time.time()
                return result
                
            elif response.status_code == 429:
                # Too soon to call again
                result = response.json()
                print(f"   ⏳ Too soon for Gemini (wait {result.get('required_interval', 90) - result.get('elapsed_seconds', 0)}s)")
                return None
            else:
                print(f"   ❌ Gemini call failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error calling Gemini: {e}")
            return None
    
    def display_party_state(self):
        """Display current party state"""
        try:
            response = requests.get(f"{FLASK_SERVER}/party-state")
            if response.status_code == 200:
                state = response.json()
                
                print(f"\n📊 PARTY STATE:")
                print(f"   Elapsed: {state.get('elapsed_minutes', 0)} minutes")
                print(f"   Stage: {state.get('party_stage', 'unknown').upper()}")
                print(f"   Current Score: {state.get('current_score', 0):.2f}")
                print(f"   Trend: {state.get('current_trend', 'unknown').upper()}")
                print(f"   Avg (90s): {state.get('avg_score_90s', 0):.2f}")
                print(f"   Recent Scores: {state.get('score_history_90s', [])}")
                print(f"   Playlist Size: {state.get('playlist_size', 0)} songs")
                print(f"   Gemini Calls: {state.get('gemini_call_count', 0)}")
                
                # Show last few playlist entries
                playlist = state.get('playlist', [])
                if playlist:
                    print(f"\n🎵 Current Playlist Queue (last 5):")
                    for song in playlist[-5:]:
                        print(f"   - {song.get('title')} - {song.get('artist')}")
                
                print()
                return state
        except Exception as e:
            print(f"   ⚠️  Could not get party state: {e}")
        return None
    
    def run_continuous_monitoring(self):
        """Main continuous monitoring loop"""
        print("\n" + "="*70)
        print("🎧 CONTINUOUS VIBE MONITORING ACTIVE")
        print("="*70)
        print(f"📡 Analyzing audio every {AUDIO_INTERVAL} seconds")
        print(f"🤖 Gemini recommendations every {GEMINI_INTERVAL} seconds")
        print("Press Ctrl+C to stop\n")
        
        loop_count = 0
        start_time = time.time()
        
        try:
            while True:
                loop_count += 1
                elapsed = time.time() - start_time
                
                print(f"\n{'─'*70}")
                print(f"🔄 MONITORING CYCLE #{loop_count} (t={int(elapsed)}s)")
                print(f"{'─'*70}")
                
                # 1. Analyze audio
                audio_file = self.get_next_demo_audio()
                print(f"🎤 Analyzing audio: {audio_file}")
                self.analyze_audio(audio_file)
                
                # 2. Check if time to call Gemini (every 90 seconds)
                if self.last_gemini_call is None or (time.time() - self.last_gemini_call) >= GEMINI_INTERVAL:
                    print("\n🤖 Time for Gemini recommendations!")
                    self.call_gemini()
                else:
                    time_until_gemini = int(GEMINI_INTERVAL - (time.time() - self.last_gemini_call))
                    print(f"   ⏳ Next Gemini call in {time_until_gemini}s")
                
                # 3. Display current state
                self.display_party_state()
                
                # Wait for next cycle
                print(f"\n⏸️  Waiting {AUDIO_INTERVAL} seconds until next analysis...")
                time.sleep(AUDIO_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping continuous monitoring...")
            print("✅ Session complete!\n")
    
    def run(self):
        """Main workflow: initialization + continuous monitoring"""
        # Check prerequisites
        if not self.check_servers():
            print("❌ Prerequisites not met. Please fix the issues above.")
            return
        
        # Initialize party
        if not self.initialize_party():
            print("❌ Initialization failed")
            return
        
        # Start continuous monitoring
        self.run_continuous_monitoring()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎧 AI DJ - CONTINUOUS VIBE MONITORING SYSTEM v2")
    print("="*70)
    
    dj = ContinuousDJSystem()
    dj.run()
