# Phase 1 acceptance run

Run on 2026-10-20 against PRD Sections 18.1, 18.4 and 18.5. This is the first run,
so it records gaps as well as passes.

## How the run was made

- Backend: `uvicorn app.main:app --port 8010` against local PostgreSQL 17.
- Frontend: `npm run dev`, served on `http://localhost:5174` (see AGENTS.md for why
  not 5173).
- Browser: Chromium, driven through the same UI a user sees.
- API-only checks: a throwaway script that registers two accounts, creates a meeting,
  stores and approves both MOMs, exports them, and probes for another account and for
  an anonymous caller. The script is not part of the repository.
- Automated suites: `uv run pytest` (118 passed) and `uv run ruff check .` (clean).

Two limits apply to everything below. No microphone exists in this container, so the
recording transport could not be exercised. Nothing is deployed, so anything about
hosting or TLS could only be read from configuration.

## Result

7 pass, 5 fail, 2 blocked, 2 not applicable.

### 18.1 Recording and meeting setup

| Requirement | Result | Evidence |
| --- | --- | --- |
| Create a physical meeting and enter metadata | Pass | Created "Uji penerimaan Phase 1" with client, participants, agenda, location and all three languages in the UI; read back through `GET /meetings/{id}` with `client_company` intact |
| Select a microphone, then start, pause, resume and stop | Fail | No microphone selector exists: `Recorder.tsx` calls `getUserMedia({audio: true})` and never enumerates devices. Start/pause/resume/stop are implemented, but with no input device in this container they were never observed working |
| Recording status clearly visible | Pass | The screen shows `Status: Not recording` and a running `Elapsed` counter; a missing microphone produces "No microphone was found" with guidance |
| Recording continues if live transcription or translation is off or unavailable | Not applicable | Neither live feature exists yet; they are Phase 2. There is nothing to switch off |

### 18.4 MOM generation and review

| Requirement | Result | Evidence |
| --- | --- | --- |
| Separate Internal and External MOM | Pass | Two independent documents per meeting; an audience mismatch is rejected (`test_an_audience_mismatch_is_rejected`) |
| Each MOM includes English and Mandarin in one document | Pass | One document holds one version per language; the UI loaded `en`, `zh` and `id` together. Indonesian is included by the 2026-10-20 ruling |
| Extract discussion points, decisions, action items, owners, deadlines, open questions | Pass | `MomContent` carries all six; the extractor fills them and keeps absent values null. The live extraction itself was verified in P1-07; this run loaded a hand-written document to test review and approval |
| Do not invent owners, deadlines, decisions or commitments when absent | Pass | `test_keeps_missing_owner_and_deadline_as_null` plus the prompt rule. This is a sample of behaviour, not a guarantee |
| External MOM checked for internal content and requires approval | Fail | Approval works (see below), but the external-content check never runs: `app/services/sensitive.py` has tests and no caller anywhere in `app/` |
| Bilingual inconsistencies flagged | Fail | Same shape as above: `app/services/consistency.py` exists with seven tests and no caller |
| Edit and approve both MOMs and export approved files | Fail | Editing and approval work in the UI (version history shows "edited · approved"). But export does not care about approval: a draft exported with HTTP 200, and the review screen offers no export control at all |

### 18.5 Security and cloud operation

| Requirement | Result | Evidence |
| --- | --- | --- |
| Meeting data transmitted and stored securely | Blocked | Passwords use PBKDF2, session tokens are stored as SHA-256 digests, and the cookie is HTTP-only. But this stack is plain HTTP with `cookie_secure` false, and storage is a local database. Whether data is secure in transit and at rest depends on the deployment, which does not exist yet |
| Recording status and AI processing notice are visible | Fail | Status is visible. There is no AI processing notice anywhere in the UI or the strings file. PRD 11.2 and 18.5 require one |
| Guest data follows a temporary retention policy | Not applicable | Guest mode was dropped on 2026-10-15 (PRD 11.1 deviation, recorded in PROGRESS.md) |
| Authenticated users reach only their own records | Pass | A second account got 404 and an anonymous caller 401, for both the meeting and its MOM |
| Runs on managed hosting without the team administering virtual machines | Blocked | Nothing is deployed. The settled plan is Azure in Indonesia Central, and this run used a local VM |

## Gaps, in the order they should be closed

1. The external-content audit is not wired in. An external MOM can be approved and
   sent without ever being checked, which defeats the safety promise the feature
   exists for.
2. The bilingual consistency check is not wired in either. Material differences
   between the three versions pass silently.
3. Export ignores approval, so an unreviewed draft can leave the app as a finished
   file. The review screen also has no export control, so the only route today is the
   API.
4. No microphone selection, although the PRD asks for it. A notebook with a built-in
   mic and a headset cannot be chosen between.
5. No AI processing notice, which the PRD asks for twice.

Follow-ups are written into `PLAN.md` as P1-16 to P1-20. P1-15 stays open until a
second run passes.

## Follow-ups since this run

- 2026-10-20, P1-16: gap 1 is closed. Approving an external MOM now runs the audit
  against the internal MOM's notes; a finding refuses approval and names the sentence,
  and an explicit acknowledgement is needed to proceed. A check that cannot run refuses
  too.
- 2026-10-20, P1-17: gap 2 is closed. Approval also compares the three language versions
  and refuses when they disagree, naming the field and the values. Both checks answer in
  one reply. Gap 3 onwards are still open.
- 2026-10-20, P1-18: gap 3 is closed. Export answers 409 on a draft, the review screen
  downloads Word and PDF only after approval, and a refused approval shows the findings
  with an "Approve anyway" button. Gaps 4 and 5 are still open.
