"""Capture a labeled, timestamped transcript of a live call.

PHASE 5: a Pipecat observer watches every frame and records two things:
  - the AGENT's speech, from Deepgram TranscriptionFrames
  - our PATIENT's speech, from the LLM's text output (accumulated per response)
Each entry is stamped with seconds-since-call-start, so bug citations like
"transcript-NN at 1:23" line up with the audio. Writes both a human-readable .txt
and a structured .json.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from pipecat.frames.frames import (
    LLMFullResponseEndFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.services.stt_service import STTService

AGENT = "AGENT"
PATIENT = "PATIENT"


@dataclass
class TurnEntry:
    seconds: float
    speaker: str
    text: str


def _mmss(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


class TranscriptCollector(BaseObserver):
    """Collects a timestamped, speaker-labeled transcript from the frame stream."""

    def __init__(self) -> None:
        super().__init__()
        self.turns: list[TurnEntry] = []
        self._llm_buffer: str = ""

    async def on_push_frame(self, data: FramePushed) -> None:
        frame = data.frame
        secs = data.timestamp / 1_000_000_000  # ns -> seconds since pipeline start

        # AGENT speech: final transcriptions from the STT service only.
        if isinstance(frame, TranscriptionFrame) and isinstance(data.source, STTService):
            text = (frame.text or "").strip()
            if text:
                self._append(AGENT, text, secs)

        # PATIENT speech: accumulate the LLM's streamed text, flush at end of response.
        elif isinstance(frame, LLMTextFrame):
            self._llm_buffer += frame.text
        elif isinstance(frame, LLMFullResponseEndFrame):
            text = self._llm_buffer.strip()
            self._llm_buffer = ""
            if text:
                self._append(PATIENT, text, secs)

    def _append(self, speaker: str, text: str, secs: float) -> None:
        # Merge consecutive lines from the same speaker (STT can emit several finals/turn).
        if self.turns and self.turns[-1].speaker == speaker:
            self.turns[-1].text = f"{self.turns[-1].text} {text}".strip()
        else:
            self.turns.append(TurnEntry(seconds=secs, speaker=speaker, text=text))


def write_transcript(
    collector: TranscriptCollector,
    out_dir: str,
    label: str,
    metadata: dict | None = None,
) -> tuple[str, str]:
    """Write <label>.txt and <label>.json into out_dir. Returns (txt_path, json_path)."""
    os.makedirs(out_dir, exist_ok=True)
    txt_path = os.path.join(out_dir, f"{label}.txt")
    json_path = os.path.join(out_dir, f"{label}.json")

    meta = metadata or {}
    header = [f"# Transcript: {label}"]
    for k, v in meta.items():
        header.append(f"# {k}: {v}")
    header.append("")

    lines = [f"[{_mmss(t.seconds)}] {t.speaker}: {t.text}" for t in collector.turns]
    with open(txt_path, "w") as f:
        f.write("\n".join(header + lines) + "\n")

    with open(json_path, "w") as f:
        json.dump(
            {
                "metadata": meta,
                "turns": [
                    {
                        "t_seconds": round(t.seconds, 2),
                        "mmss": _mmss(t.seconds),
                        "speaker": t.speaker,
                        "text": t.text,
                    }
                    for t in collector.turns
                ],
            },
            f,
            indent=2,
        )
    return txt_path, json_path
