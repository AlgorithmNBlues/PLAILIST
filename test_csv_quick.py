"""Quick test to verify CSV loading works"""
from playlist_initializer import PlaylistInitializer

print("Testing CSV Integration...")
print("=" * 50)

initializer = PlaylistInitializer("PLAILIST-dj-attendee-fingerprint")

print("\n1. Loading fingerprints from CSV files...")
data = initializer.fetch_fingerprints()

if data:
    print(f"✅ Success! Loaded {data['total_users']} users")
    print(f"   Total tracks: {sum([fp['total_tracks'] for fp in data['fingerprints']])}")
    
    print("\n2. Analyzing group preferences...")
    profile = initializer.analyze_group_preferences()
    
    if profile:
        print(f"✅ Success!")
        print(f"   Top genre: {profile['top_genres'][0]['genre']} ({profile['top_genres'][0]['percentage']:.1f}%)")
        print(f"   Top artist: {profile['top_artists'][0]['artist']} ({profile['top_artists'][0]['percentage']:.1f}%)")
        print(f"   Diversity: {profile['diversity_score']:.3f}")
        
        print("\n3. Generating seed playlist...")
        seeds = initializer.generate_seed_playlist(5)
        
        if seeds:
            print(f"✅ Success! Generated {len(seeds)} songs:")
            for i, song in enumerate(seeds, 1):
                print(f"   {i}. {song['title']} by {song['artist']} ({song['genre']})")
            
            print("\n" + "=" * 50)
            print("✅ ALL TESTS PASSED! CSV integration working!")
        else:
            print("❌ Failed to generate seed playlist")
    else:
        print("❌ Failed to analyze preferences")
else:
    print("❌ Failed to load fingerprints")
    print("\nMake sure CSV files are in: PLAILIST-dj-attendee-fingerprint/")
