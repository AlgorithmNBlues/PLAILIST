# 🎵 Integrated AI DJ System - Quick Start Guide

## 🏗️ System Architecture

```
Fingerprint Server (Node.js)  ──────┐
  - User Spotify data               │
  - Group preferences               │
  - Seed song generation            │
                                    ▼
                            Playlist Initializer (Python)
                                    │
                                    │ Initialization Context
                                    ▼
Flask AI DJ Server (Python)  ◄──────┤
  - Audio classification            │
  - Enthusiasm scoring              │
  - Party state tracking            │
  - Gemini AI integration           │
                                    ▲
                                    │
Live Audio Recorder (Python)  ──────┘
  - Microphone capture
  - Real-time analysis
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start Fingerprint Server
```bash
cd "D:\Academics\SUNY Buffalo\Semester 3\UB_Hacking\PLAILIST-dj-attendee-fingerprint"
node fingerprint-server.js
```
✅ Server runs on http://localhost:8000

### Step 2: Start Flask AI DJ Server
```bash
cd "D:\Academics\SUNY Buffalo\Semester 3\UB_Hacking"
python backend\app.py
```
✅ Server runs on http://127.0.0.1:5000

### Step 3: Run Integrated Workflow
```bash
python integrated_dj_workflow.py
```

---

## 📋 Complete Workflow

### Phase 1: Initialization (Fingerprint-Based)
1. ✅ Fetch user fingerprints from fingerprint server
2. ✅ Analyze group preferences (top genres, artists, languages)
3. ✅ Calculate musical diversity score
4. ✅ Determine DJ strategy (eclectic/balanced/focused)
5. ✅ Generate 5 seed songs based on group profile

### Phase 2: Seed Playlist (Warm-up)
1. ✅ Play seed songs from initialization
2. ✅ Track crowd reactions (simulated or real audio)
3. ✅ Build enthusiasm score history
4. ✅ Monitor transition criteria:
   - At least 3 songs played
   - Reliable reaction data (|score| > 0.3)
   - Sufficient samples collected

### Phase 3: Live AI-Driven (Production Mode)
1. ✅ Continuous audio monitoring (`record_live_audio.py`)
2. ✅ Real-time enthusiasm scoring
3. ✅ Periodic Gemini AI recommendations
4. ✅ Dynamic playlist adaptation
5. ✅ Party stage tracking (early/mid/peak/late)

---

## 🎯 Key Components

### 1. Playlist Initializer (`playlist_initializer.py`)
**Purpose**: Analyze group preferences and generate seed songs

**Key Methods**:
```python
initializer = PlaylistInitializer()
initializer.fetch_fingerprints()              # Get user data
initializer.analyze_group_preferences()       # Analyze group
initializer.generate_seed_playlist(5)         # Create 5 seed songs
initializer.build_gemini_initialization_context()  # For Gemini
```

**Output**:
- Group profile with top genres/artists/languages
- Musical diversity score (0-1)
- Recommended DJ strategy
- Seed playlist (5 songs)

### 2. Integrated DJ Workflow (`integrated_dj_workflow.py`)
**Purpose**: Orchestrate complete party workflow

**Key Methods**:
```python
system = IntegratedDJSystem()
system.check_servers()                    # Verify servers running
system.initialize_party()                 # Phase 1
system.play_seed_song(0)                  # Phase 2
system.end_current_song()                 # Get metrics
system.get_gemini_recommendations()       # Phase 3
```

### 3. Flask AI DJ Server (`backend/app.py`)
**Endpoints**:
- `POST /classify-audio` - Analyze audio file
- `POST /gemini-recommend` - Get AI recommendations
- `POST /update-song` - Start/end song tracking
- `GET /party-state` - Get current party metrics
- `POST /reset-party` - Reset for new session

### 4. Live Audio Recorder (`record_live_audio.py`)
**Modes**:
- Continuous monitoring (5-second intervals)
- Single recording (one-time analysis)
- Microphone test (verify setup)

---

## 📊 Data Flow

### Initialization Data
```json
{
  "group_context": {
    "total_attendees": 3,
    "dominant_genres": ["pop", "electronic", "hip-hop"],
    "favorite_artists": ["Tyler, The Creator", ...],
    "musical_diversity": 0.25,
    "average_popularity_preference": 67.8
  },
  "seed_songs": [
    {
      "title": "Seed Song 1",
      "artist": "Tyler, The Creator",
      "genre": "pop",
      "expected_appeal": 19.82
    }
  ]
}
```

### Live Reaction Data
```json
{
  "probs": {
    "cheering": 0.037,
    "applause": 0.933,
    "chatter": 0.017,
    "booing": 0.013
  },
  "enthusiasm_score": 0.68,
  "trend": "rising",
  "method": "HuggingFace"
}
```

### Gemini Recommendations
```json
{
  "analysis": {
    "crowd_mood": "High energy, engaged",
    "energy_trajectory": "Rising steadily"
  },
  "action": {
    "recommendation": "maintain_energy",
    "urgency": "normal",
    "confidence": 0.85
  },
  "next_songs": [
    {
      "title": "Song Name",
      "artist": "Artist",
      "genre": "Electronic",
      "reasoning": "Matches current energy",
      "predicted_impact": {
        "enthusiasm_delta": "+0.10 to +0.15",
        "expected_score": 0.75
      }
    }
  ]
}
```

---

## 🔄 Transition Logic

The system automatically transitions from seed playlist to live monitoring when:

| Criterion | Threshold | Current | Status |
|-----------|-----------|---------|--------|
| Songs played | ≥ 3 | Tracked | ✅ |
| Reaction confidence | \|score\| > 0.3 | Calculated | ✅ |
| Sample count | ≥ 10 | Monitored | ✅ |

**Example Scenarios**:
```
After 1 song, score 0.15:  ⏳ Need 2 more seed songs
After 3 songs, score 0.25:  ⏳ Reaction data too weak
After 3 songs, score 0.65:  ✅ TRANSITION - Ready for live
After 5 songs, score -0.80: ✅ TRANSITION - Strong signal
```

---

## 🎮 Usage Examples

### Example 1: Full Automated Workflow
```bash
# Terminal 1: Fingerprint server
cd PLAILIST-dj-attendee-fingerprint
node fingerprint-server.js

