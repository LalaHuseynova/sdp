# Protocol LoCoMo-v1.1: amendment to `PROTOCOL_LOCOMO_V1.md` (19 Nov 2026; DRAFT for approval)

**Why:** the owner asked that the comparison include every relevant method:
- no defence;
- original SAFE-Mem;
- R, C, M, S, SL;
- S2-ID.

The amendment was requested **before any outcome was seen** (§4).

## 1. What is added

**S2-ID** (frozen), on attack P1, auditors A1 and A2, every shape, draw and orientation. It is composed exactly as on MPBench (`workload/sv2.py`):
1. **SL's frozen decisions:** S plus content lineage, τ = 0.8.
2. **Then the frozen MemLineage deny** (`sv2._GatedReader`, `RecordedVerdicts`) on the final context: if the question is classified SENSITIVE **and** the context holds any turn not written by the memory owner, the context is emptied.

**Classifier:**
- the frozen `SensitiveAction` (`baselines/memlineage.py`) with the existing prompt `sensitive_action` v1 and GPT-4o-mini;
- run **once per distinct question** before the build, recorded in `research_data/locomo_v1_freeze/sensitive_verdicts.json`, and hashed by the freeze;
- separate guard, cap **$1**; about 1,540 short calls, estimated at under $0.05.

**Prediction stated now:**
- The classifier prompt defines SENSITIVE as dispatching actions (messages, uploads, code, database, money) and lists "recalling facts" as ORDINARY.
- LoCoMo's questions are all fact recall.
- So **S2-ID is expected to equal SL** wherever every verdict is ORDINARY. This is reported as such, not hidden.

**Reporting:**
- S2-ID appears in every P1 table.
- **SL − S and S2-ID − S** contrasts are reported per cell, with t-intervals (descriptive).
- **H1–H6, the confirmatory family, the metrics, statistics, attacks and audits are unchanged.** S2-ID is not added to the Holm family: it was never a hypothesis on LoCoMo, and adding it after the fact would change the multiplicity.

## 2. What is not added, and why: original SAFE-Mem

**Original SAFE-Mem cannot be evaluated fairly in this design. The reasons:**

1. **A different memory substrate.**
   - SAFE-Mem stores LLM-extracted, typed claims, with a use-type classifier, authority lattice, scope and conflict detection.
   - This protocol stores raw turns with top-10 retrieval for every arm.
   - A SAFE-Mem row would differ from every other row in its memory, its retrieval *and* its defence. The comparison could not attribute any difference to the defence.
2. **To make it fair, every arm would have to move onto SAFE-Mem's store**, as on MPBench, where R/C/M/S are layered on SAFE-Mem. That would need:
   - a separate SAFE-Mem store for each of the 400 poisoned scenarios × 2 orientations (about 20k paid extraction calls plus per-question use-type calls);
   - **new engineering:** the frozen `GovernedRetrieval` record bindings exist only for MPBench's native stores.
   - That is a new experiment, not an addition to this one.
3. **No defence is already the matching control in this design.** The paper must not call it "SAFE-Mem".

**Recommendation:**
- The comparison with original SAFE-Mem stays on MPBench, where it is fair: same store, and SAFE-Mem's locked-test ASR of 77% vs S 0%.
- If the owner wants SAFE-Mem on LoCoMo, it needs its own protocol: SAFE-Mem's existing LoCoMo integration (`run_memory`, `locomo.principal` = owner), with every arm on that store.
- **Expectation, unverified:** SAFE-Mem serves the other speaker's claims as descriptions, and LoCoMo's questions are descriptive. So it would likely not block this attack.

## 3. Unchanged

- Data, attacks P1 and P2, hijack shapes, auditors A1 and A2, the other arms, questions, metrics, the conversation-level aggregation, the exact sign-flip tests, Holm m = 6, the transfer rules, validity checks, stopping rules, caps ($30 + $1), the draws rule and every frozen method.

## 4. Status of the v1 run (disclosed)

- The v1 paid run started under freeze `9d14caba…0b04` and was **stopped by the owner's request** during conversation 1 (conv-26), before any answer was written to `answers.jsonl`.
- **No outcome was inspected.**
- **Spend:** $0.64 settled, plus $0.83 held for 35 calls with unknown billing (connection errors). This counts against the same $30 guard.
- **Resumption:** in the same run directory, under the v1.1 freeze. The response cache replays every finished call at $0. Cells unchanged by v1.1 have identical prompts.

## 5. Approval

The owner signs `research_data/locomo_v1_freeze/owner_approval_v1_1.json`, naming the **v1.1 freeze digest** and the caps.

The SensitiveAction precompute is paid, so it needs its own approval before the freeze (`owner_approval_sensitive.json`, cap $1).
