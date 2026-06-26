# Convenience commands. Filled in as phases land.
# Usage: make <target>

.PHONY: help install run call campaign tunnel

help:
	@echo "Targets:"
	@echo "  install      - create venv and install requirements"
	@echo "  tunnel       - start ngrok on port 8000 (run in its own terminal)"
	@echo "  run          - start the FastAPI server (run in its own terminal)"
	@echo "  call         - live conversation call:  make call SCENARIO=happy_path"
	@echo "  call-inline  - quick telephony test (fixed greeting, no AI, no server needed)"
	@echo "  campaign     - run the full batch of calls (Phase 8)"

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
