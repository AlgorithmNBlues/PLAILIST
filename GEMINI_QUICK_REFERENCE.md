# Gemini Integration - Quick Reference

## 📥 INPUT TO GEMINI

### What we send (JSON format):
```json
{
  "crowd_state": {
    "enthusiasm_score": 0.68,          // -1.5 to +1.0
    "trend": "rising",                  // rising/falling/stable
    "probs": {...},                     // cheering/applause/chatter/booing/music
    "interpretation": "Highly engaged"
  },
  "temporal_context": {
    "score_history_30s": [0.52, 0.58, 0.61, 0.65, 0.68],
    "avg_score_1min": 0.61,
    "avg_score_5min": 0.58
  },
  "party_context": {
    "stage": "mid",                     // early/mid/peak/late
    "elapsed_minutes": 45,
    "total_songs_played": 12,
    "current_song": {...}
  },
  "song_history": [
    {
      "title": "Song A",
      "genre": "Electronic",
      "avg_reaction_score": 0.72,
      "outcome": "success"
    }
    // ... last 5 songs
  ]
}
```

---

## 📤 OUTPUT FROM GEMINI

### What we receive:
```json
{
  "analysis": {
    "crowd_mood": "Energetic and engaged",
    "energy_trajectory": "Steadily rising",
    "recommendations_reasoning": "Continue building energy"
  },
  "action": {
    "recommendation": "increase_energy",  // maintain/increase/wind_down/change_genre
    "urgency": "normal",                  // low/normal/high
    "confidence": 0.85
  },
  "next_songs": [
    {
      "title": "Song Title 1",
      "artist": "Artist Name 1",
      "genre": "Electronic",
      "reasoning": "Matches rising momentum",
      "predicted_impact": {
        "enthusiasm_delta": "+0.10 to +0.15",
        "expected_score": 0.75
      },
      "priority": 1
    }
    // ... 2 more songs
  ],
  "warnings": [
    "Monitor for plateau",
    "Avoid slow tracks for next 10-15 minutes"
  ]
}
```

---

## 🔄 FEEDBACK LOOP

### What goes back into the app:

1. **Play recommended song**
   ```python
   current_song = gemini_response["next_songs"][0]
   play_song(current_song)
   ```

2. **Track reactions during song**
   ```python
   # Every 5 seconds while song plays
   reactions_during_song.append(enthusiasm_score)
   ```

3. **After song ends, update history**
   ```python
   song_history.append({
       "title": current_song["title"],
       "avg_reaction_score": np.mean(reactions_during_song),
       "peak_reaction": np.max(reactions_during_song),
       "predicted_score": 0.75,  # From Gemini
       "actual_score": 0.72,     # What we measured
       "prediction_accuracy": 0.03
   })
   ```

4. **Learn from mistakes**
   ```python
   # If Gemini's predictions are consistently wrong
   if avg_prediction_error > 0.2:
       context["feedback"] = {
           "note": "Recent predictions off by 0.2 points",
           "adjust": "Be more conservative"
       }
   ```

5. **Feed updated context back to Gemini**
   - Next API call includes updated song_history
   - Gemini sees what worked/didn't work
   - Adapts recommendations accordingly

---

## 🔄 COMPLETE CYCLE

```
Every 5 seconds:
  ├─ Capture audio
  ├─ Analyze crowd reaction
  └─ Update enthusiasm score

Every 3-4 minutes (per song):
  ├─ Build context (crowd + history + party state)
  ├─ Call Gemini API
  ├─ Get song recommendations
  ├─ Play top recommendation
  ├─ Monitor reactions
  ├─ After song: compare predicted vs actual
  └─ Update history for next cycle
```

---

## 📊 DATA FLOW DIAGRAM

```
┌──────────────┐
│ Audio Input  │
└──────┬───────┘
       │
       ↓
┌──────────────────┐
│ HF Model         │ → enthusiasm_score, probs, trend
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│ Context Builder  │ → Aggregates: crowd + history + party
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│ Gemini API       │ → Analyzes context
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│ Response Parser  │ → Extracts: next_songs, warnings, predictions
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│ Action Executor  │ → Plays song, tracks reactions
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│ Feedback Loop    │ → Updates history, validates predictions
└──────┬───────────┘
       │
       └──────────────→ (back to Context Builder)
```

---

## 🎯 KEY METRICS

### We Track:
- **Enthusiasm score**: -1.5 to +1.0
- **Trend**: rising/falling/stable
- **Prediction accuracy**: How close Gemini's predictions are
- **Song performance**: avg/peak/min reaction per song
- **Genre effectiveness**: Which genres work best for this crowd

### We Optimize For:
- Maintaining high enthusiasm (>0.5)
- Smooth energy transitions (avoid sudden drops)
- Genre diversity (not repetitive)
- Prediction accuracy (Gemini learns)

---

## 🛠️ SETUP REQUIRED

1. **Install dependencies**:
   ```bash
   pip install google-generativeai python-dotenv numpy
   ```

2. **Get Gemini API key**: https://aistudio.google.com/app/apikey

3. **Configure .env file**:
   ```
   GEMINI_API_KEY=your_key_here
   ```

4. **Create endpoints**:
   - `/gemini-recommend` - Get song recommendations
   - `/update-song-history` - Track song outcomes
   - `/session-stats` - View analytics

---

## 📝 NEXT STEPS

1. ✅ Create .env file structure
2. ⏳ Implement context builder function
3. ⏳ Implement Gemini API integration
4. ⏳ Create response parser
5. ⏳ Build feedback tracking system
6. ⏳ Add endpoints to Flask app
7. ⏳ Test with sample data
8. ⏳ Build frontend UI

---

**Status**: Ready to implement Phase 1 (Core Integration)
