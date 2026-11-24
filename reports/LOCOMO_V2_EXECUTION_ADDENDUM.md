# LoCoMo v2: execution addendum (safe pause and resume). Execution level only

**Date:** 23 Nov 2026. Written before the first paid LoCoMo v2 call.

**Scope:** how the frozen engine is driven. It does not touch the scientific protocol. `reports/PROTOCOL_LOCOMO_V2.md` and its freeze (`3a2c2df8…`, 65 files) are **unchanged and re-verified**. The new code lives in `locomo_v2_supp/`, outside the frozen file set:
- **Unchanged:** prompts, models, decoding, jobs, families, arms, metrics, hypotheses, analysis.
- **Answers:** produced only by the frozen `LoCoMoQA` through the frozen strict client, budget guard and response cache.

## Why

Inspection of the frozen engine (`locomo_v1/execute.py`, `ams.llm`) showed:

1. **Persistence:** every completed response is saved to the response cache immediately. A cache hit returns before the budget guard is touched, so a replay costs $0 and reserves nothing.
2. **Batch writes:** `answers.jsonl` and `judgements.jsonl` are written once per conversation. An interruption loses those rows (they replay from the cache at $0). A kill *during* a write can leave a truncated last line, which the frozen reader cannot parse.
3. **Unknown holds:** a failed HTTP attempt is marked "unknown" and its worst-case reservation (≈ $0.0192) stays held for good. With the frozen retry policy (10 attempts, backoff up to 60 s) and 16 workers, an internet outage would pile up holds until the cap was exhausted.
4. **No graceful stop:** the only way out was a hard kill.

## What `locomo_v2_supp/runner.py` adds

- **Segments:** one conversation at a time, conv-48 (development) first as the canary. Each segment calls the frozen `execute.run(..., convs=(conv,))`. Answered keys are skipped and cached keys cost $0.
- **Pre-flight repair:** a truncated trailing journal line is moved byte-for-byte to `run/repairs/` and never parsed.
- **STOP file:** `runner stop` makes every new request refuse *before* any reservation. In-flight calls finish and are saved, so nothing is left pending.
- **Attempt-level circuit breaker:** the first failed HTTP attempt pauses dispatch. Every later attempt, including the frozen client's own retries and other workers, is refused before reservation. Holds are therefore bounded by the attempts in flight (≤ about 16 per trip).
  - **Waiting:** the runner waits for a free connectivity probe (OpenRouter's public model list; no key, $0), then continues. This happens at most 5 times per invocation.
- **S2 (protocol §11):** per conversation, over real HTTP attempts. Above 2%, the run pauses with `S2_REVIEW_REQUIRED` (a persistent marker). It continues only with `--owner-reviewed-s2`, which is the owner's decision and is logged.
- **Records:** `run/resume_log.jsonl` holds every event. `runner status` shows progress counts and the ledger only (no prediction is shown).
- **Cache seeding:** `runner seed-cache` (owner-approved reuse) copies the rows of the v1.1 and pilot response caches into the run cache with `INSERT OR IGNORE`. The rows are never read.

## Free verification (`locomo_v2_supp/resume_test.py`)

The test drives the real paid path (frozen client, strict guard, ledger and cache) through a fake offline API, on conv-30. Report: `research_data/locomo_v2/resume_test_report.json`.

| Scenario | Outcome |
|---|---|
| A: uninterrupted | complete, 15,032 calls; ledger 15,032 settled, $0 held |
| B: hard kill (SIGKILL) at ⅓ | resumed; answers and judgements **identical to A**; 8 extra calls (in flight at the kill); 5 pending holds remain held |
| C: graceful STOP | resumed; **identical to A**; **0** extra calls; **0 pending, $0 held** |
| D: short outage (50 failing calls) | breaker plus probe, auto-continued; **identical to A**; one hold per failed attempt |
| D2: long outage (400 failing calls) | S2 pause; re-run without review **refused**; owner-reviewed resume **identical to A** |
| E: truncated journal line | repaired (bytes kept); **identical to A**; 0 new calls |

## Known, accepted costs

- **A hard kill** (power loss, `wsl --shutdown` while running) leaves the in-flight reservations held, at ≈ $0.0192 each, ≤ 16. They may also cause ≤ 16 duplicate calls (≈ $0.0003 each).
- **An outage** leaves ≈ $0.0192 held per failed attempt.
- Holds are worst-case accounting, not charges. They count against the $40 cap, never against the spent amount.
- **Preferred practice:** use `runner stop` and wait for "paused_by_user" before shutting down.
