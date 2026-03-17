# Cost Estimates

## Cost Per Video

### Hybrid Mode (Phase 1 — APIs for images, local for everything else)

| Component | Tool | Cost Per Video | Notes |
|---|---|---|---|
| Script | Ollama (local) | $0.00 | Free, runs locally |
| Images | Replicate FLUX.1 | $0.025 | 7 images × ~$0.0035 each |
| Voice | Kokoro TTS (local) | $0.00 | Free, runs locally |
| Music | Suno free tier | $0.00 | 50 songs/day free |
| Assembly | MoviePy (local) | $0.00 | Free, runs locally |
| Upload | YouTube API | $0.00 | Free quota |
| **Total** | | **~$0.025** | |

### Full Local Mode (Phase 2 — everything on-device)

| Component | Tool | Cost Per Video | Notes |
|---|---|---|---|
| Script | Ollama (local) | $0.00 | |
| Images | ComfyUI + FLUX.1 (local) | $0.00 | Electricity only |
| Voice | Kokoro TTS (local) | $0.00 | |
| Music | MusicGen (local) | $0.00 | |
| Assembly | MoviePy (local) | $0.00 | |
| Upload | YouTube API | $0.00 | |
| **Total** | | **~$0.00** | Only electricity |

### Premium Mode (highest quality, all APIs)

| Component | Tool | Cost Per Video | Notes |
|---|---|---|---|
| Script | Claude Haiku API | ~$0.001 | ~1000 tokens in/out |
| Images | Replicate FLUX.1.1 Pro | $0.025 | 7 images |
| Voice | ElevenLabs | ~$0.01 | ~800 chars @ $5/mo plan |
| Music | Suno paid | ~$0.002 | |
| Assembly | Local | $0.00 | |
| **Total** | | **~$0.038** | |

---

## Monthly Cost Projections

Assuming **Hybrid Mode** (most practical starting point):

| Videos/Month | Image Cost | Other APIs | Total/Month |
|---|---|---|---|
| 10 | $0.25 | $0.00 | **$0.25** |
| 30 | $0.75 | $0.00 | **$0.75** |
| 100 | $2.50 | $0.00 | **$2.50** |
| 300 | $7.50 | $0.00 | **$7.50** |
| 1,000 | $25.00 | $0.00 | **$25.00** |

At 1,000 videos/month, cost is still just **$25/month** — dominated entirely by image generation.

---

## API Pricing Reference (as of 2026)

### Replicate — FLUX.1 Image Generation
| Model | Cost per image |
|---|---|
| `flux-1.1-pro` | ~$0.040 |
| `flux-dev` | ~$0.025 |
| `flux-schnell` | ~$0.003 |

**Recommendation:** Use `flux-dev` for quality, `flux-schnell` for speed/cost. The quality difference for cartoon/illustration styles is minimal.

### ElevenLabs — TTS (if upgrading from Kokoro)
| Plan | Monthly Cost | Characters |
|---|---|---|
| Free | $0 | 10,000 chars |
| Starter | $5 | 30,000 chars |
| Creator | $22 | 100,000 chars |

A 60-second video narration is ~800–1,000 characters. Free plan = ~10 videos/month. Starter = ~30 videos/month.

### Claude API — Script Generation (if upgrading from Ollama)
| Model | Input | Output | Cost per script |
|---|---|---|---|
| Haiku 4.5 | $0.80/MTok | $4/MTok | ~$0.001 |
| Sonnet 4.6 | $3/MTok | $15/MTok | ~$0.005 |

Ollama is free and produces comparable quality for this use case. Only switch to Claude API if script quality is noticeably insufficient.

### Suno — Music Generation
| Plan | Monthly Cost | Songs |
|---|---|---|
| Free | $0 | 50/day (non-commercial) |
| Pro | $8 | 2,500/month |
| Premier | $24 | 10,000/month |

For commercial YouTube monetization, Suno Pro ($8/month) is required. MusicGen (local, open source) is the free commercial-safe alternative.

---

## Hardware Cost Consideration

If you're running a local pipeline, electricity is the only recurring cost.

**Rough GPU power usage:**
| Task | Duration | Power | Cost (at $0.13/kWh) |
|---|---|---|---|
| 7 images via ComfyUI (M3 Pro) | ~4 min | ~25W | ~$0.0002 |
| MusicGen 65s track | ~2 min | ~20W | ~$0.0001 |
| Video assembly | ~1 min | ~15W | ~$0.00003 |
| **Total per video** | ~7 min | | **~$0.0003** |

Electricity cost per video is negligible.

### Machine Upgrade Decision

| Scenario | Recommendation |
|---|---|
| Making < 50 videos/month | Don't upgrade. Hybrid mode API cost is < $1.25/month |
| Making 50–200 videos/month | Don't upgrade. Hybrid API cost < $5/month, still cheaper than a new machine |
| Making 500+ videos/month OR want fully offline | Consider M4 Pro (36GB) — ~$2,000. Pays for itself after ~80,000 videos at hybrid cost |
| Already have M3/M4 with 36GB+ | Full local mode, zero recurring cost |

**Bottom line:** A new machine is not justified until you're producing at high volume or have a strong preference for fully offline operation.

---

## Cost Optimization Tips

1. **Use `flux-schnell` instead of `flux-dev`** — 10x cheaper per image, negligible quality difference for cartoon styles
2. **Batch image generation** — Replicate charges per job; batching 7 images together vs. sequential calls has the same cost but is faster
3. **Cache music** — Generate 10–20 generic background tracks once, reuse them across videos. Music doesn't need to be unique per video
4. **Reuse voice models locally** — Kokoro loads in ~2 seconds; keep it warm between videos in batch mode
5. **Compress output** — Use H.264 with CRF 23 for YouTube (good quality, smaller file). TikTok accepts up to 4GB so quality is fine either way

---

## Break-Even With YouTube Monetization

YouTube pays ~$1–$5 RPM (revenue per 1,000 views) for kids educational content.

| Videos | Avg Views/Video | Monthly Views | Est. Monthly Revenue |
|---|---|---|---|
| 30 | 500 | 15,000 | $15–$75 |
| 30 | 2,000 | 60,000 | $60–$300 |
| 100 | 2,000 | 200,000 | $200–$1,000 |

At 30 videos/month with Hybrid mode, your cost is **< $1/month**. Even modest viewership covers costs immediately.
