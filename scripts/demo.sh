#!/usr/bin/env bash
#
# One-command demo: starts ngrok, boots the server, places a single live call, and
# cleans up afterward. This is the "single command after setup" the challenge asks for.
#
#   make demo                       # default scenario (happy_path)
#   make demo SCENARIO=closed_day_trap
#
# Prereqs (one-time): .venv created, .env filled, ngrok authenticated. See README.
set -euo pipefail

cd "$(dirname "$0")/.."
SCENARIO="${1:-happy_path}"

# Start from a clean slate (free tier allows one ngrok session / one server).
pkill -f "ngrok http 8000" 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1

cleanup() {
  echo "Cleaning up (stopping server + ngrok)..."
  [[ -n "${SERVER_PID:-}" ]] && kill "$SERVER_PID" 2>/dev/null || true
  [[ -n "${NGROK_PID:-}" ]] && kill "$NGROK_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting ngrok..."
ngrok http 8000 --log=stdout >/tmp/pgai_ngrok.log 2>&1 &
NGROK_PID=$!
sleep 4

URL=$(curl -s http://127.0.0.1:4040/api/tunnels \
  | .venv/bin/python -c "import sys,json; print([t['public_url'] for t in json.load(sys.stdin)['tunnels'] if t['public_url'].startswith('https')][0])")
echo "ngrok URL: $URL"

# Write the public URL into .env (PUBLIC_BASE_URL).
.venv/bin/python - "$URL" <<'PY'
import sys
url = sys.argv[1]
lines = open(".env").read().splitlines()
open(".env", "w").write("\n".join(
    f"PUBLIC_BASE_URL={url}" if l.startswith("PUBLIC_BASE_URL") else l for l in lines) + "\n")
PY

echo "Starting server..."
.venv/bin/uvicorn src.server:app --port 8000 >/tmp/pgai_server.log 2>&1 &
SERVER_PID=$!
sleep 4

echo "Placing a live call (scenario: $SCENARIO)..."
.venv/bin/python -m src.call --server --scenario "$SCENARIO"

echo "Done. Recording + transcript saved under output/."
