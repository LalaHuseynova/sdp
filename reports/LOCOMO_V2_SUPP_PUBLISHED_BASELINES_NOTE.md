# LoCoMo v2 supplementary evaluation: LLM sanitiser and A-MemGuard (pre-registration)

**Status:** written before any paid call of this evaluation (24 Nov 2026). It is hashed with its code in `research_data/locomo_v2/supp_published/supp_manifest.json`. A paid run needs `owner_approval_supp.json` naming that digest and the frozen v2 digest.

**Relation to LoCoMo v2:**
- The frozen protocol, its freeze `3a2c2df8…` and every completed result are **unchanged**.
- The frozen H3 decision stands as reported.
- This evaluation **adds the two MPBench published baselines that v2 did not run**, so that the LoCoMo method set matches MPBench's 11 main methods. Original SAFE-Mem is substituted by the no-defence reference.
- It is **descriptive**: it creates no new pass/fail family and can neither rescue nor overturn a v2 decision.

## 1. Methods, exactly as on MPBench

- **LLM sanitiser:** the frozen `LLMSanitiser` (prompts `sanitiser_audit` / `sanitiser_clean` / `sanitiser_system` v1, GPT-4o-mini, temperature 0, 1,024 tokens).
  - Each retrieved memory is audited on its own. A memory audited "harmful" is **rewritten and the rewrite is kept**.
  - It is dropped only if the rewrite is empty.
  - The context is built from the returned text (MPBench `text_from_defence=True`).
- **A-MemGuard:** the frozen `AMemGuard` wrapper around the vendored upstream checker (method "llm", GPT-4o-mini, temperature 1.0, 2,048 tokens).
  - One reasoning-chain call per retrieved memory, then one consistency judgment.
  - "Inconsistent or unsafe" memories are dropped. If the judgment cannot be parsed, every memory is dropped (upstream behaviour).
  - One draw; identical requests are answered once (response cache), as on MPBench.
- **Common:**
  - Applied to the frozen no-defence top-10 of every `loc` scenario (four hijack shapes × 2 orientations × 5 draws; all 10 conversations).
  - **No refill**, original retrieval order, as in MPBench's `published.apply`.
  - The supplementary code asserts that every reconstructed no-defence context reproduces the frozen context hash.
- **Answering and judging:** the frozen engine (GPT-4o-mini, temperature 0, frozen prompts). The answer cache is seeded from the frozen v2 run, so unchanged contexts cost $0.

## 2. Measures (held-out 8 conversations; dev conv-48/49 reported separately)

- **ASR:** v2's word-bounded injected-value match. The target set is v2's eligible scored targets not audited unsafe by A1, **the same set for every arm** (the published defences use no audits).
- **Value exposure (new):** the injected value is still present, word-bounded, in the context text. Index-based exposure would count a sanitised poison turn as exposed even after its false value is removed.
- **Utility:** judge accuracy on U_out and U_all.

## 3. Analysis (descriptive)

For each hijack shape and each baseline X ∈ {no defence, MemLineage, RandEC, LLM sanitiser, A-MemGuard, C, M}, the contrast S − X is reported for ASR, acc_U_all and acc_U_out. Each comes with its conversation-level mean, an exact sign-flip 95% interval and "S better in k/8". There is also a full table of every arm. Code: `locomo_v2_supp/supp_baselines_analysis.py`.

## 4. Meaningfulness, assessed before the run

| Issue | Expected consequence |
|---|---|
| The sanitiser audits one turn in isolation; LoCoMo's poison is a plausible false fact about fictional people | it may flag little. If so it is a faithful but inactive baseline, which is a finding about the attack type |
| A-MemGuard detects inconsistency within the retrieved set | the contradicting genuine evidence is co-retrieved in only **52.5%** of attacked held-out contexts (poison present in 99.2%), which caps detection by contradiction; false positives may cost utility (MPBench: 87 vs 91) |
| MPBench attacks are instruction-like; LoCoMo's is factual misinformation | baseline activity can differ between benchmarks; this is reported, not adjusted |
| S receives oracle A1 audits; the published defences receive none | the same information asymmetry as on MPBench: consistent with MPBench, but not an equal-information test |
| A-MemGuard at temperature 1.0, one draw | no seed control at the provider; the cached responses make it replayable |

## 5. Execution, budget and stopping

- **Safe pause/resume:** `locomo_v2_supp/published_paid.py`, a defence stage per conversation, then answers through the verified `runner`. It inherits the STOP file, the attempt-level circuit breaker, S2 review and journal repair.
- **Budget:** two strict guards on WSL ext4, separate from v2's ledger. The defence cap and the answer cap are named in the approval.
- **Stopping:** stop on any technical, budget or protocol issue (a refused gate, S2, the cap).
- **Analysis:** run once after completion.