# Terminal 2: Flask server
python backend\app.py

# Terminal 3: Run workflow
python integrated_dj_workflow.py
# Choose option 1 (Full workflow simulated)
```

### Example 2: Manual Control
```python
from integrated_dj_workflow import IntegratedDJSystem

system = IntegratedDJSystem()
system.check_servers()
system.initialize_party()

# Play seed songs manually
for i in range(5):
    system.play_seed_song(i)
    # ... record audio, analyze reactions ...
    system.end_current_song()
    
    should_transition, reason = system.should_transition_to_live()
    if should_transition:
        break

# Get AI recommendations
recommendation = system.get_gemini_recommendations()
```

### Example 3: Live Production Mode
```bash
# Terminal 1 & 2: Servers (as above)

# Terminal 3: Initialization
python playlist_initializer.py
# Note the seed songs

# Terminal 4: Live audio monitoring
python record_live_audio.py
# Choose option 1 (Continuous monitoring)

# Terminal 5: Manual Gemini calls
curl -X POST http://127.0.0.1:5000/gemini-recommend
```

---

## 📈 Metrics & Monitoring

### Party State Metrics
```bash
curl http://127.0.0.1:5000/party-state
```

Returns:
- `party_active`: Is party session active?
- `elapsed_minutes`: Time since start
- `current_song`: Currently playing track
- `total_songs_played`: Song count
- `current_score`: Latest enthusiasm score
- `current_trend`: rising/falling/stable
- `party_stage`: early/mid/peak/late
- `avg_score_5min`: 5-minute rolling average

### Enthusiasm Score Interpretation
| Score | Interpretation | Action |
|-------|----------------|--------|
| > 0.7 | Highly engaged | Maintain energy |
| 0.4 - 0.7 | Good energy | Continue current vibe |
| 0.1 - 0.4 | Moderate | Consider energy boost |
| -0.2 - 0.1 | Neutral | Change needed |
| < -0.2 | Losing interest | Urgent genre shift |
| < -0.7 | Negative reaction | Emergency change |

---

## 🛠️ Troubleshooting

### Fingerprint Server Not Running
```
❌ Fingerprint server: NOT RUNNING
```
**Fix**: 
```bash
cd PLAILIST-dj-attendee-fingerprint
node fingerprint-server.js
```

### Flask Server Not Running
```
❌ Flask server: NOT RUNNING
```
**Fix**:
```bash
python backend\app.py
```

### No Gemini Recommendations
```
❌ Gemini API not configured
```
**Fix**: Check `.env` file has `GEMINI_API_KEY`

### Audio Recording Issues
```
❌ Microphone test failed
```
**Fix**: 
```bash
pip install pipwin
pipwin install pyaudio
```

---

## 📦 Dependencies

### Python Packages
```bash
pip install flask transformers torch torchaudio
pip install soundfile scipy numpy requests
pip install google-generativeai python-dotenv
pip install pipwin
pipwin install pyaudio
pip install keyboard
```

### Node.js Packages
```bash
cd PLAILIST-dj-attendee-fingerprint
npm install express
```

---

## 🎯 Next Steps

1. ✅ **Test the workflow**: Run `python integrated_dj_workflow.py`
2. ✅ **Verify seed generation**: Check group preferences make sense
3. ✅ **Test live audio**: Run `python record_live_audio.py`
4. ✅ **Validate Gemini**: Check recommendations are relevant
5. 🔄 **Build frontend**: Visualize real-time party state
6. 🔄 **Integrate Spotify API**: Play actual tracks instead of placeholders
7. 🔄 **Add manual overrides**: Let DJ intervene when needed
8. 🔄 **Track prediction accuracy**: Validate Gemini's suggestions

---

## 📞 API Reference

See detailed API documentation in:
- `GEMINI_API_REFERENCE.md` - Full endpoint documentation
- `GEMINI_INTEGRATION_SPEC.md` - Complete technical spec
- `QUICKSTART.md` - Basic setup instructions

---

**🎉 You're ready to DJ with AI!**
