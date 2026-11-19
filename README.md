# Devin Telegram Orchestrator

An autonomous developer triage pipeline linking Telegram, GitHub Issues, and Cognition's Devin.

## Architecture Pipeline
1. **Telegram Ingress:** Incoming bug reports are captured via `/webhook/telegram` and pushed into a Celery task queue via Redis.
2. **Issue Generation:** Worker parses the report, deduplicates issues, and provisions a GitHub Issue.
3. **Sandbox Reproduction:** Devin orchestrates inside an isolated container, attempting to generate a reproducing test first.
4. **Autonomous PR:** On passing reproduction and zero regressions, Devin submits a draft PR with artifact logs.

## Stack
- Framework: FastAPI (Python 3.11)
- Queue & Broker: Celery + Redis
- External Integration: GitHub REST API / Octokit + Telegram Bot API
