# Progress

## Current state
Phase: P1. Last done: P1-16 (external-content audit before approval)
Next: P1-17 (check the three language versions agree)
Blockers: none
Open: P1-15, the Phase 1 acceptance run, failed on five items on 2026-10-20 and is
tracked as P1-17 to P1-20 (P1-16 closed). See docs/ACCEPTANCE_PHASE1.md.
Open decisions: the production LLM is a target, not a fact. Until 2026-10-20 the
extractor runs through the Messages-compatible gateway present in this environment,
which ignores the model name and serves deepseek-flash. Azure OpenAI replaces it before
release, and the user asked to be reminded at that switch. Recording input is settled
2026-10-20: stay on local Whisper for now; a managed API is one class and one line
behind the seam when credentials exist. MOM languages are settled 2026-10-20: English,
Mandarin and Indonesian, all three by default, the reviewer chooses at review, a removed
language is hidden rather than deleted, and the MOM is authored once in the meeting's
language with the other two translated from it. The source language is the one the
transcript detected.
Platform is settled: Azure, on infrastructure the user rents in Indonesia
(`indonesiacentral`). This replaces the AWS plan, and no AWS code exists. Retention is
settled: 90 days from upload, and account mode only. Region layout is settled 2026-10-20
as option A: app, database and recordings in Indonesia Central, Azure Speech and Azure
OpenAI in Singapore. Re-confirm that layout with the user before writing either cloud
driver; they asked to be reminded. Every other PRD §19 item
is answered — see the log. A Huawei SIS driver now exists as an alternative, but it has
never run against the live service, so the provider is not settled by evidence yet.

## Data residency — what is known (2026-10-20)

One place to check before anyone writes a client promise about where meeting data goes.
It exists because three things go wrong without it: a promise gets written from memory, an
assumption hardens into a fact, and the detail is lost when the session ends.

| Data or step | Where | Status |
| --- | --- | --- |
| App server, PostgreSQL | Azure, Indonesia Central | settled |
| Recordings (Blob Storage) | Azure, Indonesia Central | assumed, not confirmed with Microsoft |
| Batch transcription (Azure Speech) | Azure, Singapore | no Indonesian region offered |
| Extraction, MOM, translation (Azure OpenAI) | Azure, Singapore | no Indonesian model table |

Today, before any Azure AI credential exists, only the first row runs as described.
Transcription is local Whisper on the Indonesian VM, so it stays in the country. MOM
generation goes to the temporary gateway at ecoapi.ai, whose processing location is
unknown; its website names Singapore and Indonesia, but that is marketing text, not a
processing commitment.

So "recordings are stored in Indonesia" is true. "Nothing leaves Indonesia" is not, and
must not be said until that gateway is replaced and Speech and OpenAI are live. Full
in-country processing would need self-hosted models, which breaks the managed-services
rule, or an Indonesian provider, which nobody has researched.

Live transcription and live translation change none of this. They decide whether
processing happens during the meeting or after it, not where it happens.

## Log (newest first)

### P1-16 — 2026-10-20 (done)

Wired the external-content audit into approval. Before this, `sensitive.py` was a
tested service with no caller, so an external MOM could reach a client unread.

The design choices worth knowing:

- The secrets it checks against are the **internal MOM's `internal_notes`** for the same
  meeting, deduplicated across languages. That is the product's own record of what
  stayed in the room, so no new place to declare secrets was needed. If no internal MOM
  exists yet, the audit runs with an empty list and only catches what reads as internal.
- A finding answers **409** with a plain-text list of excerpt and reason, and the MOM
  stays a draft. The text shape is deliberate: the review screen already prints a string
  `detail`, so the reviewer sees which sentence is the problem without a UI change.
- Re-posting with `{"acknowledge_findings": true}` approves anyway. The acknowledgement
  is not stored: there is no column for it, and the PRD asks only that the user
  acknowledge. Recording who overrode what is in the parking lot.
- A check that cannot run answers **503** and approves nothing. Failing closed is the
  point: an audit that silently degrades to "no findings" would be worse than none.
- Internal MOMs never call the checker. The route only audits `external`.

