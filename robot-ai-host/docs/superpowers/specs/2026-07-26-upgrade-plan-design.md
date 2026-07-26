# Upgrade Plan Design — robot-ai-host → Intelligent Expressive Vietnamese Agent

Date: 2026-07-26
Status: Approved (user, session 2026-07-26)

## Source of truth

- `../ROBOT_AI_AGENT_MASTER_SPECIFICATION_v1_1.md` (spec — business content wins on conflict)
- `../PROMPT_IMPLEMENT_ROBOT_AI_AGENT_UPGRADE_v1_1.md` (execution prompt)
- v1.0 documents are superseded by v1.1 (v1.1 changelog fixes latency contradictions, adds streaming STT, two-tier TTS, router constraints, reduced action-tool MVP scope). v1.0 is historical reference only.

## Execution mode

- One session = one complete phase, in order Phase 0 → 6. A complete phase beats three partial ones.
- Each phase ends with: gate check + `reports/upgrade/0N_*.md` + snapshot backup.
- Expected honest outcome of any agent session: `PARTIAL` + complete `HUMAN_TASK_CHECKLIST.md`.

## Decisions (deviations from prompt, user-approved)

1. **No git.** User declined git init. Backup strategy instead: full snapshot at
   `../artifacts/pre-upgrade-snapshot/` before changes; per-phase snapshots
   `../artifacts/phase-N-snapshot/` after each phase gate. Deviation from prompt §3 backup
   and constraint 23 (branch/commit per phase).
2. **Runner: `uv`.** `uv.lock` exists → `uv run pytest -q` is the canonical test command
   (prompt §4.7 allows this when uv.lock present). `.venv-hybrid` remains for hybrid profile runtime.
3. **Config source of truth: `config/`.** `configs/profiles.yaml` moves to `config/profiles.yaml`;
   `configs/` removed; `PROFILES_PATH` updated; test proves active source; no silent fallback.
4. **Persona name from env** (`PERSONA_NAME`, default until school confirms branding — spec 9.4 warning).

## Phase roadmap (summary — spec is the authority for detail)

| Phase | Content | Gate | Human dependency |
|---|---|---|---|
| 0 | Config single-source, dep pin reports, persona per spec 9.4–9.5, context cap/summarize/reset, 16-event metrics timeline, browser AEC flags, license inventory | tests pass, metrics timeline complete | 30-min soak |
| 1 | 5 STT profiles incl. `stt_streaming_vi`, round-1 benchmark on public corpora (VIVOS/CV-vi/VLSP), glossary, VAD tune | spec 8.6; round-2 BLOCKED until recorded corpus | 6-speaker corpus |
| 2 | Two-tier TTS (Piper opener + VieNeu expressive, spec 16.2a), Expression Composer, prosody chunking | TTFA P50 ≤500ms; subjective gates BLOCKED until panel | ≥8-listener panel |
| 3 | Router (heuristic bypass ≥60%, LLM router ≤300ms P50, spec 9.8), capability probe, Response Composer | router_latency, router_bypass_rate | — |
| 4 | Orchestrator + Pipecat Flows, typed tools (create_reminder real backend, draft_email; interface-only fakes excluded from acceptance), confirmation, task state | zero false success on real backends only | — |
| 5 | Knowledge schema + retrieval, session memory 6–8 turns, opt-in long-term preference | zero cross-user leakage | — |
| 6 | Robot behavior IDs, style→behavior map, ACK, barge-in behavior cancel | ACK enforced | — |

Cross-cutting: SECURITY_REVIEW.md, five review rounds → CHANGELOG_REVIEW.md, final outputs per prompt §14.

## Fable 5 session strategy

- Reports per phase are the inter-session handoff; next session starts by reading them.
- Anything requiring a human (mic, listening, recording, panel, physical reconnect) goes to
  `HUMAN_TASK_CHECKLIST.md` with steps + pass criteria + blocked gate, never scattered BLOCKED marks.
