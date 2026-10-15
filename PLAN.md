# PLAN

Roadmap for AI Meeting Agent. Grouped by the phases in PRD §13.
One atomic step per session turn. Every step has an ID, a PRD reference, the
files it touches, and a "done when" check.

Phase 1 is planned in detail below. Phases 2-4 are headings only and are broken
into atomic steps when their turn comes.

File paths for the P1 steps are placeholders until the skeleton exists (P0-04 and
P0-05).

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

- [ ] P0-05  Frontend skeleton: Vite React app that starts and builds
  PRD: §12   Files: frontend/ (Vite scaffold plus a minimal page)
  Done when: npm install, npm run dev, npm run build, and npm run lint work.
  Split from the original P0-04 on 2026-10-15: one skeleton was two concerns and
  well past the file limit in PRD §22.3.

## Phase 1 — Core Meeting Intelligence and MOM (PRD §13)

- [ ] P1-01  Define data model: meeting, audio, transcript, MOM, version
  PRD: §7.1, §12   Files: TBD (paths from P0-04/P0-05)
  Done when: schema file reviewed; migration runs.

- [ ] P1-02  Meeting creation: metadata form and API
  PRD: §7.1   Files: TBD (paths from P0-04/P0-05)
  Done when: meeting can be created and read back.

- [ ] P1-03  Microphone capture in the client (record and stop)
  PRD: §7.2   Files: TBD (paths from P0-04/P0-05)
  Done when: local audio recorded and playable.

- [ ] P1-04  Secure audio upload and storage with retention setting
  PRD: §7.2, §11   Files: TBD (paths from P0-04/P0-05)
  Done when: audio stored and linked to a meeting.

- [ ] P1-05  Post-meeting transcription job, English only
  PRD: §7.5   Files: TBD (paths from P0-04/P0-05)
  Done when: transcript saved for a sample audio.

- [ ] P1-06  Add Mandarin and mixed-language transcription
  PRD: §7.5   Files: TBD (paths from P0-04/P0-05)
  Done when: mixed EN/ZH sample transcribed.

- [ ] P1-07  Meeting intelligence extraction: topics, decisions, actions, owners, deadlines
  PRD: §7.6, §7.7   Files: TBD (paths from P0-04/P0-05)
  Done when: structured JSON output on a sample.

- [ ] P1-08  Internal MOM generator (bilingual) with audience-specific prompt
  PRD: §8.2, §8.4   Files: TBD (paths from P0-04/P0-05)
  Done when: Internal MOM draft produced.

- [ ] P1-09  External MOM generator (bilingual) with audience-specific prompt
  PRD: §8.3, §8.5   Files: TBD (paths from P0-04/P0-05)
  Done when: External MOM draft produced.

- [ ] P1-10  Sensitive-content check on External MOM
  PRD: §8.5, §11.3   Files: TBD (paths from P0-04/P0-05)
  Done when: seeded internal-only text is flagged.

- [ ] P1-11  Bilingual consistency check
  PRD: §8.6   Files: TBD (paths from P0-04/P0-05)
  Done when: mismatch between EN and ZH is flagged.

- [ ] P1-12  Review screen: edit, approve, version history
  PRD: §10   Files: TBD (paths from P0-04/P0-05)
  Done when: approved MOM is locked and versioned.

- [ ] P1-13  DOCX and PDF export
  PRD: §10   Files: TBD (paths from P0-04/P0-05)
  Done when: both formats open correctly.

- [ ] P1-14  Basic access control (account mode only)
  PRD: §11   Files: TBD (paths from P0-04/P0-05)
  Done when: unauthorized access is blocked.
  Guest mode dropped 2026-10-15, so the guest-deletion half is gone. Deliberate
  deviation from PRD §11.1; see PROGRESS.md.

- [ ] P1-15  Phase 1 acceptance run against Section 18.1, 18.4, 18.5
  PRD: §18   Files: TBD (paths from P0-04/P0-05)
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
