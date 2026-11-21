# Protocol LoCoMo-v1.2: technical restart after stopping rule S2 (20 Nov 2026; DRAFT for approval)

This amends `PROTOCOL_LOCOMO_V1.md` and `PROTOCOL_LOCOMO_V1_1_AMENDMENT.md`.

**It is infrastructure only.** Nothing scientific changes, and the amendment was written **without any outcome having been inspected** (§5).

## 1. What happened

The approved v1.1 run (freeze `373e4b5a…9d22`) was stopped by **rule S2** (more than 2% of calls failed) after conversation 3 of 10:

| conversation | calls (cumulative) | failed (cumulative) |
|---|---|---|
| conv-26 | 12,209 | 0 |
| conv-30 | 18,881 | 33 |
| conv-41 | 27,978 | 617 (2.2%) |

**Every failure was `BudgetAccountingError("Budget database operation failed")`**, caused by `sqlite3.OperationalError: database is locked`. None was an API or model error.

Two other defects surfaced in the same run:
- **The judge check** (Claude Haiku 5.5) failed on all 400 items.
- **The pipeline script** read the stop record from the wrong file. It ran the judge check and the analysis even though S2 had fired. Those analysis files were moved **unread** to `research_data/locomo_v1_run/quarantine_S2_partial_analysis_UNREAD/`, and they stay unread.

## 2. Root causes, each measured for free

### 2.1 Budget-ledger lock starvation (the S2 failures)

**Why every call got slower:**
- The frozen strict client (`openai_client.py`, Option B-hashed) calls `guard.snapshot()` before every request. It does this only to read the guard's fixed price ceilings and context bound.
- The frozen `snapshot()` also runs `_audit_totals`, a scan of **every** reservation row, inside `BEGIN IMMEDIATE`, an exclusive write lock.
- So each call cost O(ledger size) under one global lock, and the ledger grows by one row per call.
- The ledger lived on `/mnt/c`, the Windows drive seen from WSL, where SQLite I/O is very slow.

**Measured single-snapshot latency** (`ams.llm.budget.BudgetGuard`, test databases):

| ledger rows | `/mnt/c` | WSL ext4 |
|---|---|---|
| 0 | 50 ms | 0.4 ms |
| 30,000 | 530 ms | 24 ms |
| 120,000 | 2,190 ms | 82 ms |

**Concurrency** (16 workers; each cycle is what the client does per call: snapshot, reserve, settle):

| setup | ledger | cycles/s | lock errors |
|---|---|---|---|
| frozen behaviour, `/mnt/c` | 90k | 0.5 | 8 of 48 |
| frozen behaviour, ext4 | 200k | 6.0 | 6 of 400 |
| frozen behaviour, ext4, 32 workers | 200k | 5.7 | 24 of 480 |
| **v1.2 (audit between batches), ext4** | 200k | **152** | **0 of 2,400** |
| **v1.2, ext4, 32 workers** | 200k | **165** | **0 of 3,200** |

SQLite's busy handler is not fair. Under constant exclusive-lock traffic, a waiter can starve past the 30-second timeout. Moving to ext4 alone does not remove this, so **both** changes in §3.1 are needed.

### 2.2 Judge check: HTTP 404, then a spent allowance

The id `anthropic/claude-haiku-5.5` **is valid.** OpenRouter's public model list, retrieved 20 Nov 2026 and recorded in `research_data/locomo_v1_freeze/openrouter_model_check_v1_2.json`, shows:
- the id is listed;
- its price is $0.10 in / $0.50 out per million tokens, exactly the guard's approved ceilings;
- its context is 1M tokens.

**What failed:**
- The frozen strict client sends `temperature` together with `provider.require_parameters = true`.
- **None of the five Haiku 5.5 endpoints** (Google, Claude Platform on AWS, Azure, Anthropic, Amazon Bedrock) supports `temperature`.
- OpenRouter therefore answered *404 No endpoints found that can handle the requested parameters*.

**Why the other 391 items failed:**
- Each of the 9 failed attempts left its $0.10 reservation held, which covers the 1M-token context.
- That used up the $1 allowance, so the remaining 391 items were refused locally with `BudgetExhausted`.
- A 404 is not billed. The $0.90 stays held in the v1.1 judge-check guard, which is kept unchanged.

### 2.3 Pipeline stop check

`locomo_v1_1_pipeline.sh` looked for `"stop"` in `progress.jsonl`, but v1.1 wrote the stop record only to standard output, and the `paid` stage exited with 0.

## 3. Changes, all in `locomo_v1/` and the pipeline (no frozen file is touched)

### 3.1 Ledger (fixes 2.1)

**1. Live ledger on ext4.**
- On the first paid start, the `/mnt/c` ledger is copied to `~/.locomo_v1_state/locomo_v1_run/budget_guard.sqlite` using the SQLite backup API, with the source opened read-only.
- The copy is verified **row by row**: settings, totals, counts by state and a SHA-256 over every reservation row. The original's data files must be byte-identical before and after.
- The result is recorded in `research_data/locomo_v1_run/guard_migration_v1_2.json`.
- The original is never opened for writing again. It is kept as the record of the ledger at the S2 stop.

**What carries over:**
- The live ledger keeps the whole spend history.
- The **$30 cap still covers the whole run**: $2.19 settled plus $5.74 held are already counted against it.

**Refusals:** the code refuses to start in either of these states:
- a migration record exists but the live ledger is missing;
- a live ledger exists without a migration record.

Either would mean spend history could be lost.

