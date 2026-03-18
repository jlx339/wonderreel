"""
Script generation — converts a topic into a structured video script.
Providers: ollama (local, free) | claude (API, cheap fallback)
"""

import json
import re
import ollama
from dataclasses import dataclass, field


SYSTEM_PROMPT = """You are a children's educational video scriptwriter.
Your scripts are fun, clear, and perfect for kids aged {target_age}.
Always respond with valid JSON only — no markdown, no explanation."""

USER_PROMPT = """Write a 60-second educational video script for kids aged {target_age} about: "{topic}"

Rules:
- Use VERY simple words — short sentences, max 8 words each
- No big words. Say "big" not "enormous". Say "far away" not "distant".
- Include exactly 3 surprising, delightful facts a young child would love
- Split into exactly {scenes_count} scenes of ~8 seconds each
- Each scene "text" must be 15-20 words — enough to read aloud in 8 seconds
- The full "narration" must be 120-140 words total — enough to fill 60 seconds of speaking
- Tone: warm, playful, full of wonder — like a favourite parent reading a bedtime story
- No scary or violent content

For each scene, also provide a Simplified Chinese translation of the scene text (text_zh).
The Chinese translation must be complete — do not mix English words into the Chinese text.

Return this exact JSON structure:
{{
  "title": "Short punchy video title (max 60 chars)",
  "narration": "The full narration as one continuous string. Must be 120-140 words.",
  "mood": "2-3 word mood description for music generation (e.g. 'cheerful and curious')",
  "scenes": [
    {{
      "id": 1,
      "text": "Simple English narration for this scene. Must be 15-20 words.",
      "text_zh": "该场景的完整简体中文翻译，不包含英文单词。",
      "image_prompt": "Vivid visual description for image generation, no text in image"
    }}
  ]
}}"""


@dataclass
class Scene:
    id: int
    text: str
    text_zh: str
    image_prompt: str


@dataclass
class Script:
    title: str
    narration: str
    mood: str
    scenes: list[Scene] = field(default_factory=list)
    topic: str = ""


MIN_NARRATION_WORDS = 100


def generate_script(topic: str, config: dict) -> Script:
    provider = config["script"]["provider"]
    target_age = config["script"]["target_age"]
    scenes_count = config["script"]["scenes_count"]

    system = SYSTEM_PROMPT.format(target_age=target_age)
    user = USER_PROMPT.format(topic=topic, scenes_count=scenes_count, target_age=target_age)

    for attempt in range(3):
        if provider == "ollama":
            raw = _generate_ollama(system, user, config["script"]["ollama_model"])
        elif provider == "claude":
            raw = _generate_claude(system, user, config["script"]["claude_model"])
        else:
            raise ValueError(f"Unknown script provider: {provider}")

        script = _parse_script(raw, topic)
        word_count = len(script.narration.split())
        if word_count >= MIN_NARRATION_WORDS:
            return script
        print(f"  [script] narration too short ({word_count} words), retrying ({attempt + 1}/3)...")

    # Fallback: build narration from scene texts to guarantee enough spoken content
    print(f"  [script] using scene texts as narration fallback")
    script.narration = " ".join(s.text for s in script.scenes)
    return script


def _generate_ollama(system: str, user: str, model: str) -> str:
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format="json",
        options={"temperature": 0.8},
    )
    return response["message"]["content"]


def _generate_claude(system: str, user: str, model: str) -> str:
    import anthropic
    import os

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text


def _parse_script(raw: str, topic: str) -> Script:
    # Strip any accidental markdown code fences
    raw = re.sub(r"```json|```", "", raw).strip()

    # Extract the outermost JSON object in case of leading/trailing text
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    data = json.loads(raw)

    scenes = []
    for s in data["scenes"]:
        # Accept common alternative field names the LLM might use
        image_prompt = s.get("image_prompt") or s.get("image") or s.get("visual") or s.get("scene_description") or ""
        scenes.append(Scene(
            id=s["id"],
            text=s.get("text") or s.get("narration") or s.get("script") or "",
            text_zh=s.get("text_zh") or s.get("chinese") or s.get("zh") or "",
            image_prompt=image_prompt,
        ))

    return Script(
        title=data["title"],
        narration=data["narration"],
        mood=data["mood"],
        scenes=scenes,
        topic=topic,
    )
