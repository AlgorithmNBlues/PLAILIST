"""
Real-time audio recording and classification
Captures audio from microphone and sends to Flask server for analysis
"""
import pyaudio
import wave
import requests
import time
import json
from datetime import datetime
import keyboard  # For press 'q' to quit
import threading

# Configuration
SERVER_URL = "http://127.0.0.1:5000"
CHUNK = 1024  # Audio chunk size
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1  # Mono
RATE = 44100  # Sample rate (44.1kHz)
RECORD_SECONDS = 5  # Duration of each recording

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def record_audio(duration=RECORD_SECONDS):
    """Record audio from microphone"""
    print(f"{Colors.CYAN}🎤 Recording for {duration} seconds...{Colors.RESET}")
    
    audio = pyaudio.PyAudio()
    
    # Open audio stream
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    frames = []
    
    # Record audio
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    # Stop and close stream
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    print(f"{Colors.GREEN}✓ Recording complete{Colors.RESET}")
    
    return frames

def save_audio_to_file(frames, filename="temp_recording.wav"):
    """Save recorded audio to WAV file"""
    audio = pyaudio.PyAudio()
    
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    audio.terminate()
    return filename

def classify_audio_file(filename):
    """Send audio file to Flask server for classification"""
    try:
        with open(filename, 'rb') as f:
            files = {'audio': (filename, f, 'audio/wav')}
            response = requests.post(f"{SERVER_URL}/classify-audio", files=files, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Server returned status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def display_results(result, recording_num):
    """Display classification results in a nice format"""
    print("\n" + "="*70)
    print(f"{Colors.BOLD}📊 ANALYSIS #{recording_num} - {datetime.now().strftime('%H:%M:%S')}{Colors.RESET}")
    print("="*70)
    
    if "error" in result:
        print(f"{Colors.RED}✗ Error: {result['error']}{Colors.RESET}")
        return
    
    # Enthusiasm score with color coding
    score = result['enthusiasm_score']
    if score > 0.6:
        color = Colors.GREEN
        emoji = "🔥"
        status = "EXCELLENT"
    elif score > 0.3:
        color = Colors.CYAN
        emoji = "✅"
        status = "GOOD"
    elif score > 0:
        color = Colors.YELLOW
        emoji = "😐"
        status = "MODERATE"
    elif score > -0.5:
        color = Colors.YELLOW
        emoji = "⚠️"
        status = "LOW"
    else:
        color = Colors.RED
        emoji = "😞"
        status = "NEGATIVE"
    
    print(f"\n{color}{Colors.BOLD}{emoji} ENTHUSIASM SCORE: {score:.2f} ({status}){Colors.RESET}")
    print(f"   Trend: {result['trend'].upper()}")
    print(f"   Method: {result['method']}")
    
    # Probabilities
    print(f"\n{Colors.BOLD}Crowd Reaction Breakdown:{Colors.RESET}")
    probs = result['probs']
    
    # Sort by probability
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    
    for label, prob in sorted_probs:
        bar_length = int(prob * 40)  # Scale to 40 characters
        bar = "█" * bar_length
        percentage = prob * 100
        
        # Color code based on type
        if label == 'cheering':
            label_color = Colors.GREEN
        elif label == 'applause':
            label_color = Colors.CYAN
        elif label == 'chatter':
            label_color = Colors.YELLOW
        elif label == 'booing':
            label_color = Colors.RED
        else:
            label_color = Colors.MAGENTA
        
        print(f"   {label_color}{label:12s}{Colors.RESET} {bar} {percentage:5.1f}%")
    
    print("="*70 + "\n")

def continuous_monitoring():
    """Continuously record and analyze audio"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("🎵 LIVE CROWD REACTION MONITOR")
    print("="*70)
    print(f"{Colors.RESET}")
    print(f"Recording: {RECORD_SECONDS} seconds per analysis")
    print(f"Server: {SERVER_URL}")
    print(f"\n{Colors.YELLOW}Press 'q' to stop monitoring{Colors.RESET}\n")
    
    recording_num = 0
    stop_flag = False
    
    def check_quit():
        nonlocal stop_flag
        keyboard.wait('q')
        stop_flag = True
        print(f"\n{Colors.YELLOW}⏸️  Stopping after current recording...{Colors.RESET}")
    
    # Start quit listener in separate thread
    quit_thread = threading.Thread(target=check_quit, daemon=True)
    quit_thread.start()
    
    try:
        while not stop_flag:
            recording_num += 1
            
            # Record audio
            frames = record_audio(RECORD_SECONDS)
            
            if stop_flag:
                break
            
            # Save to file
            filename = "temp_recording.wav"
            save_audio_to_file(frames, filename)
            
            # Classify
            print(f"{Colors.CYAN}🤖 Analyzing crowd reaction...{Colors.RESET}")
            result = classify_audio_file(filename)
            
            # Display results
            display_results(result, recording_num)
            
            # Small delay before next recording
            if not stop_flag:
                print(f"{Colors.MAGENTA}⏳ Next recording in 2 seconds... (Press 'q' to stop){Colors.RESET}\n")
                for _ in range(20):  # Check every 0.1s for 2 seconds
                    if stop_flag:
                        break
                    time.sleep(0.1)
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏸️  Monitoring stopped by user{Colors.RESET}")
    
    print(f"\n{Colors.GREEN}✓ Total recordings analyzed: {recording_num}{Colors.RESET}")

def record_single():
    """Record a single audio sample and classify it"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🎤 SINGLE RECORDING MODE{Colors.RESET}\n")
    
    # Record
    frames = record_audio(RECORD_SECONDS)
    
    # Save
    filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    save_audio_to_file(frames, filename)
    print(f"{Colors.GREEN}✓ Saved to: {filename}{Colors.RESET}")
    
    # Classify
    print(f"{Colors.CYAN}🤖 Analyzing...{Colors.RESET}")
    result = classify_audio_file(filename)
    
    # Display
    display_results(result, 1)
    
    return filename, result

