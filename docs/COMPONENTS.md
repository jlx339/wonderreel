# Components

Detailed breakdown of every tool in the WonderReel pipeline.

---

## 1. Script Generator

### Tool: Ollama + Llama 3.3 (70B or 8B)

**What it does:** Takes a topic string and generates a structured 60-second educational script with scene breakdowns.

**Why Ollama:**
- Runs fully locally on macOS with Apple Silicon (MPS)
- Llama 3.3 70B is genuinely good at creative writing and following structured output formats
- Free, no API key, no rate limits
- 8B model is fast even on 8GB RAM; 70B is better quality on 16GB+

**Setup:**
```bash
brew install ollama
ollama pull llama3.3        # 70B, needs ~40GB, best quality
ollama pull llama3.2        # 3B, fast, needs ~2GB, decent for scripts
```

**Prompt strategy:**

Use a structured system prompt that enforces JSON output:
```
You are a children's educational content writer.
Write a 60-second video script for kids aged 5-8 about: "{topic}"

Rules:
- Use simple words a 6-year-old understands
- Include exactly 3 surprising facts
- Split into 7 scenes of ~8 seconds each
- Each scene needs: narration text + a vivid image description
- Tone: enthusiastic, warm, wonder-filled

Return valid JSON following this schema: [schema here]
```

**Fallback:** Claude API (claude-haiku-4-5) at ~$0.001/script if Ollama quality is insufficient.

---

## 2. Image Generator

### Primary: RunningHub (Cloud ComfyUI — free tier)
### Alternative: FLUX.1 via Replicate API (Hybrid Mode)
### Alternative: FLUX.1 via ComfyUI (Local Mode)

**What it does:** Generates one illustrated scene image per script scene (~7 images per video).

**Why FLUX.1:**
- State-of-the-art open-source image model (by Black Forest Labs)
- Excellent at following style instructions and maintaining visual consistency
- Significantly better than SDXL for illustration-style prompts
- Available via RunningHub cloud, Replicate API, or local ComfyUI

### RunningHub (Cloud ComfyUI — Recommended Free Option)

Runs ComfyUI workflows in the cloud. Free daily credits on signup; FLUX.1 Kontext [dev] is unlimited free.

**Setup:**
1. Sign up at https://www.runninghub.ai
2. Browse the workflow gallery and pick a FLUX.1 text-to-image workflow
3. Open the workflow, copy its **Workflow ID** from the URL or workflow settings
4. Note the **node ID** of the CLIPTextEncode (prompt) node — typically `"6"` in standard FLUX workflows
5. Add your API key (Account → API Key) to `.env`

**Config** (`config/settings.yaml`):
```yaml
images:
  provider: runninghub
  runninghub_workflow_id: "your-workflow-id"
  runninghub_prompt_node_id: "6"   # CLIPTextEncode node in your workflow
  runninghub_prompt_field: "text"
```

**`.env`:**
```
RUNNINGHUB_API_KEY=your_api_key_here
```

Cost: Free (daily credits) — FLUX.1 Kontext [dev] is unlimited free

### Replicate API (Hybrid Mode)

Easy setup, no local GPU needed:
```python
import replicate
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": f"{STYLE_PREFIX}, {scene.image_prompt}"}
)
```

Cost: ~$0.003–$0.004 per image → ~$0.025 per video (7 images)

### ComfyUI (Local Mode)

Runs on Apple Silicon via MPS. Requires 16GB+ unified memory.
- Download: https://github.com/comfyanonymous/ComfyUI
- Install FLUX.1-dev or FLUX.1-schnell (faster, slightly lower quality)
- FLUX.1-schnell: ~30s/image on M3 Pro, free after setup

**Style consistency trick:**
Prepend the same style prefix to every image prompt in a video. This creates a cohesive illustrated look throughout.

```python
STYLE_PREFIX = (
    "children's book illustration, flat design, bright warm colors, "
    "friendly characters, simple shapes, soft shadows, no text, no words"
)
full_prompt = f"{STYLE_PREFIX}, {scene.image_prompt}"
```

---

## 3. Voiceover Generator

### Tool: Kokoro TTS

**What it does:** Converts the narration text into a warm, natural-sounding audio file.

**Why Kokoro:**
- Open source (Apache 2.0), runs entirely locally
- Surprisingly high quality — comparable to commercial TTS
- Multiple voice styles available; `af_heart` is warm and friendly (good for kids content)
- Fast: a 60-second narration generates in 5–10 seconds on CPU
- No API key, no cost, no rate limits

**Setup:**
```bash
pip install kokoro-onnx soundfile
```

