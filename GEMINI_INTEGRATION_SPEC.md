# Gemini Integration - Detailed Implementation Plan

## Architecture Overview

```
[Audio Analysis] → [Context Builder] → [Gemini API] → [Action Processor] → [Feedback Loop]
```

---

## 1. INPUT TO GEMINI API

### A. Crowd Analysis (Real-time)
```json
{
  "crowd_state": {
    "enthusiasm_score": 0.68,
    "trend": "rising",
    "probs": {
      "cheering": 0.037,
      "applause": 0.933,
      "chatter": 0.017,
      "booing": 0.001,
      "music_only": 0.011
    },
    "interpretation": "Highly engaged - crowd loving it",
    "confidence": "high"
  }
}
```

### B. Temporal Context (History)
```json
{
  "temporal_context": {
    "score_history_30s": [0.52, 0.58, 0.61, 0.65, 0.68],
    "avg_score_1min": 0.61,
    "avg_score_5min": 0.58,
    "score_variance": 0.004,
    "trend_duration": "30 seconds"
  }
}
```

### C. Party Context (Session State)
```json
{
  "party_context": {
    "stage": "mid",
    "elapsed_minutes": 45,
    "start_time": "2025-11-08T19:00:00",
    "total_songs_played": 12,
    "current_song": {
      "title": "Song X",
      "artist": "Artist Y",
      "genre": "Pop",
      "duration_seconds": 180,
      "time_remaining": 45
    }
  }
}
```

### D. Song History (Learning Data)
```json
{
  "song_history": [
    {
      "title": "Song A",
      "artist": "Artist 1",
      "genre": "Electronic",
      "played_at": "2025-11-08T19:35:00",
      "avg_reaction_score": 0.72,
      "peak_reaction": 0.85,
      "min_reaction": 0.61,
      "outcome": "success"
    },
    {
      "title": "Song B",
      "artist": "Artist 2",
      "genre": "Hip Hop",
      "played_at": "2025-11-08T19:32:00",
      "avg_reaction_score": 0.45,
      "peak_reaction": 0.52,
      "min_reaction": 0.38,
      "outcome": "moderate"
    }
    // ... last 5 songs
  ]
}
```

### E. Music Library Context (Available Options)
```json
{
  "available_genres": ["Pop", "Electronic", "Hip Hop", "Rock", "R&B"],
  "library_size": 500,
  "recently_played_genres": ["Electronic", "Pop", "Hip Hop"],
  "genre_restrictions": {
    "avoid_repetition": true,
    "max_same_genre_streak": 2
  }
}
```

---

## 2. OUTPUT FROM GEMINI API

### Complete Response Structure
```json
{
  "analysis": {
    "crowd_mood": "Energetic and engaged, responding well to upbeat tracks",
    "energy_trajectory": "Steadily rising over last 5 minutes",
    "recommendations_reasoning": "Crowd is warming up well. Continue building energy with familiar high-tempo tracks.",
    "risk_assessment": "Low risk - crowd is responsive and engaged"
  },
  
  "action": {
    "recommendation": "increase_energy",
    "urgency": "normal",
    "confidence": 0.85
  },
  
  "next_songs": [
    {
      "title": "Song Title 1",
      "artist": "Artist Name 1",
      "genre": "Electronic",
      "reasoning": "High energy track matches current rising momentum",
      "predicted_impact": {
        "enthusiasm_delta": "+0.10 to +0.15",
        "expected_score": 0.75,
        "confidence": 0.80
      },
      "priority": 1
    },
    {
      "title": "Song Title 2",
      "artist": "Artist Name 2",
      "genre": "Pop",
      "reasoning": "Familiar crowd-pleaser as backup if energy plateaus",
      "predicted_impact": {
        "enthusiasm_delta": "+0.05 to +0.10",
        "expected_score": 0.70,
        "confidence": 0.75
      },
      "priority": 2
    },
    {
      "title": "Song Title 3",
      "artist": "Artist Name 3",
      "genre": "Hip Hop",
      "reasoning": "Genre switch option if electronic becomes repetitive",
      "predicted_impact": {
        "enthusiasm_delta": "0 to +0.05",
        "expected_score": 0.65,
        "confidence": 0.70
      },
      "priority": 3
    }
  ],
  
  "warnings": [
    "Energy rising but monitor for plateau",
    "Avoid slow tracks for next 10-15 minutes"
  ],
  
  "alternative_strategies": [
    {
      "scenario": "if_energy_drops",
      "action": "Play high-energy crowd favorite immediately"
    },
    {
      "scenario": "if_energy_plateaus",
      "action": "Switch genre to refresh crowd interest"
    }
  ]
}
```

---

## 3. WHAT GETS FED BACK INTO APP

### A. Update Party State
```python
# Update internal tracking
current_song = next_songs[0]  # Play first recommendation
song_start_time = datetime.now()
last_gemini_recommendation = gemini_response
```