- 2026-10-20, P1-19: gap 4 is closed. The recording screen lists the microphones and
  records from the chosen one, and the choice holds through pause and resume. Verified in
  Chromium with a fake capture device, since this container has no real microphone. Gap 5
  is still open.
- 2026-10-20, P1-20: gap 5 is closed. The recording screen carries a notice that the
  audio is processed by AI, visible before recording starts and while it runs. All five
  gaps are closed; this run should be repeated to confirm.

## What this run does not cover

- The recording path end to end (no microphone here), including uploading audio.
- Anything that needs a deployment: TLS, Azure storage, managed hosting.
- Extraction quality on real audio; P1-07 covered the mechanism, not accuracy.
- Concurrent use by two people on the same meeting.

## Second run — 2026-10-20

Repeated after P1-16 to P1-20 closed the five gaps. Same PRD sections, same limits, with
one addition: this container now has a way to exercise a microphone.

### How the run was made

- Backend: `uvicorn app.main:app --port 8010` against local PostgreSQL 17.
- Frontend: `npm run dev`, served on `http://localhost:5174`.
- Browser: real Chromium with `--use-fake-device-for-media-stream`, driven by Playwright,
  which supplies "Fake Audio Input 1" and two others. This is the first run that could
  start, pause, resume and stop a recording at all.
- The API half is a throwaway script: two accounts, three meetings, both MOMs, approval,
  export and isolation probes. The browser half registers an account and creates a
  meeting through the form, records, then reviews, approves and downloads through the
  screen. Neither script is part of the repository.
- Automated suites: `uv run pytest` (134 passed), `uv run ruff check .` (clean),
  `npm run build` and `npm run lint` (clean).

### Result

12 pass, 0 fail, 2 blocked, 2 not applicable.

### 18.1 Recording and meeting setup

| Requirement | Result | Evidence |
| --- | --- | --- |
| Create a physical meeting and enter metadata | Pass | Created through the form with client, participants, agenda, location, type and all three languages; `GET /meetings/{id}` returned every field unchanged |
| Select a microphone, then start, pause, resume and stop | Pass | Four inputs listed with "System default" first; recording from a named device ran through pause, resume and stop and produced an audio element. Device list and choice checked in P1-19 |
| Recording status clearly visible | Pass | "Status: Recording", "Paused", "Recording stopped", with a running `Elapsed` counter |
| Recording continues if live transcription or translation is off or unavailable | Not applicable | Neither live feature exists yet; they are Phase 2 |

### 18.4 MOM generation and review

| Requirement | Result | Evidence |
| --- | --- | --- |
| Separate Internal and External MOM | Pass | Two MOMs per meeting, stored and read independently (201 for both) |
| Each MOM includes English, Mandarin and Indonesian in one document | Pass | One document, three versions listed as `en`, `zh`, `id` |
| Extract discussion points, decisions, action items, owners, deadlines, open questions | Pass | All sections present with an owner and a deadline. Extraction itself was P1-07; this run reviewed a stored document, as the first run did |
| Do not invent owners, deadlines, decisions or commitments when absent | Pass | `test_keeps_missing_owner_and_deadline_as_null`, still green. Not re-exercised here because extraction did not run |
| External MOM checked for internal content and requires approval | Pass | A sentence about the 9 percent margin, in all three languages, was refused with the `[en]` excerpt quoted; `acknowledge_issues` then approved it. Same result through the screen: findings listed, status stayed draft, "Approve anyway" went through |
| Bilingual inconsistencies flagged | Pass | A deadline of 3 November in English and 10 November in Mandarin and Indonesian was refused as `action_items[0].deadline` with the three values named; the on-demand endpoint reported one mismatch |
| Edit and approve both MOMs and export approved files | Pass | Edited through the screen, saved as a draft, approved and locked; Word (37,105 bytes) and PDF (4,588 bytes) downloaded from the button, and both files open as their format. A draft still answers 409, and an edit to an approved MOM answers 409. Hiding a language removes it from the export (no Chinese characters in the Word file) while all three versions stay stored |

### 18.5 Security and cloud operation

| Requirement | Result | Evidence |
| --- | --- | --- |
| Meeting data transmitted and stored securely | Blocked | Unchanged: plain HTTP here, `cookie_secure` false, local database. Depends on the deployment, which does not exist |
| Recording status and AI processing notice are visible | Pass | The notice is on screen before recording, while recording and while paused, in the same words each time |
| Guest data follows a temporary retention policy | Not applicable | Guest mode was dropped 2026-10-15 |
| Authenticated users reach only their own records | Pass | A second account got 404 for the meeting and its MOM; an anonymous caller got 401 |
| Runs on managed hosting without the team administering virtual machines | Blocked | Unchanged: nothing is deployed |

### What the run found

- The gate also compares **internal notes** across languages. A note written in English
  only is refused ("English includes the note ..., while the Chinese and Indonesian
  versions have an empty internal_notes list"). That is the check doing its job, but it
  means notes must be translated like every other field, which is worth knowing before
  anyone writes a MOM by hand.
- An edit that adds a claim the other versions do not carry is refused, even on the
  internal MOM. Rephrasing without changing the meaning passes. Both were observed by
  accident while driving the screen.
- The one gap this run cannot close by testing: **the recording never leaves the
  browser.** The meeting screen records, plays back and stops there; nothing uploads the
  audio, so a user cannot get from a recorded meeting to minutes inside the app. The
  upload endpoint and the worker exist and were exercised through the API, so this is a
  missing button and one call, not a missing pipeline. Recorded as P1-21.