def main():
    """Main menu"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("🎵 AUDIO RECORDING & CLASSIFICATION")
    print("="*70)
    print(f"{Colors.RESET}")
    print("Choose mode:")
    print(f"  {Colors.GREEN}1{Colors.RESET}. Continuous monitoring (record every {RECORD_SECONDS}s)")
    print(f"  {Colors.GREEN}2{Colors.RESET}. Single recording")
    print(f"  {Colors.GREEN}3{Colors.RESET}. Test microphone")
    print(f"  {Colors.GREEN}4{Colors.RESET}. Exit")
    
    choice = input(f"\n{Colors.CYAN}Enter choice (1-4): {Colors.RESET}")
    
    if choice == "1":
        continuous_monitoring()
    elif choice == "2":
        record_single()
    elif choice == "3":
        test_microphone()
    elif choice == "4":
        print(f"{Colors.GREEN}Goodbye!{Colors.RESET}")
        return
    else:
        print(f"{Colors.RED}Invalid choice{Colors.RESET}")
        main()

def test_microphone():
    """Test if microphone is working"""
    print(f"\n{Colors.BOLD}🎤 MICROPHONE TEST{Colors.RESET}")
    print(f"{Colors.YELLOW}Recording 3 seconds to test microphone...{Colors.RESET}\n")
    
    try:
        frames = record_audio(3)
        filename = "mic_test.wav"
        save_audio_to_file(frames, filename)
        
        print(f"{Colors.GREEN}✓ Microphone working! Test saved to: {filename}{Colors.RESET}")
        print(f"{Colors.CYAN}Play it back to verify audio quality.{Colors.RESET}\n")
        
    except Exception as e:
        print(f"{Colors.RED}✗ Microphone test failed: {e}{Colors.RESET}")
        print(f"{Colors.YELLOW}Make sure you have a microphone connected and allowed in settings.{Colors.RESET}\n")

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=2)
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ Server is running{Colors.RESET}")
            main()
        else:
            print(f"{Colors.RED}✗ Server returned unexpected status{Colors.RESET}")
    except requests.exceptions.RequestException:
        print(f"{Colors.RED}✗ Cannot connect to server at {SERVER_URL}{Colors.RESET}")
        print(f"{Colors.YELLOW}Make sure Flask server is running: python backend/app.py{Colors.RESET}")
