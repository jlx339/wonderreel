# Architecture

## Pipeline Overview

WonderReel is a sequential, stage-based pipeline. Each stage produces artifacts consumed by the next. Stages are independently swappable — you can replace any component without touching the rest.

```
┌─────────────┐
│  Topic Input │  (manual string or auto-picked from topic bank)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Script    │  LLM → narration text + scene descriptions
│  Generator  │
└──────┬──────┘
       │
       ├──────────────────────┐
       ▼                      ▼
┌─────────────┐        ┌─────────────┐
│   Image     │        │  Voiceover  │  (parallel)
│  Generator  │        │  Generator  │
└──────┬──────┘        └──────┬──────┘
       │                      │
       │        ┌─────────────┘
       ▼        ▼
┌──────────────────┐
│  Music Generator │  (generates based on script mood)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Video Assembler │  FFmpeg + MoviePy
│  - sync audio    │
│  - transitions   │
│  - subtitles     │
│  - format export │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Upload / Export │  YouTube API or local file
└──────────────────┘
```

---

## Data Flow

### 1. Topic → Script

**Input:** A topic string, e.g. `"How do volcanoes work?"`

**Output:** A structured script object:
```json
{
  "title": "How Do Volcanoes Work?",
  "narration": "Full 60-second narration text...",
  "scenes": [
    { "id": 1, "text": "Deep inside the Earth...", "image_prompt": "cross-section of Earth with magma, bright cartoon style" },
    { "id": 2, "text": "Pressure builds up...",    "image_prompt": "glowing orange magma rising, dramatic light" },
    ...
  ],
  "mood": "adventurous and exciting",
  "target_age": "5-8"
}
```

### 2. Script → Images

Each scene's `image_prompt` is sent to FLUX.1. A consistent style prefix is prepended to every prompt to maintain visual brand identity across the video.

**Style prefix example:**
```
"children's book illustration, flat design, bright colors, friendly,
 warm lighting, simple shapes, no text, [scene description]"
```

Output: 6–8 PNG images at 1792×1024 (landscape) or 1024×1792 (portrait)

### 3. Script → Voiceover

The full `narration` text is passed to Kokoro TTS. Output is a single WAV file.

Timing metadata (word-level timestamps) is extracted for subtitle sync.

### 4. Script → Music

The `mood` field is used to generate a prompt for MusicGen:
```
"cheerful background music for kids, upbeat, no lyrics, 65 seconds, [mood]"
```

Output: a WAV file slightly longer than the narration (padded, then trimmed at assembly).

### 5. Assembly

MoviePy combines all assets:

1. Each image is displayed for `total_duration / num_scenes` seconds
2. Crossfade transitions (0.3s) between scenes
3. Voiceover audio layer at 100% volume
4. Music audio layer at 20% volume
5. Subtitles burned in (white text, black outline, bottom third)
6. Export in two formats:
   - `output_16x9.mp4` — YouTube (1920×1080)
   - `output_9x16.mp4` — TikTok/Reels (1080×1920), images center-cropped

---

## Hybrid vs. Full Local Mode

### Hybrid Mode (recommended for Phase 1)

```
Script       → Ollama (local)
Images       → Replicate API (remote)
Voice        → Kokoro TTS (local)
Music        → Suno web app (manual) or MusicGen API
Assembly     → MoviePy (local)
```

Good for: M1/M2 Macs with 8–16GB RAM. Fast iteration, low cost.

### Full Local Mode (Phase 2)

```
Script       → Ollama (local)
Images       → FLUX.1 via ComfyUI (local, needs 16GB+ RAM)
Voice        → Kokoro TTS (local)
Music        → MusicGen (local, MPS accelerated)
Assembly     → MoviePy (local)
```

Good for: M3/M4 Macs with 36GB+ unified memory. Zero API cost.

---

## Configuration

All behavior is controlled via `config/settings.yaml`:

```yaml
pipeline:
  mode: hybrid           # hybrid | local
  output_formats:
    - 16x9
    - 9x16

script:
  model: llama3.3        # ollama model name
  target_age: "5-8"
  duration_seconds: 60
  scenes_count: 7

images:
  provider: replicate    # replicate | comfyui
  style_prefix: "children's book illustration, flat design, bright colors, friendly, warm lighting, simple shapes, no text"
  width: 1792
  height: 1024

voice:
  provider: kokoro       # kokoro | elevenlabs
  voice_id: "af_heart"   # warm, child-friendly voice

music:
  provider: musicgen     # musicgen | suno
  duration_seconds: 65

assembly:
  transition_duration: 0.3
  music_volume: 0.2
  subtitle_font_size: 48

upload:
  youtube:
    enabled: false
    category: "Education"
    tags: ["kids", "learning", "education"]
```

---

## Error Handling Strategy

Each stage writes its outputs to `output/assets/{run_id}/` before the next stage begins. If any stage fails, the pipeline can resume from the last successful checkpoint rather than restarting from scratch.

```
output/assets/
└── run_20260316_143022/
    ├── script.json       ← checkpoint 1
    ├── scene_01.png      ← checkpoint 2
    ├── scene_02.png
    ├── ...
    ├── narration.wav     ← checkpoint 3
    ├── music.wav         ← checkpoint 4
    └── final_16x9.mp4    ← checkpoint 5
```
