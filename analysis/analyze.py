"""LLM-assisted transcript reviewer: flags CANDIDATE bugs for human verification.

PHASE 7. Reads a transcript JSON (from src.transcripts), sends it to GPT-4o with the
rubric and the scenario's bug hypothesis, and returns candidate issues. The output is a
starting point — a human confirms each against the audio/transcript before it goes in
BUG_REPORT.md. Run:

    python -m analysis.analyze output/transcripts/transcript-XXXX.json
    python -m analysis.analyze output/transcripts/*.json --out output/candidates.json
"""

from __future__ import annotations

import argparse
import json
import sys

from openai import OpenAI

from src.config import load_settings
from src.scenarios import SCENARIOS
from .rubric import CATEGORIES, rubric_text

_SYSTEM = (
    "You are a meticulous QA reviewer auditing a medical clinic's voice AGENT. You are given "
    "a phone transcript between a simulated PATIENT (our test bot) and the AGENT (under test). "
    "Find real, consequential bugs in the AGENT's behavior only. Be strict: surface useful "
    "issues, not nitpicks. If there are no real issues, return an empty list. Treat your "
    "findings as CANDIDATES a human will verify."
)


def _format_transcript(turns: list[dict]) -> str:
    return "\n".join(f"[{t['mmss']}] {t['speaker']}: {t['text']}" for t in turns)


def _build_user_prompt(transcript: dict) -> str:
    meta = transcript.get("metadata", {})
    scenario_id = meta.get("scenario", "")
    sc = SCENARIOS.get(scenario_id)
    hypothesis = sc.bug_hypothesis if sc else "(unknown — general review)"
    goal = sc.goal if sc else "(unknown)"

    return f"""\
SCENARIO: {scenario_id} — {meta.get('title','')}
PATIENT GOAL: {goal}
BUG HYPOTHESIS WE'RE TESTING: {hypothesis}

{rubric_text()}

TRANSCRIPT:
{_format_transcript(transcript.get('turns', []))}

Return STRICT JSON of this shape:
{{
  "candidates": [
    {{
      "title": "one-line summary of the AGENT bug",
      "severity": "High|Medium|Low",
      "category": "one of: {', '.join(CATEGORIES)}",
      "timestamp": "MM:SS of the agent's problematic line",
      "what_patient_asked": "the request that triggered it",
      "what_agent_did": "brief quote/paraphrase of the agent's actual response",
      "what_it_should_have_done": "correct behavior",
      "why_it_matters": "real-world consequence for a clinic/patient",
      "confidence": "high|medium|low",
      "relates_to_hypothesis": true
    }}
  ]
}}
Only include genuine issues. Empty list if none."""


def analyze_transcript(transcript: dict, client: OpenAI, model: str) -> list[dict]:
    """Return a list of candidate bug dicts for one transcript."""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_user_prompt(transcript)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    candidates = data.get("candidates", [])
    # tag each candidate with its source transcript for traceability
    label = transcript.get("metadata", {}).get("call_sid", "")
    for c in candidates:
        c["source_call_sid"] = label
        c["source_scenario"] = transcript.get("metadata", {}).get("scenario", "")
    return candidates


def _print_candidates(path: str, candidates: list[dict]) -> None:
    print(f"\n=== {path} — {len(candidates)} candidate(s) ===")
    if not candidates:
        print("  (no issues flagged)")
    for c in candidates:
        print(f"  [{c.get('severity','?')}] {c.get('title','')}")
        print(f"      @ {c.get('timestamp','?')} | {c.get('category','?')} | confidence={c.get('confidence','?')}")
        print(f"      agent did: {c.get('what_agent_did','')}")
        print(f"      should: {c.get('what_it_should_have_done','')}")
        print(f"      why: {c.get('why_it_matters','')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Flag candidate agent bugs from transcripts.")
    parser.add_argument("transcripts", nargs="+", help="transcript .json file(s)")
    parser.add_argument("--out", default=None, help="write all candidates to this JSON file")
    args = parser.parse_args()

    settings = load_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    all_candidates = []
    for path in args.transcripts:
        if not path.endswith(".json"):
            continue
        with open(path) as f:
            transcript = json.load(f)
        candidates = analyze_transcript(transcript, client, settings.llm_model)
        _print_candidates(path, candidates)
        all_candidates.extend(candidates)

    print(f"\nTotal candidates across {len(args.transcripts)} transcript(s): {len(all_candidates)}")
    print("NOTE: these are CANDIDATES — verify each against the audio before adding to BUG_REPORT.md.")

    if args.out:
        with open(args.out, "w") as f:
            json.dump({"candidates": all_candidates}, f, indent=2)
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
