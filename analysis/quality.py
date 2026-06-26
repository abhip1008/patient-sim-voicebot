"""Self-scoring conversation-quality metric for our OWN patient bot.

PHASE 10 (standout): rates each call on how natural/lucid our caller sounded — the #1 graded
criterion. An LLM scores each transcript 1-5 on naturalness, flow/turn-taking, goal-steering,
and staying in character, then we average wave 1 (calls 01-04) vs wave 2 (05-14) to show
measured improvement after the mid-campaign iteration.

    python -m analysis.quality output/transcripts/transcript-*.json --out output/quality.json
"""

from __future__ import annotations

import argparse
import glob
import json

from openai import OpenAI

from src.config import load_settings

_SYSTEM = (
    "You are evaluating the PATIENT caller (a simulated test bot), NOT the clinic agent. "
    "Judge only how human and effective the PATIENT sounded. Score strictly and consistently."
)

_DIMENSIONS = ["naturalness", "flow_turn_taking", "goal_steering", "in_character"]


def _format(turns: list[dict]) -> str:
    return "\n".join(f"[{t['mmss']}] {t['speaker']}: {t['text']}" for t in turns)


def score_transcript(transcript: dict, client: OpenAI, model: str) -> dict:
    prompt = f"""\
Rate the PATIENT caller in this transcript on a 1-5 scale (5 = best) for each dimension:
- naturalness: sounds like a real human, not robotic or scripted
- flow_turn_taking: responds on-topic, no awkward non-sequiturs, good conversational rhythm
- goal_steering: actively and believably drives toward the patient's goal
- in_character: stays a patient, never breaks role or reveals it's an AI

TRANSCRIPT:
{_format(transcript.get('turns', []))}

Return STRICT JSON: {{"naturalness":N,"flow_turn_taking":N,"goal_steering":N,"in_character":N,"note":"one short sentence"}}"""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    data["overall"] = round(sum(data[d] for d in _DIMENSIONS) / len(_DIMENSIONS), 2)
    data["scenario"] = transcript.get("metadata", {}).get("scenario", "")
    return data


def main() -> None:
    p = argparse.ArgumentParser(description="Score conversation quality of our patient bot.")
    p.add_argument("transcripts", nargs="+", help="transcript .json file(s) or globs")
    p.add_argument("--out", default="output/quality.json")
    args = p.parse_args()

    paths = sorted(set(sum((glob.glob(t) for t in args.transcripts), [])))
    paths = [p for p in paths if p.endswith(".json")]

    settings = load_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    rows = {}
    print(f"{'call':>5} {'overall':>8} {'natural':>8} {'flow':>6} {'steer':>6} {'char':>5}  scenario")
    for path in paths:
        # derive call number from filename transcript-NN.json
        num = path.split("transcript-")[-1].split(".")[0]
        with open(path) as f:
            t = json.load(f)
        s = score_transcript(t, client, settings.llm_model)
        rows[num] = s
        print(f"{num:>5} {s['overall']:>8} {s['naturalness']:>8} {s['flow_turn_taking']:>6} "
              f"{s['goal_steering']:>6} {s['in_character']:>5}  {s['scenario']}")

    def avg(keys):
        vals = [rows[k]["overall"] for k in keys if k in rows]
        return round(sum(vals) / len(vals), 2) if vals else None

    wave1 = [f"{i:02d}" for i in range(1, 5)]
    wave2 = [f"{i:02d}" for i in range(5, 15)]
    w1, w2 = avg(wave1), avg(wave2)
    overall_all = avg(list(rows))
    print("\n--- averages ---")
    print(f"Wave 1 (01-04): {w1}")
    print(f"Wave 2 (05-14): {w2}")
    print(f"All calls:      {overall_all}")

    with open(args.out, "w") as f:
        json.dump({"per_call": rows, "wave1_avg": w1, "wave2_avg": w2, "overall_avg": overall_all}, f, indent=2)
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
