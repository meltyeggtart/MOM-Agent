# Progress

## Current state
Phase: P1. Last done: P1-06
Next: P1-07
Blockers: none
Open decisions: the LLM for MOM generation is still TBD (PRD §19.1), due before P1-08.
Storage is settled: AWS S3 in Singapore. Retention is settled: 90 days from upload,
and account mode only. Speech is settled: Amazon Transcribe. Every other PRD §19 item
is answered — see the log.

## Log (newest first)

### P1-06 — 2026-10-19 (done)
Did: Mandarin and mixed-language transcription. The worker no longer assumes English.
A meeting that declares one language passes it as a hint; a meeting that declares two
lets Whisper detect the language, which is what code-switching needs. The transcript
stores the detected language.
Files: backend/app/services/speech.py, backend/app/worker.py,
backend/tests/test_speech.py, backend/tests/fixtures/mandarin.mp3,
backend/tests/fixtures/mixed.wav, backend/app/core/settings.py
Verified: 22 tests pass (3 new) and ruff is clean. A Mandarin sample transcribed as
correct simplified Chinese. A sample that starts in English and switches to Mandarin
kept both languages in one transcript. Through the real API, a meeting declaring en+zh
produced a four-segment transcript containing both sentences, and a meeting declaring
only zh produced simplified Chinese.
Notes: the model is now `small`. `tiny` garbled Mandarin: "项目预算" came out as
"像武玉算", so it was not usable. `small` takes about 5 seconds per 12 seconds of audio
on this CPU and downloads about 460 MB on first use.
Whisper writes Mandarin in traditional characters when the audio mixes languages and in
simplified characters when the audio is Mandarin only. The bilingual checks in P1-11
must compare characters, not assume a script.
The fixtures are synthesized sentences, so they prove the pipeline, not real-meeting
accuracy. A real recording is still the only way to judge that.

### P1-05 — 2026-10-19 (done)
Did: added post-meeting transcription. A worker process looks for recordings whose
meeting has no English transcript, transcribes the audio, and stores the text with
timestamps and the provider name. Running it twice does not duplicate the transcript.
Files: backend/app/services/speech.py, backend/app/worker.py,
backend/tests/test_speech.py, backend/tests/fixtures/kickoff.mp3,
backend/app/core/settings.py, backend/.env.example, backend/pyproject.toml
Verified: 19 tests pass (4 new) and ruff is clean. A 7.4-second English sample was
uploaded through the API, the worker transcribed it in under a second, and the row held
the expected sentence, one segment spanning 0-7000 ms, and the provider name. A second
pass saved nothing. A recording whose audio file was gone was skipped instead of
failing.
Notes: no AWS or Google credentials exist here, so the production target (Amazon
Transcribe) could not be called or tested. The code runs a local Whisper model
(faster-whisper, tiny.en) behind a single-method seam instead. That is a deliberate
departure from the managed-API rule in AGENTS.md, taken so the pipeline could be proven
end to end; Transcribe slots into the same seam once credentials exist.
The fixture is a synthesized English sentence, committed so the test repeats without a
network. The model downloads on first use (75 MB) and is cached outside the repository.
The first run needed av<14: faster-whisper 1.2.1 calls a PyAV argument that 19.0.1
removed. That pin is in pyproject.toml.

### P1-04 — 2026-10-19 (done)
Did: added the recording upload. A file posted to a meeting is stored under a
generated key and recorded in the recordings table with its content type, byte size,
optional duration, and an expiry 90 days out. A download endpoint returns the stored
bytes. An unknown meeting, a content type outside a small audio allowlist, an empty
file, and a file over 200 MB are all refused.
Files: backend/app/services/storage.py, backend/app/api/recordings.py,
backend/app/schemas/recording.py, backend/app/core/settings.py, backend/app/main.py,
backend/app/db/models.py, backend/.env.example, .gitignore, backend/pyproject.toml,
backend/tests/test_recordings_api.py
Verified: 15 tests pass (8 of them new) and ruff is clean. Against a running server, a
real 2-second WAV was created and uploaded with its meeting, stored as a 64 KB file,
and downloaded back byte for byte with the right content type. The row carried the
meeting link, the size, the duration, and a retention window of exactly 90 days. An
unknown meeting answered 404, text/plain answered 415, an empty file answered 400, and
an "audio/webm;codecs=opus" header was stored as "audio/webm". Every rejection left no
file behind. The test meeting and its files were then deleted.
Notes: ten files rather than the usual 1-3. A new endpoint needs its settings, schema,
router registration, dependency and tests; splitting that would ship a route that does
nothing on its own.
Storage is a local directory for now. The production target is AWS S3 in Singapore,
settled 2026-10-19 under the user's delegation, but there are no AWS credentials in
this environment, so the S3 driver is not written yet. The storage module is the seam
for it. Encryption at rest (PRD §11.2) arrives with that driver; a local development
directory has nothing to configure.

