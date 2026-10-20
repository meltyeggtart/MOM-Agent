# PLAN

Roadmap for AI Meeting Agent. Grouped by the phases in PRD §13.
One atomic step per session turn. Every step has an ID, a PRD reference, the
files it touches, and a "done when" check.

Phase 1 is planned in detail below. Phases 2-4 are headings only and are broken
into atomic steps when their turn comes.

File paths were filled in at P0-06 (PRD §22.6). A step may adjust them, and must
record the change in PROGRESS.md when it does.

## Phase 0 — Foundation

- [x] P0-01  Create AGENTS.md, PLAN.md, PROGRESS.md (skeleton only, no app code)
  PRD: §22.6   Files: AGENTS.md, PLAN.md, PROGRESS.md
  Done when: three files exist and are reviewed by the user.

- [x] P0-02  Record the cloud provider, region, and managed AI services decision
  PRD: §12, §19   Files: AGENTS.md
  Done when: decision written in AGENTS.md; user approved.
  Re-scoped 2026-10-15: the user accepted a placeholder for now, so this step
  records "TBD" and the real choice moves to a deferred, unapproved step (see
  PROGRESS.md > Parking lot). Blocking before P1-04 and P1-05.

- [x] P0-03  Choose tech stack and write folder structure and commands
  PRD: §12   Files: AGENTS.md
  Done when: AGENTS.md stack and commands filled in.

- [x] P0-04  Backend skeleton: FastAPI app that starts and answers
  PRD: §12   Files: backend/pyproject.toml, backend/app/main.py, backend/tests/
  Done when: uv sync, uv run uvicorn, uv run pytest, and uv run ruff check work.

- [x] P0-05  Frontend skeleton: Vite React app that starts and builds
  PRD: §12   Files: frontend/ (Vite scaffold plus a minimal page)
  Done when: npm install, npm run dev, npm run build, and npm run lint work.
  Split from the original P0-04 on 2026-10-15: one skeleton was two concerns and
  well past the file limit in PRD §22.3.

- [x] P0-06  Fill in the concrete file paths for every Phase 1 step
  PRD: §22.6   Files: PLAN.md, AGENTS.md
  Done when: no placeholder path remains in PLAN.md and the AGENTS.md folder tree
  matches the paths the steps name.

## Phase 1 — Core Meeting Intelligence and MOM (PRD §13)

- [x] P1-01a  Connect the database and the migration tool
  PRD: §12   Files: backend/pyproject.toml, backend/app/core/settings.py,
  backend/app/db/base.py, backend/app/db/session.py, backend/alembic.ini,
  backend/alembic/env.py
  Done when: an empty migration runs against a real PostgreSQL instance.
  Split from P1-01 on 2026-10-15: wiring the toolchain and defining five tables are
  two concerns, and together they pass the file limit in PRD §22.3.

- [x] P1-01b  Define data model: meeting, audio, transcript, MOM, version
  PRD: §7.1, §12   Files: backend/app/db/models.py,
  backend/alembic/versions/ (schema migration)
  Done when: schema file reviewed; migration creates every table.

- [x] P1-02a  Meeting creation API: create and read back
  PRD: §7.1   Files: backend/app/schemas/meeting.py, backend/app/api/meetings.py,
  backend/app/main.py, backend/app/core/settings.py
  Done when: a create request stores the meeting and a read request returns it.
  Split from P1-02 on 2026-10-15: the storage path and the screen are two concerns.

- [x] P1-02b  New meeting form on screen
  PRD: §7.1   Files: frontend/src/pages/NewMeeting.tsx,
  frontend/src/i18n/messages.ts, frontend/src/App.tsx
  Done when: the form creates a meeting through the API and shows the result.
  Settled 2026-10-15: the interface is English only, and screen text lives in the one
  string file so Mandarin can be added later by translating it.

- [x] P1-02c  Automated test foundation: tests run against the database
  Source: added 2026-10-15 with the user's agreement; not required by the PRD.
  Files: backend/tests/conftest.py, backend/tests/test_meetings_api.py
  Done when: the meeting endpoints are covered by tests that leave no data behind.
  Reason: P1-02a shipped with hand verification only, and every later feature builds
  on those endpoints.

- [x] P1-03  Microphone capture in the client (record and stop)
  PRD: §7.2   Files: frontend/src/components/Recorder.tsx, frontend/src/pages/Meeting.tsx
  Done when: local audio recorded and playable.

- [x] P1-04  Secure audio upload and storage with retention setting
  PRD: §7.2, §11   Files: backend/app/services/storage.py, backend/app/api/recordings.py, backend/app/core/settings.py
  Done when: audio stored and linked to a meeting.

