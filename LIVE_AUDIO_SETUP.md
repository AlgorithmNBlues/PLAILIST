# 🎤 Live Audio Recording Setup

## 📦 Installation

Install the required packages:

```bash
pip install pyaudio keyboard
```

### ⚠️ PyAudio Installation Issues

If `pip install pyaudio` fails on Windows:

**Option 1: Use pipwin (Easiest)**
```bash
pip install pipwin
pipwin install pyaudio
```

**Option 2: Download wheel file**
1. Go to: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
2. Download the appropriate `.whl` for your Python version
3. Install: `pip install PyAudio‑0.2.11‑cp311‑cp311‑win_amd64.whl`

**Option 3: Install Visual C++ Build Tools**
1. Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install with C++ development tools
3. Then: `pip install pyaudio`

---

## 🚀 Usage

### Start the Flask Server First
```bash
python backend\app.py
```

Wait for: `✓ Gemini AI integration ENABLED`

### Run the Audio Recorder
```bash
python record_live_audio.py
```

---

## 📋 Menu Options

### **1. Continuous Monitoring** (Recommended for live events)
- Records audio every 5 seconds
- Automatically analyzes and displays results
- Shows real-time enthusiasm scores
- Press 'q' to stop

**Use case:** Live DJ monitoring, party tracking

```
🎤 Recording for 5 seconds...
✓ Recording complete
🤖 Analyzing crowd reaction...

📊 ANALYSIS #1 - 18:45:23
🔥 ENTHUSIASM SCORE: 0.68 (GOOD)
   Trend: rising
   
Crowd Reaction Breakdown:
   applause     ████████████████████  93.3%
   cheering     ██  3.7%
   chatter      █  1.7%
```

### **2. Single Recording**
- Record one 5-second sample
- Saves with timestamp
- One-time analysis

**Use case:** Quick checks, testing

### **3. Test Microphone**
- 3-second test recording
- Verifies microphone works
- Saves to `mic_test.wav`

**Use case:** Setup verification

---

## 🎯 Features

### Visual Feedback
- ✅ Color-coded scores (green = good, red = negative)
- 📊 Bar chart of probabilities
- 🎨 Emoji indicators
- ⏱️ Timestamps

### Real-time Monitoring
- Records every 5 seconds
- 2-second gap between recordings
- Press 'q' anytime to stop gracefully
- Shows recording number

### Score Interpretation
| Score | Color | Status | Emoji |
|-------|-------|--------|-------|
| > 0.6 | 🟢 Green | EXCELLENT | 🔥 |
| 0.3 - 0.6 | 🔵 Cyan | GOOD | ✅ |
| 0 - 0.3 | 🟡 Yellow | MODERATE | 😐 |
| -0.5 - 0 | 🟡 Yellow | LOW | ⚠️ |
| < -0.5 | 🔴 Red | NEGATIVE | 😞 |

---

## 🔧 Configuration

Edit these variables in `record_live_audio.py`:

```python
SERVER_URL = "http://127.0.0.1:5000"  # Flask server URL
RECORD_SECONDS = 5  # Duration of each recording
RATE = 44100  # Sample rate (44.1kHz)
CHANNELS = 1  # Mono audio
```

---

## 🎵 Typical Workflow

### For Live DJ Monitoring:

**Terminal 1: Start Server**
```bash
python backend\app.py
```

**Terminal 2: Start Recording**
```bash
python record_live_audio.py
# Choose option 1 (Continuous monitoring)
```

**Terminal 3: Get Recommendations** (optional)
```bash
# After collecting some data
curl -X POST http://127.0.0.1:5000/gemini-recommend
```

### Recording Flow:
```
1. Microphone captures 5 seconds
2. Audio saved as temp_recording.wav
3. Sent to Flask /classify-audio endpoint
4. HuggingFace model analyzes crowd reaction
5. Results displayed with colors and bars
6. Wait 2 seconds
7. Repeat (or press 'q' to stop)
```

---

## 📊 Output Examples

### Positive Crowd Reaction:
```
📊 ANALYSIS #5 - 19:15:42
🔥 ENTHUSIASM SCORE: 0.85 (EXCELLENT)
   Trend: rising
   Method: HuggingFace

Crowd Reaction Breakdown:
   applause     ███████████████████████  94.2%
   cheering     ███  5.1%
   chatter      ·  0.5%
   booing       ·  0.2%
```

### Negative Crowd Reaction:
```
📊 ANALYSIS #12 - 19:32:18
😞 ENTHUSIASM SCORE: -1.15 (NEGATIVE)
   Trend: falling
   Method: HuggingFace

Crowd Reaction Breakdown:
   booing       ████████████████████████████  82.5%
   chatter      ████  10.2%
   cheering     ██  5.1%
   applause     ·  2.2%
```

---

## 🐛 Troubleshooting

### "Cannot connect to server"
- Make sure Flask server is running
- Check server is on http://127.0.0.1:5000
- Test: `curl http://127.0.0.1:5000/health`

### "Microphone test failed"
- Check microphone is connected
- Allow microphone access in Windows settings
- Try different USB port
- Check Windows Sound settings → Recording devices

### PyAudio import error
- See installation instructions above
- Use pipwin method (easiest on Windows)

### "Input overflowed"
- Reduce CHUNK size: `CHUNK = 512`
- Or increase buffer: `frames_per_buffer=2048`

### High latency
- Reduce RECORD_SECONDS to 3
- Use faster server (GPU if available)

---

## 🎤 Microphone Recommendations

**For best results:**
- Use external USB microphone (better than laptop mic)
- Position 3-5 feet from speakers
- Avoid directly in front of speakers (feedback)
- Test different positions for best crowd pickup

**Good budget options:**
- Blue Snowball (~$50)
- Audio-Technica ATR2100 (~$80)
- Any USB conference mic

---

## 🔄 Integration with Gemini

The recorded audio automatically feeds into the enthusiasm score history, which Gemini uses for recommendations.

**To start song tracking:**
```python
# In another script or manually via API
POST /update-song
{
  "song": {
    "title": "Current Song",
    "artist": "Artist Name",
    "genre": "Electronic"
  }
}
```

Then run `record_live_audio.py` - reactions are automatically tracked for that song!

---

## 📝 Notes

- Temporary file `temp_recording.wav` is overwritten each cycle
- Single recordings save with timestamp: `recording_20251108_183045.wav`
- Audio is mono 44.1kHz WAV format
- Each recording is ~400KB (5 seconds)

---

**Ready to capture live crowd reactions!** 🎉
