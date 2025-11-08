# Gemini Integration Architecture

## Improvements to Current System

### 1. Revise Enthusiasm Score Formula
```python
# Current weights (too lenient)
W1, W2, W3, W4 = 1.0, 0.8, 0.5, 1.2

# Proposed weights (more discriminative)
W1, W2, W3, W4 = 1.0, 0.7, 0.6, 1.5
# Rationale:
# - Reduce applause (0.8→0.7): Often background noise
# - Increase chatter penalty (0.5→0.6): Talking = not engaged
# - Increase booing penalty (1.2→1.5): More severe negative signal
```

### 2. Add Party Stage Logic
```python
def calculate_party_stage(elapsed_minutes, avg_enthusiasm_5min, current_trend):
    """Determine party phase based on time and energy"""
    
    # Early: First 30 min OR low energy OR just starting up
    if elapsed_minutes < 30 or avg_enthusiasm_5min < 0.3:
        return "early"
    
    # Peak: 30-120 min AND high sustained energy
    elif 30 <= elapsed_minutes < 120 and avg_enthusiasm_5min > 0.6:
        return "peak"
    
    # Winding down: After 120 min OR declining energy for 10+ min
    elif elapsed_minutes >= 120 or (current_trend == "falling" and avg_enthusiasm_5min < 0.5):
        return "late"
    
    # Mid: Everything else (transition phases)
    else:
        return "mid"
```

### 3. Context Aggregation for Gemini
```python
def build_gemini_context():
    """Construct rich context for Gemini API"""
    return {
        "crowd_state": {
            "current_probs": last_probs,  # Raw HF output
            "enthusiasm_score": current_score,
            "trend": current_trend,  # rising/falling/stable
            "timestamp": datetime.now().isoformat()
        },
        
        "temporal_context": {
            "history_30s": SCORE_HISTORY[-6:],  # Last 30 sec (5s intervals)
            "avg_score_1min": np.mean(SCORE_HISTORY[-12:]),
            "avg_score_5min": np.mean(SCORE_HISTORY[-60:]),
            "score_variance": np.var(SCORE_HISTORY[-12:])  # Stability indicator
        },
        
        "party_context": {
            "stage": calculate_party_stage(...),
            "elapsed_minutes": (datetime.now() - party_start_time).seconds // 60,
            "total_songs_played": len(song_history),
            "crowd_size_estimate": "medium"  # Could add people counting later
        },
        
        "song_history": [
            {
                "title": song.title,
                "artist": song.artist,
                "genre": song.genre,
                "played_at": song.timestamp,
                "avg_reaction_score": song.reaction_score,
                "peak_reaction": song.peak_score
            }
            for song in song_history[-5:]  # Last 5 songs
        ]
    }
```

### 4. Gemini API Call Structure
```python
def get_gemini_recommendation(context):
    """Query Gemini for next actions"""
    
    prompt = f"""
You are an AI DJ assistant analyzing a live party. Based on the crowd analysis below, 
recommend the next 3 songs to play and explain your reasoning.

CROWD STATE:
- Current enthusiasm: {context['crowd_state']['enthusiasm_score']:.2f} (scale -1 to 1)
- Trend: {context['crowd_state']['trend']}
- Crowd reaction breakdown: {json.dumps(context['crowd_state']['current_probs'], indent=2)}

TEMPORAL CONTEXT:
- Last 30s scores: {context['temporal_context']['history_30s']}
- 5-min average: {context['temporal_context']['avg_score_5min']:.2f}

PARTY CONTEXT:
- Stage: {context['party_context']['stage']}
- Time elapsed: {context['party_context']['elapsed_minutes']} minutes
- Songs played: {context['party_context']['total_songs_played']}

RECENT SONGS:
{json.dumps(context['song_history'], indent=2)}

Provide response in JSON format:
{{
  "vibe_analysis": "Brief assessment of crowd mood and energy",
  "recommended_action": "maintain_energy | increase_energy | wind_down | change_genre",
  "next_songs": [
    {{"title": "Song Name", "artist": "Artist", "reason": "Why this song"}},
    ...
  ],
  "confidence": 0.85,
  "warnings": ["Any concerns, e.g., 'Energy declining for 5+ min'"]
}}
"""
    
    response = gemini_model.generate_content(prompt)
    return json.loads(response.text)
```

### 5. Feedback Loop Implementation
```python
# Main loop structure
party_start_time = datetime.now()
song_history = []
current_song = None

while party_active:
    # Step 1: Capture and analyze audio every 5 seconds
    audio_buffer = capture_microphone(duration=5)
    analysis = classify_audio(audio_buffer)
    
    # Step 2: Update history
    SCORE_HISTORY.append(analysis['enthusiasm_score'])
    
    # Step 3: Check if song should change (every 3-4 minutes)
    if should_request_new_song(current_song):
        context = build_gemini_context()
        recommendation = get_gemini_recommendation(context)
        
        # Step 4: Apply recommendation
        next_song = select_song_from_recommendation(recommendation)
        play_song(next_song)
        
        # Step 5: Log for learning
        if current_song:
            current_song['avg_reaction_score'] = np.mean(current_song['reactions'])
            song_history.append(current_song)
        
        current_song = {
            'title': next_song.title,
            'reactions': [],
            'start_time': datetime.now()
        }
    
    # Track reaction to current song
    if current_song:
        current_song['reactions'].append(analysis['enthusiasm_score'])
    
    time.sleep(5)  # Analyze every 5 seconds
```

## Key Differences from Your Original Plan

| Your Plan | Improved Plan |
|-----------|---------------|
| Manually classify `current_vibe` | Let Gemini interpret raw features |
| Single current snapshot | Rich temporal history (30s, 1min, 5min) |
| Basic party_stage (early/mid/late) | Hybrid timing + energy-based stages |
| Static formula | Tunable weights based on testing |
| No song tracking | Track reactions per song for learning |

## Additional Features to Consider

1. **Genre diversity tracking**: Prevent playing same genre 3x in a row
2. **Energy trajectory**: Gemini can plan multi-song arcs (build → peak → sustain)
3. **Crowd size estimation**: Use audio amplitude + speech overlap
4. **Intervention alerts**: "Crowd losing interest - recommend high-energy track NOW"
5. **A/B testing**: Try Gemini vs. rule-based recommendations, compare outcomes

## Testing Strategy

1. **Collect baseline data**: Run party with manual DJ, log all scores
2. **Offline simulation**: Replay audio logs, test Gemini recommendations
3. **Shadow mode**: Run Gemini in parallel but don't apply (compare to human DJ)
4. **Gradual rollout**: Use Gemini for 50% of decisions, monitor
5. **Full automation**: Let Gemini drive all song selections

## Expected Outcomes

- **Better timing**: Gemini understands context (e.g., don't play slow song when energy rising)
- **Genre matching**: Crowd reactions guide music style selection
- **Proactive adjustments**: Detect declining energy early, intervene before crowd disengages
- **Learning over time**: Song history shows what works for this crowd
