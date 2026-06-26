# Patient Simulator Voice Bot

An automated voice bot that places real phone calls to a live AI agent, role-plays
realistic patient scenarios (scheduling, refills, insurance questions, edge cases), records
and transcribes each conversation, and surfaces bugs in the agent's behavior.

Built for the Pretty Good AI — AI Engineering Challenge.

## What it does

- Places outbound calls to a single test number using Twilio.
- Holds a natural, real-time voice conversation as a "patient" (Deepgram STT → GPT-4o →
  Cartesia TTS over a Twilio Media Stream, orchestrated with Pipecat).
- Records both sides of every call (mp3/ogg) and writes labeled, timestamped transcripts.
- Runs a catalog of ~15 designed test scenarios, each with a goal and a bug hypothesis.
- Analyzes transcripts to produce a verified bug report.

See `ARCHITECTURE.md` for how it works and why, and `BUG_REPORT.md` for findings.

## Prerequisites

- Python 3.11+
- ffmpeg installed and on your PATH
- ngrok (to expose the local server to Twilio during calls)
- Accounts / API keys for: Twilio (Voice-enabled number), Deepgram, OpenAI, Cartesia

## Setup

```bash
git clone <your-repo-url>
cd patient-sim-voicebot
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit .env with your real values
ngrok http 8000                  # put the https URL into .env as PUBLIC_BASE_URL
```

## Run

> [CONFIRM ACTUAL COMMANDS AFTER BUILDING — this is graded as "single command after setup".]

```bash
make run                          # start the FastAPI server
make call SCENARIO=happy_path     # place a single test call
make campaign                     # run the full batch of calls
```

Outputs:
- `output/recordings/` — `call-NN.mp3` / `.ogg`
- `output/transcripts/` — `transcript-NN.txt` and `.json`
- `output/costs.csv` — per-call cost estimate

## Environment variables

All documented in `.env.example`. Never commit `.env`.

## Notes

- Estimated total cost for the full run: [FILL IN from output/costs.csv] — under $20.
- All test calls were placed from a single number: [YOUR E.164 NUMBER].
- This project uses AI tooling throughout development; see the Loom walkthroughs in the
  submission.
