"""
Test the integrated frontend + backend system
"""

import requests
import time

FLASK_SERVER = "http://127.0.0.1:5000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing /health endpoint...")
    response = requests.get(f"{FLASK_SERVER}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    return response.status_code == 200

def test_frontend_routes():
    """Test frontend routes"""
    print("\n🔍 Testing frontend routes...")
    
    # Test login page
    response = requests.get(f"{FLASK_SERVER}/")
    print(f"   Login page (/) - Status: {response.status_code}")
    
    # Test session page
    response = requests.get(f"{FLASK_SERVER}/session")
    print(f"   Session page (/session) - Status: {response.status_code}")
    
    return response.status_code == 200

def test_audio_endpoint():
    """Test the /audio endpoint with a demo file"""
    print("\n🔍 Testing /audio endpoint (unified frontend endpoint)...")
    
    # Use demo audio file
    audio_file = "crowd-cheer-and-applause-406644.mp3"
    
    try:
        with open(audio_file, 'rb') as f:
            files = {'audio': (audio_file, f, 'audio/mpeg')}
            response = requests.post(f"{FLASK_SERVER}/audio", files=files)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success!")
                print(f"   Vibe: {result.get('vibe')}")
                print(f"   Score: {result.get('score')}")
                print(f"   Trend: {result.get('trend')}")
                print(f"   Method: {result.get('method')}")
                print(f"   Gemini called: {result.get('gemini_called')}")
                print(f"   Songs returned: {len(result.get('songs', []))}")
                
                if result.get('songs'):
                    print(f"   Recommended songs:")
                    for i, song in enumerate(result['songs'][:3], 1):
                        print(f"      {i}. {song.get('title')} - {song.get('artist')}")
                
                return True
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
    except FileNotFoundError:
        print(f"   ⚠️  Demo audio file not found: {audio_file}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_multiple_audio_calls():
    """Test multiple calls to trigger Gemini"""
    print("\n🔍 Testing multiple /audio calls (should trigger Gemini on 2nd call after 90s)...")
    
    audio_file = "crowd-disappointment-reaction-352718.mp3"
    
    try:
        # First call
        print("   Call #1...")
        with open(audio_file, 'rb') as f:
            files = {'audio': (audio_file, f, 'audio/mpeg')}
            response = requests.post(f"{FLASK_SERVER}/audio", files=files)
            
            if response.status_code == 200:
                result = response.json()
                print(f"      Score: {result.get('score')}, Gemini: {result.get('gemini_called')}")
        
        # Wait a bit
        print("   Waiting 3 seconds...")
        time.sleep(3)
        
        # Second call (won't trigger Gemini yet - too soon)
        print("   Call #2 (too soon for Gemini)...")
        with open(audio_file, 'rb') as f:
            files = {'audio': (audio_file, f, 'audio/mpeg')}
            response = requests.post(f"{FLASK_SERVER}/audio", files=files)
            
            if response.status_code == 200:
                result = response.json()
                print(f"      Score: {result.get('score')}, Gemini: {result.get('gemini_called')}")
        
        print("   ✅ Multiple calls working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TESTING INTEGRATED PLAILIST SYSTEM")
    print("=" * 70)
    
    # Check if server is running
    try:
        requests.get(f"{FLASK_SERVER}/health", timeout=2)
    except:
        print("\n❌ Flask server is not running!")
        print("   Start it with: python backend/app.py")
        exit(1)
    
    print("\n✅ Flask server is running\n")
    
    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Frontend Routes", test_frontend_routes()))
    results.append(("Audio Endpoint", test_audio_endpoint()))
    results.append(("Multiple Calls", test_multiple_audio_calls()))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print("\n" + "=" * 70)
    print(f"   Total: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        print("\n📱 Open in browser: http://127.0.0.1:5000/session")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
