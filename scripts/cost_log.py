"""Estimate and log per-call cost so we can prove the run stayed under $20.

PHASE 8. These are ESTIMATES from public per-minute rates, not billed amounts — enough
to show the order of magnitude in the writeup. Columns:
call_id, scenario, timestamp, duration_sec, twilio_usd, stt_usd, llm_usd, tts_usd, total_usd
"""

from __future__ import annotations

import csv
import os

# Rough public rates (USD).
TWILIO_PER_MIN = 0.014    # outbound voice
DEEPGRAM_PER_MIN = 0.0043  # Nova streaming STT
CARTESIA_PER_1K_CHARS = 0.030  # TTS, approx
LLM_PER_TURN = 0.0020     # GPT-4o, short turns

HEADER = [
    "call_id", "scenario", "timestamp", "duration_sec",
    "twilio_usd", "stt_usd", "llm_usd", "tts_usd", "total_usd",
]


def estimate_cost(duration_sec: float, patient_chars: int, turns: int) -> dict:
    minutes = max(duration_sec, 0) / 60.0
    twilio = minutes * TWILIO_PER_MIN
    stt = minutes * DEEPGRAM_PER_MIN
    tts = (patient_chars / 1000.0) * CARTESIA_PER_1K_CHARS
    llm = turns * LLM_PER_TURN
    return {
        "twilio_usd": round(twilio, 4),
        "stt_usd": round(stt, 4),
        "llm_usd": round(llm, 4),
        "tts_usd": round(tts, 4),
        "total_usd": round(twilio + stt + tts + llm, 4),
    }


def append_cost(csv_path: str, row: dict) -> None:
    """Append a cost row, writing the header if the file is new/empty."""
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in HEADER})


def total_spent(csv_path: str) -> float:
    if not os.path.exists(csv_path):
        return 0.0
    total = 0.0
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            try:
                total += float(r.get("total_usd") or 0)
            except ValueError:
                pass
    return round(total, 4)
