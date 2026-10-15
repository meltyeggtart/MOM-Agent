# Progress

## Current state
Phase: P0   Last done: P0-02   Next: P0-03
Blockers: none
Open decisions: cloud provider, region, and managed AI services are TBD by
decision (PRD §19.1), due before P1-04. Retention is settled: account mode only.
Every other PRD §19 item is answered — see the log.

## Log (newest first)

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
- Unapproved step: finalize the cloud provider, region, and managed AI services
  decision that was deferred out of P0-02. Blocking before P1-04 and P1-05.
- Open value: how long stored account meeting data is kept. Due before P1-04.
