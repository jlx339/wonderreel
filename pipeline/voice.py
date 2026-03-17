"""
Voiceover generation — converts narration text to a WAV audio file.
Providers: kokoro (local, free) | elevenlabs (API, ~$5/mo)
"""

import os
import soundfile as sf
from pathlib import Path


def generate_voice(narration: str, run_dir: Path, config: dict) -> Path:
    """Returns path to generated narration WAV file."""
    out_path = run_dir / "narration.wav"

    if out_path.exists():
        print("  [voice] using cached narration.wav")
        return out_path

    provider = config["voice"]["provider"]
    print(f"  [voice] generating narration via {provider}...")

    if provider == "kokoro":
        _generate_kokoro(narration, out_path, config["voice"])
    elif provider == "elevenlabs":
        _generate_elevenlabs(narration, out_path, config["voice"])
    else:
        raise ValueError(f"Unknown voice provider: {provider}")

    print(f"  [voice] saved to {out_path}")
    return out_path


def _generate_kokoro(narration: str, out_path: Path, cfg: dict):
    from kokoro_onnx import Kokoro

    # Model files are downloaded automatically on first run to ~/.cache/kokoro
    kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")

    samples, sample_rate = kokoro.create(
        narration,
        voice=cfg.get("kokoro_voice", "af_heart"),
        speed=cfg.get("kokoro_speed", 0.95),
        lang="en-us",
    )

    sf.write(str(out_path), samples, sample_rate)


def _generate_elevenlabs(narration: str, out_path: Path, cfg: dict):
    import requests

    api_key = os.environ["ELEVENLABS_API_KEY"]
    voice_id = cfg["elevenlabs_voice_id"]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": narration,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    out_path.write_bytes(response.content)


def get_audio_duration(audio_path: Path) -> float:
    """Returns duration of audio file in seconds."""
    import soundfile as sf
    info = sf.info(str(audio_path))
    return info.duration
