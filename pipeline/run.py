"""
WonderReel — main pipeline entry point.

Usage:
    # Single video
    python -m pipeline.run --topic "Why is the sky blue?"

    # Batch from topic bank
    python -m pipeline.run --batch --count 5

    # Batch from specific category
    python -m pipeline.run --batch --category science --count 3

    # Use specific config
    python -m pipeline.run --topic "Volcanoes" --config config/settings.yaml
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .script import generate_script
from .images import generate_images
from .voice import generate_voice
from .music import generate_music
from .assembly import assemble_video
from .upload import upload_video


def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_topic_bank(path: str = "topics/topic_bank.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def pick_topic(category, topic_bank: dict) -> str:
    if category:
        topics = topic_bank.get(category)
        if not topics:
            raise ValueError(f"Category '{category}' not found in topic bank.")
    else:
        topics = [t for cat in topic_bank.values() for t in cat]
    return random.choice(topics)


def make_run_dir(output_dir: str, topic: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = topic.lower().replace(" ", "_").replace("?", "")[:40]
    run_dir = Path(output_dir) / "assets" / f"{timestamp}_{slug}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_pipeline(topic: str, config: dict, run_dir: Path = None) -> dict:
    """
    Runs the full pipeline for a single topic.
    Returns a dict with paths to generated outputs.
    Pass run_dir to resume from an existing checkpoint directory.
    """
    print(f"\n{'='*60}")
    print(f"WonderReel: {topic}")
    print(f"{'='*60}")

    if run_dir is None:
        run_dir = make_run_dir(config["pipeline"]["output_dir"], topic)
    else:
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run dir: {run_dir}\n")

    # --- Stage 1: Script ---
    script_path = run_dir / "script.json"
    if script_path.exists():
        print("[1/5] Script — using checkpoint")
        from .script import Script, Scene
        data = json.loads(script_path.read_text())
        script = Script(
            title=data["title"],
            narration=data["narration"],
            mood=data["mood"],
            topic=data["topic"],
            scenes=[Scene(**s) for s in data["scenes"]],
        )
    else:
        print("[1/5] Generating script...")
        script = generate_script(topic, config)
        script_path.write_text(json.dumps({
            "title": script.title,
            "narration": script.narration,
            "mood": script.mood,
            "topic": script.topic,
            "scenes": [{"id": s.id, "text": s.text, "image_prompt": s.image_prompt} for s in script.scenes],
        }, indent=2))
        print(f"  Title: {script.title}")
        print(f"  Scenes: {len(script.scenes)}")

    # --- Stage 2: Images ---
    print("\n[2/5] Generating scene images...")
    image_paths = generate_images(script.scenes, run_dir, config)

    # --- Stage 3: Voice ---
    print("\n[3/5] Generating voiceover...")
    narration_path = generate_voice(script.narration, run_dir, config)

    # --- Stage 4: Music ---
    print("\n[4/5] Generating background music...")
    import soundfile as sf
    narration_info = sf.info(str(narration_path))
    music_path = generate_music(script.mood, narration_info.duration, run_dir, config)

    # --- Stage 5: Assembly ---
    print("\n[5/5] Assembling video...")
    video_paths = assemble_video(
        image_paths, narration_path, music_path, script.scenes, run_dir, config
    )

    # --- Upload (optional) ---
    youtube_url = None
    if config["upload"]["youtube"]["enabled"]:
        primary_video = video_paths.get("16x9") or next(iter(video_paths.values()))
        youtube_url = upload_video(primary_video, script, config)

    print(f"\nDone! Output files:")
    for fmt, path in video_paths.items():
        print(f"  {fmt}: {path}")
    if youtube_url:
        print(f"  YouTube: {youtube_url}")

    return {"script": script, "videos": video_paths, "youtube_url": youtube_url}  # type: ignore[return-value]


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="WonderReel video pipeline")
    parser.add_argument("--topic", type=str, help="Topic for a single video")
    parser.add_argument("--batch", action="store_true", help="Batch mode from topic bank")
    parser.add_argument("--category", type=str, help="Topic bank category (for batch mode)")
    parser.add_argument("--count", type=int, default=1, help="Number of videos to generate")
    parser.add_argument("--config", type=str, default="config/settings.yaml")
    parser.add_argument("--run-dir", type=str, help="Resume from existing run directory (skips completed stages)")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.batch:
        topic_bank = load_topic_bank()
        topics = [pick_topic(args.category, topic_bank) for _ in range(args.count)]
    elif args.topic:
        topics = [args.topic]
    else:
        parser.print_help()
        sys.exit(1)

    results = []
    for topic in topics:
        result = run_pipeline(topic, config, run_dir=args.run_dir)
        results.append(result)

    print(f"\nAll done. Generated {len(results)} video(s).")


if __name__ == "__main__":
    main()