Verified twice. The unit tests use a fake checker (seven new tests: blocked, acknowledged,
clean, notes passed through, document passed through, internal untouched, failure
blocks). Then a live run against the real model with a deliberately leaked sentence in
all three languages: approval answered 409 quoting *"Our margin on this account is 8
percent and we expect to drop them in Q1"* with the reason, the MOM stayed a draft, and
the acknowledged retry approved.

One consequence to be honest about: the review screen can now be refused with no button
to acknowledge, because that control does not exist yet. The safe way out works today —
edit the sentence away and approve — and the button is written into P1-18, which already
touches that screen.

Run into while testing: the API process needs `ANTHROPIC_BASE_URL` and
`ANTHROPIC_API_KEY` in its own environment. Started without them, every approval got a
503 with "must be set" — which is the fail-closed path doing its job, and worth knowing
before mistaking it for a code bug.

### P1-15 — 2026-10-20 (first run, open)

Ran the Phase 1 acceptance list against §18.1, §18.4 and §18.5. Full table with
evidence in `docs/ACCEPTANCE_PHASE1.md`. Result: 7 pass, 5 fail, 2 blocked, 2 not
applicable. The step stays open; the five failures became P1-16 to P1-20.

What passed, tested through the UI and the API as a user would: creating a meeting
with full metadata, three languages in one MOM document, separate internal and
external MOMs, editing and approving with a version history, exported Word and PDF,
one account unable to read another's meeting (404) or an anonymous caller (401), and
recording status visible with a clear message when no microphone exists.

What failed, and it is worth being blunt about two of them. The external-content
audit and the bilingual consistency check both exist as tested services and **nothing
calls them**. An external MOM can be approved today without either check ever
running. Export also ignores approval, so a draft leaves the app as a finished file,
and the review screen has no export control at all. There is no microphone selector,
though §18.1 asks for one, and no AI processing notice, which §11.2 and §18.5 ask for.

Two items cannot be judged here: secure transmission and storage, and running on
managed hosting. Nothing is deployed, so both wait on the Azure work.

Blocked by the environment, not by the code: this container has no microphone, so
start, pause, resume and stop were never observed working end to end. The code has
them, and the failure path (no device) is handled well, but a second run on a machine
with a microphone is needed before those controls can be called verified.

Also found while running: PostgreSQL had stopped, and background servers started
without `setsid` were reaped between commands. Both are sandbox habits, now in
AGENTS.md.

### P1-14 — 2026-10-20 (done)
Did: accounts and sessions. `app/core/security.py` hashes passwords with PBKDF2 and
session tokens with SHA-256. `app/api/auth.py` serves register, login, logout and
`/auth/me`; the HTTP-only `mom_session` cookie is the only credential and the digest,
never the token, is stored. Every meeting and MOM route now needs a signed-in account
and answers 404 for another account's meeting, so the existence of a meeting does not
leak.

Frontend: `api.ts` wraps `fetch` with `credentials: "include"`, `Login.tsx` is the
sign-in and create-account screen, and `App.tsx` gates the three existing screens
behind a session check on mount. `vite.config.ts` proxies `/api` to the backend, which
keeps the cookie first-party in development.

Found: port 8000 in this sandbox belongs to the Agent Canvas platform, so uvicorn
never bound and the browser talked to the wrong server. The API now runs on 8010 and
the proxy target follows `API_PROXY_TARGET`.

Found while verifying: the platform's own service worker on `localhost:5173` answers
`/api/auth/me`, so the app's session check never reached our backend there and the
login form reappeared on reload. That is a collision in this sandbox only. Checked on
`localhost:5174`, where the session restores from the cookie with no login form, and
the sign-out and sign-in flow both work.

Fixed while verifying: `tests/test_auth.py` used a fixed address and assumed empty
tables, so the account left behind by the browser run made nine tests fail. Addresses
are now unique per run and the session queries filter on the account under test.

Verified: 118 tests pass, ruff clean, `npm run build` and `npm run lint` clean. Browser
run: register, create a meeting, reload (still signed in), sign out, sign in.

