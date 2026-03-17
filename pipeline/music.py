"""
Background music generation — generates a looping kids-friendly track.
Providers: musicgen (local, free) | suno_manual (place file manually)
"""

import os
import soundfile as sf
from pathlib import Path


MUSIC_PROMPT_TEMPLATE = (
    "cheerful upbeat background music for children's educational video, "
    "{mood}, playful melody, xylophone and light percussion, no lyrics, "
    "loopable, bright and positive, {duration} seconds"
)


def generate_music(mood: str, duration_seconds: float, run_dir: Path, config: dict) -> Path:
    """Returns path to generated background music WAV file."""
    out_path = run_dir / "music.wav"

    if out_path.exists():
        print("  [music] using cached music.wav")
        return out_path

    provider = config["music"]["provider"]
    target_duration = duration_seconds + config["music"].get("extra_seconds", 5)
    print(f"  [music] generating {target_duration:.0f}s track via {provider}...")

    if provider == "musicgen":
        _generate_musicgen(mood, target_duration, out_path, config["music"])
    elif provider == "suno_manual":
        _check_manual_music(out_path)
    else:
        raise ValueError(f"Unknown music provider: {provider}")

    print(f"  [music] saved to {out_path}")
    return out_path


def _generate_musicgen(mood: str, duration: float, out_path: Path, cfg: dict):
    # xformers doesn't support Apple Silicon MPS.
    # Provide a complete stub that delegates to PyTorch's native attention.
    import sys
    import types
    import torch
    import torch.nn.functional as F

    if "xformers" not in sys.modules:
        class _LowerTriangularMask:
            """Causal mask sentinel — audiocraft checks isinstance() against this."""
            pass

        def _memory_efficient_attention(q, k, v, attn_bias=None, scale=None, p=0.0):
            # xformers uses (B, S, H, D); PyTorch sdpa uses (B, H, S, D)
            q, k, v = q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)
            is_causal = isinstance(attn_bias, _LowerTriangularMask)
            attn_mask = None if is_causal else attn_bias
            out = F.scaled_dot_product_attention(
                q, k, v, attn_mask=attn_mask, dropout_p=p, is_causal=is_causal, scale=scale
            )
            return out.transpose(1, 2)

        xops = types.ModuleType("xformers.ops")
        xops.unbind = torch.unbind
        xops.memory_efficient_attention = _memory_efficient_attention
        xops.LowerTriangularMask = _LowerTriangularMask

        xf = types.ModuleType("xformers")
        xf.ops = xops
        sys.modules["xformers"] = xf
        sys.modules["xformers.ops"] = xops

    from audiocraft.models import MusicGen

    model_name = cfg.get("musicgen_model", "facebook/musicgen-small")
    model = MusicGen.get_pretrained(model_name)
    model.set_generation_params(duration=duration)

    prompt = MUSIC_PROMPT_TEMPLATE.format(mood=mood, duration=int(duration))
    print(f"  [music] prompt: {prompt}")

    wav = model.generate([prompt])  # shape: [1, channels, samples]

    # audiocraft's audio_write saves without extension — we handle manually
    audio = wav[0].cpu().numpy()  # [channels, samples]
    if audio.ndim == 2:
        audio = audio.T  # soundfile expects [samples, channels]

    sample_rate = model.cfg.sample_rate
    sf.write(str(out_path), audio, sample_rate)


def _check_manual_music(out_path: Path):
    """
    For suno_manual mode: user downloads a track from suno.com and places it at
    output/assets/{run_id}/music.wav (or .mp3 — will be auto-detected).
    """
    mp3_path = out_path.with_suffix(".mp3")
    if mp3_path.exists():
        # Convert mp3 to wav using ffmpeg
        os.system(f'ffmpeg -i "{mp3_path}" -ar 44100 "{out_path}" -y -loglevel quiet')
        return

    raise FileNotFoundError(
        f"suno_manual mode: place your downloaded music file at {out_path} "
        f"(WAV or MP3) before running assembly."
    )
