// Mock Fingerprint Server - Loads real data from CSV files
// Returns user fingerprints with top genres, artists, and languages

import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 8000;

// Parse CSV file
function parseCSV(csvContent) {
  const lines = csvContent.split('\n');
  const headers = lines[0].split(',');
  const data = [];

  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    
    const values = [];
    let currentValue = '';
    let insideQuotes = false;

    for (let char of lines[i]) {
      if (char === '"') {
        insideQuotes = !insideQuotes;
      } else if (char === ',' && !insideQuotes) {
        values.push(currentValue.trim());
        currentValue = '';
      } else {
        currentValue += char;
      }
    }
    values.push(currentValue.trim());

    const row = {};
    headers.forEach((header, index) => {
      row[header.trim()] = values[index];
    });
    data.push(row);
  }

  return data;
}

// Detect language from text
function detectLanguage(text) {
  if (!text) return 'unknown';
  
  if (/[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]/.test(text)) return 'japanese/chinese';
  if (/[\u0600-\u06ff]/.test(text)) return 'arabic';
  if (/[\u0400-\u04ff]/.test(text)) return 'russian';
  if (/[\u0900-\u097f]/.test(text)) return 'hindi';
  if (/[\uac00-\ud7af]/.test(text)) return 'korean';
  if (/\b(el|la|los|las|de|del|y|con|por|para)\b/i.test(text)) return 'spanish';
  if (/\b(le|la|les|de|du|et|avec|pour)\b/i.test(text)) return 'french';
  if (/\b(der|die|das|und|mit|von)\b/i.test(text)) return 'german';
  if (/\b(o|a|os|as|de|do|da|e|com)\b/i.test(text)) return 'portuguese';
  
  return 'english';
}

// Load and process CSV files
function loadFingerprints() {
  const csvFiles = [
    './spotify_tracks_arin.csv',
    './spotify_tracks_atharva.csv',
    './spotify_tracks_jayanth.csv'
  ];

  const fingerprints = [];

  csvFiles.forEach(file => {
    const filepath = path.join(__dirname, file);
    
    if (!fs.existsSync(filepath)) {
      console.log(`⚠️  File not found: ${file}`);
      return;
    }

    const content = fs.readFileSync(filepath, 'utf-8');
    const rows = parseCSV(content);

    if (rows.length === 0) return;

    const userName = rows[0].user_name;
    const userId = rows[0].user_id;

    // Count genres
    const genreCounts = {};
    rows.forEach(row => {
      const genres = row.genres ? row.genres.split(';').map(g => g.trim()).filter(Boolean) : [];
      genres.forEach(genre => {
        genreCounts[genre] = (genreCounts[genre] || 0) + 1;
      });
    });

    // Count artists
    const artistCounts = {};
    rows.forEach(row => {
      const artists = row.artist_names ? row.artist_names.split(';').map(a => a.trim()) : [];
      artists.forEach(artist => {
        artistCounts[artist] = (artistCounts[artist] || 0) + 1;
      });
    });

    // Detect languages
    const languageCounts = {};
    rows.forEach(row => {
      const trackLang = detectLanguage(row.track_name);
      languageCounts[trackLang] = (languageCounts[trackLang] || 0) + 1;
      
      const artistLang = detectLanguage(row.artist_names);
      languageCounts[artistLang] = (languageCounts[artistLang] || 0) + 1;
    });

    // Calculate average popularity
    const avgPopularity = rows.reduce((sum, row) => sum + (parseInt(row.popularity) || 0), 0) / rows.length;

    // Build fingerprint
    const topGenres = Object.entries(genreCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([genre, count]) => ({
        genre,
        count,
        percentage: ((count / rows.length) * 100).toFixed(2)
      }));

    const topArtists = Object.entries(artistCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([artist, count]) => ({
        artist,
        count,
        percentage: ((count / rows.length) * 100).toFixed(2)
      }));

    const topLanguages = Object.entries(languageCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([language, count]) => ({
        language,
        count,
        percentage: ((count / (rows.length * 2)) * 100).toFixed(2)
      }));

    fingerprints.push({
      user_id: userId,
      user_name: userName,
      total_tracks: rows.length,
      top_genres: topGenres,
      top_artists: topArtists,
      top_languages: topLanguages,
      average_popularity: parseFloat(avgPopularity.toFixed(2)),
      unique_genres: Object.keys(genreCounts).length,
      unique_artists: Object.keys(artistCounts).length
    });

    console.log(`✓ Loaded ${userName}: ${rows.length} tracks`);
  });

  return {
    total_users: fingerprints.length,
    fingerprints
  };
}

// Load data on startup
console.log('\n📂 Loading CSV data...');
const fingerprintData = loadFingerprints();
console.log(`✅ Loaded ${fingerprintData.total_users} users\n`);

// Single endpoint - returns all fingerprints
app.get('/api/fingerprints', (req, res) => {
  res.json(fingerprintData);
});

// Health check
app.get('/', (req, res) => {
  res.json({
    message: "Mock Fingerprint Server",
    status: "running",
    endpoint: "/api/fingerprints"
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`\n🎵 Mock Fingerprint Server`);
  console.log(`📍 http://localhost:${PORT}`);
  console.log(`🔧 Endpoint: http://localhost:${PORT}/api/fingerprints`);
  console.log(`\n👥 Users: ${fingerprintData.total_users}`);
  console.log(`✅ Ready!\n`);
});
