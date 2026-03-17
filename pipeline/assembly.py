"""
Video assembly — combines images, narration, music, and subtitles into final video.
Outputs both 16:9 (YouTube) and 9:16 (TikTok/Reels) formats.
"""

import shutil
import textwrap
from pathlib import Path

import numpy as np
from moviepy.config import change_settings

# ImageMagick 7 uses 'magick' binary; tell MoviePy where to find it
_magick = shutil.which("magick") or shutil.which("convert")
if _magick:
    change_settings({"IMAGEMAGICK_BINARY": _magick})

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    concatenate_videoclips,
    TextClip,
    CompositeVideoClip,
)
from PIL import Image


# Resolution presets
RESOLUTIONS = {
    "16x9": (1920, 1080),
    "9x16": (1080, 1920),
}


def assemble_video(
    image_paths: list[Path],
    narration_path: Path,
    music_path: Path,
    scenes,
    run_dir: Path,
    config: dict,
) -> dict[str, Path]:
    """
    Assembles final video(s). Returns dict of format -> output path.
    e.g. {"16x9": Path("output/.../final_16x9.mp4"), "9x16": Path(...)}
    """
    cfg = config["assembly"]
    narration = AudioFileClip(str(narration_path))
    total_duration = narration.duration
    scene_duration = total_duration / len(image_paths)

    music = (
        AudioFileClip(str(music_path))
        .subclip(0, min(total_duration, AudioFileClip(str(music_path)).duration))
        .volumex(cfg["music_volume"])
        .audio_fadeout(2.0)
    )
    mixed_audio = CompositeAudioClip([narration, music])

    subtitle_clips = _build_subtitles(scenes, scene_duration, total_duration, cfg)

    outputs = {}
    for fmt in config["pipeline"]["output_formats"]:
        w, h = RESOLUTIONS[fmt]
        out_path = run_dir / f"final_{fmt}.mp4"

        if out_path.exists():
            print(f"  [assembly] {fmt} — using cached video")
            outputs[fmt] = out_path
            continue

        print(f"  [assembly] rendering {fmt} ({w}x{h})...")
        scene_clips = _build_scene_clips(image_paths, scene_duration, w, h, cfg)
        video = concatenate_videoclips(scene_clips, method="compose")
        video_with_subs = CompositeVideoClip([video, *subtitle_clips])
        final = video_with_subs.set_audio(mixed_audio).set_duration(total_duration)

        final.write_videofile(
            str(out_path),
            fps=cfg["fps"],
            codec=cfg["video_codec"],
            audio_codec=cfg["audio_codec"],
            ffmpeg_params=["-crf", str(cfg["crf"])],
            logger=None,
        )
        outputs[fmt] = out_path
        print(f"  [assembly] saved {out_path}")

    return outputs


def _build_scene_clips(image_paths, scene_duration, width, height, cfg):
    clips = []
    transition = cfg["transition_duration"]

    for i, img_path in enumerate(image_paths):
        img = _fit_image(img_path, width, height)
        clip = ImageClip(img).set_duration(scene_duration)

        if i > 0:
            clip = clip.crossfadein(transition)

        clips.append(clip)

    return clips


def _fit_image(img_path: Path, width: int, height: int) -> np.ndarray:
    """Resize and center-crop image to exactly (width, height)."""
    img = Image.open(img_path).convert("RGB")
    src_w, src_h = img.size
    target_ratio = width / height
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # Source is wider — crop sides
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        # Source is taller — crop top/bottom
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    img = img.resize((width, height), Image.LANCZOS)
    return np.array(img)


def _build_subtitles(scenes, scene_duration, total_duration, cfg):
    """Build subtitle TextClips timed to each scene."""
    clips = []
    font_size = cfg["subtitle_font_size"]

    for scene in scenes:
        start = (scene.id - 1) * scene_duration
        end = min(start + scene_duration, total_duration)

        # Wrap long lines
        wrapped = "\n".join(textwrap.wrap(scene.text, width=38))

        txt_clip = (
            TextClip(
                wrapped,
                fontsize=font_size,
                color=cfg["subtitle_color"],
                stroke_color=cfg["subtitle_stroke_color"],
                stroke_width=cfg["subtitle_stroke_width"],
                font="/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                method="caption",
                size=(1800, None),
                align="center",
            )
            .set_start(start)
            .set_end(end)
            .set_position(("center", 0.82), relative=True)
        )
        clips.append(txt_clip)

    return clips