- [x] P1-05  Post-meeting transcription job, English only
  PRD: §7.5   Files: backend/app/services/speech.py, backend/app/worker.py, backend/tests/test_speech.py
  Done when: transcript saved for a sample audio.

- [x] P1-06  Add Mandarin and mixed-language transcription
  PRD: §7.5   Files: backend/app/services/speech.py, backend/tests/test_speech.py
  Done when: mixed EN/ZH sample transcribed.

- [x] P1-06b  Add Huawei Cloud SIS speech driver behind the same seam
  PRD: §7.5   Files: backend/app/services/speech.py,
  backend/app/core/settings.py, backend/tests/test_huawei.py,
  backend/.env.example, backend/pyproject.toml
  Done when: the driver builds a valid SIS job body and maps a real response.
  Never called against the live service; no credentials exist here. See PROGRESS.md.

- [x] P1-06c  Add Indonesian as a meeting language
  Source: added 2026-10-20 at the user's request. "Additional languages" is a Phase 4
  item in this plan, so this deliberately pulls one language into Phase 1.
  Files: backend/app/schemas/meeting.py, backend/tests/test_meetings_api.py,
  backend/tests/test_speech.py, frontend/src/pages/NewMeeting.tsx,
  frontend/src/i18n/messages.ts
  Done when: a meeting declaring "id" is accepted, and the worker passes "id" as the
  transcription hint.
  Scope: the spoken meeting language and its transcript only. Whether Indonesian also
  enters the MOM is open and due before P1-08.

- [ ] P1-07  Meeting intelligence extraction: topics, decisions, actions, owners, deadlines
  PRD: §7.6, §7.7   Files: backend/app/services/intelligence.py, backend/app/schemas/insights.py, backend/tests/test_intelligence.py
  Done when: structured JSON output on a sample.

- [ ] P1-08  Internal MOM generator (bilingual) with audience-specific prompt
  PRD: §8.2, §8.4   Files: backend/app/services/mom.py, backend/app/prompts/internal_mom.md, backend/app/schemas/mom.py
  Done when: Internal MOM draft produced.

- [ ] P1-09  External MOM generator (bilingual) with audience-specific prompt
  PRD: §8.3, §8.5   Files: backend/app/prompts/external_mom.md, backend/app/services/mom.py, backend/tests/test_mom.py
  Done when: External MOM draft produced.

- [ ] P1-10  Sensitive-content check on External MOM
  PRD: §8.5, §11.3   Files: backend/app/services/sensitive.py, backend/app/prompts/sensitive_check.md, backend/tests/test_sensitive.py
  Done when: seeded internal-only text is flagged.

- [ ] P1-11  Bilingual consistency check
  PRD: §8.6   Files: backend/app/services/consistency.py, backend/app/prompts/consistency_check.md, backend/tests/test_consistency.py
  Done when: mismatch between EN and ZH is flagged.

- [ ] P1-12  Review screen: edit, approve, version history
  PRD: §10   Files: backend/app/api/mom.py, frontend/src/pages/Review.tsx, frontend/src/components/MomEditor.tsx
  Done when: approved MOM is locked and versioned.

- [ ] P1-13  DOCX and PDF export
  PRD: §10   Files: backend/app/services/documents.py, backend/app/api/export.py, backend/tests/test_documents.py
  Done when: both formats open correctly.

- [ ] P1-14  Basic access control (account mode only)
  PRD: §11   Files: backend/app/api/auth.py, backend/app/core/security.py, backend/app/db/models.py
  Done when: unauthorized access is blocked.
  Guest mode dropped 2026-10-15, so the guest-deletion half is gone. Deliberate
  deviation from PRD §11.1; see PROGRESS.md.

- [ ] P1-15  Phase 1 acceptance run against Section 18.1, 18.4, 18.5
  PRD: §18   Files: docs/ACCEPTANCE_PHASE1.md
  Done when: checklist passed and logged.
  Skip the guest-data item of §18.5 (guest mode dropped 2026-10-15).

## Phase 2 — Optional Live Transcription (PRD §13)
Live Transcription On/Off control, streaming EN/Mandarin text, timestamps and
speaker labels when available, service status, recording continues when the
feature is off or unavailable.
Not yet broken into atomic steps.

## Phase 3 — Optional Live Translation (PRD §13)
Live Translation On/Off control, independent of but dependent on transcription,
original and translated text, latency and code-switching validation, prospective
resume with no backfill.
Not yet broken into atomic steps.

## Phase 4 — Extended Meeting Intelligence (PRD §13)
Terminology and knowledge base/RAG, confirmed speaker-name mapping, meeting
templates and more export options, history search and cross-meeting comparison,
optional calendar/CRM/email/project-management integrations, additional languages.
Not yet broken into atomic steps.
