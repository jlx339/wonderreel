"""
Upload — publishes finished video to YouTube via Data API v3.
Requires OAuth2 credentials from Google Cloud Console.
"""

import os
import json
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = Path("config/youtube_token.json")
CREDENTIALS_PATH = Path("config/youtube_credentials.json")


def upload_video(video_path: Path, script, config: dict) -> str | None:
    """
    Uploads video to YouTube. Returns the YouTube video URL on success.
    Returns None if upload is disabled in config.
    """
    if not config["upload"]["youtube"]["enabled"]:
        print("  [upload] YouTube upload disabled in settings.yaml — skipping")
        return None

    print("  [upload] authenticating with YouTube...")
    youtube = _get_youtube_client()

    cfg = config["upload"]["youtube"]
    tags = cfg.get("tags", []) + [script.topic]

    body = {
        "snippet": {
            "title": script.title,
            "description": _build_description(script),
            "tags": tags,
            "categoryId": cfg["category_id"],
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": cfg.get("privacy", "public"),
            "selfDeclaredMadeForKids": True,
        },
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)

    print(f"  [upload] uploading '{script.title}'...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  [upload] {pct}% uploaded...", end="\r")

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\n  [upload] published: {url}")
    return url


def _build_description(script) -> str:
    return (
        f"Learn about {script.topic} in just 60 seconds!\n\n"
        f"WonderReel — bite-sized learning for curious kids.\n\n"
        f"#kids #learning #education #{script.topic.replace(' ', '').lower()}"
    )


def _get_youtube_client():
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    "YouTube OAuth credentials not found. "
                    "Download credentials.json from Google Cloud Console "
                    f"and place it at {CREDENTIALS_PATH}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)
