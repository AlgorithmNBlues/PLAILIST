"""
Playlist Initializer - Integrates Spotify Fingerprint Data with AI DJ System

This module:
1. Loads user fingerprint data from CSV files
2. Analyzes group preferences (common genres, artists, languages)
3. Generates initial playlist seed songs
4. Transitions to live audio analysis after warm-up period
"""

import csv
import os
import logging
from collections import Counter
from typing import Dict, List, Any
import re

logging.basicConfig(level=logging.INFO)

class PlaylistInitializer:
    def __init__(self, csv_directory="PLAILIST-dj-attendee-fingerprint"):
        self.csv_directory = csv_directory
        self.fingerprints = None
        self.group_profile = None
        self.raw_tracks = []
    
    def _detect_language(self, text):
        """Detect language from text"""
        if not text:
            return 'unknown'
        
        if re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]', text):
            return 'japanese/chinese'
        if re.search(r'[\u0600-\u06ff]', text):
            return 'arabic'
        if re.search(r'[\u0400-\u04ff]', text):
            return 'russian'
        if re.search(r'[\u0900-\u097f]', text):
            return 'hindi'
        if re.search(r'[\uac00-\ud7af]', text):
            return 'korean'
        if re.search(r'\b(el|la|los|las|de|del|y|con|por|para)\b', text, re.IGNORECASE):
            return 'spanish'
        if re.search(r'\b(le|la|les|de|du|et|avec|pour)\b', text, re.IGNORECASE):
            return 'french'
        if re.search(r'\b(der|die|das|und|mit|von)\b', text, re.IGNORECASE):
            return 'german'
        if re.search(r'\b(o|a|os|as|de|do|da|e|com)\b', text, re.IGNORECASE):
            return 'portuguese'
        
        return 'english'
    
    def fetch_fingerprints(self) -> Dict[str, Any]:
        """Load user fingerprints from CSV files"""
        try:
            csv_files = [
                'spotify_tracks_arin.csv',
                'spotify_tracks_atharva.csv',
                'spotify_tracks_jayanth.csv'
            ]
            
            user_data = {}
            total_tracks = 0
            
            for csv_file in csv_files:
                filepath = os.path.join(self.csv_directory, csv_file)
                
                if not os.path.exists(filepath):
                    logging.warning(f"⚠️  File not found: {filepath}")
                    continue
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    tracks = list(reader)
                    
                    if not tracks:
                        continue
                    
                    user_id = tracks[0]['user_id']
                    user_name = tracks[0]['user_name']
                    
                    if user_id not in user_data:
                        user_data[user_id] = {
                            'user_id': user_id,
                            'user_name': user_name,
                            'tracks': []
                        }
                    
                    user_data[user_id]['tracks'].extend(tracks)
                    total_tracks += len(tracks)
                    self.raw_tracks.extend(tracks)
                    
                    logging.info(f"✓ Loaded {len(tracks)} tracks from {csv_file} ({user_name})")
            
            # Build fingerprints for each user
            self.fingerprints = []
            for user_id, data in user_data.items():
                fingerprint = self._build_user_fingerprint(data)
                self.fingerprints.append(fingerprint)
            
            logging.info(f"✓ Loaded fingerprints for {len(self.fingerprints)} users ({total_tracks} total tracks)")
            
            return {
                'total_users': len(self.fingerprints),
                'fingerprints': self.fingerprints
            }
            
        except Exception as e:
            logging.error(f"✗ Error loading CSV files: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_user_fingerprint(self, user_data: Dict) -> Dict[str, Any]:
        """Build fingerprint for a single user"""
        tracks = user_data['tracks']
        
        # Count genres
        genre_counter = Counter()
        for track in tracks:
            genres = track.get('genres', '').split(';')
            for genre in genres:
                genre = genre.strip()
                if genre:
                    genre_counter[genre] += 1
        
        # Count artists
        artist_counter = Counter()
        for track in tracks:
            artists = track.get('artist_names', '').split(';')
            for artist in artists:
                artist = artist.strip()
                if artist:
                    artist_counter[artist] += 1
        
        # Count languages
        language_counter = Counter()
        for track in tracks:
            track_name = track.get('track_name', '')
            artist_names = track.get('artist_names', '')
            lang = self._detect_language(track_name + ' ' + artist_names)
            language_counter[lang] += 1
        
        # Calculate average popularity
        popularities = [int(track.get('popularity', 0)) for track in tracks if track.get('popularity')]
        avg_popularity = sum(popularities) / len(popularities) if popularities else 0
        
        # Build top lists
        total_genres = sum(genre_counter.values())
        top_genres = [
            {
                'genre': genre,
                'count': count,
                'percentage': round(count / total_genres * 100, 2) if total_genres > 0 else 0
            }
            for genre, count in genre_counter.most_common(10)
        ]
        
        total_artists = sum(artist_counter.values())
        top_artists = [
            {
                'artist': artist,
                'count': count,
                'percentage': round(count / total_artists * 100, 2) if total_artists > 0 else 0
            }
            for artist, count in artist_counter.most_common(10)
        ]
        
        total_languages = sum(language_counter.values())
        top_languages = [
            {
                'language': lang,
                'count': count,
                'percentage': round(count / total_languages * 100, 2) if total_languages > 0 else 0
            }
            for lang, count in language_counter.most_common(5)
        ]
        
        return {
            'user_id': user_data['user_id'],
            'user_name': user_data['user_name'],
            'total_tracks': len(tracks),
            'top_genres': top_genres,
            'top_artists': top_artists,
            'top_languages': top_languages,
            'average_popularity': round(avg_popularity, 2),
            'unique_genres': len(genre_counter),
            'unique_artists': len(artist_counter)
        }
    
    def analyze_group_preferences(self) -> Dict[str, Any]:
        """Analyze combined preferences across all users"""
        if not self.fingerprints:
            logging.warning("No fingerprints available. Call fetch_fingerprints() first.")
            return None
        
        # Aggregate genres across all users
        all_genres = []
        for fp in self.fingerprints:
            for genre in fp.get('top_genres', []):
                all_genres.extend([genre['genre']] * genre['count'])
        
        # Aggregate artists across all users
        all_artists = []
        for fp in self.fingerprints:
            for artist in fp.get('top_artists', []):
                all_artists.extend([artist['artist']] * artist['count'])
        
        # Aggregate languages
        all_languages = []
        for fp in self.fingerprints:
            for lang in fp.get('top_languages', []):
                all_languages.extend([lang['language']] * lang['count'])
        
        # Calculate consensus metrics
        genre_counter = Counter(all_genres)
        artist_counter = Counter(all_artists)
        language_counter = Counter(all_languages)
        
        # Get average popularity
        avg_popularity = sum([fp.get('average_popularity', 0) for fp in self.fingerprints]) / len(self.fingerprints)
        
        # Calculate diversity score (higher = more diverse tastes)
        total_unique_genres = sum([fp.get('unique_genres', 0) for fp in self.fingerprints])
        total_tracks = sum([fp.get('total_tracks', 0) for fp in self.fingerprints])
        diversity_score = total_unique_genres / total_tracks if total_tracks > 0 else 0
        
        self.group_profile = {
            "total_users": len(self.fingerprints),
            "total_tracks": total_tracks,
            "top_genres": [
                {"genre": genre, "count": count, "percentage": round(count / len(all_genres) * 100, 2)}
                for genre, count in genre_counter.most_common(10)
            ],
            "top_artists": [
                {"artist": artist, "count": count, "percentage": round(count / len(all_artists) * 100, 2)}
                for artist, count in artist_counter.most_common(10)
            ],
            "top_languages": [
                {"language": lang, "count": count, "percentage": round(count / len(all_languages) * 100, 2)}
                for lang, count in language_counter.most_common(5)
            ],
            "average_popularity": round(avg_popularity, 2),
            "diversity_score": round(diversity_score, 3),
            "user_profiles": self.fingerprints
        }
        
        logging.info(f"✓ Group profile created: {total_tracks} tracks from {len(self.fingerprints)} users")
        logging.info(f"  Top 3 genres: {[g['genre'] for g in self.group_profile['top_genres'][:3]]}")
        logging.info(f"  Top 3 artists: {[a['artist'] for a in self.group_profile['top_artists'][:3]]}")
        logging.info(f"  Diversity score: {self.group_profile['diversity_score']}")
        
        return self.group_profile
    
    def generate_seed_playlist(self, count=5) -> List[Dict[str, Any]]:
        """Generate initial seed songs based on group preferences using actual track data"""
        if not self.group_profile:
            logging.warning("No group profile available. Call analyze_group_preferences() first.")
            return []
        
        if not self.raw_tracks:
            logging.warning("No track data available.")
            return []
        
        # Strategy: Pick actual songs from top genres with high popularity
        seed_songs = []
        top_genres = [g['genre'] for g in self.group_profile['top_genres'][:5]]
        top_artists = [a['artist'] for a in self.group_profile['top_artists'][:10]]
        
        # Score each track based on genre match, artist match, and popularity
        scored_tracks = []
        for track in self.raw_tracks:
            score = 0
            
            # Genre match (highest weight)
            track_genres = [g.strip() for g in track.get('genres', '').split(';') if g.strip()]
            for genre in track_genres:
                if genre in top_genres:
                    score += 100 * (1 + top_genres.index(genre))  # Higher score for top genres
            
            # Artist match (medium weight)
            track_artists = [a.strip() for a in track.get('artist_names', '').split(';') if a.strip()]
            for artist in track_artists:
                if artist in top_artists:
                    score += 50
            
            # Popularity (lower weight)
            try:
                popularity = int(track.get('popularity', 0))
                score += popularity * 0.5
            except:
                pass
            
            if score > 0:
                scored_tracks.append((score, track))
        
        # Sort by score and pick top tracks
        scored_tracks.sort(reverse=True, key=lambda x: x[0])
        
        # Select diverse tracks (avoid same artist)
        selected_artists = set()
        for score, track in scored_tracks:
            if len(seed_songs) >= count:
                break
            
            artists = track.get('artist_names', '').split(';')[0].strip()
            
            # Skip if we already have a song from this artist (for diversity)
            if artists in selected_artists and len(scored_tracks) > count:
                continue
            
            selected_artists.add(artists)
            
            # Get primary genre
            track_genres = [g.strip() for g in track.get('genres', '').split(';') if g.strip()]
            primary_genre = track_genres[0] if track_genres else "unknown"
            
            # Find expected appeal based on genre
            expected_appeal = 0
            for g in self.group_profile['top_genres']:
                if primary_genre == g['genre']:
                    expected_appeal = g['percentage']
                    break
            
            seed_songs.append({
                "title": track.get('track_name', 'Unknown'),
                "artist": artists,
                "genre": primary_genre,
                "album": track.get('album_name', ''),
                "popularity": int(track.get('popularity', 0)),
                "track_id": track.get('track_id', ''),
                "source": "fingerprint_seed",
                "expected_appeal": expected_appeal,
                "priority": len(seed_songs) + 1,
                "match_score": round(score, 1)
            })
        
        logging.info(f"✓ Generated {len(seed_songs)} seed songs")
        for song in seed_songs:
            logging.info(f"  {song['priority']}. {song['title']} by {song['artist']} ({song['genre']}) - {song['expected_appeal']}% appeal")
        
        return seed_songs
    
    def build_gemini_initialization_context(self) -> Dict[str, Any]:
        """Build context for Gemini API to initialize the party"""
        if not self.group_profile:
            return None
        
        context = {
            "initialization_phase": True,
            "group_context": {
                "total_attendees": self.group_profile['total_users'],
                "musical_diversity": self.group_profile['diversity_score'],
                "average_popularity_preference": self.group_profile['average_popularity'],
                "dominant_genres": [g['genre'] for g in self.group_profile['top_genres'][:5]],
                "genre_distribution": self.group_profile['top_genres'][:10],
                "favorite_artists": [a['artist'] for a in self.group_profile['top_artists'][:5]],
                "language_preferences": self.group_profile['top_languages']
            },
            "seed_songs": self.generate_seed_playlist(5),
            "recommendation_strategy": self._determine_strategy()
        }
        
        return context
    
    def _determine_strategy(self) -> Dict[str, Any]:
        """Determine initial DJ strategy based on group profile"""
        diversity = self.group_profile.get('diversity_score', 0)
        avg_popularity = self.group_profile.get('average_popularity', 0)
        
        # High diversity = eclectic tastes, need careful song selection
        # Low diversity = focused tastes, can be more aggressive
        if diversity > 0.3:
            strategy = "eclectic_mix"
            approach = "Play diverse genres to appeal to varied tastes"
        elif diversity > 0.15:
            strategy = "balanced_mix"
            approach = "Mix popular and niche tracks from top genres"
        else:
            strategy = "focused_genre"
            approach = "Focus on dominant genres with high confidence"
        
        # High popularity = mainstream crowd
        # Low popularity = indie/alternative crowd
        crowd_type = "mainstream" if avg_popularity > 65 else "alternative" if avg_popularity < 50 else "mixed"
        
        return {
            "strategy": strategy,
            "approach": approach,
            "crowd_type": crowd_type,
            "confidence": "high" if self.group_profile['total_tracks'] > 500 else "medium" if self.group_profile['total_tracks'] > 100 else "low"
        }
    
    def should_transition_to_live(self, songs_played: int, avg_reaction_score: float) -> bool:
        """Determine if we should transition from seed playlist to live audio analysis"""
        # Transition criteria:
        # 1. Played at least 3 seed songs (give it a chance)
        # 2. Have reliable reaction data (avg score not near 0)
        # 3. Enough samples collected
        
        MIN_SONGS = 3
        MIN_CONFIDENCE_SCORE = 0.3  # Absolute value
        
        if songs_played < MIN_SONGS:
            return False, f"Need {MIN_SONGS - songs_played} more seed songs"
        
        if abs(avg_reaction_score) < MIN_CONFIDENCE_SCORE:
            return False, f"Reaction data too weak (score: {avg_reaction_score:.2f})"
        
        return True, "Ready for live audio-driven recommendations"
    
    def print_summary(self):
        """Print a formatted summary of the analysis"""
        if not self.group_profile:
            print("❌ No data to summarize. Run analyze_group_preferences() first.")
            return
        
        print("\n" + "="*70)
        print("🎵 PARTY INITIALIZATION SUMMARY")
        print("="*70)
        
        print(f"\n👥 Group Profile:")
        print(f"   • Total attendees: {self.group_profile['total_users']}")
        print(f"   • Total tracks analyzed: {self.group_profile['total_tracks']}")
        print(f"   • Musical diversity: {self.group_profile['diversity_score']} (0=uniform, 1=very diverse)")
        print(f"   • Average popularity preference: {self.group_profile['average_popularity']}/100")
        
        print(f"\n🎼 Top Genres:")
        for i, genre in enumerate(self.group_profile['top_genres'][:5], 1):
            print(f"   {i}. {genre['genre']:<20} {genre['percentage']:>6.1f}%  {'█' * int(genre['percentage'] / 5)}")
        
        print(f"\n🎤 Top Artists:")
        for i, artist in enumerate(self.group_profile['top_artists'][:5], 1):
            print(f"   {i}. {artist['artist']:<30} {artist['percentage']:>6.1f}%")
        
        print(f"\n🌍 Language Distribution:")
        for i, lang in enumerate(self.group_profile['top_languages'][:3], 1):
            print(f"   {i}. {lang['language']:<15} {lang['percentage']:>6.1f}%")
        
        strategy = self._determine_strategy()
        print(f"\n🎯 Recommended Strategy:")
        print(f"   • Strategy: {strategy['strategy']}")
        print(f"   • Approach: {strategy['approach']}")
        print(f"   • Crowd type: {strategy['crowd_type']}")
        print(f"   • Confidence: {strategy['confidence']}")
        
        print(f"\n🎵 Seed Playlist (First {len(self.generate_seed_playlist())} songs):")
        for song in self.generate_seed_playlist():
            print(f"   {song['priority']}. {song['artist']} - {song['genre']} ({song['expected_appeal']:.1f}% appeal)")
        
        print("\n" + "="*70)
        print("✅ Ready to start party! Play seed songs, then transition to live analysis.")
        print("="*70 + "\n")


def main():
    """Example usage"""
    print("🎵 Initializing PLAILIST AI DJ System...")
    print("-" * 50)
    
    # Initialize
    initializer = PlaylistInitializer()
    
    # Step 1: Fetch fingerprints
    print("\n📡 Fetching user fingerprints...")
    data = initializer.fetch_fingerprints()
    if not data:
        print("❌ Failed to fetch fingerprints. Make sure fingerprint server is running:")
        print("   cd PLAILIST-dj-attendee-fingerprint")
        print("   node fingerprint-server.js")
        return
    
    # Step 2: Analyze group preferences
    print("\n📊 Analyzing group preferences...")
    initializer.analyze_group_preferences()
    
    # Step 3: Print summary
    initializer.print_summary()
    
    # Step 4: Build context for Gemini
    print("\n🤖 Building Gemini initialization context...")
    context = initializer.build_gemini_initialization_context()
    
    print("\n✅ Initialization complete!")
    print("\n💡 Next steps:")
    print("   1. Start Flask server: python backend/app.py")
    print("   2. Use seed songs from the analysis above")
    print("   3. Begin live audio monitoring: python record_live_audio.py")
    print("   4. System will automatically transition to AI-driven recommendations")
    
    # Simulate transition logic
    print("\n" + "-" * 50)
    print("🔄 Transition Logic Simulation:")
    test_scenarios = [
        (1, 0.15, "After 1 song with weak reaction"),
        (3, 0.25, "After 3 songs with weak reaction"),
        (3, 0.65, "After 3 songs with strong positive reaction"),
        (5, -0.80, "After 5 songs with strong negative reaction"),
    ]
    
    for songs, score, desc in test_scenarios:
        should_transition, reason = initializer.should_transition_to_live(songs, score)
        status = "✅ TRANSITION" if should_transition else "⏳ CONTINUE SEED"
        print(f"   {status}: {desc}")
        print(f"              → {reason}")


if __name__ == "__main__":
    main()