**2. `FixedCeilingGuard`.** This proxy wraps the frozen `BudgetGuard`:
- **Served from cache:** the three fixed settings the client reads. They come from one audited snapshot, and the frozen guard refuses any change to its configuration anyway.
- **Delegated unchanged:** `reserve`, `settle`, `mark_unknown` and `halt`. So **the cap is still checked atomically on every call**, and unknown billing still halts the guard.
- **Audit timing:** the frozen full audit (`snapshot()`) runs at start and after every answer batch and judge batch, when no worker is active.
- **On a blocked guard:** the audit stops the run.

**3. Workers stay at 16.** A copy of the real ledger was used for a free rehearsal at real scale:
- conv-42, about 9.5k real prompts, 9,694 calls;
- the frozen client and guard, with only the SDK faked;
- **0 failures**, at 134 calls/s;
- the ledger stayed consistent, and the 263 pending holds were unchanged.

### 3.2 Judge check (fixes 2.2)

- **`DropParamsSDK`** removes only `temperature` from the request body, and only for the judge check:
  - the prompt, the model, `max_tokens` and the strict routing (`require_parameters`, `max_price`, no fallbacks) are unchanged;
  - a test checks that every parameter sent is supported by **all five** endpoints.
- **Canary:**
  - the first item is sent alone;
  - if it fails, nothing more is sent and the stage exits 5;
  - this includes the case where the response names an unexpected model, which halts the guard.
- **New files:** the output is `judge_check_v1_2.jsonl` and the guard is `judge_check_guard_v1_2.sqlite`, with a cap of **$1**.
  - v1.1's `judge_check.jsonl` and guard are kept unchanged.
  - Worst-case Haiku exposure is $1 plus $0.90 held for unbilled 404s.
- **Disclosed consequence:** Haiku 5.5 cannot be called at temperature 0 on OpenRouter, so the check uses the provider's default sampling. The check is a validity check (Cohen's κ against the GPT-4o-mini judge), not a hypothesis test.

### 3.3 Stopping and completeness (fixes 2.3)

**Exit codes:**
- `paid` exits **3** when S2 fires or the run is incomplete;
- `judge-check` exits **5** when the canary fails or more than 2% of items fail;
- `analyse` exits **6**, and refuses, when the last segment stopped or did not finish, any selected key lacks an answer or a judgement, or the judge check is missing.

**Records:** every stop is written to `progress.jsonl` as well as to the log.

**The pipeline** (`research_data/locomo_v1_2_pipeline.sh`) moves to the next stage only on exit 0.

### 3.4 Restart semantics, and why the evaluation stays valid

**1. Same work, same inputs.**
- The build, the scenarios, the contexts, the prompts, the models, the questions and the draws are unchanged.
- The freeze hashes all of them, and the build hashes are identical to v1.1's.

**2. Nothing is redone or dropped by outcome.**
- A key is skipped only if it already has an answer. Finished calls are never repeated, and their recorded answers and judgements are used as recorded.
- Every key without an answer is attempted, including the 650 that failed in v1.1. The same applies to every answer without a judgement.
- An attempt is retried **only** when the call raised an exception, which is a technical failure. This happens in at most one extra pass (`RETRY_PASSES = 1`).
- **No answer is ever re-asked because of its content.**

**3. S2 is unchanged.** It is still checked after each conversation, on this segment's calls, including the retried keys.

**4. Analysis only on complete data.** It runs only when every selected key has an answer and a judgement, and the result reports these completeness counts.

**5. Unchanged:** the hypotheses H1–H6, the confirmatory set, Holm (m = 6), the metrics, the tests, the margins, the transfer rules, every arm (no defence, R, C, M, S, SL, S2-ID), both attacks, both auditors and every frozen method.

**6. Disclosed in the paper:** the run was executed in two segments separated by an S2 stop that had infrastructure causes. Failures, spend and the restart are reported.

### 3.5 Preservation

`research_data/locomo_v1_freeze/preservation_record_v1_2.json`, recorded before any v1.2 change touched the run directory, holds:
- the sizes and SHA-256 hashes of the append-only logs (answers, judgements, errors, progress);
- the hashes of the v1.1 ledger, the v1.1 judge check and its guard, and the quarantined files;
- the response cache's row count (27,361) and a digest of its keys.

`python -m locomo_v1 preflight` re-checks it, by hash and size only:
- each log must still **begin** with its recorded bytes;
- the ledgers, the failed judge check and the quarantine must be **unchanged**;
- the cache must keep every row.

## 4. Cost and caps

**Spend so far** (v1 + v1.1, one guard):
- $2.19 settled;
- $5.74 held:
  - 263 pending, each about $0.0003 actually billed:
    - 9 were in flight when v1 was terminated (15:00 UTC hour);
    - the other 254 were sent in v1.1, but recording their result failed on the lock;
  - 36 unknown: v1's 35 connection errors ($0.83) and 1 in v1.1.

**Remaining,** by the protocol's estimator:
- 62,762 answer prompts, plus their judgements;
- calibrated estimate **$6.25** (raw $7.73);
- the cap left in the same $30 guard is $22.07.

**Expected total:** about $8.5, close to the original $8.57 estimate for the whole run.

**Haiku:** the new $1 guard, with expected spend of a few cents.

## 5. Status

- No outcome has been inspected.
- The quarantined analysis remains unread.
- **No paid call has been made since the stop.**
- The owner signs `research_data/locomo_v1_freeze/owner_approval_v1_2.json`, naming the v1.2 freeze digest and the caps.