**Usage:**
```python
from kokoro_onnx import Kokoro
kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
samples, sample_rate = kokoro.create("Your narration text here...", voice="af_heart", speed=1.0)
```

**Voice options for kids content:**
| Voice ID | Character |
|---|---|
| `af_heart` | Warm, gentle American female — best for young kids |
| `af_sky` | Bright, energetic — good for exciting topics |
| `am_fenrir` | Friendly male voice |

**Fallback:** ElevenLabs API ($5/month, 30 min audio/month) if higher quality is needed. The "Rachel" or "Aria" voices work well for kids content.

---

## 4. Music Generator

### Tool: Meta MusicGen (Local) or Suno (Web)

**What it does:** Generates a royalty-free background music track matched to the video's mood.

### Meta MusicGen (Local Mode)

Open source model by Meta AI. Runs via the `audiocraft` library.

```bash
pip install audiocraft
```

```python
from audiocraft.models import MusicGen
model = MusicGen.get_pretrained("facebook/musicgen-small")  # 300M params, fast
model.set_generation_params(duration=65)
wav = model.generate(["upbeat cheerful background music for kids, xylophone, no lyrics"])
```

**Models:**
| Model | Size | Quality | Speed (M2) |
|---|---|---|---|
| `musicgen-small` | 300M | Good | ~20s |
| `musicgen-medium` | 1.5B | Better | ~60s |
| `musicgen-large` | 3.3B | Best | ~3 min |

MPS acceleration supported on Apple Silicon.

### Suno (Hybrid Mode)

Web-based, free tier, extremely easy:
1. Go to suno.com
2. Prompt: `"upbeat background music for children's educational video, playful, no lyrics, 60 seconds"`
3. Download MP3

Free tier: 50 songs/day. More than enough for most production volumes.

**Music mixing rule:** Background music should sit at 15–25% of voiceover volume. Kids content needs the voice to be clearly dominant.

---

## 5. Video Assembler

### Tool: MoviePy + FFmpeg

**What it does:** Combines all assets (images, voice, music) into the final video with transitions, subtitles, and correct aspect ratios.

**Why MoviePy:**
- Pure Python, easy to script and automate
- Built on FFmpeg under the hood
- Handles all the fiddly stuff: audio mixing, transitions, image resizing, subtitle rendering

**Setup:**
```bash
pip install moviepy
brew install ffmpeg
```

**Assembly logic:**
```python
from moviepy.editor import *

scene_duration = total_audio_duration / num_scenes

clips = []
for i, (image_path, scene) in enumerate(zip(images, scenes)):
    img_clip = ImageClip(image_path).set_duration(scene_duration)
    clips.append(img_clip)

video = concatenate_videoclips(clips, method="crossfade", transition=0.3)
narration = AudioFileClip("narration.wav")
music = AudioFileClip("music.wav").volumex(0.2)
mixed_audio = CompositeAudioClip([narration, music])

final = video.set_audio(mixed_audio)
final.write_videofile("output_16x9.mp4", fps=24, codec="libx264")
```

**Subtitle rendering:**
Subtitles are generated directly from the script (no transcription needed since we control the narration text). Word-level timing is estimated by distributing words evenly across the audio duration, then refined using timestamps from Kokoro.

**Output formats:**
- `16x9` (1920×1080): YouTube standard
- `9x16` (1080×1920): TikTok, Instagram Reels, YouTube Shorts — images are center-cropped

---

## 6. Upload

### Tool: YouTube Data API v3

**What it does:** Publishes the final video to YouTube with auto-generated title, description, and tags.

**Setup:** Requires a Google Cloud project with YouTube Data API enabled. Free quota: 10,000 units/day (~50 video uploads).

```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

youtube = build("youtube", "v3", credentials=creds)
youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": script["title"],
            "description": f"Learn about {topic} in just 60 seconds!",
            "tags": ["kids", "learning", topic],
            "categoryId": "27"  # Education
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=MediaFileUpload("output_16x9.mp4")
).execute()
```

**TikTok:** TikTok for Developers API exists but has a more complex approval process. For early phase, manual upload of the 9:16 file is fine.

---

## Component Dependency Map

```
Ollama ──────────────────────────► script.json
                                        │
                      ┌─────────────────┼──────────────────┐
                      ▼                 ▼                   ▼
              FLUX.1 images       Kokoro TTS          MusicGen
              (scene images)     (narration.wav)      (music.wav)
                      │                 │                   │
                      └─────────────────┴───────────────────┘
                                        │
                                   MoviePy/FFmpeg
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                       output_16x9.mp4    output_9x16.mp4
                              │
                         YouTube API
```
