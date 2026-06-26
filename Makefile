# Convenience commands. Filled in as phases land.
# Usage: make <target>

.PHONY: help install run call campaign tunnel

help:
	@echo "Targets:"
	@echo "  install   - create venv and install requirements (Phase 1)"
	@echo "  tunnel    - start ngrok on port 8000 (Phase 2)"
	@echo "  run       - start the FastAPI server (Phase 2)"
	@echo "  call      - place a single test call: make call SCENARIO=happy_path (Phase 2+)"
	@echo "  campaign  - run the full batch of calls (Phase 8)"

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

tunnel:
	ngrok http 8000

run:
	. .venv/bin/activate && uvicorn src.server:app --port 8000 --reload

call:
	. .venv/bin/activate && python -m src.call --scenario $(SCENARIO)

campaign:
	. .venv/bin/activate && python -m runner.campaign
