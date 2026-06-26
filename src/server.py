"""FastAPI app Twilio talks to during a call.

PHASE 3: /twiml tells Twilio to open a bidirectional Media Stream to our /ws
WebSocket, where the Pipecat pipeline runs the live conversation. The Phase 2
inline-greeting path still lives in call.py for quick telephony tests.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response, WebSocket
from loguru import logger

from .bot import run_bot
from .config import load_settings

# Validate the environment once, at startup (fails loudly if a key is missing).
settings = load_settings()

app = FastAPI(title="Patient Simulator Voice Bot")


def _wss_url() -> str:
    """Turn the public https base URL into the wss:// URL Twilio streams audio to."""
    host = urlparse(settings.public_base_url).netloc
    return f"wss://{host}/ws"


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "phase": 3}


@app.post("/twiml")
async def twiml(request: Request) -> Response:
    """Twilio fetches this on connect. <Connect><Stream> opens the live audio pipe.

    The chosen scenario id (from ?scenario=...) is forwarded to the WebSocket as a
    Twilio <Parameter>, so the bot knows which patient to role-play for this call.
    """
    scenario = request.query_params.get("scenario", "")
    param_tag = f'\n      <Parameter name="scenario" value="{scenario}"/>' if scenario else ""
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{_wss_url()}">{param_tag}
    </Stream>
  </Connect>
</Response>"""
    return Response(content=body, media_type="application/xml")


@app.websocket("/ws")
async def media_stream(websocket: WebSocket) -> None:
    """The Twilio Media Stream connects here; we run the conversation pipeline on it."""
    await websocket.accept()
    logger.info("WebSocket accepted — starting bot.")
    try:
        await run_bot(websocket, settings)
    except Exception:  # noqa: BLE001 — log full traceback, don't crash the server
        logger.exception("Bot run failed")
    finally:
        logger.info("WebSocket handler finished.")


@app.post("/status")
async def status_callback(request: Request) -> Response:
    form = await request.form()
    print(
        f"[call status] sid={form.get('CallSid')} "
        f"status={form.get('CallStatus')} "
        f"duration={form.get('CallDuration')}s "
        f"error={form.get('ErrorCode')}"
    )
    return Response(status_code=204)
