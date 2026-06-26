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

**One command** (starts ngrok, boots the server, places a live call, then cleans up):

```bash
make demo SCENARIO=happy_path
# try a harder one:  make demo SCENARIO=closed_day_trap
```

See all 19 scenarios with `python -m src.scenarios`.

### Or run the pieces yourself

```bash
make tunnel                       # terminal 1: start ngrok, put the https URL in .env
make run                          # terminal 2: start the server
make call SCENARIO=happy_path     # terminal 3: place one live call
make campaign                     # or: run the whole batch of scenarios
```

### Review the results

```bash
make analyze     # flag candidate bugs from saved transcripts (you verify them)
make quality     # score how natural each call sounded
```

Everything lands under `output/`:
- `recordings/` — `call-NN.mp3` (both sides, dual-channel)
- `transcripts/` — `transcript-NN.txt` and `.json` (speaker-labeled, timestamped)
- `costs.csv`, `campaign.csv`, `quality.json` — run data

## Environment variables

All documented in `.env.example`. Never commit `.env`.

## Results at a glance

- 14 calls, 5 verified bugs (2 High, 2 Medium, 1 Low) — see `BUG_REPORT.md` and `SUMMARY.md`.
- Total cost for the full run: **~$1.27** (well under $20).
- All calls placed from a single number: **+1 425-287-5599**.
- This project used AI throughout development — including verifying every AI-flagged bug by
  hand. See the Loom walkthroughs in the submission (scripts in `LOOM_SCRIPTS.md`).
