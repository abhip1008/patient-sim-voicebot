"""Pull a call's dual-channel recording from Twilio and save it as mp3 (and optional ogg).

PHASE 5: the challenge requires audio in mp3 or ogg with both sides. Twilio records both
legs (dual channel) and serves mp3 directly, so we just download it; ogg is an optional
ffmpeg conversion.
"""

from __future__ import annotations

import base64
import os
import subprocess
import time
import urllib.request

from twilio.rest import Client

from .config import Settings


def fetch_recording(
    client: Client,
    settings: Settings,
    call_sid: str,
    out_dir: str,
    label: str,
    also_ogg: bool = False,
    wait_secs: int = 40,
) -> str | None:
    """Download the recording for call_sid to <out_dir>/<label>.mp3. Returns the path or None.

    Twilio finalizes recordings a few seconds after the call ends, so we poll briefly.
    """
    os.makedirs(out_dir, exist_ok=True)
    deadline = time.time() + wait_secs
    rec = None
    while time.time() < deadline:
        recs = client.recordings.list(call_sid=call_sid, limit=1)
        if recs and recs[0].status == "completed" and str(recs[0].duration) not in ("-1", "None"):
            rec = recs[0]
            break
        time.sleep(3)
    if rec is None:
        return None

    mp3_path = os.path.join(out_dir, f"{label}.mp3")
    media_url = f"https://api.twilio.com{rec.uri.replace('.json', '.mp3')}"
    auth = base64.b64encode(
        f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
    ).decode()
    req = urllib.request.Request(media_url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(mp3_path, "wb") as f:
        f.write(resp.read())

    if also_ogg:
        ogg_path = os.path.join(out_dir, f"{label}.ogg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libvorbis", ogg_path],
            check=True,
            capture_output=True,
        )

    return mp3_path
