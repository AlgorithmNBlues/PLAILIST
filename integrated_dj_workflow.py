"""
Integrated AI DJ Workflow - Complete Party Management System

This orchestrates:
1. Fingerprint-based initialization
2. Seed playlist generation
3. Live audio monitoring
4. Gemini AI recommendations
5. Automatic transition between phases
"""

import requests
import time
import json
from datetime import datetime
from playlist_initializer import PlaylistInitializer

# Configuration
FLASK_SERVER = "http://127.0.0.1:5000"
CSV_DIRECTORY = "PLAILIST-dj-attendee-fingerprint"

class IntegratedDJSystem:
    def __init__(self):
        self.initializer = PlaylistInitializer(CSV_DIRECTORY)
        self.phase = "initialization"  # initialization -> seed_playlist -> live_monitoring
        self.songs_played = 0
        self.current_song = None
        
    def check_servers(self):
        """Check if Flask server is running and CSV files are available"""
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
        
        # Check CSV files are available
        import os
        csv_dir = "PLAILIST-dj-attendee-fingerprint"
        csv_files = [
            'spotify_tracks_arin.csv',
            'spotify_tracks_atharva.csv',
            'spotify_tracks_jayanth.csv'
        ]
        
        csv_ok = True
        for csv_file in csv_files:
            filepath = os.path.join(csv_dir, csv_file)
            if os.path.exists(filepath):
                print(f"✅ CSV data: {csv_file} found")
            else:
                print(f"❌ CSV data: {csv_file} NOT FOUND")
                csv_ok = False
        
        print()
        return flask_ok and csv_ok
    
    def initialize_party(self):
        """Phase 1: Initialize using fingerprint data"""
        print("\n" + "="*70)
        print("🎉 PHASE 1: PARTY INITIALIZATION")
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
        
        # Print summary
        self.initializer.print_summary()
        
        # Get seed songs
        self.seed_songs = self.initializer.generate_seed_playlist(5)
        
        # Add seed songs to Flask playlist
        try:
            response = requests.post(
                f"{FLASK_SERVER}/add-to-playlist",
                json={"songs": self.seed_songs}
            )
            if response.status_code == 200:
                print(f"✅ Added {len(self.seed_songs)} seed songs to Flask playlist")
            else:
                print(f"⚠️  Failed to add seed songs to Flask: {response.text}")
        except Exception as e:
            print(f"❌ Error adding seed songs to Flask: {e}")
        
        print(f"✅ Initialization complete! Ready to play {len(self.seed_songs)} seed songs\n")
        self.phase = "seed_playlist"
        return True
    
    def play_seed_song(self, song_index):
        """Phase 2: Play a seed song and track reactions"""
        if song_index >= len(self.seed_songs):
            print("✅ All seed songs played!")
            return False
        
        song = self.seed_songs[song_index]
        self.songs_played += 1
        
        print("\n" + "="*70)
        print(f"🎵 PLAYING SEED SONG #{self.songs_played}")
        print("="*70)
        print(f"Title:   {song['title']}")
        print(f"Artist:  {song['artist']}")
        print(f"Genre:   {song['genre']}")
        print(f"Expected Appeal: {song['expected_appeal']:.1f}%")
        print("="*70 + "\n")
        
        # Start tracking this song
        try:
            response = requests.post(
                f"{FLASK_SERVER}/update-song",
                json={"song": song}
            )
            if response.status_code == 200:
                print("✅ Song tracking started")
                self.current_song = song
            else:
                print(f"⚠️  Failed to start song tracking: {response.text}")
        except Exception as e:
            print(f"❌ Error starting song tracking: {e}")
        
        return True
    
    def end_current_song(self):
        """End the current song and get performance metrics"""
        if not self.current_song:
            return None
        
        try:
            response = requests.post(
                f"{FLASK_SERVER}/update-song",
                json={"action": "end_song"}
            )
            if response.status_code == 200:
                result = response.json()
                song_record = result.get('song_record', {})
                
                print(f"\n📊 Song Performance:")
                print(f"   Average reaction: {song_record.get('avg_reaction_score', 0):.2f}")
                print(f"   Peak reaction: {song_record.get('peak_reaction', 0):.2f}")
                print(f"   Outcome: {song_record.get('outcome', 'unknown').upper()}")
                
                self.current_song = None
                return song_record
            else:
                print(f"⚠️  Failed to end song: {response.text}")
        except Exception as e:
            print(f"❌ Error ending song: {e}")
        
        return None
    
    def get_party_state(self):
        """Get current party state and metrics"""
        try:
            response = requests.get(f"{FLASK_SERVER}/party-state")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"⚠️  Could not get party state: {e}")
        return None
    
    def should_transition_to_live(self):
        """Check if we should transition to live monitoring"""
        state = self.get_party_state()
        if not state:
            return False, "Cannot determine state"
        
        songs_played = state.get('total_songs_played', 0)
        avg_score = state.get('avg_score_5min', 0.0)
        
        return self.initializer.should_transition_to_live(songs_played, avg_score)
    
    def send_audio_for_classification(self, audio_file):
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
                    
                    # Color coding for terminal output
                    if score > 0.6:
                        emoji = "🔥"
                        status = "EXCELLENT"
                    elif score > 0.3:
                        emoji = "✅"
                        status = "GOOD"
                    elif score > 0:
                        emoji = "😐"
                        status = "MODERATE"
                    elif score > -0.5:
                        emoji = "⚠️"
                        status = "LOW"
                    else:
                        emoji = "😞"
                        status = "NEGATIVE"
                    
                    print(f"   {emoji} Score: {score:.2f} ({status}) | Trend: {trend} | Method: {method}")
                    return result
                else:
                    print(f"   ❌ Classification failed: {response.text}")
                    return None
        except Exception as e:
            print(f"   ❌ Error sending audio: {e}")
            return None
    
    def get_gemini_recommendations(self):
        """Get AI recommendations from Gemini"""
        print("\n🤖 Requesting Gemini AI recommendations...")
        
        try:
            response = requests.post(f"{FLASK_SERVER}/gemini-recommend")
            if response.status_code == 200:
                result = response.json()
                recommendation = result.get('recommendation', {})
                
                print("\n" + "="*70)
                print("🎯 GEMINI AI RECOMMENDATIONS")
                print("="*70)
                
                # Analysis
                analysis = recommendation.get('analysis', {})
                print(f"\n📊 Analysis:")
                print(f"   Crowd mood: {analysis.get('crowd_mood', 'N/A')}")
                print(f"   Energy trajectory: {analysis.get('energy_trajectory', 'N/A')}")
                
                # Action
                action = recommendation.get('action', {})
                print(f"\n🎯 Action:")
                print(f"   Recommendation: {action.get('recommendation', 'N/A').upper()}")
                print(f"   Urgency: {action.get('urgency', 'N/A').upper()}")
                print(f"   Confidence: {action.get('confidence', 0)*100:.0f}%")
                
                # Next songs
                next_songs = recommendation.get('next_songs', [])
                print(f"\n🎵 Next {len(next_songs)} Songs:")
                for i, song in enumerate(next_songs, 1):
                    print(f"\n   {i}. {song.get('title', 'Unknown')} by {song.get('artist', 'Unknown')}")
                    print(f"      Genre: {song.get('genre', 'Unknown')}")
                    print(f"      Reasoning: {song.get('reasoning', 'N/A')}")
                    impact = song.get('predicted_impact', {})
                    print(f"      Expected score: {impact.get('expected_score', 'N/A')}")
                
                # Warnings
                warnings = recommendation.get('warnings', [])
                if warnings:
                    print(f"\n⚠️  Warnings:")
                    for warning in warnings:
                        print(f"   • {warning}")
                
                print("\n" + "="*70 + "\n")
                
                return recommendation
            elif response.status_code == 400:
                error_data = response.json()
                print(f"\n❌ Cannot get recommendations yet:")
                print(f"   {error_data.get('message', 'Unknown error')}")
                print(f"   Hint: {error_data.get('hint', 'N/A')}")
                return None
            else:
                print(f"❌ Failed to get recommendations (HTTP {response.status_code}): {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error getting Gemini recommendations: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def run_workflow(self, simulate_reactions=True):
        """Run the complete workflow"""
        print("\n🚀 Starting Integrated AI DJ System...")
        print("="*70 + "\n")
        
        # Check servers
        if not self.check_servers():
            print("\n❌ Not all servers are running. Please start them first.")
            return
        
        # Phase 1: Initialize
        if not self.initialize_party():
            print("❌ Initialization failed")
            return
        
        input("\n⏸️  Press Enter to start playing seed songs...")
        
        # Phase 2: Play seed songs
        # Audio files to use for demo (in root directory)
        audio_files = [
            "crowd-cheer-and-applause-406644.mp3",
            "crowd-disappointment-reaction-352718.mp3"
        ]
        
        for i in range(len(self.seed_songs)):
            if not self.play_seed_song(i):
                break
            
            if simulate_reactions:
                print(f"\n🎧 Analyzing crowd reactions (using demo audio files)...")
                
                # Simulate 3 reactions per song using actual audio files
                for j in range(3):
                    # Alternate between positive and negative reactions
                    audio_file = audio_files[j % len(audio_files)]
                    audio_name = audio_file.split('/')[-1]
                    
                    print(f"\n   📊 Reaction #{j+1}/3 - Using: {audio_name}")
                    result = self.send_audio_for_classification(audio_file)
                    
                    if result:
                        probs = result.get('probs', {})
                        print(f"      Crowd breakdown: ", end="")
                        if probs.get('applause', 0) > 0.5:
                            print("👏 Applause dominant")
                        elif probs.get('cheering', 0) > 0.5:
                            print("📣 Cheering dominant")
                        elif probs.get('booing', 0) > 0.5:
                            print("👎 Disappointment detected")
                        elif probs.get('chatter', 0) > 0.5:
                            print("💬 Crowd chatting")
                        else:
                            print("🎵 Music only")
                    
                    time.sleep(1)  # Brief pause between samples
            else:
                input("\n⏸️  Press Enter when song is finished...")
            
            # End song and get metrics
            song_record = self.end_current_song()
            
            # Check if we should transition
            should_transition, reason = self.should_transition_to_live()
            print(f"\n🔄 Transition check: {reason}")
            
            if should_transition:
                print("\n" + "="*70)
                print("✅ TRANSITIONING TO LIVE AUDIO MONITORING")
                print("="*70)
                self.phase = "live_monitoring"
                break
            
            if i < len(self.seed_songs) - 1:
                input("\n⏸️  Press Enter to play next seed song...")
        
        # Phase 3: Live monitoring with Gemini recommendations
        if self.phase == "live_monitoring":
            input("\n⏸️  Press Enter to get first Gemini recommendation...")
            
            recommendation = self.get_gemini_recommendations()
            
            print("\n💡 From here, the system would:")
            print("   1. Play recommended songs from Gemini")
            print("   2. Continue live audio monitoring (record_live_audio.py)")
            print("   3. Track reactions in real-time")
            print("   4. Request new Gemini recommendations periodically")
            print("   5. Adapt to crowd energy dynamically")
            
            print("\n✅ Workflow demonstration complete!")
            print("\n📝 To run the full live system:")
            print("   1. Keep Flask server running")
            print("   2. Keep fingerprint server running")
            print("   3. Run: python record_live_audio.py")
            print("   4. Monitor crowd reactions in real-time")
            print("   5. Call /gemini-recommend endpoint when needed")


def main():
    system = IntegratedDJSystem()
    
    print("="*70)
    print("🎵 PLAILIST - Integrated AI DJ System")
    print("="*70)
    print("\nThis system combines:")
    print("  • Spotify user fingerprints (group preferences)")
    print("  • Live audio crowd analysis (real-time reactions)")
    print("  • Gemini AI recommendations (intelligent song selection)")
    print("\n" + "="*70)
    
    mode = input("\nChoose mode:\n  1. Full workflow (with demo audio files)\n  2. Manual control\n\nChoice (1 or 2): ").strip()
    
    if mode == "1":
        print("\n📁 Using demo audio files:")
        print("   • crowd-cheer-and-applause-406644.mp3 (positive reactions)")
        print("   • crowd-disappointment-reaction-352718.mp3 (negative reactions)")
        system.run_workflow(simulate_reactions=True)
    else:
        print("\n📝 Manual mode - use these methods:")
        print("  system.check_servers()")
        print("  system.initialize_party()")
        print("  system.play_seed_song(0)")
        print("  system.end_current_song()")
        print("  system.get_gemini_recommendations()")
        print("\nDropping to interactive Python shell...")
        
        import code
        code.interact(local=locals())


if __name__ == "__main__":
    main()
