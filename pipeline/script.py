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

USER_PROMPT = """Write a 60-second educational video script for kids about: "{topic}"

Rules:
- Use simple words a 6-year-old understands
- Include exactly 3 surprising, delightful facts
- Split into exactly {scenes_count} scenes of ~8 seconds each
- Tone: enthusiastic, warm, full of wonder — like a favourite teacher
- No scary or violent content

Return this exact JSON structure:
{{
  "title": "Short punchy video title (max 60 chars)",
  "narration": "The full narration as one continuous string, ~120-140 words",
  "mood": "2-3 word mood description for music generation (e.g. 'cheerful and curious')",
  "scenes": [
    {{
      "id": 1,
      "text": "The narration words for this scene (~15-20 words)",
      "image_prompt": "Vivid visual description for image generation, no text in image"
    }}
  ]
}}"""


@dataclass
class Scene:
    id: int
    text: str
    image_prompt: str


@dataclass
class Script:
    title: str
    narration: str
    mood: str
    scenes: list[Scene] = field(default_factory=list)
    topic: str = ""


def generate_script(topic: str, config: dict) -> Script:
    provider = config["script"]["provider"]
    target_age = config["script"]["target_age"]
    scenes_count = config["script"]["scenes_count"]

    system = SYSTEM_PROMPT.format(target_age=target_age)
    user = USER_PROMPT.format(topic=topic, scenes_count=scenes_count)

    if provider == "ollama":
        raw = _generate_ollama(system, user, config["script"]["ollama_model"])
    elif provider == "claude":
        raw = _generate_claude(system, user, config["script"]["claude_model"])
    else:
        raise ValueError(f"Unknown script provider: {provider}")

    return _parse_script(raw, topic)


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

    scenes = [
        Scene(id=s["id"], text=s["text"], image_prompt=s["image_prompt"])
        for s in data["scenes"]
    ]

    return Script(
        title=data["title"],
        narration=data["narration"],
        mood=data["mood"],
        scenes=scenes,
        topic=topic,
    )
