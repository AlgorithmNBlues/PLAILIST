# Gemini Integration - API Reference

## Endpoints

### 1. POST /classify-audio
Analyze crowd reaction from audio file.

**Request:**
```bash
curl -X POST -F "audio=@crowd-cheer.mp3" http://127.0.0.1:5000/classify-audio
```

**Response:**
```json
{
  "probs": {
    "cheering": 0.037,
    "applause": 0.933,
    "chatter": 0.017,
    "booing": 0.001,
    "music_only": 0.011
  },
  "enthusiasm_score": 0.68,
  "trend": "rising",
  "method": "HuggingFace"
}
```

---

### 2. POST /gemini-recommend
Get AI song recommendations based on crowd analysis.

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/gemini-recommend
```

**Response:**
```json
{
  "context": {
    "crowd_state": {
      "enthusiasm_score": 0.68,
      "trend": "rising",
      "interpretation": "Good energy - crowd enjoying"
    },
    "temporal_context": {
      "score_history_30s": [0.52, 0.58, 0.61, 0.65, 0.68],
      "avg_score_5min": 0.58
    },
    "party_context": {
      "stage": "mid",
      "elapsed_minutes": 45,
      "total_songs_played": 12
    }
  },
  "recommendation": {
    "analysis": {
      "crowd_mood": "Energetic and engaged",
      "energy_trajectory": "Steadily rising",
      "recommendations_reasoning": "Continue building energy"
    },
    "action": {
      "recommendation": "increase_energy",
      "urgency": "normal",
      "confidence": 0.85
    },
    "next_songs": [
      {
        "title": "Song Name",
        "artist": "Artist Name",
        "genre": "Electronic",
        "reasoning": "Matches rising momentum",
        "predicted_impact": {
          "enthusiasm_delta": "+0.10 to +0.15",
          "expected_score": 0.75
        },
        "priority": 1
      }
    ],
    "warnings": ["Monitor for plateau"]
  }
}
```

---

### 3. POST /update-song
Track song performance.

**Start a song:**
```bash
curl -X POST http://127.0.0.1:5000/update-song \
  -H "Content-Type: application/json" \
  -d '{
    "song": {
      "title": "Energy Boost",
      "artist": "DJ Awesome",
      "genre": "Electronic",
      "predicted_score": 0.75
    }
  }'
```

**End current song:**
```bash
curl -X POST http://127.0.0.1:5000/update-song \
  -H "Content-Type: application/json" \
  -d '{"action": "end_song"}'
```

**Response (end song):**
```json
{
  "status": "Song ended and added to history",
  "song_record": {
    "title": "Energy Boost",
    "artist": "DJ Awesome",
    "genre": "Electronic",
    "avg_reaction_score": 0.72,
    "peak_reaction": 0.85,
    "min_reaction": 0.61,
    "outcome": "success",
    "predicted_score": 0.75,
    "prediction_accuracy": 0.03
  }
}
```

---

### 4. GET /party-state
Get current party statistics.

**Request:**
```bash
curl http://127.0.0.1:5000/party-state
```

**Response:**
```json
{
  "party_active": true,
  "elapsed_minutes": 45,
  "current_song": {
    "title": "Current Song",
    "artist": "Artist",
    "genre": "Pop",
    "reactions": [0.65, 0.68, 0.70]
  },
  "total_songs_played": 12,
  "current_score": 0.68,
  "current_trend": "rising",
  "party_stage": "mid",
  "avg_score_5min": 0.58,
  "song_history": [...],
  "gemini_enabled": true
}
```

---

### 5. POST /reset-party
Reset party session (for testing or new event).

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/reset-party
```

---

## Typical Workflow

### 1. Continuous Audio Analysis (Every 5 seconds)
```python
# Capture audio → Analyze
POST /classify-audio
# Returns enthusiasm_score, trend

# Score automatically tracked for current song
```

### 2. Song Management
```python
# When starting a song
POST /update-song with song details

# During song: Keep analyzing audio (step 1)
# Reactions automatically tracked

# When song ends
POST /update-song with action="end_song"
# Calculates avg/peak/min, adds to history
```

### 3. Get AI Recommendations (Every song or as needed)
```python
# After analyzing crowd for a while
POST /gemini-recommend
# Returns next 3 song suggestions with reasoning

# Pick top recommendation
# Start tracking it (step 2)
# Continue loop
```

### 4. Monitor Progress
```python
# Check party stats anytime
GET /party-state
```

---

## Testing

Run the integration test:
```bash
python test_gemini_integration.py
```

This simulates:
- 3 songs with different reactions
- Tracks each song's performance
- Calls Gemini for recommendations
- Shows complete workflow

---

## Score Interpretation

| Score Range | Meaning | Action |
|-------------|---------|--------|
| +0.7 to +1.0 | Crowd loving it 🔥 | Maintain energy, similar style |
| +0.4 to +0.7 | Good energy ✅ | Keep momentum |
| +0.1 to +0.4 | Moderate interest 😐 | Consider energy boost |
| -0.2 to +0.1 | Neutral 💬 | Change strategy |
| -0.7 to -0.2 | Losing interest ⚠️ | Play crowd favorite |
| -1.5 to -0.7 | Negative reaction 😞 | Emergency intervention |

---

## Party Stages

- **early**: First 30 min OR low energy (avg < 0.3)
- **mid**: Transition phase, building energy
- **peak**: 30-120 min AND high energy (avg > 0.6)
- **late**: After 120 min OR declining energy

Gemini adjusts recommendations based on stage.
