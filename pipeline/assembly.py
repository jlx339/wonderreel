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
    ColorClip,
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
    title: str = "",
) -> dict[str, Path]:
    """
    Assembles final video(s). Returns dict of format -> output path.
    e.g. {"16x9": Path("output/.../final_16x9.mp4"), "9x16": Path(...)}
    """
    cfg = config["assembly"]
    pause_duration = cfg.get("scene_pause_duration", 1.0)
    intro_duration = cfg.get("intro_duration", 3.0)
    narration = AudioFileClip(str(narration_path))
    total_duration = narration.duration
    num_scenes = len(image_paths)
    scene_duration = total_duration / num_scenes

    music_clip = AudioFileClip(str(music_path))
    full_duration = intro_duration + total_duration
    music = (
        music_clip
        .subclip(0, min(full_duration, music_clip.duration))
        .volumex(cfg["music_volume"])
        .audio_fadeout(2.0)
    )
    # Narration starts after the intro
    narration = narration.set_start(intro_duration)
    mixed_audio = CompositeAudioClip([narration, music])

    subtitle_clips = _build_subtitles(scenes, scene_duration, total_duration, intro_duration, cfg)

    outputs = {}
    for fmt in config["pipeline"]["output_formats"]:
        w, h = RESOLUTIONS[fmt]
        out_path = run_dir / f"final_{fmt}.mp4"

        if out_path.exists():
            print(f"  [assembly] {fmt} — using cached video")
            outputs[fmt] = out_path
            continue

        print(f"  [assembly] rendering {fmt} ({w}x{h})...")
        intro_clip = _build_intro(title, w, h, intro_duration, cfg)
        scene_clips = _build_scene_clips(image_paths, scene_duration, w, h, pause_duration, cfg)
        video = concatenate_videoclips([intro_clip, *scene_clips], method="compose")
        video_with_subs = CompositeVideoClip([video, *subtitle_clips])
        final = video_with_subs.set_audio(mixed_audio).set_duration(full_duration)

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


def _build_intro(title, width, height, duration, cfg):
    """Black title card with the video title, fades in and out."""
    bg = ColorClip(size=(width, height), color=[0, 0, 0], duration=duration)

    txt = (
        TextClip(
            title,
            fontsize=cfg["subtitle_font_size"] + 20,
            color="white",
            stroke_color="black",
            stroke_width=2,
            font=FONT_EN,
            method="caption",
            size=(int(width * 0.85), None),
            align="center",
        )
        .set_duration(duration)
        .set_position("center")
        .fadein(0.5)
        .fadeout(0.5)
    )

    return CompositeVideoClip([bg, txt]).fadein(0.5).fadeout(0.5)


def _build_scene_clips(image_paths, scene_duration, width, height, pause_duration, cfg):
    clips = []
    fade = cfg["transition_duration"]

    for i, img_path in enumerate(image_paths):
        img = _fit_image(img_path, width, height)
        clip = ImageClip(img).set_duration(scene_duration).crossfadeout(fade)

        if i > 0:
            # 1-second black pause before each scene (except the first)
            black = ColorClip(size=(width, height), color=[0, 0, 0], duration=pause_duration)
            clips.append(black)

        clip = clip.crossfadein(fade)
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


FONT_EN = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ZH = "/System/Library/Fonts/STHeiti Medium.ttc"


def _build_subtitles(scenes, scene_duration, total_duration, intro_duration, cfg):
    """Build bilingual subtitle TextClips (English + Simplified Chinese) timed to each scene."""
    clips = []
    font_size = cfg["subtitle_font_size"]
    font_size_zh = int(font_size * 0.85)
    color = cfg["subtitle_color"]
    stroke_color = cfg["subtitle_stroke_color"]
    stroke_width = cfg["subtitle_stroke_width"]

    for scene in scenes:
        start = intro_duration + (scene.id - 1) * scene_duration
        end = min(start + scene_duration, intro_duration + total_duration)

        wrapped_en = "\n".join(textwrap.wrap(scene.text, width=38))

        en_clip = (
            TextClip(
                wrapped_en,
                fontsize=font_size,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                font=FONT_EN,
                method="caption",
                size=(1800, None),
                align="center",
            )
            .set_start(start)
            .set_end(end)
            .set_position(("center", 0.78), relative=True)
        )
        clips.append(en_clip)

        if scene.text_zh:
            zh_clip = (
                TextClip(
                    scene.text_zh,
                    fontsize=font_size_zh,
                    color=color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    font=FONT_ZH,
                    method="caption",
                    size=(1800, None),
                    align="center",
                )
                .set_start(start)
                .set_end(end)
                .set_position(("center", 0.88), relative=True)
            )
            clips.append(zh_clip)

    return clips