### P1-03 — 2026-10-19 (done)
Did: added microphone capture to the meeting screen. Start, pause, resume, and stop
drive the browser recorder. The screen shows the recording status and the elapsed
time, and plays the captured audio back once recording stops. A blocked microphone,
a missing device, and an unsupported browser each show their own message and the
practical step to take next.
Files: frontend/src/components/Recorder.tsx, frontend/src/pages/Meeting.tsx,
frontend/src/App.tsx, frontend/src/i18n/messages.ts
Verified: lint and the type-checked production build pass. In a real browser
(Chromium with a simulated microphone) recording started, pause and resume changed
the status, stop produced a playable 51 KB WebM/Opus clip inside the page, and no
console error appeared. Two failure runs were checked: a blocked microphone showed
"The microphone is blocked" with the settings guidance, and a machine without a
device showed "No microphone was found" with the connection guidance. Both returned
the control to "Not recording".
Notes: PLAN.md names two files for this step; four were needed. The app had no way
to reach a second screen, so App.tsx now switches between the new-meeting screen and
the meeting screen. A plain state switch was used instead of adding a router, since
routing is not needed yet.
Elapsed time counts wall clock from the start, so it keeps running while recording is
paused; PRD §7.2 calls it the meeting duration, not the audio length.
The browser check used a throwaway Playwright script. It is not committed, so no
automated test covers this component yet.

### Push and pull request for P0 + P1-02 — 2026-10-19 (done)
Did: pushed branch p0-foundation and opened pull request #1 against main, then merged
it with a rebase. Created branch p1-core from the merged main for the rest of Phase 1.
Verified: the remote branch pointed at the committed head, the pull request reported
12 commits, 42 files, and no conflict, and main moved to the merged commit.
Notes: the first GITHUB_TOKEN value was rejected by GitHub. The user replaced it and
the push then succeeded.

### P1-02b — 2026-10-15 (done)
Did: built the new meeting screen. It carries the fields from PRD §7.1 — title, date
and time, meeting languages, client or company, project, participants, agenda,
location, meeting type, and the in-person flag — posts them to the meeting API, and
shows the created meeting with its reference.
Files: frontend/src/pages/NewMeeting.tsx, frontend/src/i18n/messages.ts,
frontend/src/App.tsx, frontend/src/index.css, frontend/src/vite-env.d.ts
Verified: lint and production build pass. In a real browser the form was filled and
submitted; the backend logged "POST /meetings 201 Created", the meeting table held the
row, and the screen showed "Meeting created" with the title and reference. The row was
then deleted and both servers stopped.
Notes: the date field starts at the current local time, because a meeting is usually
recorded once it is under way. The value can still be changed, and clearing it still
produces the "enter a date and time" message.
The screen sends the browser's time zone offset, so a typed local time is stored as the
same instant instead of being read as UTC.
Port 8000 is held by a platform service on this machine, so the browser check ran with
the API on 8010 and VITE_API_BASE_URL pointing there. The code default stays on 8000,
the usual local address for this backend.

### P1-02c — 2026-10-15 (done, added at the user's request)
Did: made the automated checks able to use the database, and covered the meeting
endpoints. Each test runs inside a transaction that is rolled back, so a commit made
by the code under test only releases a savepoint and no row reaches the table. The API
session dependency is overridden to use that transaction.
Files: backend/tests/conftest.py, backend/tests/test_meetings_api.py
Verified: 7 tests pass — health, create returns the stored meeting with id, status and
timestamps, read returns it, an unknown id answers not found, and three rejection
cases (empty title, no languages, unknown language). The meetings table holds no rows
after the run. To prove the checks are real, one expectation was deliberately broken:
that test failed while the others passed, then it was restored and everything passed
again. ruff clean.
Notes: the tests need backend/.env because the application loads settings at import.
They use the development database but never keep anything in it.

