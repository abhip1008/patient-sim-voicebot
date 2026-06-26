# Debug Log — real problems hit while building (raw material for Loom #2)

> The "debugging with AI" video wants real, iterative problem-solving with actual prompts.
> These are genuine issues we hit and fixed during development. Pick the strongest 1–2 to
> re-stage / narrate on camera. Each entry: symptom → how we diagnosed → fix → lesson.

## 1. HTTPS silently broken in the venv (missing CA certs)
- **Symptom:** Outbound HTTPS failed with `CERTIFICATE_VERIFY_FAILED` (pypi, Twilio). Would
  have broken Deepgram/Cartesia mid-call.
- **Diagnosis:** Compared reachability across several sites; isolated it to the venv's Python
  having no CA bundle (not a network problem).
- **Fix:** Point Python at `certifi`'s bundle automatically on startup (set `SSL_CERT_FILE`
  in `config.py`, imported by every entry point).
- **Lesson:** A confusing runtime error was an environment problem, not a code problem —
  isolate the variable before changing code.

## 2. ngrok "red herring" — misleading local errors
- **Symptom:** Every local test of the ngrok tunnel failed (`WRONG_VERSION_NUMBER` locally,
  `ECONNREFUSED` from an external fetch). Looked completely broken.
- **Diagnosis:** Instead of trusting the misleading client errors, placed a real call and
  read **Twilio's own call status** — which showed `in-progress` for 40s, proving Twilio
  reached the tunnel fine.
- **Fix:** Nothing to fix — the tunnel worked; the local test tools were the problem.
- **Lesson:** Trust the authoritative signal (Twilio's view), not a flaky proxy/diagnostic.

## 3. Pipecat 1.4.0 API mismatch (don't trust one-shot AI)
- **Symptom:** First-pass API guidance mixed APIs (`PipelineWorker`, `vad_analyzer` on the
  transport, `OpenAILLMContext`) that don't exist in the installed version.
- **Diagnosis:** Introspected the **actual installed package** (`inspect.signature`, dir())
  to get real class names and kwargs before writing any pipeline code.
- **Fix:** Wrote the pipeline from verified signatures → it ran first try.
- **Lesson:** Verify AI-provided APIs against the installed source; never paste blindly.

## 4. Twilio trial account couldn't reach the assessment line
- **Symptom:** Account was `Trial`; trial accounts can only call *verified* numbers, and the
  assessment line can't be verified (not ours).
- **Diagnosis:** Checked account type via the API before burning call attempts.
- **Fix:** Upgraded the account; calls connected.
- **Lesson:** Check preconditions (account state) before debugging the call path itself.