Notes: the test suite runs against the development database. Writes are rolled back,
but rows from a dev run or a browser session stay visible, so a test must never assume
an empty table.

### P1-13 — 2026-10-20 (done)
Did: `app/services/documents.py` turns a MOM into Word or PDF, using only the languages
the reviewer kept. `app/api/export.py` serves them as
`/meetings/{id}/moms/{audience}/export.docx` and `.../export.pdf`.

Chosen: python-docx and reportlab, both pure Python. reportlab carries the STSong-Light
Chinese font, so no font file is downloaded or committed, and the deployment image grows
by two libraries instead of a 15 MB font.

Found by rendering the pages to images: putting Latin text in the Chinese font makes
reportlab measure the line with the wrong widths. Words overlapped ("thebudget") and the
"·" separator vanished. Latin now uses Helvetica and only Chinese runs switch font.

Found by reading the extracted text: the bullet came out as a control character, so the
bullet is set in the Latin font.

Verified: 13 new tests, 98 in total. Both formats are generated and read back, visible
languages appear, a hidden one does not, and an external MOM carries no internal notes.
The API returns the right type and filename, and an unknown meeting gives 404.

Limit: the Word file was read back with python-docx, not opened in Word, so how it looks
in a real word processor is unconfirmed. The PDF was rendered and inspected.

### P1-12 — 2026-10-20 (done)
Did: `app/api/mom.py`, the review API. Store the first draft, read it, edit it, approve
it, and reopen it as a new version. `frontend/src/pages/Review.tsx` and
`components/MomEditor.tsx` are the screen that drives those calls.

Approval locks a version: an edit to an approved MOM returns 409 rather than silently
changing history. Editing after approval goes through reopen, which writes version N+1
as a draft and leaves the approved version untouched.

Chosen: the visible-language set lives in the MOM document as `visible_languages`, not
in a new table column. The existing Mom and MomVersion tables already hold versions and
approval, so nothing needed migrating, and P1-13 reads the same field for export.

Simplified: lists are edited as text, one entry per line, with "|" between fields (for
example `Send the plan | Ana | 15 November 2026`). A row editor would be friendlier, but
this keeps the first screen small and round-trips without loss.

Verified: 85 tests pass, 11 of them new, ruff and eslint clean, frontend builds. Then
against a running server and database: store 201, approve 200, edit after approve 409,
reopen produces version 2 with version 1 still approved, and hiding Mandarin leaves all
three versions stored. The screen itself was driven in a browser through load, edit, save
and approve; the approved state greyed out Save and Approve and enabled Reopen.

Limit: the screen takes a meeting reference typed by hand, because there is no list of
meetings yet. Access control arrives in P1-14, and `approved_by` is still an optional
string with nothing checking it.

### P1-11 — 2026-10-20 (done)
Did: `app/services/consistency.py`, a semantic comparison of the three versions. The
generator already refuses a translation whose entry counts differ, which catches a dropped
decision. It cannot catch a decision whose date changed, so this reads for meaning.

Each mismatch names the field, describes both values, and lists the versions that disagree.
A single language is rejected as a mismatch, because one version cannot disagree with
itself.

Verified: 74 tests pass, 7 of them new and offline, ruff clean. Two live cases. A
consistent document produced nothing. Changing the Indonesian deadline to 15 September was
flagged at action_items[0].deadline, naming both dates. The Chinese 2026年11月15日 was read
as equal to 15 November 2026, so the date-format difference did not become a false finding.

Limits: this compares what the versions say, not what the meeting actually contained. Three
versions that are wrong in the same way pass, and the transcript is the only defence there.

### Live features default off — 2026-10-20 (user decision, nothing built yet)
A requirement, not work done. Live transcription (Phase 2) and live translation (Phase 3)
do not exist yet, so there is no switch whose default could be changed. The behaviour is
recorded in PLAN.md for the phase that builds them:

- Both default to OFF at the start of every meeting.
- Turning either one on first shows a consent dialog naming the cost and performance
  effect. The switch only moves after the user agrees; cancelling leaves it off.
- The two controls stay separate buttons. Live translation depends on live transcription,
  but transcription must be usable on its own.

