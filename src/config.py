"""Central settings: loads + validates env vars at startup.

Run `python -m src.config` to verify your .env is complete. It prints
"all env vars present." on success, or lists exactly what's missing.

Every other module imports `settings` from here, so a misconfigured .env
fails loudly once, at startup, instead of mysteriously mid-call.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

# Ensure HTTPS works even on a venv without system CA certs. Must run before any
# library (aiohttp/httpx/websockets) creates an SSL context, so it lives at the very
# top of the module every entry point imports first.
import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from dotenv import load_dotenv

# Load .env from the repo root (one level up from src/).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

# The ONLY number this project is permitted to call (challenge hard rule).
ALLOWED_TARGET_NUMBER = "+18054398008"

# Keys required for any phase to import cleanly (service credentials + identity).
REQUIRED = {
    "TWILIO_ACCOUNT_SID": "Twilio Account SID",
    "TWILIO_AUTH_TOKEN": "Twilio Auth Token",
    "TWILIO_FROM_NUMBER": "your Twilio Voice number (E.164), the one number you test from",
    "TARGET_NUMBER": "the assessment line to call",
    "DEEPGRAM_API_KEY": "Deepgram API key (speech-to-text)",
    "OPENAI_API_KEY": "OpenAI API key (the patient LLM)",
    "LLM_MODEL": "LLM model name, e.g. gpt-4o",
    "CARTESIA_API_KEY": "Cartesia API key (text-to-speech)",
    "TTS_VOICE_ID": "Cartesia voice id",
}

# Only needed once we actually place a call (Phase 2+). ngrok generates it at runtime,
# so it's validated separately via require_public_base_url() rather than at import.
PUBLIC_BASE_URL_DESC = "your ngrok https URL (set in Phase 2)"


@dataclass(frozen=True)
class Settings:
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    target_number: str
    public_base_url: str
    deepgram_api_key: str
    openai_api_key: str
    llm_model: str
    cartesia_api_key: str
    tts_voice_id: str
    log_level: str = "INFO"


class ConfigError(RuntimeError):
    """Raised when the environment is missing or invalid."""


def load_settings() -> Settings:
    """Validate the environment and return a Settings object, or raise ConfigError."""
    missing = []
    for key, desc in REQUIRED.items():
        value = os.getenv(key, "").strip()
        if not value:
            missing.append(f"  - {key}  ({desc})")

    if missing:
        raise ConfigError(
            "Missing required environment variables:\n"
            + "\n".join(missing)
            + "\n\nCopy .env.example to .env and fill these in."
        )

    target = os.getenv("TARGET_NUMBER", "").strip()
    if target != ALLOWED_TARGET_NUMBER:
        raise ConfigError(
            f"TARGET_NUMBER must be {ALLOWED_TARGET_NUMBER} (the only number this "
            f"challenge permits calling). Got: {target!r}"
        )

    from_number = os.environ["TWILIO_FROM_NUMBER"].strip()
    if not (from_number.startswith("+") and from_number[1:].isdigit()):
        raise ConfigError(
            f"TWILIO_FROM_NUMBER must be E.164 (e.g. +14255551234). Got: {from_number!r}"
        )

    # PUBLIC_BASE_URL is optional at import; if present it must be a real https URL
    # (guards against the value accidentally being a comment or an http:// URL).
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if public_base_url and not public_base_url.startswith("https://"):
        public_base_url = ""

    return Settings(
        twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"].strip(),
        twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"].strip(),
        twilio_from_number=from_number,
        target_number=target,
        public_base_url=public_base_url,
        deepgram_api_key=os.environ["DEEPGRAM_API_KEY"].strip(),
        openai_api_key=os.environ["OPENAI_API_KEY"].strip(),
        llm_model=os.environ["LLM_MODEL"].strip(),
        cartesia_api_key=os.environ["CARTESIA_API_KEY"].strip(),
        tts_voice_id=os.environ["TTS_VOICE_ID"].strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
    )


def require_public_base_url(settings: Settings) -> str:
    """Return the public base URL, or raise if it isn't set yet (needed to place a call)."""
    if not settings.public_base_url:
        raise ConfigError(
            "PUBLIC_BASE_URL is not set. Start ngrok (`ngrok http 8000`) and put its "
            "https URL into .env as PUBLIC_BASE_URL before placing a call (Phase 2)."
        )
    return settings.public_base_url


if __name__ == "__main__":
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error:\n{exc}", file=sys.stderr)
        sys.exit(1)
    print("all env vars present.")
    if settings.public_base_url:
        print(f"PUBLIC_BASE_URL set: {settings.public_base_url}")
    else:
        print("PUBLIC_BASE_URL not set yet — that's expected; we set it in Phase 2 (ngrok).")
