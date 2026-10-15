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

## Tech stack (fill after the stack decision step)
Cloud provider, region, managed AI services: TBD — a placeholder was accepted on
2026-10-15 (P0-02). Not decided yet. Settle it before P1-04 (secure storage) and
P1-05 (speech-to-text), weighing speech-service availability and EN/ZH
code-switching quality, latency, regional availability, privacy terms, and cost
(PRD §12, §19.1).

Language, framework, runtime: not decided. P0-03 picks these and fills in Folder
structure and Commands below.

## Folder structure
Not decided. Set by P0-03, created by P0-04.

## Commands (install, run, test, lint, build)
Not decided. Set by P0-03, verified by P0-04.

## Conventions (naming, error handling, logging, i18n EN/ZH)
Not decided. Set by P0-03.

Fixed constraints that do not depend on the stack choice:
- User-facing text is offered in English and Mandarin.
- Each MOM carries English and Mandarin in the same document (PRD §8.1, §8.4).
- Application logs stay free of raw audio, transcript text, credentials, and
  confidential payloads (PRD §11.2).

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