Answered 2026-10-20: the consent is shown every time, with no "do not ask again" option.
When live translation is turned on while live transcription is off, the offer turns both
on together, explained in one dialog because it is one action.

Wording deliberately left open 2026-10-20: the user chose to settle it when Phase 2 is
built, not now. Do not block anything on it, and do not reuse a draft as if it were
agreed. One correction is already known: "may increase cost or lower latency" reads
inverted, because the cost rises and latency usually gets worse rather than better.

### P1-10 — 2026-10-20 (done)
Did: `app/services/sensitive.py`, an audit of the finished external minutes against the
internal facts. It runs after the external MOM is written, deliberately: the writer's
prompt is a request, and this is a second reader that can disagree with it. Each finding
carries the language, the exact excerpt, a reason and a severity, so the reviewer sees
where the problem is instead of a bare refusal.

The check only accepts an external document; auditing an internal one would report a
clean result while the file is full of notes, so that raises.

Verified: 67 tests pass, 9 of them new and offline, ruff clean. Two live cases against the
real model. The leaky document produced two findings, the English sentence and its
Indonesian paraphrase ("marjin kami ... lebih tipis"), and did not flag the clean Chinese
version. The clean document produced no findings.

Limits worth knowing: this reader is another model, so it can be fooled, and two cases are
not a benchmark. It catches disclosure, not the absence of judgement about what belongs in
client minutes.

### P1-09 — 2026-10-20 (done)
Did: the external MOM, reusing the writer-then-translate machinery. `Audience` picks the
prompt, the document records it, and an external document is rejected if the model puts
anything in `internal_notes`, including when only a translation does.

A gap this work exposed, and closed: extraction had no field for internal concerns, so the
writer never saw them. "Off the record, our margin is thinner" reached neither MOM, and the
first leak test therefore passed for the wrong reason. `Insights` gained `risks`; the
extraction prompt fills it, the internal prompt carries it into `internal_notes`, and the
external prompt forbids it.

Verified: 58 tests pass, 7 of them new here, ruff clean. Live run on a transcript with a
seeded off-the-record margin remark: the remark appeared in `insights.risks` and in the
internal notes, and the strings margin, marjin, 利润 and 毛利 appeared nowhere in the
external document in EN, ZH or ID. The external document carried all three languages with
empty notes, and dates read natively (11月15日, 15 November, 星期五, Jumat).

Still P1-10's job: this proves the prompt and the structure, not that no sensitive content
can slip through in other words. The word-list scan above is a spot check, not a check.

### P1-08 — 2026-10-20 (done)
Did: the internal MOM, authored once in the meeting's language and translated into the
other two. `app/schemas/mom.py` holds one document with exactly one version per language,
so hiding a language at review stays a view of the document rather than a deletion.
`app/services/mom.py` writes the source version from the extracted facts, then translates
it, and refuses a translation whose entry counts differ from the source.

Also extracted `app/services/llm.py`, the Messages client both generators share, so the
transport and the JSON handling are written once instead of twice.

Verified: 51 tests pass, 9 of them new and offline, and ruff is clean. A live run on an
English transcript produced three versions with identical counts: 2 topics, 2 decisions,
2 action items, 1 open question, 2 internal notes. Names were preserved and the
unassigned action stayed null in all three languages.

Defect the live run found and the fix: the first translation prompt said to keep dates
"exactly as written", and the Chinese version came back with "October 15" and "Friday" in
English inside otherwise Chinese sentences. The rule now requires dates and weekdays to
read naturally in the target language. The re-run produced 10月15日 and 星期五, and
15 Oktober and Jumat.

### P1-07 — 2026-10-20 (done)
Did: extraction of topics, decisions, action items, owners, deadlines and open questions
from a transcript, in `app/services/intelligence.py`, with the prompt in
`app/prompts/extraction.md` and the shape in `app/schemas/insights.py`. The LLM sits
behind `InsightExtractor`, one method, so changing provider is a one-class change.

