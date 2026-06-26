"""Quick preflight check: confirm the keys load and the APIs are reachable over HTTPS.

Run before a campaign so you catch a bad key or a broken setup early:

    python scripts/healthcheck.py     (or: make healthcheck)
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

# Allow running as `python scripts/healthcheck.py` from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_settings  # importing also applies the SSL cert fix

ENDPOINTS = {
    "Deepgram": "https://api.deepgram.com/v1/projects",
    "OpenAI": "https://api.openai.com/v1/models",
    "Cartesia": "https://api.cartesia.ai/",
    "Twilio": "https://api.twilio.com",
}


def main() -> None:
    load_settings()  # validates required env vars
    all_ok = True
    for name, url in ENDPOINTS.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as r:
                print(f"  {name}: reachable (HTTP {r.status})")
        except urllib.error.HTTPError as e:
            # 401/404 still means the HTTPS connection itself worked.
            print(f"  {name}: reachable (HTTP {e.code})")
        except Exception as e:  # noqa: BLE001
            print(f"  {name}: FAILED — {e}")
            all_ok = False
    print("\nAll endpoints reachable." if all_ok else "\nSome endpoints failed (see above).")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