### P1-02a — 2026-10-15 (done)
Did: added the meeting API. Posting a meeting stores it and returns it; reading by id
returns the stored record or "not found". The app also now accepts browser requests
from the frontend address, without which the form in the next step would be blocked
by the browser itself.
Files: backend/app/schemas/meeting.py, backend/app/api/meetings.py,
backend/app/main.py, backend/app/core/settings.py
Verified against the running server: create answered 201 with the stored meeting,
including a generated id, status "created" and both timestamps; reading that id
answered 200 with the same content; an unknown id answered 404; the cross-origin
header named the frontend address. The row was confirmed in the database and then
deleted. ruff clean, pytest 1 passed. Every check was repeated after switching the
dependency style, so the committed code is the code that passed.
Notes: P1-02 was split because the storage path and the screen are two concerns.
Language codes are checked as en or zh. Adding a language later is a code change only,
no migration, because the column stores text.
Known gap: no automated test covers these endpoints yet; they were verified by hand.
A database-backed test fixture is worth adding before the API grows further.
The health test now needs backend/.env, because the application loads settings at
startup.

### P1-01b — 2026-10-15 (done)
Did: defined five tables and generated the migration that creates them.
  meetings: title, date and time, language list, client/company, project,
    participants, agenda, location, meeting type, in-person flag, status, timestamps.
  recordings: storage key, content type, size, duration, upload time, and an expiry
    that stays null until the retention value is settled.
  transcripts: language, text, optional segments, provider, creation time.
  moms: one per meeting per audience, with a status.
  mom_versions: number, JSON content, ai_generated flag, approval fields, timestamps.
Files: backend/app/db/models.py, backend/alembic/env.py,
backend/alembic/versions/4a3a767eaba2_initial_schema.py
Verified: autogenerate detected every table; upgrade created them with the expected
columns and types; downgrade to base dropped them and upgrade restored them, re-run
after the lint fixes so the tested file is the committed file. A mapping smoke test
inserted a meeting, a MOM and a version, read back the generated id, the defaults and
the relationship, then deleted the meeting and confirmed the tables were empty.
ruff clean, pytest 1 passed.
Notes: no owner column. The account link arrives with P1-14 and there is no
production data, so the ordering costs nothing.
Status, audience and language values are stored as text driven by Python StrEnum
instead of PostgreSQL enums, so adding a case later is an ordinary migration.

### P1-01a — 2026-10-15 (done)
Did: connected the database layer. Added SQLAlchemy, Alembic, psycopg and
pydantic-settings; wrote app/core/settings.py, app/db/base.py, app/db/session.py;
rewrote alembic/env.py so the connection comes from settings; removed the dummy URL
from alembic.ini so no credential sits in a tracked file.
Files: backend/pyproject.toml, backend/app/core/settings.py, backend/app/db/base.py,
backend/app/db/session.py, backend/alembic.ini, backend/alembic/env.py,
backend/.env.example, .gitignore
Verified: created an empty baseline migration and ran it against a real PostgreSQL 17
instance. alembic_version holds f2c2e6573d4a, `alembic current` reports head, and a
downgrade to base followed by an upgrade both succeed. ruff clean, pytest 1 passed.
Notes: P1-01 was split because wiring the toolchain and defining five tables are two
concerns.
Sandbox setup, not part of the product: PostgreSQL 17 was installed with apt. Docker
cannot run here — the daemon fails on iptables rules, and image layers cannot be
unmounted. The development DSN lives in backend/.env, now gitignored, with
.env.example documenting the variable.
Known friction: Alembic's generated migrations trip ruff's unused-import rule, so a
fresh migration needs `ruff check --fix` afterwards. Left alone for now.

### P0-06 — 2026-10-15 (done)
Did: filled in the files every Phase 1 step expects to touch, and extended the folder
tree in AGENTS.md to match. New in the tree: app/schemas/, app/prompts/,
app/worker.py, backend/alembic/, frontend/src/pages/, frontend/src/components/.
Files: PLAN.md, AGENTS.md
Verified: a script confirmed that all 41 paths named across Phase 1 sit inside a
folder the tree declares, and that no placeholder path is left. PRD §22.6 was read
first: it says the agent refines the starter steps in a planning step, so this is the
step the PRD expects.
Notes: found one claim in AGENTS.md that the PRD does not support. The conventions
say the interface carries matching English and Mandarin strings, but the PRD requires
bilingual meetings and MOMs, not a bilingual interface. Recorded as an open question
against P1-02 rather than settled silently.

