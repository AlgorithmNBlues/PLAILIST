# PLAILIST - DJ Attendee Fingerprint Server

A mock server that generates user music fingerprints from Spotify track data for group recommendation systems.

## 🎵 Features

- **User Fingerprinting**: Analyzes user listening habits to generate comprehensive profiles
- **Top Genres**: Identifies top 10 genres with counts and percentages
- **Top Artists**: Tracks most-played artists with frequency data
- **Language Detection**: Detects languages in track and artist names (10+ languages supported)
- **CSV-Based Data**: Loads real Spotify track data from CSV files
- **Simple API**: Single endpoint returning JSON fingerprints for all users

## 📊 Data Included

The server loads data from 3 CSV files:
- **ASM (Arin)**: 7 tracks
- **Atharva Prabhu**: 315 tracks
- **Jayanth Shanmugam**: 439 tracks

**Total**: 761 tracks across 3 users

## 🚀 Quick Start

### Installation

```bash
npm install express
```

### Running the Server

```bash
node fingerprint-server.js
```

The server will start on `http://localhost:8000`

### API Endpoint

**GET** `/api/fingerprints`

Returns fingerprint data for all users:

```json
{
  "total_users": 3,
  "fingerprints": [
    {
      "user_id": "arin_asm",
      "user_name": "ASM",
      "total_tracks": 7,
      "top_genres": [
        { "genre": "pop", "count": 87, "percentage": "19.82" }
      ],
      "top_artists": [
        { "artist": "Tyler, The Creator", "count": 12, "percentage": "2.73" }
      ],
      "top_languages": [
        { "language": "english", "count": 850, "percentage": "96.82" }
      ],
      "average_popularity": 67.8,
      "unique_genres": 125,
      "unique_artists": 287
    }
  ]
}
```

## 📁 Project Structure

```
PLAILIST/
├── fingerprint-server.js          # Main server file
├── spotify_tracks_arin.csv        # ASM's track data
├── spotify_tracks_atharva.csv     # Atharva's track data
├── spotify_tracks_jayanth.csv     # Jayanth's track data
├── package.json                   # Dependencies
└── README.md                      # This file
```

## 🔧 How It Works

1. **CSV Parsing**: Loads track data from CSV files with proper quote handling
2. **Genre Analysis**: Counts genre occurrences and ranks by frequency
3. **Artist Analysis**: Tracks artist play counts across all tracks
4. **Language Detection**: Uses regex patterns to detect 10+ languages
5. **Fingerprint Generation**: Creates comprehensive user profiles with statistics

## 🌐 Frontend Integration

Your frontend can fetch fingerprint data with:

```javascript
fetch('http://localhost:8000/api/fingerprints')
  .then(res => res.json())
  .then(data => {
    console.log('Users:', data.total_users);
    console.log('Fingerprints:', data.fingerprints);
  });
```

## 📝 CSV Format

Expected CSV columns:
- `user_id` - Unique user identifier
- `user_name` - Display name
- `track_id` - Spotify track ID
- `track_name` - Track title
- `artist_names` - Semicolon-separated artist names
- `genres` - Semicolon-separated genre tags
- `album_name` - Album title
- `release_date` - Release date
- `popularity` - Spotify popularity score (0-100)
- `duration_ms` - Track duration in milliseconds
- `explicit` - Boolean for explicit content

## 🎯 Use Case

This server enables group music recommendation systems by:
- Identifying common genres across users
- Finding shared artist preferences
- Analyzing musical diversity in groups
- Building collaborative playlists based on group fingerprints

## 👥 Branch: dj-attendee-fingerprint

This branch contains the fingerprint server implementation for DJ and attendee music profile analysis.