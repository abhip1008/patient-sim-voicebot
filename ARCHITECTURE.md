# Architecture

## How it works

This is a patient-simulator voice bot that places real outbound phone calls to a live AI
agent and role-plays realistic patients to surface bugs. A call begins when `call.py` uses
the Twilio REST API to dial the assessment line from a single dedicated Twilio number.
Twilio connects the call and, following TwiML instructions from a FastAPI server, opens a
**Media Stream** — a WebSocket that carries the call's audio both directions in real time —
and simultaneously records both legs of the call. The audio flows into a **Pipecat**
pipeline that runs the conversation loop: **Deepgram** transcribes the agent's speech to
text (streaming, low-latency), **GPT-4o** acting as the patient decides the next line, and
**Cartesia** text-to-speech speaks the reply back through the same WebSocket to the agent.
Silero VAD plus Pipecat's turn-taking logic govern when the bot listens versus speaks, so
the conversation feels natural and the bot can handle interruptions. After the call,
`recording.py` pulls the Twilio recording and converts it to mp3/ogg, `transcripts.py`
writes a labeled, timestamped transcript, and an LLM-assisted analyzer flags candidate bugs
that a human then verifies into the final bug report.

## Why these choices

I chose a **cascaded pipeline** (separate STT → LLM → TTS stages) over a single
speech-to-speech model because this challenge rewards introspection and control: the
cascaded design gives clean text transcripts for free, lets me read and debug each stage
independently, and lets me steer the patient persona precisely toward each test goal — all
of which directly serve the deliverables (transcripts, bug-hunting, debuggability) at the
cost of slightly higher latency, which I mitigated by streaming STT and TTS and capping LLM
reply length. I used **Twilio** for telephony because its Media Streams give real-time
bidirectional audio over a WebSocket and its dual-channel recording captures both AIs
cleanly, and **Pipecat** as the orchestration layer because it handles VAD, turn-taking,
and interruption — the exact qualities the evaluation gates on first — so my own effort
could go into the testing intelligence (the scenario catalog and bug analysis) rather than
reinventing the real-time voice plumbing. **Deepgram** was chosen for its low-latency
streaming transcription tuned for phone audio, and **Cartesia** for the lowest-latency TTS,
since transcription and synthesis lag are the main drivers of unnatural turn-taking.

## Tradeoff I'm proudest of reasoning through

The cascaded-vs-speech-to-speech decision. Speech-to-speech would have given marginally
lower latency and slightly more natural prosody, but it would have made the system a black
box: harder to get reliable transcripts, harder to debug a specific failure, and harder to
deliberately steer the patient toward a test case. Because the whole point is to *test
another agent and document what breaks*, observability mattered more than the last few
hundred milliseconds of latency.

## What I'd do with more time

- **A/B the cascaded pipeline against a speech-to-speech model** (e.g. OpenAI Realtime) on the
  same scenarios, and write up the latency/naturalness/controllability tradeoff with numbers.
- **Auto-score every call's conversation quality** over time to track naturalness across runs
  (a first version of this already ships — see `analysis/quality.py`).
- **Grow the scenario catalog** with more multi-constraint and multilingual edge cases, and add
  automatic reproduction runs for any newly found bug.