### P0-05 — 2026-10-15 (done)
Did: scaffolded the frontend with create-vite (react-ts) and replaced the delivered
demo with a minimal page. Phase 0 is complete.
Files: frontend/ (17 files)
Verified: every "done when" command was run. `npm install` added 160 packages with 0
vulnerabilities. `npm run build` exited 0 and wrote dist/. `npm run lint` exited 0
with no findings. `npm run dev` answered HTTP 200 with the new title, and served
src/App.tsx transformed, carrying the new page text.
Notes: create-vite v8 now defaults to Oxlint; I passed --eslint to keep the stack
AGENTS.md records. Worth revisiting if the faster linter is ever wanted.
Removed as part of "a minimal page": the demo App.css, src/assets/ (hero.png,
react.svg, vite.svg), public/icons.svg, and the scaffold README.md.
AGENTS.md now marks the frontend `npm run test` line as not wired, because this
step's scope was install, dev, build, and lint only.
Sandbox quirk: the Vite dev server binds localhost over IPv6, so a check against
127.0.0.1 fails unless it is started with `--host 127.0.0.1`.
Scaffolding quirk: `npm create vite@latest` now stops to ask which linter to use, so
the non-interactive form needs `--no-interactive --eslint --no-immediate`.

### P0-04 — 2026-10-15 (done)
Did: split the old P0-04 in PLAN.md into P0-04 (backend) and P0-05 (frontend), then
built the backend skeleton.
Files: backend/pyproject.toml, backend/app/__init__.py, backend/app/main.py,
backend/tests/test_health.py, .gitignore
Verified: every "done when" command was run, not assumed. `uv sync` resolved the
environment. `uv run pytest` passed 1 test. `uv run ruff check .` reported "All checks
passed". `uv run uvicorn` started, answered GET /health with 200 and
{"status":"ok"}, and was then stopped cleanly.
Notes: a root .gitignore was added beyond the file list in PLAN.md, so .venv and
later node_modules stay out of the repository. Four files rather than the usual 1-3,
but a single concern. uv.lock is committed, because an application should pin its
versions.
One harmless warning: starlette 1.8.0 reports that its TestClient prefers `httpx2`
over `httpx`. No action taken; revisit if it becomes a failure.

### P0-03 — 2026-10-15 (done)
Did: the user chose option B. AGENTS.md now carries the stack, folder structure,
commands, and conventions. Also fixed the stale "fixed by P0-03" path placeholders in
PLAN.md and gave P0-04 concrete files to create.
Files: AGENTS.md, PLAN.md
Verified: checked the toolchain on this machine before writing any command, instead
of assuming: Python 3.13.15, uv 0.12.15, Node 24.21.0, npm 11.19.1, git 2.47.3, and
libpango plus libcairo present for WeasyPrint. The commands themselves are exercised
in P0-04, which is that step's job.
Notes: uv over plain venv and pip, because it is already installed at /usr/bin/uv and
gives a lockfile. Python 3.13 to match this machine.
Options considered and rejected: A. TypeScript end to end — the bilingual DOCX and
PDF export, which is a whole Phase 1 step, would land on the weakest part of the Node
document tooling (headless Chromium, or the low-level pdfkit). C. Python only, server
rendered — the live transcript and translation UI in Phase 2 and 3 needs a real
frontend.

