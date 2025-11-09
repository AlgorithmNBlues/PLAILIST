import 'dotenv/config';
import fs from 'fs';
import { spawn } from 'child_process';
import fetch from 'node-fetch';

const VOICE_ID = process.env.ELEVEN_VOICE_ID || 'Rachel';
const API_KEY  = process.env.ELEVENLABS_API_KEY;

function now() { return Date.now(); }

const PROMPTS = {
  warmup: [
    "How we feeling, crew? Energy check!",
    "Hands up if you're ready to lift the room—how's the vibe?"
  ],
  peak: [
    "Vibes on max? Let me hear you!",
    "How's the energy—are we peaking right now?"
  ],
  recovery: [
    "Quick check—do we push it harder or keep it smooth?",
    "How are the vibes—need a lift or keep this groove?"
  ],
  cooldown: [
    "How's the energy out there—still with me?",
    "Vibes good? Want one more before we land?"
  ],
  fallback: [
    "How's the energy out there?",
    "Talk to me—how are the vibes?"
  ]
};

function pick(arr){ return arr[Math.floor(Math.random()*arr.length)]; }

class EnergyPrompter {
  constructor(opts={}){
    this.minIntervalMs   = opts.minIntervalMs   ?? 10000;  // 2 min between crowd prompts
    this.minScoreToAsk   = opts.minScoreToAsk   ?? 35;      // don’t ask if totally flatlined
    this.dropToAsk       = opts.dropToAsk       ?? 15;      // ask if drop ≥ 15 in last window
    this.trendWindow     = opts.trendWindow     ?? 3;       // need N consecutive falling ticks
    this.noTalkGateMs    = opts.noTalkGateMs    ?? 8000;    // guard after any TTS/music cue
    this.lastPromptAt    = 0;
    this.lastTtsAt       = 0;
    this.recentScores    = [];
    this.maxHistory      = 10;
    this.duckHook        = opts.duckHook;  // optional: (on)=>void to duck/restore music
  }

  onAnyAudioActivity(){ this.lastTtsAt = now(); }

  ingest({ score, trend, state, anomaly, ts=now() }){
    // Keep short history
    this.recentScores.push({ts, score});
    if (this.recentScores.length > this.maxHistory) this.recentScores.shift();

    if (!this.shouldConsiderAsking({score, trend, state, anomaly})) return;

    const line = this.selectPrompt({state});
    this.speak(line);
  }

  shouldConsiderAsking({score, trend, state, anomaly}){
    const t = now();
    if (t - this.lastPromptAt < this.minIntervalMs) return false;   // prompt cooldown
    if (t - this.lastTtsAt    < this.noTalkGateMs)  return false;   // avoid barge/self-trigger
    if (score < this.minScoreToAsk) return false;                    // room too flat—play music first

    // Ask on: sustained falling trend OR anomaly big drop OR recovery checkpoint
    const fallingStreak = this.isFallingStreak(this.trendWindow);
    const bigDrop = this.recentDrop() >= this.dropToAsk;
    const recoveryMoment = state === 'recovery';

    const permit = fallingStreak || bigDrop || anomaly?.type === 'mass_exit' || recoveryMoment;
    return permit;
  }

  isFallingStreak(N){
    if (this.recentScores.length < N+1) return false;
    let ok = true;
    for (let i=this.recentScores.length-1; i>this.recentScores.length-1-N; i--){
      if (!(this.recentScores[i].score < this.recentScores[i-1].score)) { ok = false; break; }
    }
    return ok;
  }

  recentDrop(){
    const arr = this.recentScores;
    if (arr.length < 2) return 0;
    const a = arr[arr.length-2].score;
    const b = arr[arr.length-1].score;
    return Math.max(0, a - b);
  }

  selectPrompt({state}){
    const bank = PROMPTS[state] || PROMPTS.fallback;
    return pick(bank);
  }

  async speak(text){
    try{
      this.duckHook?.(true);                 // optional: duck music ~6–9 dB
      this.lastPromptAt = now();
      this.lastTtsAt    = now();
      const outfile = `tts_${this.lastPromptAt}.mp3`;
      await ttsToFile({ text, voiceId: VOICE_ID, outPath: outfile });
      await playFile(outfile);               // macOS: uses afplay; replace as needed
      setTimeout(()=>this.duckHook?.(false), 400); // short release after speech
    }catch(e){
      console.error('TTS error:', e.message);
      this.duckHook?.(false);
    }
  }
}

async function ttsToFile({ text, voiceId, outPath }){
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/stream`, {
    method: 'POST',
    headers: {
      'xi-api-key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text,
      model_id: 'eleven_multilingual_v2',
      optimize_streaming_latency: 1,   // lower = faster start
      voice_settings: { stability: 0.5, similarity_boost: 0.8 }
    })
  });
  if (!res.ok) throw new Error(await res.text());
  const file = fs.createWriteStream(outPath);
  await new Promise((resolve, reject)=>{
    res.body.pipe(file);
    res.body.on('error', reject);
    file.on('finish', resolve);
  });
  return outPath;
}

function playFile(path){
  return new Promise((resolve, reject)=>{
    // macOS. On Linux, use "mpg123" or "aplay"; on Windows, "powershell -c (New-Object Media.SoundPlayer ...).PlaySync()"
    const p = spawn('afplay', [path]);
    p.on('close', (code)=> code===0 ? resolve() : reject(new Error('afplay failed')));
  });
}

// --- Example wiring ---
const prompter = new EnergyPrompter({
  duckHook: (on)=> {
    // TODO: call your mixer/DAW/OBS or send MIDI to reduce master gain.
    // For now, just log:
    console.log(on ? '[DUCKING -6dB]' : '[UNDUCK]');
  }
});

// Simulate your energy layer calling this every ~10s:
//function simulate(){ 
//  const states = ['warmup','peak','recovery','cooldown'];
//  const s = 40 + Math.floor(Math.random()*50);
//  const trend = Math.random() < 0.5 ? 'falling' : 'rising';
//  const state = states[Math.floor(Math.random()*states.length)];
//  const anomaly = Math.random() < 0.1 ? {type:'mass_exit'} : null;
//  prompter.ingest({ score: s, trend, state, anomaly });
//}
//setInterval(simulate, 10000);

import http from 'http';

const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/energy') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const msg = JSON.parse(body);
        // { score: 0-100, trend: "rising"|"falling"|"stable",
        //   state: "warmup"|"peak"|"recovery"|"cooldown",
        //   anomaly: null | {type:"mass_exit"}, ts?: number }
        prompter.ingest(msg);
        res.writeHead(200); res.end('ok');
      } catch (e) {
        res.writeHead(400); res.end(e.message);
      }
    });
  } else {
    res.writeHead(404); res.end('not found');
  }
});

server.listen(5057, () => {
  console.log('Energy endpoint on http://127.0.0.1:5057/energy');
});
