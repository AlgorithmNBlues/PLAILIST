"""
Test Script for Integrated AI DJ System

This script tests the complete workflow:
1. Fingerprint server connectivity
2. Group preference analysis
3. Seed playlist generation
4. Flask server integration
5. Gemini recommendations
"""

import sys
from playlist_initializer import PlaylistInitializer

def test_fingerprint_server():
    """Test 1: CSV Data Loading"""
    print("\n" + "="*70)
    print("TEST 1: CSV Data Loading")
    print("="*70)
    
    initializer = PlaylistInitializer()
    data = initializer.fetch_fingerprints()
    
    if data:
        print(f"✅ PASS: Loaded data for {data.get('total_users', 0)} users")
        return True
    else:
        print("❌ FAIL: Could not load CSV files")
        return False

def test_group_analysis():
    """Test 2: Group Preference Analysis"""
    print("\n" + "="*70)
    print("TEST 2: Group Preference Analysis")
    print("="*70)
    
    initializer = PlaylistInitializer()
    initializer.fetch_fingerprints()
    profile = initializer.analyze_group_preferences()
    
    if profile:
        print(f"✅ PASS: Analyzed {profile['total_tracks']} tracks")
        print(f"   Top genre: {profile['top_genres'][0]['genre']} ({profile['top_genres'][0]['percentage']:.1f}%)")
        print(f"   Top artist: {profile['top_artists'][0]['artist']} ({profile['top_artists'][0]['percentage']:.1f}%)")
        print(f"   Diversity: {profile['diversity_score']:.3f}")
        return True
    else:
        print("❌ FAIL: Could not analyze group preferences")
        return False

def test_seed_generation():
    """Test 3: Seed Playlist Generation"""
    print("\n" + "="*70)
    print("TEST 3: Seed Playlist Generation")
    print("="*70)
    
    initializer = PlaylistInitializer()
    initializer.fetch_fingerprints()
    initializer.analyze_group_preferences()
    seeds = initializer.generate_seed_playlist(5)
    
    if seeds and len(seeds) == 5:
        print(f"✅ PASS: Generated {len(seeds)} seed songs")
        for i, song in enumerate(seeds, 1):
            print(f"   {i}. {song['artist']} - {song['genre']}")
        return True
    else:
        print(f"❌ FAIL: Expected 5 seeds, got {len(seeds) if seeds else 0}")
        return False

def test_gemini_context():
    """Test 4: Gemini Context Building"""
    print("\n" + "="*70)
    print("TEST 4: Gemini Context Building")
    print("="*70)
    
    initializer = PlaylistInitializer()
    initializer.fetch_fingerprints()
    initializer.analyze_group_preferences()
    context = initializer.build_gemini_initialization_context()
    
    if context:
        print("✅ PASS: Built Gemini context")
        print(f"   Attendees: {context['group_context']['total_attendees']}")
        print(f"   Strategy: {context['recommendation_strategy']['strategy']}")
        print(f"   Crowd type: {context['recommendation_strategy']['crowd_type']}")
        print(f"   Seed songs: {len(context['seed_songs'])}")
        return True
    else:
        print("❌ FAIL: Could not build Gemini context")
        return False

def test_transition_logic():
    """Test 5: Transition Logic"""
    print("\n" + "="*70)
    print("TEST 5: Transition Logic")
    print("="*70)
    
    initializer = PlaylistInitializer()
    initializer.fetch_fingerprints()
    initializer.analyze_group_preferences()
    
    test_cases = [
        (1, 0.15, False, "Too few songs, weak reaction"),
        (3, 0.20, False, "Enough songs, but weak reaction"),
        (3, 0.65, True, "Enough songs, strong positive reaction"),
        (5, -0.80, True, "Many songs, strong negative reaction"),
    ]
    
    all_passed = True
    for songs, score, expected, desc in test_cases:
        result, reason = initializer.should_transition_to_live(songs, score)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"{status} Songs={songs}, Score={score:.2f}: {desc}")
        print(f"   Expected: {expected}, Got: {result} - {reason}")
    
    if all_passed:
        print("\n✅ PASS: All transition logic correct")
    else:
        print("\n❌ FAIL: Some transition logic incorrect")
    
    return all_passed

def test_flask_integration():
    """Test 6: Flask Server Integration"""
    print("\n" + "="*70)
    print("TEST 6: Flask Server Integration")
    print("="*70)
    
    import requests
    
    try:
        # Test health endpoint
        response = requests.get("http://127.0.0.1:5000/health", timeout=3)
        if response.status_code == 200:
            print("✅ Flask server is running")
        else:
            print(f"⚠️  Flask server returned {response.status_code}")
            return False
        
        # Test party state endpoint
        response = requests.get("http://127.0.0.1:5000/party-state", timeout=3)
        if response.status_code == 200:
            state = response.json()
            print(f"✅ Party state accessible")
            print(f"   Gemini enabled: {state.get('gemini_enabled', False)}")
            return True
        else:
            print(f"⚠️  Party state returned {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Flask server not running")
        print("   Start with: python backend/app.py")
        return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*70)
    print("🧪 INTEGRATED AI DJ SYSTEM - TEST SUITE")
    print("="*70)
    
    tests = [
        ("CSV Data Loading", test_fingerprint_server),
        ("Group Analysis", test_group_analysis),
        ("Seed Generation", test_seed_generation),
        ("Gemini Context", test_gemini_context),
        ("Transition Logic", test_transition_logic),
        ("Flask Integration", test_flask_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready.")
        print("\nNext steps:")
        print("  1. Run: python integrated_dj_workflow.py")
        print("  2. Test live audio: python record_live_audio.py")
        print("  3. Build frontend for visualization")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")
        print("\nCommon fixes:")
        print("  • Start fingerprint server: node fingerprint-server.js")
        print("  • Start Flask server: python backend/app.py")
        print("  • Check .env has GEMINI_API_KEY")
    
    print("="*70 + "\n")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
