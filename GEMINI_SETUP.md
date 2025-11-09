# 🎵 AI DJ Assistant - Gemini Integration Setup

## 📋 Quick Start

### 1. Get Your Gemini API Key

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key

### 2. Configure Environment

1. Open the `.env` file in the project root
2. Replace the placeholder with your actual key:
   ```
   GEMINI_API_KEY=your_actual_key_here
   ```
3. Save the file

### 3. Install Dependencies

```bash
pip install google-generativeai python-dotenv numpy
```

Or install all requirements:
```bash
pip install -r backend/requirements.txt
```

---

## 🎯 What This Does

### Input → Gemini
We send crowd analysis data:
- **Enthusiasm score** (-1.5 to +1.0)
- **Trend** (rising/falling/stable)
- **Reaction breakdown** (cheering/applause/chatter/booing)
- **History** (last 30s, 1min, 5min scores)
- **Party context** (stage, time elapsed, songs played)
- **Song history** (last 5 songs with their reaction scores)

### Gemini → Output
We receive AI recommendations:
- **Analysis** (crowd mood, energy trajectory)
- **Next 3 songs** to play with reasoning
- **Action recommendation** (increase energy / maintain / wind down)
- **Warnings** (e.g., "avoid slow tracks")
- **Predicted impact** (expected enthusiasm score)

### Output → Feedback Loop
We track and learn:
- Play recommended song
- Monitor real reactions every 5 seconds
- Compare predicted vs actual scores
- Update history for next Gemini call
- Adapt strategy if predictions are wrong

---

## 📊 Data Flow

```
Audio → HF Model → Enthusiasm Score → Context Builder → Gemini API
                                                            ↓
                                          Song Recommendations
                                                            ↓
                                          Play Song & Track
                                                            ↓
                                    Compare Predicted vs Actual
                                                            ↓
                                        Update History ────→ Loop
```

---

## 🔧 Configuration Options

Edit `.env` to customize:

```bash
# Required
GEMINI_API_KEY=your_key_here

# Model Selection
GEMINI_MODEL=gemini-2.5-flash        # Fast and cheap (recommended)
# GEMINI_MODEL=gemini-2.5-pro        # More intelligent but slower
# GEMINI_MODEL=gemini-2.0-flash      # Alternative fast model

# Creativity Control
GEMINI_TEMPERATURE=0.7               # 0.0 = conservative, 1.0 = creative

# Party Settings
PARTY_NAME=My Party
CALL_GEMINI_EVERY_N_SONGS=1         # How often to request recommendations
```

---

## 📈 Expected Results

### Score Ranges
- **+0.7 to +1.0**: Crowd loving it 🔥
- **+0.4 to +0.7**: Good energy ✅
- **+0.1 to +0.4**: Moderate interest 😐
- **-0.2 to +0.1**: Neutral / chatting 💬
- **-0.7 to -0.2**: Losing interest ⚠️
- **-1.5 to -0.7**: Negative reaction 😞

### Gemini Recommendations
Based on scores, Gemini suggests:
- **Rising trend + high score** → Maintain energy, similar genre
- **Falling trend** → Change strategy, try crowd favorite
- **Plateau** → Switch genre to refresh interest
- **Negative reaction** → Emergency intervention, play guaranteed hit

---

## 🚀 Next Steps

1. ✅ Configure `.env` with your API key
2. ⏳ Run integration test: `python test_gemini_integration.py` (coming next)
3. ⏳ Start server: `python backend/app.py`
4. ⏳ Build frontend UI for live monitoring

---

## 📚 Documentation

- **Full specification**: `GEMINI_INTEGRATION_SPEC.md`
- **Quick reference**: `GEMINI_QUICK_REFERENCE.md`
- **Implementation plan**: `backend/gemini_integration_plan.md`

---

## ⚠️ Important Notes

### Security
- ⚠️ **NEVER commit `.env` to git** (already in `.gitignore`)
- 🔒 Keep your API key private
- 🚫 Don't share screenshots with API keys visible

### API Limits (Free Tier)
- **Rate**: 15 requests/min
- **Daily**: 1500 requests/day
- **Cost**: FREE for moderate usage

### For 4-hour party:
- ~80 songs → ~80 API calls → Well within limits ✅

---

## 🐛 Troubleshooting

### "Invalid API key"
- Check `.env` file has correct key
- No spaces around `=` in `.env`
- Restart Flask server after updating `.env`

### "Rate limit exceeded"
- Free tier: 15 requests/min
- Increase `CALL_GEMINI_EVERY_N_SONGS` to reduce frequency

### "Module not found: google.generativeai"
```bash
pip install google-generativeai python-dotenv
```

---

**Status**: Environment configured ✅  
**Next**: Implement Gemini endpoints in Flask app