### B. Track Predictions vs Reality
```python
# Store prediction for validation
prediction_tracker.append({
    "song": current_song,
    "predicted_score": 0.75,
    "predicted_delta": 0.12,
    "actual_score": None,  # Will be filled after song plays
    "actual_delta": None,
    "accuracy": None
})
```

### C. Update Song History
```python
# After song finishes playing
song_history.append({
    "title": current_song["title"],
    "artist": current_song["artist"],
    "genre": current_song["genre"],
    "played_at": song_start_time,
    "avg_reaction_score": np.mean(reactions_during_song),
    "peak_reaction": np.max(reactions_during_song),
    "min_reaction": np.min(reactions_during_song),
    "outcome": "success" if avg_reaction > 0.6 else "moderate" if avg_reaction > 0.3 else "poor",
    "gemini_predicted_score": 0.75,
    "prediction_accuracy": abs(actual - predicted)
})
```

### D. Adjust Strategy Based on Feedback
```python
# If predictions are consistently wrong
if np.mean([t["prediction_accuracy"] for t in prediction_tracker[-5:]]) > 0.2:
    # Feed correction data back to Gemini in next call
    context["performance_feedback"] = {
        "recent_prediction_accuracy": "low",
        "note": "Last 5 predictions off by average 0.2 points"
    }
```

---

## 4. FEEDBACK LOOP FLOW

```
┌─────────────────────────────────────────────────────────────┐
│  CONTINUOUS CYCLE (Every 5 seconds)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
         1. Capture audio (5 seconds)
                            ↓
         2. Analyze with HF model
                            ↓
         3. Update SCORE_HISTORY
                            ↓
         4. Check: Should we request new song?
            ├─ Yes: Continue to step 5
            └─ No:  Return to step 1
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  GEMINI DECISION CYCLE (Every 3-4 minutes / per song)       │
└─────────────────────────────────────────────────────────────┘
                            ↓
         5. Build context from:
            - Current crowd state
            - 30s/1min/5min history
            - Party stage & elapsed time
            - Last 5 songs played
            - Available music library
                            ↓
         6. Call Gemini API
                            ↓
         7. Parse response
            - Extract top song recommendation
            - Store predictions
            - Note warnings
                            ↓
         8. Execute action:
            - Play recommended song
            - Update party state
            - Start tracking this song
                            ↓
         9. Monitor reactions during song:
            - Collect enthusiasm scores every 5s
            - Calculate avg/peak/min
                            ↓
        10. After song ends:
            - Compare predicted vs actual
            - Add to song_history
            - Update prediction_tracker
                            ↓
        11. Learn & adapt:
            - If predictions consistently wrong,
              add feedback notes for next Gemini call
                            ↓
         Return to step 1 ────────────────────────┘
```

---

## 5. KEY DECISIONS TO MAKE

### A. When to Call Gemini?
**Options:**
1. **Every song** (3-4 min intervals) - Most responsive but costly
2. **Every 2 songs** (6-8 min) - Balanced
3. **On trigger events** - When trend changes or score drops >0.2

**Recommendation:** Every song, but cache recommendations for next 3 songs to reduce API calls

### B. How to Handle Gemini Failures?
**Fallback strategies:**
1. Use last cached recommendation
2. Rule-based selection: 
   - If score rising → maintain genre
   - If score falling → switch to crowd favorite
3. Random from high-rated songs

### C. Manual Override?
**User controls:**
- DJ can skip song
- DJ can reject Gemini suggestion
- DJ can set "manual mode" (Gemini gives advice but doesn't auto-play)

---

## 6. API RATE LIMITS & COSTS

### Gemini API Considerations
- **Free tier:** 15 requests/min, 1500 requests/day
- **Cost per song:** ~1 request (assuming song is 3 min)
- **4-hour party:** ~80 songs → 80 requests → Well within limits

### Optimization
- Cache recommendations (get 3 songs per call)
- Only call on significant events
- Use streaming for long responses

---

## 7. DATA PERSISTENCE

### What to Save?
```python
session_data = {
    "session_id": "party_2025_11_08",
    "start_time": datetime,
    "end_time": datetime,
    "total_songs": 80,
    "avg_crowd_score": 0.65,
    "peak_score": 0.92,
    "song_history": [...],
    "prediction_accuracy": 0.85,
    "gemini_calls": 80,
    "genre_distribution": {"Pop": 25, "Electronic": 30, ...}
}
```

### Storage Options
1. **JSON file** (simple)
2. **SQLite database** (queryable)
3. **Cloud storage** (persistent)

---

## Implementation Priority

### Phase 1: Core Integration ⭐ (Now)
- ✅ Environment variables (.env)
- ✅ Gemini API setup
- ✅ Context builder function
- ✅ Basic prompt engineering
- ✅ Response parser

### Phase 2: Feedback Loop (Next)
- Song history tracking
- Prediction validation
- Learning from mistakes

### Phase 3: Advanced Features (Later)
- Manual override UI
- Session analytics
- Multi-party learning

---

**Next Step:** Create `.env` file structure and Gemini integration endpoint
