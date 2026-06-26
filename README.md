# Patient Simulator Voice Bot

This bot calls Pretty Good AI's test line, pretends to be a patient, and tries to find bugs
in their phone agent. It actually holds a conversation (it listens, thinks, and talks back),
records both sides, writes a transcript, and then I go through those to see where the agent
slips up.

Built for the Pretty Good AI engineering challenge.

## How it works (short version)

The call goes out through Twilio. The audio runs through a Pipecat pipeline: Deepgram turns
the agent's speech into text, GPT-4o decides what the "patient" says next, and Cartesia
speaks it back. Silero handles turn-taking so the bot waits its turn instead of talking over
the agent. Every call is recorded and transcribed automatically.

There's a fuller writeup of the design choices in `ARCHITECTURE.md`, and the bugs I found are
in `BUG_REPORT.md`.

## What you need

- Python 3.11+ (I used 3.13)
- ffmpeg and ngrok installed
- API keys for Twilio (with a voice-enabled number), Deepgram, OpenAI, and Cartesia

## Setup

```bash
git clone <your-repo-url>
cd patient-sim-voicebot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your keys
```

You also need to authenticate ngrok once: `ngrok config add-authtoken <your-token>`.

## Running it

Easiest way is one command. It starts ngrok, starts the server, places a call, and cleans up
after itself:

```bash
make demo SCENARIO=happy_path
make demo SCENARIO=closed_day_trap   # a tougher one
```

Run `python -m src.scenarios` to see all 19 patient scenarios.

If you'd rather run the pieces by hand, use three terminals:

```bash
make tunnel    # ngrok — then copy the https URL into .env
make run       # the server
make call SCENARIO=happy_path
```

To run the whole batch of scenarios at once: `make campaign`.

## Looking at the results

```bash
make analyze   # GPT flags likely bugs in the transcripts (I verify them by hand)
make quality   # scores how natural each call sounded
```

Everything is saved under `output/`:

- `recordings/` — the call audio (`call-NN.mp3`, both sides)
- `transcripts/` — text and json, labeled by speaker with timestamps
- `costs.csv`, `campaign.csv`, `quality.json` — the run data

## Results

I ran 14 calls and found 5 real bugs (2 high, 2 medium, 1 low). The whole run cost about
$1.27. Every call went out from one number, +1 425-287-5599. The headline numbers are in
`SUMMARY.md`; the detailed findings are in `BUG_REPORT.md`.

Worth saying: I used AI heavily while building this, but I checked every bug it flagged
myself. A couple of its "bugs" turned out to be quirks of the test line (a transfer that goes
nowhere, a demo mode that accepts any birthday), not the agent, so I left those out.

## Secrets

Your real keys live in `.env`, which is gitignored and never committed. `.env.example` shows
which variables you need.
