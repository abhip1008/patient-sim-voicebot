"""FastAPI app Twilio talks to during a call.

PHASE 2 (current): a /twiml route that tells Twilio to speak a fixed greeting and
hold the line briefly so we capture the agent's voice on the recording. This proves
the whole telephony path (dial -> connect -> audio -> record) works before we add AI.

The live Media Stream WebSocket + Pipecat pipeline arrive in PHASE 3.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, Response

from .config import load_settings

# Validate the environment once, at startup (fails loudly if a key is missing).
settings = load_settings()

app = FastAPI(title="Patient Simulator Voice Bot")

# Phase 2 fixed greeting — no AI yet. Just proves audio flows and gets recorded.
GREETING = (
    "Hello, this is a test call from a patient simulator. "
    "I'm just checking that this connection works. Thank you."
)


@app.get("/health")
async def health() -> dict:
    """Simple liveness check so we can confirm the server is up via the browser/curl."""
    return {"ok": True, "phase": 2}


@app.post("/twiml")
async def twiml(request: Request) -> Response:
    """Twilio fetches this when the call connects. We tell it what to do.

    <Say>   speaks our greeting into the call (the agent hears it).
    <Pause> holds the line so the agent's own greeting is captured on the recording.
    """
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{GREETING}</Say>
  <Pause length="12"/>
</Response>"""
    return Response(content=body, media_type="application/xml")


@app.post("/status")
async def status_callback(request: Request) -> Response:
    """Twilio posts call lifecycle events here so we can see what happened in the logs."""
    form = await request.form()
    print(
        f"[call status] sid={form.get('CallSid')} "
        f"status={form.get('CallStatus')} "
        f"duration={form.get('CallDuration')}s "
        f"error={form.get('ErrorCode')}"
    )
    return Response(status_code=204)