Temporary provider, and what it actually is: the user authorised the Messages-compatible
endpoint already present in this environment. Probing it showed that it ignores the
requested model name and answers as `deepseek-flash` for every name tried, including
nonsense ones. So the model under test is DeepSeek Flash, not Claude, and not what
production will use. Recorded because the user believed the key was an Anthropic one.
Azure OpenAI remains the target and replaces it before release; the user asked to be
reminded at that point.

Verified: 42 tests pass, 11 of them new and offline by injecting the sender, and ruff is
clean. A live call on an English transcript returned two topics, two decisions, two action
items and one open question, leaving the unassigned contract review as owner null instead
of inventing one. A live call on an Indonesian transcript answered in Indonesian, kept
"hari Jumat" as spoken, and attributed the action to Budi.

Not covered: a mixed English-Mandarin transcript, and any comparison against Azure
OpenAI. Both wait for the production model.

### Region layout ruling — 2026-10-20 (user decided)
Option A, hybrid. The app, the PostgreSQL database and the recordings live in Indonesia
Central. Azure Speech and Azure OpenAI, which Microsoft does not offer in Indonesia, run
in Singapore (Southeast Asia). Audio and transcripts leave the country only for the
processing call; stored data stays in Indonesia.

The user asked to be reminded at build time: before writing either cloud driver, confirm
the layout again. Recorded here so a later session does not build it on autopilot.

Not chosen: all-Singapore (B), simpler but moves stored data abroad; self-hosted AI on
the VM (C), which breaks the managed-services rule; an in-country AI provider (D),
which has not been researched.

### Azure region check — 2026-10-20 (research, not a decision)
The user rents Azure infrastructure in Indonesia, so the platform moves from AWS to
Azure. Before choosing a layout I checked Microsoft's own documentation.

Verified:
- `indonesiacentral` is a real region: Indonesia Central, Jakarta, three availability
  zones (`learn.microsoft.com/azure/reliability/regions-list`).
- PostgreSQL Flexible Server runs there, engines v3/v4/v5
  (`learn.microsoft.com/azure/postgresql/flexible-server/overview`).
- Azure Speech supports `id-ID` for speech to text
  (`learn.microsoft.com/azure/ai-services/speech-service/language-support`).
- Azure Speech's supported-region page lists `southeastasia` and 18 other region ids,
  and does not contain "indonesiacentral" anywhere
  (`learn.microsoft.com/azure/ai-services/speech-service/regions`).
- No Azure OpenAI / Foundry model page mentioned Indonesia at all; for this part of the
  world the model region tables stop at Southeast Asia
  (`learn.microsoft.com/azure/ai-foundry/openai/concepts/models`).

Not verified:
- Blob Storage in Indonesia Central. Storage exists in every generally available
  region, but no documentation page enumerated it for this one.
- Whether the user's subscription has Indonesia Central enabled, and whether Azure
  OpenAI can be deployed in Indonesia despite the documentation.

Consequence: "everything in Indonesia" is not possible with Azure's managed AI. The
layout is a choice between hybrid (app, database and recordings in Indonesia, Speech and
OpenAI in Singapore) and all-Singapore. The hybrid keeps stored data in the country and
sends only a copy abroad for processing.

Deferred on purpose: the layout does not block P1-07, which needs only an LLM endpoint.
Nothing is hard to change yet, because no cloud driver is written and no data is stored.
Two deadlines do apply. Settle the storage region before the cloud storage driver is
written (still pending from P1-04). Settle the residency commitment before any client is
told where their meetings are kept, because that is a promise, not a setting.

### MOM language ruling, follow-up — 2026-10-20 (user decided)
Two questions left open by the previous ruling are answered.

1. A language the reviewer removes is hidden, not deleted. It stays in the version and
   can be brought back; the approved document and the export leave it out. The choice
   protects against a mistaken removal, which matters because MOMs get revised.
2. The MOM is authored once, in the meeting's language. The other two languages are
   translations of that one text, not three independent drafts. The three sections
   therefore cannot disagree about a decision, a date or an owner: they are one text
   and two translations of it.

Consequence: the reviewer's language choice is a view of a version, not an edit to it.
All three languages stay in storage, so the choice needs no history of its own.

