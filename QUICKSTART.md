# AI DJ Assistant - Quick Start Guide

## 🚀 Setup (One-time)

1. **Install dependencies:**
   ```bash
   pip install google-generativeai python-dotenv numpy
   ```
   
2. **Configure API key:**
   - Your key is already in `.env`: `AIzaSyDx5OwoturDv_u3SIlzFgWygerrvNr_-kY`
   - ✅ Ready to use!

## ▶️ Start Server

```bash
python .\backend\app.py
```

You should see:
```
==================================================
Starting Flask server on http://127.0.0.1:5000
==================================================
Endpoints:
  GET  /health              - Health check
  POST /classify-audio     - Analyze audio crowd reaction
  POST /gemini-recommend   - Get AI song recommendations
  POST /update-song        - Update current/end song tracking
  GET  /party-state        - Get party statistics
  POST /reset-party        - Reset party session
==================================================
✓ Gemini AI integration ENABLED
==================================================
```

## 🧪 Test Integration

In a new terminal:
```bash
python test_gemini_integration.py
```

This will:
1. Reset party state
2. Simulate 3 songs with different crowd reactions
3. Track each song's performance
4. **Call Gemini AI for recommendations**
5. Display analysis and next song suggestions

## 📊 Check Party State

```bash
curl http://127.0.0.1:5000/party-state
```

## 🎵 Get Recommendations

```bash
curl -X POST http://127.0.0.1:5000/gemini-recommend
```

## 🔧 New Features Added

### 1. Gemini Integration
- ✅ Analyzes crowd mood and energy
- ✅ Recommends next 3 songs with reasoning
- ✅ Predicts expected enthusiasm scores
- ✅ Provides strategic warnings and tips

### 2. Song Tracking
- ✅ Track current playing song
- ✅ Collect reactions during song
- ✅ Calculate avg/peak/min scores
- ✅ Compare predicted vs actual performance
- ✅ Song history with outcomes

### 3. Party Analytics
- ✅ Party stage detection (early/mid/peak/late)
- ✅ Real-time statistics
- ✅ Historical trends (30s, 1min, 5min averages)
- ✅ Learning from past performance

## 📁 New Files

- `backend/app.py` - Updated with Gemini integration
- `test_gemini_integration.py` - Full integration test
- `GEMINI_API_REFERENCE.md` - API documentation
- `GEMINI_SETUP.md` - Setup instructions
- `GEMINI_INTEGRATION_SPEC.md` - Technical spec
- `.env` - Configuration (API key)
- `.gitignore` - Protects secrets

## 🎯 Next Steps

1. ✅ Backend complete with Gemini
2. ⏳ Build React frontend for live monitoring
3. ⏳ Add microphone capture
4. ⏳ Real-time visualization
5. ⏳ Manual DJ override controls

## 💡 Usage Tips

### Continuous Analysis Loop
```python
while party_active:
    # Every 5 seconds
    analyze_audio()  # Updates enthusiasm_score
    
    # Every 3-4 minutes (when song ends)
    end_song()  # Calculates performance
    recommendations = get_gemini_recommendations()
    play_next_song(recommendations[0])
```

### Emergency Override
If crowd reaction is negative (<-0.5), Gemini will:
- Urgency: HIGH
- Action: "Play guaranteed crowd favorite NOW"
- Strategy: Emergency intervention mode

### Learning System
- Gemini sees past song performance
- Adapts recommendations based on what worked
- Improves prediction accuracy over time

---

**Status**: ✅ Gemini integration complete and ready to test!
