# AI Meeting Agent — Project Rules

## What this is
Standalone cloud-hosted bilingual (EN/ZH) in-person meeting app that produces
Internal MOM and External MOM. Full spec: `PRD_AI_MEETING_AGENT_v2.1_FINAL.docx`
(repo root). The build workflow is defined in that document, Section 22.
Separate from every other project. Never reuse their code, config, or credentials.

## Working rules (MANDATORY)
- Do ONE atomic step from PLAN.md per turn, then stop and wait.
- Start by reading: AGENTS.md, PROGRESS.md (Current state), next step in PLAN.md.
- Do not read the whole PRD; read only the section the step cites.
- Verify the step's "done when" check, then update PROGRESS.md and PLAN.md.
- No extra features or refactors. Park ideas in PROGRESS.md > Parking lot.
- If a decision is open, ask. Do not guess.
- Size limit: one concern, normally 1-3 files, verifiable in minutes (PRD §22.3).
- Commit after every verified step, on one branch per phase, so the repo is the
  checkpoint (PRD §22.11). Push only on an explicit instruction.

OpenHands auto-loads only this file. PLAN.md and PROGRESS.md are not loaded
automatically, so open them at the start of every step.

## Tech stack
Decided 2026-10-15 (P0-03).
- Backend: Python 3.13, FastAPI, SQLAlchemy, Alembic, Pydantic.
- Frontend: TypeScript, React, Vite. A plain SPA; the backend serves JSON only.
- Database: PostgreSQL.
- Files: object storage.
- Speech, translation, LLM: managed APIs, called from the backend only.
- Documents: python-docx for DOCX, WeasyPrint for PDF.
- Jobs: a background worker for post-meeting processing.
- Tests: pytest (backend), Vitest (frontend).
- Lint and format: Ruff (backend), ESLint and Prettier (frontend).
- Tooling: uv for Python, npm for Node.

Why this split: document generation and the speech and LLM SDKs are strongest in
Python, while the meeting screen, live transcript, and review UI need a real
frontend (PRD §12, §13).

Still TBD: cloud provider, region, and managed AI services (P0-02). Settle before
P1-04 and P1-05. This stack is cloud agnostic; the queue and storage products follow
that choice.

## Folder structure
Two apps in one repository, deployed separately. Created in P0-04.

    backend/app/           FastAPI application
    backend/app/api/       HTTP routes
    backend/app/core/      settings and logging
    backend/app/db/        models and migrations
    backend/app/services/  speech, translation, LLM, documents
    backend/tests/         pytest tests
    frontend/src/          React SPA
    frontend/src/i18n/     English and Mandarin strings
    docs/                  project documents

## Commands (install, run, test, lint, build)
Written in P0-03, verified in P0-04.

Backend, run from `backend/`:
- install: `uv sync`
- run:     `uv run uvicorn app.main:app --reload`
- test:    `uv run pytest`
- lint:    `uv run ruff check .`
- format:  `uv run ruff format .`

Frontend, run from `frontend/`:
- install: `npm install`
- run:     `npm run dev`
- test:    `npm run test`
- lint:    `npm run lint`
- build:   `npm run build`

## Conventions (naming, error handling, logging, i18n EN/ZH)
- Naming: snake_case in Python, camelCase in TypeScript, kebab-case for file names.
- Errors: typed exceptions in services, one JSON error shape from the API, and no
  silently swallowed exceptions.
- Logging: structured logs at the API boundary. Never log raw audio, transcript
  text, credentials, or MOM content (PRD §11.2).
- i18n: user-facing text lives in frontend string files with matching English and
  Mandarin keys. Each MOM carries both languages in one document (PRD §8.1, §8.4).
- Prompts: audience-specific MOM prompts live in the backend, versioned with the code.

## Product guardrails
- External MOM must never contain internal-only content (PRD §8.5, §11.3).
- Never invent decisions, owners, or deadlines (PRD §2.2, §7.7).
- MOMs need human approval before they are final or shared (PRD §8.5, §10).
- Managed cloud services only; no self-managed servers (PRD §11.4).
- Recording status and the AI-processing notice must stay visible (PRD §11.2).
- First release is Phase 1 only. Live transcription and live translation ship in
  Phases 2 and 3 (PRD §13).
- Raw audio is retained by default after MOM generation, and users can delete
  their own recordings.
- First release is account mode only. Guest mode is out; do not build anonymous
  meetings or guest-data deletion (deviation from PRD §11.1 and §18.5).

## Do not
- Do not commit secrets or real meeting audio/transcripts.
- Do not touch files outside this project folder.