Source language, settled in the same session: the language the transcript detected.
A meeting that declared en+zh but was mostly spoken in Mandarin is therefore authored
in Mandarin, then translated. No new field is needed, because the transcript already
stores the detected language.

### MOM language ruling — 2026-10-20 (user decided)
Each MOM carries three languages in one document: English, Mandarin and Indonesian.
All three are produced by default. At review, the user chooses which languages to keep.
This replaces the PRD rule of English plus Mandarin only (PRD §8.1, §8.4). Recorded as
a deliberate deviation, the same way guest mode and the retention rule were.

Carried into PLAN.md:
- P1-08 and P1-09 produce three languages, not two.
- P1-11 compares three texts instead of one pair.
- P1-12 gains the language choice; P1-13 exports only the chosen languages.

Consequence worth naming: translation becomes part of MOM generation. A meeting that
never spoke Mandarin still needs a Mandarin version, so the quality of that section
rests on the translation step rather than on the transcript. That cost grows with the
number of languages and will need a model good at translation, not only at writing.

Still open, due before P1-12: whether a language removed at review is deleted or only
hidden from the approved document and the export, and whether the choice is per
version or per MOM.

### P1-06c — 2026-10-20 (done)
Did: Indonesian is now a meeting language. The API accepts "id", the new-meeting form
offers it, and the worker passes "id" as the transcription hint when a meeting declares
only Indonesian. A meeting that declares Indonesian together with another language gets
no hint, so the audio decides.
Files: backend/app/schemas/meeting.py, backend/tests/test_meetings_api.py,
backend/tests/test_speech.py, frontend/src/pages/NewMeeting.tsx,
frontend/src/i18n/messages.ts, PLAN.md, PROGRESS.md, docs/PLAN_NON_TECHNICAL.md
Verified: 31 tests pass (3 new) and ruff is clean. eslint and the vite build both pass.
The API test creates a real meeting with languages ["id"] against the development
database, and the two hint tests call the worker's own helper, so neither uses a stub.
Missing: there is no Indonesian audio fixture, because no text-to-speech tool exists in
this environment. Whisper accepts the "id" code, but its Indonesian output is unproven
end to end. Only a real recording can judge accuracy, exactly as with the earlier
fixtures.
Notes: no database change. The languages column stores text, so a new code needs no
migration. Scope is the spoken language and its transcript only; whether the MOM gains
Indonesian is still open.
Known gap, older than this step: SPEECH_PROVIDER=huawei always sends the single
configured model property (default chinese_16k_conversation), whatever the meeting
declares. An English meeting on Huawei is therefore already transcribed with a Chinese
model, and Indonesian inherits that. Worth fixing before Huawei is used for real.
Decision in the same session: the user chose to stay on local Whisper for now, with a
provider swap later. That swap touches speech.py plus one settings block.

### P1-06b — 2026-10-19 (scaffold, never run against the live service)
Did: added a Huawei Cloud speech driver behind the same seam. `SPEECH_PROVIDER=huawei`
selects SIS batch recognition; the default stays `whisper`, so behavior is unchanged
until the variable is set. The driver uploads the audio to OBS, submits a transcriber
job, polls it, maps segments, and deletes the temporary object. SIS accepts files up to
5 hours and 300 MB and keeps results for 72 hours, which covers the 75-minute recording.
Files: backend/app/services/speech.py, backend/app/core/settings.py,
backend/tests/test_huawei.py, backend/.env.example, backend/pyproject.toml
Verified: 28 tests pass (6 new) and ruff is clean. The new tests build a real SIS job
body and parse a real response model, so the request and response mapping is covered.
Missing credentials fail before anything is uploaded.
Notes: no Huawei credentials exist here, so the driver has never called the live API.
`auto_language_detect` exists in the job body, but whether SIS switches language inside
a single file is unproven; it may only choose one language per job. The Jakarta region
could not be confirmed from public pages; only Singapore appeared. The model default is
`chinese_16k_conversation`; `english_16k_common` is the English alternative.

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
- From P1-16: the acknowledgement of a sensitive-content finding is not stored. Add a
  column and show in the version history that this version was approved over a finding,
  by whom and when.
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
