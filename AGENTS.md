# AI Meeting Agent — Project Rules

## What this is
Standalone cloud-hosted multilingual (EN/ZH/ID) in-person meeting app that produces
Internal MOM and External MOM. Full spec: `PRD_AI_MEETING_AGENT_v2.1_FINAL.docx`
(repo root). The build workflow is defined in that document, Section 22.
Separate from every other project. Never reuse their code, config, or credentials.

## Talking to the user (read before writing any message)
The user does not have an IT background. This section covers anything written for the
user. PLAN.md, PROGRESS.md, and the rest of this file are read by the agent, so they
stay precise and technical.

- Write to the user in English as of 2026-10-20, because the user forwards these
  messages to their engineer. Keep sentences short and still explain a technical term
  the first time it appears. Before that date the rule was Indonesian.
  docs/PLAN_NON_TECHNICAL.md stays in Indonesian, because it is the user's own view.
  Code, comments, commit messages, and file contents stay in English.
- Explain a technical term once, in a few words, the first time it appears. Do not
  re-explain it later.
- Report a problem as: what went wrong, what I did about it, what it means for the
  user. Never paste a command dump or a log excerpt as the explanation.
- When a decision is needed, offer two or three options with the consequences in
  plain words, then name a recommendation. Never hand over a bare list of
  technologies and call it a choice.
- Every report answers three questions: what is finished, what it means for the user,
  and what the user needs to decide. Anything else is optional detail.
- Leave out checksums, port numbers, package counts, and version numbers unless the
  user asks. Say "the file is unchanged" rather than quoting a fingerprint.
- docs/PLAN_NON_TECHNICAL.md is the user's view of the plan. Update it when a step
  changes what the user will be able to do.

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

Settled 2026-10-20: the cloud platform is Azure, because the user rents Azure
infrastructure in Indonesia (`indonesiacentral`). This replaces the AWS plan of
2026-10-19; no AWS code was ever written, so the switch cost nothing. Retention stays
90 days from upload, with the owner able to delete sooner. Region layout is still open.
Verified 2026-10-20: Indonesia Central exists (Jakarta, three availability zones) and
PostgreSQL Flexible Server runs there, but Azure Speech's supported-region list omits it
and no Azure OpenAI model table mentions Indonesia. Speech and OpenAI therefore appear
to need Southeast Asia (Singapore) at the nearest. Blob Storage in Indonesia Central is
assumed, not verified.
Layout settled 2026-10-20, user chose option A: the app, the database and the recordings
stay in Indonesia Central, while Azure Speech and Azure OpenAI run in Singapore. The
user asked to be reminded at build time, so confirm this layout again before writing
either cloud driver. Neither cloud driver is verified yet, because no credentials
exist in the working environment. Until then `app/services/storage.py` writes to a
local directory and `app/services/speech.py` runs a local Whisper model. Both are
single-method seams, so swapping a driver touches one file. The local model is `small`,
the first size that handles Mandarin and English code-switching acceptably; `tiny`
garbled Mandarin badly. Still TBD: the LLM for MOM generation, due before P1-08. The
queue and the remaining products follow those choices.

Residency facts, including what is verified and what is only assumed, are collected in
`PROGRESS.md` under "Data residency — what is known". Read that before writing any
client-facing sentence about where meeting data is stored or processed.

On 2026-10-19 the speech seam also gained a Huawei Cloud SIS driver, selected with
`SPEECH_PROVIDER=huawei`, because the customer asked whether the whole stack could run
on Huawei. It has never called the live service: there are no Huawei credentials here.
Its job body and response mapping are tested, but whether SIS switches language inside
one file is unproven. Test it with a real recording before treating Huawei as settled.

## Folder structure
Two apps in one repository, deployed separately. Created in P0-04.

    backend/app/           FastAPI application
    backend/app/api/       HTTP routes
    backend/app/core/      settings and logging
    backend/app/db/        database models
    backend/app/schemas/   request and response models
    backend/app/prompts/   MOM and check prompts
    backend/app/services/  speech, translation, LLM, documents
    backend/app/worker.py  background job entry point
    backend/alembic/       database migrations
    backend/tests/         pytest tests
    frontend/src/          React SPA
    frontend/src/pages/    route-level screens
    frontend/src/components/  shared components
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
- lint:    `npm run lint`
- build:   `npm run build`
- test:    not wired yet. Vitest arrives with the first frontend test step.

Development wiring (since P1-14):
- The frontend calls `/api/...` on its own origin and `vite.config.ts` proxies that to
  the backend, so the session cookie stays first-party.
- Port 8000 belongs to the Agent Canvas platform here, not to us. Run the API on 8010:
  `uvicorn app.main:app --reload --port 8010`, which is the proxy's default target
  (`API_PROXY_TARGET` overrides it).
- The platform's service worker on `localhost:5173` also answers `/api/auth/me`, so a
  browser session there loses the sign-in on reload. The dev server therefore defaults
  to 5174 (`VITE_DEV_PORT` overrides it).
- PostgreSQL 17 is a local cluster here, not a container: `sudo pg_ctlcluster 17 main
  start`. It does stop between long sessions; a 500 that reports "connection refused"
  on 5432 means it stopped, not that the code broke.
- Start the API and the dev server with `setsid nohup ... &`. A plain background job is
  reaped when the tool call that started it ends, which looks like a crash.
- That API process needs `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY` in its own
  environment, passed on the same command line that starts it. Without them every route
  that calls the model answers 503 "must be set", which looks like an outage but is the
  process missing its credentials.

## Conventions (naming, error handling, logging, i18n EN/ZH)
- Naming: snake_case in Python, camelCase in TypeScript, kebab-case for file names.
- Errors: typed exceptions in services, one JSON error shape from the API, and no
  silently swallowed exceptions.
- Logging: structured logs at the API boundary. Never log raw audio, transcript
  text, credentials, or MOM content (PRD §11.2).
- i18n: the interface ships in English only for the first release. Screen text lives
  in one string file, so adding another interface language later means translating
  that file rather than rewriting screens. The PRD requires bilingual meetings and
  MOMs, not a bilingual interface. Ruling 2026-10-20: each MOM carries English,
  Mandarin and Indonesian in one document by default, and the reviewer chooses which
  languages to keep. A removed language is hidden, not deleted. The MOM is authored
  once in the meeting's language and the other two are translations of that text.
  The source language is the one the transcript detected.
  Deliberate deviation from PRD §8.1 and §8.4; see PROGRESS.md.
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