### P0-02 — 2026-10-15 (done)
Did: recorded the cloud decision state in AGENTS.md. The user chose a placeholder,
so what is recorded is "TBD", when the choice is due, and the criteria for making
it.
Files: AGENTS.md
Verified: the "done when" is that the decision is written in AGENTS.md and that the
user approved it. The decision recorded is the one the user gave ("placeholder
dulu"), so the step is ticked in PLAN.md. The wording itself is new and unreviewed;
reopen the step if it reads wrong.
Notes: the real choice moves to a deferred, unapproved step in the Parking lot.
Nothing is blocked by it until P1-04.

### Interface language ruling — 2026-10-15 (user approved the recommendation)
The interface ships in English only. Screen text lives in one string file under
frontend/src/i18n/, so adding Mandarin later means translating that file instead of
rewriting screens. This settles the convention written at P0-03, which assumed an
EN+ZH interface without support in the PRD. The PRD requires bilingual meetings and
MOMs, not a bilingual interface. The question recorded against P1-02 is closed.

### Retention ruling — 2026-10-15 (user answered "mode dengan akun")
Account mode only. Guest mode is dropped from the first release, so every meeting
belongs to an authenticated account and its data is kept.

Deliberate deviation from the PRD, not an oversight:
- PRD §11.1 lists Guest mode and Authenticated mode. Guest mode is dropped.
- PRD §18.5 requires guest data to follow a temporary retention policy. That item
  is dropped from the Phase 1 acceptance run.

Carried into PLAN.md:
- P1-14 becomes "Basic access control (account mode only)"; the guest-deletion half
  is gone.
- P1-15 acceptance run skips the guest-data item of §18.5.
- The lifetime of stored account data is still an open value, due before P1-04.

### Decisions — 2026-10-15 (user answers to PRD §19)
Answered by the user in session. Recorded here and in docs/PLAN_NON_TECHNICAL.md.
Two scope lines were folded into AGENTS.md; the rest stay here until the stack
step.

1. Cloud provider, region, managed AI services: placeholder for now. The real
   choice is deferred; see the Parking lot. It becomes blocking before P1-04
   (secure storage) and P1-05 (speech-to-text).
2. Live Transcription and Live Translation: not in the first release. They ship in
   Phase 2 and Phase 3, matching PRD §13.
3. Retention: the user answered "meeting data is always stored". This conflicts
   with PRD §11.1 and §18.5, which require guest meeting data to be temporary and
   deleted under a defined period, and it removes the deletion half of step P1-14.
   Recorded as an open item, not as a settled rule. Superseded by the retention
   ruling entry above.
4. Raw audio: retained by default after MOM generation; users may delete their own
   recordings. Accepted, together with the privacy obligation that retention
   brings (PRD §11.2).
5. Export layout: section-by-section, not paired columns. Matches the preferred
   layout in PRD §8.4.
6. Pilot thresholds: numeric accuracy and latency targets deferred to Phase 2.
   Phase 1 is verified functionally instead — the feature exists and works.
7. Per-market recording notice and consent: dropped. Only the per-market legal
   analysis is dropped. The in-product recording indicator and the AI-processing
   notice stay in scope, because PRD §11.2 and §18.5 require them.

Project-local items:
- The PRD stays at the repo root. No move to docs/.
- Commit and push policy: closed. Following the PRD §22.11 default of committing
  after each verified step. Pushing to origin still happens only on an explicit
  instruction.
- Version 2.0 inside the document vs v2.1 in the filename: a typo. The filename is
  authoritative. Do not raise this again.

### P0-01 — 2026-10-15 (done)
Did: created AGENTS.md, PLAN.md, PROGRESS.md as skeletons. PLAN.md carries the
starter steps P0-01 to P0-04 and P1-01 to P1-15, each with a PRD reference and a
"done when" check. No application code written, no dependencies installed.
Files: AGENTS.md, PLAN.md, PROGRESS.md
Verified: the "done when" is user review of the three files. Review passed on
2026-10-15 when the user answered "continue", so P0-01 is ticked in PLAN.md. The
reviewed version includes the decision records, the retention ruling, and the
re-scoped P0-02.
Notes: `PRD_AI_MEETING_AGENT_v2.1_FINAL.docx` sits at the repo root, which the user
confirmed is where it stays. Nothing committed or pushed yet.
Also created at the user's request, outside P0-01 and not part of the P0-01
deliverable: `docs/PLAN_NON_TECHNICAL.md`, a plain-language companion to PLAN.md.
It is not a step in PLAN.md. Still to decide whether it stays a reference document
or becomes a step of its own.

## Parking lot
- Pending step: the S3 storage driver, blocked on AWS credentials for the chosen
  Singapore region. Until then audio is written under the local `.storage/` directory,
  which is gitignored.
- Pending step: the Transcribe speech driver, blocked on the same credentials. Until
  then the worker runs a local Whisper model.
- Pending step: the meeting screen does not upload its recording yet, so the worker
  only sees audio posted through the API.
- Deferred from P1-03: the audio-quality indicator in PRD §7.2. It needs a real
  microphone to verify properly, and the rest of the step is complete.
- Deferred from P1-03: a router, once the number of screens makes a state switch
  awkward. Two screens do not justify the dependency yet.
