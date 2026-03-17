# WonderReel

> AI-powered pipeline that automatically generates 1-minute educational videos for kids and publishes them to YouTube, TikTok, and Instagram Reels.

---

## What Is WonderReel?

WonderReel is a fully automated content engine. You give it a topic — or let it pick one — and it produces a polished, narrated, illustrated short video suitable for children aged 4–10, ready to publish on social platforms.

Every part of the pipeline is driven by AI: the script, the visuals, the voice, and the background music. Human involvement is optional.

---

## Goals

- Generate high-quality, age-appropriate educational videos with minimal human input
- Keep per-video cost under $0.10 using open-source models and cheap APIs
- Produce platform-optimized output (vertical 9:16 for TikTok/Reels, horizontal 16:9 for YouTube)
- Support batch production — run overnight, wake up to a queue of ready-to-publish videos
- Build a consistent visual brand across all videos

---

## Key Features


| Feature               | Description                                                |
| --------------------- | ---------------------------------------------------------- |
| Script generation     | LLM-generated 60-second kids scripts with scene breakdowns |
| Illustrated scenes    | AI-generated images with consistent art style per video    |
| Natural voiceover     | High-quality TTS narration in a warm, child-friendly voice |
| Background music      | AI-generated royalty-free music matched to video mood      |
| Auto subtitles        | Burned-in captions synced to narration                     |
| Multi-platform export | Outputs both vertical (9:16) and horizontal (16:9) formats |
| Auto-upload           | Publishes directly to YouTube via API (TikTok optional)    |
| Topic pipeline        | Manual topics or auto-generated from a curated topic bank  |

---

## Tech Stack Summary


| Layer         | Tool                                          | License                   |
| ------------- | --------------------------------------------- | ------------------------- |
| Orchestration | Python                                        | Open source               |
| Script        | Ollama + Llama 3.3                            | Open source / free        |
| Images        | FLUX.1 via ComfyUI (local) or Replicate (API) | Open source / pay-per-use |
| Voice         | Kokoro TTS                                    | Open source / free        |
| Music         | Meta MusicGen (local) or Suno (web)           | Open source / free tier   |
| Assembly      | MoviePy + FFmpeg                              | Open source / free        |
| Subtitles     | Auto from script                              | —                        |
| Upload        | YouTube Data API v3                           | Free                      |

---

## Project Structure

```
wonderreel/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md       # System design and data flow
│   ├── COMPONENTS.md         # Detailed component documentation
│   └── COST.md               # Cost estimates and optimization
├── pipeline/
│   ├── __init__.py
│   ├── script.py             # Script generation
│   ├── images.py             # Image generation
│   ├── voice.py              # TTS narration
│   ├── music.py              # Background music
│   ├── assembly.py           # Video assembly
│   └── upload.py             # Platform upload
├── config/
│   ├── settings.yaml         # Global config (resolution, voice, style)
│   └── prompts/              # LLM prompt templates
├── topics/
│   └── topic_bank.yaml       # Curated list of kid-friendly topics
├── output/
│   ├── assets/               # Generated images, audio
│   └── videos/               # Final rendered videos
└── requirements.txt
```

---

## Phases

### Phase 1 — MVP (Hybrid Mode)

Run script, voice, and assembly locally. Offload image generation and music to APIs. Validate output quality and publish first videos manually.

### Phase 2 — Full Local Pipeline

Replace API calls with local models (ComfyUI for FLUX.1, MusicGen). Achieve near-zero per-video cost. Add batch scheduling.

### Phase 3 — Auto-Publish + Analytics

Integrate YouTube upload API. Track view counts and use performance data to guide future topic selection.

---

## Quick Start (planned)

```bash
git clone https://github.com/yourname/wonderreel
cd wonderreel
pip install -r requirements.txt

# Generate a single video
python -m pipeline.run --topic "Why is the sky blue?"

# Batch mode from topic bank
python -m pipeline.run --batch --count 5
```

---

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system design.
See [`docs/COMPONENTS.md`](docs/COMPONENTS.md) for details on each tool.
See [`docs/COST.md`](docs/COST.md) for cost breakdown and estimates.
