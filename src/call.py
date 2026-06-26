"""Places the outbound call to TARGET_NUMBER via the Twilio REST API.

PHASE 2: dials the assessment line and records both legs (dual-channel).

Two modes:
  - inline TwiML (default): the greeting instructions travel WITH the call, so no
    public server/ngrok is needed. Perfect for proving telephony in isolation.
  - server mode (--server): Twilio fetches TwiML from our /twiml route via PUBLIC_BASE_URL.
    Needed in Phase 3 for the live Media Stream WebSocket.

Run:  python -m src.call          (inline test greeting)
      python -m src.call --server (use the FastAPI server + ngrok)

Safety: config enforces TARGET_NUMBER is the assessment line and nothing else.
"""

from __future__ import annotations

import argparse
import time

from twilio.rest import Client

from .config import load_settings, require_public_base_url

# Phase 2 fixed greeting — no AI yet. Proves audio flows to the agent and gets recorded.
GREETING = (
    "Hello, this is a test call from a patient simulator. "
    "I'm just checking that this connection works. Thank you."
)


def build_test_twiml() -> str:
    """Inline TwiML: speak a greeting, hold the line to capture the agent, then hang up."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Say>{GREETING}</Say>"
        '<Pause length="12"/>'
        "<Hangup/>"
        "</Response>"
    )


def place_call(scenario: str | None = None, use_server: bool = False, wait: bool = True) -> str:
    """Place one outbound call. Returns the Twilio Call SID."""
    settings = load_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    kwargs = dict(
        to=settings.target_number,
        from_=settings.twilio_from_number,
        record=True,
        recording_channels="dual",
    )
    if use_server:
        base_url = require_public_base_url(settings)
        twiml_url = f"{base_url}/twiml"
        if scenario:
            twiml_url += f"?scenario={scenario}"
        kwargs["url"] = twiml_url
        kwargs["method"] = "POST"
        kwargs["status_callback"] = f"{base_url}/status"
        kwargs["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]
        kwargs["status_callback_method"] = "POST"
    else:
        kwargs["twiml"] = build_test_twiml()

    call = client.calls.create(**kwargs)

    print("Call placed.")
    print(f"  SID:   {call.sid}")
    print(f"  From:  {settings.twilio_from_number}")
    print(f"  To:    {settings.target_number}")
    print(f"  Mode:  {'server (ngrok)' if use_server else 'inline TwiML'}")
    if scenario:
        print(f"  Scenario: {scenario}")

    if wait:
        _poll_until_done(client, call.sid)
        _show_recordings(client, call.sid)

    return call.sid


def _poll_until_done(client: Client, sid: str, timeout_s: int = 90) -> None:
    """Poll the call until it ends, printing status transitions."""
    print("\nWatching call status...")
    last = None
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        call = client.calls(sid).fetch()
        if call.status != last:
            print(f"  status: {call.status}")
            last = call.status
        if call.status in ("completed", "failed", "busy", "no-answer", "canceled"):
            print(f"  duration: {call.duration}s")
            return
        time.sleep(2)
    print("  (stopped watching after timeout; check the Twilio console)")


def _show_recordings(client: Client, sid: str) -> None:
    """List any recordings produced for this call (may take a few seconds to appear)."""
    print("\nLooking for recordings (waiting a few seconds for Twilio to finalize)...")
    for _ in range(6):
        recs = client.recordings.list(call_sid=sid, limit=5)
        if recs:
            for r in recs:
                print(f"  recording: SID={r.sid} duration={r.duration}s channels={r.channels}")
                print(f"  media URL: https://api.twilio.com{r.uri.replace('.json', '.mp3')}")
            return
        time.sleep(3)
    print("  No recording yet — it may still be processing; check the Twilio console.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Place a test call to the assessment line.")
    parser.add_argument("--scenario", default=None, help="(Phase 6+) scenario id to run")
    parser.add_argument("--server", action="store_true", help="use FastAPI server + ngrok (Phase 3)")
    parser.add_argument("--no-wait", action="store_true", help="don't poll for status/recording")
    args = parser.parse_args()
    place_call(args.scenario, use_server=args.server, wait=not args.no_wait)
