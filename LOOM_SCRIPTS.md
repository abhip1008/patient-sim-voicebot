# Loom Video Scripts

Two videos, each ≤ 5 minutes. Talk like a person, not a script-reader. The goal is to show
you understand the system and made deliberate choices. Both are recorded at the end.

---

## Loom #1 — Approach walkthrough (≤ 5 min)

The single most important deliverable. Suggested beats:

1. **(0:00–0:30) What & why.** "I built a voice bot that calls your agent, role-plays
   realistic patients, records and transcribes the calls, and finds bugs. Here's the one
   command to run it." → show `make demo SCENARIO=closed_day_trap`.

2. **(0:30–1:30) Architecture, plainly.** Show the pipeline: a phone call over Twilio →
   Deepgram turns their speech to text → GPT-4o decides the patient's next line → Cartesia
   speaks it back, with Silero VAD handling turn-taking. State the key decision: **cascaded
   (STT→LLM→TTS) over speech-to-speech**, because it gives clean transcripts, per-stage
   debuggability, and precise control to steer each test — which is the whole point.

3. **(1:30–2:30) Play a strong call.** 20–40s of `call-01.mp3` (happy_path) or `call-03`
   (emergency). Let the natural back-and-forth speak for itself — this is the lucidity gate.

4. **(2:30–3:30) Show one great bug.** The controlled-substance one (call-04 @ 1:41): the
   agent starts processing an early Adderall refill without flagging it needs provider
   review. Show the transcript line, explain the real-world risk, note it **reproduced 2/2**.

5. **(3:30–4:30) Iteration.** "After my first 4 calls, the bot kept dead-ending on transfers
   to the test line, cutting tests short. I changed the persona to decline transfers and keep
   the agent engaged." Show a wave-2 call where it keeps probing.

6. **(4:30–5:00) Close.** One sentence on what you'd do next (A/B a speech-to-speech variant).

**Also worth a mention:** you used AI heavily but **verified every flagged bug by hand** —
two AI-flagged "bugs" turned out to be test-environment artifacts (transfer stub, demo DOB),
which you correctly discarded.

---

## Loom #2 — Debugging with AI (≤ 5 min)

They want to see how you *think with AI* on a real problem. Use a genuine issue from
`DEBUG_LOG.md`. Strongest pick: **the Pipecat API mismatch** or **the ngrok red-herring**.

1. **(0:00–0:30) The symptom.** Show the actual failure (e.g. the ngrok tests all failing
   with `ECONNREFUSED` / `WRONG_VERSION_NUMBER` — looked completely broken).

2. **(0:30–1:00) Frame it for the AI.** Show yourself writing a *specific* prompt: the
   symptom + what you expected + the relevant code/log. Narrate why each piece is included.

3. **(1:00–3:00) Iterate.** Show the back-and-forth: the AI's first guesses, you testing one,
   it being partly wrong, you feeding back the new result, narrowing in. For the ngrok case:
   the insight was to stop trusting the misleading client errors and check **Twilio's own
   call status**, which proved the tunnel actually worked.

4. **(3:00–4:30) The fix + verification.** Apply it, re-run, show it working. Explain in your
   own words *why* it was broken (e.g. the venv lacked CA certs → pointed Python at certifi).

5. **(4:30–5:00) Reflection.** One sentence: what made the AI collaboration effective —
   giving it the real error + verifying its claims instead of pasting blindly.

**Tip:** it's good to show a wrong turn and recover. That's real debugging.
