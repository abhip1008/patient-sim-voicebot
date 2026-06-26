# Convenience commands. Filled in as phases land.
# Usage: make <target>

.PHONY: help install demo run call call-inline campaign tunnel analyze quality healthcheck

help:
	@echo "Targets:"
	@echo "  install      - create venv and install requirements"
	@echo "  demo         - ONE-COMMAND live call: make demo SCENARIO=happy_path"
	@echo "  tunnel       - start ngrok on port 8000 (run in its own terminal)"
	@echo "  run          - start the FastAPI server (run in its own terminal)"
	@echo "  call         - live conversation call:  make call SCENARIO=happy_path"
	@echo "  call-inline  - quick telephony test (fixed greeting, no AI, no server needed)"
	@echo "  campaign     - run the full batch of calls"
	@echo "  analyze      - flag candidate bugs from saved transcripts"
	@echo "  quality      - score conversation quality of saved calls"

# One command after setup: ngrok + server + a live call, with cleanup.
demo:
	bash scripts/demo.sh $(SCENARIO)

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

tunnel:
	ngrok http 8000

run:
	. .venv/bin/activate && uvicorn src.server:app --port 8000 --reload

# Live conversation: needs `make tunnel` + `make run` going first (server + ngrok).
call:
	. .venv/bin/activate && python -m src.call --server --scenario $(SCENARIO)

# Quick telephony smoke test: dials, speaks a fixed line, records. No server/ngrok needed.
call-inline:
	. .venv/bin/activate && python -m src.call

campaign:
	. .venv/bin/activate && python -m runner.campaign

analyze:
	. .venv/bin/activate && python -m analysis.analyze output/transcripts/transcript-*.json

quality:
	. .venv/bin/activate && python -m analysis.quality "output/transcripts/transcript-*.json"

healthcheck:
	. .venv/bin/activate && python scripts/healthcheck.py
