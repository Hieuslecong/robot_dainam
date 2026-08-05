# 03 — Phase 2: Read-only Agent

Date: 2026-07-26
Status: **PASS (code + tests)** — runtime tool-selection accuracy (≥95% correct tool) needs live LLM eval, recorded below as PENDING EVAL.

## Router (spec 9.8, 10.1–10.4) — [app/core/routing.py](../../app/core/routing.py)

- Heuristic bypass BEFORE any LLM call: greeting/farewell/thanks, stop commands, common small-talk patterns, robot-behavior phrases, ≤2-word utterances. Measured on the representative test set: **≥60% bypass** (`test_bypass_rate_at_least_60_percent`).
- LLM router: injected one-shot call, non-streaming, `max_tokens=60`, temperature 0, `LLM_ROUTER_MODEL` (falls back to `LLM_MODEL`). Hard budget `ROUTER_TIMEOUT_S = 0.3`.
- Timeout / bad JSON / bad enum ⇒ fallback `intent=unclear`, turn never blocked (tested).
- `confirmed_write`/`sensitive`/action intents ⇒ `path=flow` (spec 10.4).
- Metrics: `router_latency` + `router_bypass_rate` recorded per decision (names reserved in Phase 0 metrics module).
- Full intent taxonomy 10.1 and risk taxonomy 10.2 as enums.

## Knowledge (spec 12) — [app/core/knowledge.py](../../app/core/knowledge.py)

- Docs in `knowledge/school/*.yaml`; docs missing required metadata (source_id/title/version/effective_date/issuing_unit) are REJECTED at load.
- Retrieval returns evidence + source title/version/effective date/relevance/timestamp (12.4).
- Expired or undated docs carry a staleness warning (tested).
- No match ⇒ `partial` + empty results — **sources are never invented** (tested).
- Current content is placeholder; real school documents are a human task.

## Read-only tools (spec 11.1) — [app/tools/school_tools.py](../../app/tools/school_tools.py)

All five registered through the Typed Tool Gateway: `search_school_knowledge`,
`get_school_schedule`, `find_school_form`, `get_deadline`, `get_contact_information`.

## Task state (spec 10.5) — [app/core/task_state.py](../../app/core/task_state.py)

Full field set + all 8 statuses + expiry; store is session-scoped (19.2).

## Tests

`test_routing.py` (8), `test_knowledge_tools.py` (7), `test_task_state.py` (5) — in the 171-test suite run.

## Gate (spec §22 Phase 2)

| Item | Status |
|---|---|
| Router with bypass + budget + fallback | PASS (unit-tested) |
| Knowledge retrieval with source/version | PASS |
| Five read-only tools | PASS |
| Task state | PASS |
| "Correct tool ≥95%" on live agent eval | **PENDING EVAL** — needs LLM endpoint + eval set (23.3); not claimable from unit tests |
| "Không bịa nguồn" | PASS at the retrieval layer (empty ⇒ no source); end-to-end persona behavior needs live eval |
