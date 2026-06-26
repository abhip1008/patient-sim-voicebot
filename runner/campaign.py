"""Run a batch of scenario calls, saving recording + transcript + metadata + cost per call.

PHASE 8. Each call: dial (server mode with the scenario), let it run up to a cap, end it
cleanly, download the recording as call-NN.mp3, rename the server-written transcript to
transcript-NN.{txt,json}, estimate cost, and append a metadata row. Designed to run in
waves so you can stop, listen, improve, and continue (the graded "iteration" story).

Usage:
  python -m runner.campaign                 # full default campaign
  python -m runner.campaign --count 4       # wave 1: first 4
  python -m runner.campaign --start 5       # wave 2: the rest
  python -m runner.campaign --scenarios happy_path,closed_day_trap
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time

from twilio.rest import Client

from scripts.cost_log import append_cost, estimate_cost, total_spent
from src.config import load_settings, require_public_base_url
from src.recording import fetch_recording

RECORDINGS_DIR = "output/recordings"
TRANSCRIPTS_DIR = "output/transcripts"
COSTS_CSV = "output/costs.csv"
CAMPAIGN_CSV = "output/campaign.csv"

# Curated default campaign: 2 clean baselines + high-value probes (weighted to safety).
DEFAULT_CAMPAIGN = [
    "happy_path",
    "closed_day_trap",
    "emergency_escalation",
    "controlled_substance_refill",
    "reschedule_midcall",
    "insurance_obscure",
    "multi_constraint",
    "identity_correction",
    "topic_switch",
    "third_party_privacy",
    "past_date_booking",
    "readback_stress",
    "hours_location",
    "prompt_injection",
]


def _wait_for_transcript(call_sid: str, timeout: int = 25) -> str | None:
    """The server writes transcript-<call_sid>.json on disconnect; wait for it."""
    src = os.path.join(TRANSCRIPTS_DIR, f"transcript-{call_sid}.json")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(src):
            return src
        time.sleep(2)
    return None


def _rename_transcript(call_sid: str, seq: str) -> tuple[int, int]:
    """Rename transcript-<call_sid>.{txt,json} -> transcript-<seq>.*. Returns (turns, patient_chars)."""
    turns = patient_chars = 0
    for ext in ("txt", "json"):
        old = os.path.join(TRANSCRIPTS_DIR, f"transcript-{call_sid}.{ext}")
        new = os.path.join(TRANSCRIPTS_DIR, f"transcript-{seq}.{ext}")
        if os.path.exists(old):
            os.replace(old, new)
            if ext == "json":
                with open(new) as f:
                    data = json.load(f)
                turns = len(data.get("turns", []))
                patient_chars = sum(
                    len(t.get("text", "")) for t in data.get("turns", []) if t.get("speaker") == "PATIENT"
                )
    return turns, patient_chars


def run_one(client: Client, settings, scenario_id: str, seq: str, max_call_secs: int) -> dict:
    """Place one scenario call, capture everything, return a metadata row."""
    base = require_public_base_url(settings)
    print(f"\n[{seq}] scenario={scenario_id} — dialing...")
    call = client.calls.create(
        to=settings.target_number,
        from_=settings.twilio_from_number,
        url=f"{base}/twiml?scenario={scenario_id}",
        method="POST",
        record=True,
        recording_channels="dual",
    )
    # Let the conversation run up to the cap, then end it cleanly.
    start = time.time()
    status = "unknown"
    while time.time() - start < max_call_secs:
        status = client.calls(call.sid).fetch().status
        if status in ("completed", "failed", "busy", "no-answer", "canceled"):
            break
        time.sleep(3)
    else:
        client.calls(call.sid).update(status="completed")
        status = "completed (capped)"
    time.sleep(5)
    duration = client.calls(call.sid).fetch().duration or 0

    # Recording -> call-<seq>.mp3
    rec_path = fetch_recording(client, settings, call.sid, RECORDINGS_DIR, f"call-{seq}")

    # Transcript: wait for the server to write it, then rename to transcript-<seq>.*
    _wait_for_transcript(call.sid)
    turns, patient_chars = _rename_transcript(call.sid, seq)

    cost = estimate_cost(float(duration), patient_chars, turns)
    append_cost(COSTS_CSV, {
        "call_id": f"call-{seq}", "scenario": scenario_id,
        "timestamp": int(time.time()), "duration_sec": duration, **cost,
    })

    print(f"[{seq}] done: status={status} dur={duration}s turns={turns} "
          f"rec={'yes' if rec_path else 'NO'} cost=${cost['total_usd']}")
    return {
        "seq": seq, "scenario": scenario_id, "call_sid": call.sid,
        "status": status, "duration_sec": duration, "turns": turns,
        "recording": rec_path or "", "total_usd": cost["total_usd"],
    }


def _append_campaign_row(row: dict) -> None:
    fields = ["seq", "scenario", "call_sid", "status", "duration_sec", "turns", "recording", "total_usd"]
    exists = os.path.exists(CAMPAIGN_CSV) and os.path.getsize(CAMPAIGN_CSV) > 0
    with open(CAMPAIGN_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def main() -> None:
    p = argparse.ArgumentParser(description="Run a batch of scenario calls.")
    p.add_argument("--scenarios", help="comma-separated scenario ids (default: curated campaign)")
    p.add_argument("--start", type=int, default=1, help="starting sequence number (for waves)")
    p.add_argument("--count", type=int, default=None, help="how many to run from --start")
    p.add_argument("--max-secs", type=int, default=160, help="max seconds per call before ending it")
    p.add_argument("--gap", type=int, default=8, help="seconds to wait between calls")
    args = p.parse_args()

    settings = load_settings()
    require_public_base_url(settings)  # fail early if ngrok/server not configured
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    scenarios = args.scenarios.split(",") if args.scenarios else DEFAULT_CAMPAIGN
    # Apply wave windowing on the full list, keeping sequence numbers stable.
    indexed = list(enumerate(scenarios, start=1))
    window = [(i, s) for (i, s) in indexed if i >= args.start]
    if args.count is not None:
        window = window[: args.count]

    print(f"Running {len(window)} call(s): {[s for _, s in window]}")
    results = []
    for i, sid in window:
        results.append(run_one(client, settings, sid, f"{i:02d}", args.max_secs))
        _append_campaign_row(results[-1])
        if (i, sid) != window[-1]:
            time.sleep(args.gap)

    print("\n===== WAVE SUMMARY =====")
    for r in results:
        print(f"  call-{r['seq']} {r['scenario']:28} {r['status']:18} {r['duration_sec']}s  ${r['total_usd']}")
    print(f"Total estimated spend so far: ${total_spent(COSTS_CSV)}")


if __name__ == "__main__":
    main()
