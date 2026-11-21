# plan.md: master plan for the ICML paper (protocol v2 and paper)

**Read this file first in every new session.** It is the single source of truth for what is decided, what is done and what comes next. Update it after every step: tick the box, add the date, note the output files.

- Started: 14 Nov 2026.
- Owner: Ulker Huseynova.
- Goal: an ICML submission on *selective (evidence-supported) propagation of distrust in agent memory*.

---

## 0. Standing rules (never break)

1. **No paid API call without the owner's explicit approval for that specific stage.** Before each paid stage: explain why, give the exact cost from a dry run, set a hard cap, and wait.
2. **No algorithm change without approval.** Frozen code must not change: S, R, C, M, original SAFE-Mem, ledger, retrieval, prompts. New methods are separate research-layer wrappers.
3. **Never delete earlier documentation or results.** Never overwrite outputs; every run writes a new directory.
4. **After every task:** update `README.md` §10 (progress log) **and** this file.
5. **Protocol v2 must be frozen (hashes) before any held-out data is generated.** The held-out data is never inspected for outcomes before the single analysis run, and it is never used to tune anything.
6. Report every result, including failures and negative results.

## 1. Owner decisions (all recommended defaults accepted on 14 Nov 2026)

| # | Decision | Value |
|---|---|---|
| 1 | Fresh test data | New attacks generated (MPBench scored-attack supply exhausted: 3 of 102 unused) |
| 2 | Generator model (attacks + benign) | **Claude Sonnet** (a different family from the evaluated GPT-4o-mini), via OpenRouter |
| 3 | Benign documents | **1,342 generated** + 1,154 unused MPBench, each used **at most once**: groups share no documents. *Revised by step 1.5 (14 Nov): 963 truly unused MPBench (deduped by text) + 1,957 generated specs (domain shortfall + 20% reserve).* |
| 4 | Number of held-out groups | **96** |
| 5 | Replication | The old v4 test split (24 groups), in a separate table |
| 6 | Main table rows (11) | Original SAFE-Mem, R, C, M, A-MemGuard, MemLineage, LLM sanitiser, RandEC, **S**, **SL**, **S2-ID** |
| 7 | S2-BS | Appendix only (negative result); not in Tables 1–8 or hypotheses |
| 8 | "+R" published variants | Appendix |
| 9 | Table 2 rows | One row per method (11 rows) |
| 10 | Table 2 columns | localized, distributed, uninformative, Sybil k=2, 4, 8, own-batch k=4, laundering r=.25, .5, 1, audit-aware shift, framing, **worst case** |
| 11 | Audits in Table 2 | Oracle; random audits in Tables 3–4 |
| 12 | Random draws | 6 per random condition |
| 13 | Boundary verification | Appendix table (with vs without) |
| 14 | Table 2 cell | "ASR (strict utility)"; exposure in a separate Table 2b |
| 15 | ASR type | **Target-specific ASR** in the main tables; judge ASR in the appendix |
| 16 | Worst case | Over all pre-registered attack conditions (≈ 50), random draws averaged first |
| 17 | CIs | [95% CI] in Tables 1, 7, 8; other tables values only, with CIs in the appendix |
| 18 | Number format | % with no decimals |
| 19 | Imperfect audits | 20% missed poison (FN); **1 of 5 audits wrongly flags the innocent** (FP); late = audits revealed after half the questions |
| 20 | Imperfect-audit attacks | localized, distributed, Sybil k=2, laundering r=.5 |
| 21 | Table 6 cell | ASR / strict utility |
| 22 | Second backbone | **Claude Haiku** (answer model; judge stays GPT-4o-mini) |
| 23 | Second-model scope | Table 1 (localized) + hypothesis conditions, all 11 methods |
| 24 | Best baseline in Table 7 | Chosen in advance: the best published method (lowest ASR) and the best internal method (C or M) |
| 25 | H4 | Test = **average over the hard attacks**; worst case reported alongside |
| 26 | H5 | Primary = relay **exposure**; gated secondary = relay target-specific ASR; separate utility non-inferiority |
| 27 | H6 | **Superiority:** S harms innocents less than C and M |
| 28 | Margins | Non-inferiority 5 pts (H2; utility parts of H4, H5; ASR part of H1); H1 superiority +3 pts |
| 29 | Ablations | Dev only (appendix) |
| 30 | Human judge check | 300 cases, 2 annotators + 1 adjudicator. **⏳ Owner must name the 3 people.** |
| 31 | Budget | Exact figure from the free dry run (step 1.12); then the owner decides between raising the allowance and reducing scope |
| 32 | Approvals | Separate approval for every paid stage |
| 33 | Figures | Line plots for Tables 3 and 4; bar chart for Table 1 |
| 34 | Old locked test v1 | Appendix, labelled "earlier pre-registered test (protocol v1)" |
| 36 | Scope (owner, 15 Nov; resolves decision 31) | **Option B:** all 11 methods (+ 5 appendix methods) on every registered condition (62 cells / 272 runtime conditions) of the MPBench-derived **v4 test split (24 groups)**; Claude Haiku on Table 1 + hypothesis cells; ablations dev only. Results labelled **replication evidence, not fresh held-out, not confirmatory**. The full v5 plan (96 generated groups) is kept unchanged as the future evaluation (`reports/PROTOCOL_V2_DRAFT_20261113.md`). Final text: `reports/PROTOCOL_V2_OPTION_B_20261115.md` (rev 5) |
| 35 | Uninformative cell (owner, 14 Nov, during step 1.12) | **Option (a):** stays a Table 2 column, labelled **"no-signal control"** (not an attack: it assumes the attacker controls every contributor, see `brainstorm.md` and the supervisors' feedback), and is **excluded from the worst case**. Revises decision 10 and the registry's `WORST_CASE` (currently 47 cells incl. uninformative). No cost change (the cell still runs). **To implement at step 2.1** (registry + Table 2 label + protocol text), tests first. |

## 2. Target output: the 8 paper tables (+ appendix)

1. **Main result:** 11 methods × {target ASR, judge ASR, strict utility, unaudited exposure, useful-fact exposure, relay exposure}, localized, with [95% CI].
2. **ASR (strict utility)** under 12 attack columns + worst case (oracle). **2b:** the same with exposure.
3. **Sybil-k**, oracle and random (k = 1, 2, 4, 8).
4. **Laundering-r**, oracle and random (r = 0, .25, .5, .75, 1) + innocent-forwarder utility.
5. **Harm to innocents:** framing (concentrated, spread), cohabit, FP audit.
6. **Imperfect audits:** perfect / FN 20% / FP 1-of-5 / late.
7. **Generalization:** fresh test with GPT-4o-mini; fresh test with Claude Haiku; old split replication.
8. **Pre-registered hypotheses H1–H6:** estimate [CI], margin, ✓/✗.

**Appendix:** S2-BS; "+R" variants; boundary verification; judge ASR; ablations; judge validation (κ); cost and runtime; locked test v1; dev results.

---

## 3. To-do list (⬜ todo · 🔄 in progress · ✅ done · ⏸ waiting for owner · 🔒 approval gate · 💰 paid)

### Phase 0: Setup and decisions

- ✅ **0.1** Archive all implementation and results before v2 (13 Nov) → `research_data/archive_pre_protocol_v2_20261113/`. Verify: `scripts/archive_snapshot.py verify`.
- ✅ **0.2** Protocol v2 draft rev 1 + rev 2 (power, independence, H5 endpoints) → `reports/PROTOCOL_V2_DRAFT_20261113.md`, `scripts/power_protocol_v2b.py`.
- ✅ **0.3** Record all 34 owner decisions (this file §1) and update the protocol draft to **rev 3** to match them (14 Nov).
- ⏸ **0.4** Owner names the 2 annotators + 1 adjudicator for the human judge check (needed only by step 6.1).

### Phase 1: Build everything offline (free; mocks only, no API)

- ✅ **1.1** Guarded transport for the **generator model (Claude Sonnet via OpenRouter)**: a new purpose, price ceilings, exact request-shape checks, hard caps, mock tests. *(14 Nov)*
  - **Allowlist:** `APPROVED_MODELS` in `src/ams/llm/budget.py`: gpt-4o-mini 0.15/0.60 (default, unchanged), `anthropic/claude-sonnet-5.5` 2.00/10.00, `anthropic/claude-haiku-5.5` 0.10/0.50 (public OpenRouter list prices, 14 Nov; `configs/research/pricing_claude_*_20261114.json`).
  - **Wiring:** the OpenRouter `max_price` routing cap is read from the guard (same 0.15/0.60 for GPT); `ExecutionSession.create(..., model=)`.
  - **Transport:** `ConstructionSession` takes the model from the session. New purpose `v2_generation` (upper cap $10) on split `v2_heldout`, needing `check_v2_approval` (owner file with the frozen v2 digest, cap, model). Exact shape: Sonnet, temperature 1.0, 4,096 or 2,048 tokens, system prompt starting with `[SAFE-Mem protocol v2 generator]`. Per-purpose model map `V2_MODELS`. `GuardedV2Client`.
  - **Tests:** `tests/test_v2_transport.py` (5). Full suite 680 passed. Existing sessions v2/v3 open unchanged.
- ✅ **1.2** Guarded support for the **second backbone (Claude Haiku)** as the answer model; the judge stays GPT-4o-mini. Tests. *(14 Nov)*
  - **Router:** `src/ams/research/protocol_v2/backbone.py` `BackboneRouter(gpt_session, haiku_session)`. Answer and no-memory-answer requests are re-addressed to `anthropic/claude-haiku-5.5` **before** any replay and sent to purpose `v2_backbone_answer` (Haiku session; exact shape: temperature 0, 200 tokens, answer prompt). Conflict checks and judges stay on GPT-4o-mini via the new purpose `v2_stage3` (upper cap $80; owner approval sets the actual cap).
  - **Tests:** `tests/test_v2_backbone.py` (3).
- ✅ **1.3** **Generation prompts** (attack, benign), a strict JSON schema and parser; MPBench family descriptions (category, domain, carrier style; never case text); fixed quotas per domain and type. Tests with scripted replies. *(14 Nov)*
  - **Prompts:** `prompts/v2_generator_attack_system/v1.txt`, `prompts/v2_generate_attack/v1.txt`, `prompts/v2_generator_benign_system/v1.txt`, `prompts/v2_generate_benign/v1.txt`. Fictional names, example.com only, no working secrets.
  - **Module:** `src/ams/research/protocol_v2/generation.py`:
    - label definitions written by us (6 domains, 5 attack types, 6 goals, 3 signals);
    - `load_reachable_cases` (the 102) → `reachable_distribution` (type × goal and signal proportions; exfiltration ≈ 55%);
    - `attack_specs` (1,080 = 180 per domain, deterministic, unique scenario seeds) and `benign_specs` (1,610);
    - `attack_request` / `benign_request` (Sonnet, temperature 1.0, 4,096/2,048 tokens; they pass `v2_stage`);
    - E1 parsers `parse_attack` / `parse_benign` with reason codes (json, keys, types, context length, verbatim payload, target length, question mark, query leaks target, repetition, credential-like strings, non-example URLs, AI-directed benign text).
  - **Tests:** `tests/test_v2_generation.py` (6), including "no MPBench attack text in any prompt".
- ✅ **1.4** **Exclusion pipeline E1–E4** (schema, description classifier, MiniLM near-duplicate < 0.6 against MPBench + accepted, no 8-gram overlap with MPBench and v1–v4) + **inclusion I1** (original write path stores the poison), with a reason code per item and the full funnel report. Mock tests. *(14 Nov)*
  - **Module:** `src/ams/research/protocol_v2/inclusion.py`:
    - `local_exclusions` (E3 near-duplicate vs MPBench and earlier accepted items in spec order; E4 stable 8-gram overlap);
    - `is_description` (E2, frozen classifier, granularity 5);
    - `stores_poison` (I1: frozen write path in an isolated store + Stage-2 `carrier_stored` rule);
    - `funnel`.
  - **Rule order corrected:** E1 → E3 → E4 are free; **E2 and I1 are both paid** (an LLM classifier and the write path) and run together in the new guarded purpose `v2_inclusion` (GPT-4o-mini, frozen construction shapes, upper cap $5). Also added `v2_stage1` (memory building, upper cap $5).
  - **Tests:** `tests/test_v2_inclusion.py` (6); suite 695 passed.
- ✅ **1.5** **Fresh group builder (workload v5):** 96 held-out groups + a generation-check subset (10%); unique documents (no reuse); reserve handling; manifest and hashes. Tests: no shared document, no overlap with MPBench/v1–v4, determinism. *(14 Nov)*
  - **Module:** `src/ams/research/protocol_v2/groups.py`: `select` → `replace_failed` → `emit`, plus `validate_v5`. It reuses v4's group code via `generator.emit_group` (pure refactor; v1–v4 still regenerate byte for byte). CLI: `scripts/build_workload_v5.py pools | dry-run | build`.
  - **Protocol rev 4 (owner decision, 14 Nov):** the copied seed `seed_a` is a **generated** attack, because MPBench seeds' questions are never answered from external memory, so H5 would be dead. Per group: 6 generated attacks + 2 MPBench seeds (`seed_b`). Attack specs **1,440**; check subset 10 per domain.
  - **Corrected supply:** unused MPBench benign = **963** (not 1,154: duplicate texts and missed copy bases). Benign stays domain-matched, so generated benign quotas per domain = shortfall + 20%: **1,957** (`generation.BENIGN_QUOTAS`). Seeds: 1,595 available, 192 needed.
  - **I1** also returns `carrier_text` (used for the unlinked relay).
  - **Checks:** dry run on the real MPBench pools (96 groups, 3,360 documents, valid); `tests/test_v2_groups.py` (6); suite 701 passed.
- ✅ **1.6** **Imperfect-audit conditions:** FN 20%, FP 1-of-5, late (audits after half the questions, fixed question order), applied to localized, distributed, Sybil k=2, laundering r=.5, 6 draws. Runner support for late audits. Tests. *(14 Nov)*
  - **Conditions:** `imp_{attack}_{fn20|fp1|late}_d{i}` in `src/ams/research/workload/adaptive.py` (`imperfect_conditions`, `parse_imperfect`, `pre_reveal_probes`): 4 attacks × 3 kinds × 6 draws = 72. Each is the attack's existing perfect-audit condition (the "perfect" column of Table 6) with only the tickets changed, so the existing `build_condition` / `extend_store` relabelling is reused.
    - FN: each unsafe ticket → "safe" with probability 0.2.
    - FP: the safe ticket is replaced in place by "unsafe" on a random innocent benign item.
    - Late: oracle tickets; the first half of a per-group, per-draw shuffled probe order is answered before the audits are revealed.
    - Draw *i* uses the same random numbers for every attack.
  - **Runner:** `prepare_state(..., revealed=False)` gives the arm's state before any audit. `run` answers a late condition's pre-reveal probes on that state (answering is read-only, so this is exact). The default path is unchanged; the existing runner tests pass.
  - **Checks:** `tests/test_v2_imperfect_audits.py` (8, written first); suite 709 passed; v1/v4 regenerate; both integrity archives verify. No frozen algorithm touched; no paid call.
- ✅ **1.7** **Condition registry v2:** the exact list of all pre-registered attack conditions (Table 2 columns, Tables 3–6, worst-case list), with fixed seeds. Tests. *(14 Nov)*
  - **Module:** `src/ams/research/protocol_v2/registry.py`. It defines no condition: it groups the runtime names from the existing `adaptive.py` generators into **62 cells** (272 runtime conditions; random cells hold 6 draws).
    - Families: base 3, audit-aware 2, framing 2, random detection 4, Sybil-k 12, own-batch 9, laundering-r 15, cohabit 3, imperfect audits 12.
    - `TABLES` (1–7), `HYPOTHESES` (H1–H6 populations), `WORST_CASE` (47 cells = every attack cell except boundary verification; protocol "≈ 50"), `SECOND_BACKBONE` (8 cells), `APPENDIX` (15 boundary-verification cells).
    - `adaptive_conditions()` = the 269 that `extend_store` must build; `fingerprint()` to hash at the freeze.
  - **Fixed seeds:** every draw's seed is a hash of (group, condition name) in `adaptive.py`, the same for all methods. Tests confirm each draw is reproducible and that the draws differ.
  - **Problems found:**
    1. Random-detection cells were labelled "oracle" (their names lack `_rand`); caught by a test and fixed.
    2. Own-batch and cohabit "± boundary verification" had no generator; built as `{c}_fu`, which the existing `_sweep` already supports, and verified to build.
    3. `sybil_k1` and `launder_r0` are the localized attack by definition; kept as registered (they cannot change a maximum, and identical requests are replay-cached).
    4. The old single `sybil` condition is not in §4 (Sybil-k replaced it), so it is not registered.
    5. **Scale:** 182–272 conditions × 96 groups × 11 methods × 35 probes ≈ **6.7–10 million answers before replay dedupe**. This must be priced at step 1.12 (decision 31: owner chooses between budget and scope).
  - **Checks:** `tests/test_v2_registry.py` (6, written first): all 269 adaptive conditions build with the equal 5-ticket budget. Suite 715 passed.
- ✅ **1.8** **Paid-run pipeline v2** (built, not run):
  - free parallel retrieval precompute;
  - single-writer guarded answer + judge stage for all 11 methods (+ S2-BS, "+R" variants);
  - published methods' answers on their filtered contexts;
  - resumable, with exact replay.

  Mock end-to-end test. *(14 Nov)*
  - **Module:** `src/ams/research/protocol_v2/pipeline.py`, one loop `evaluate(...)` for every method:
    - `answer=False` = the free precompute (exposure + a hash of each would-be answer prompt);
    - `answer=True` = the paid stage (frozen answer prompt, MemoryJudge, guarded session).
    - Internal arms reuse `prepare_state` + `lineage` / `sv2`. Published defences filter static (or R, for "+R") retrieval via `published.apply`, and their kept memories are answered with the same prompt.
    - Late audits, journal, grading and exposure are the existing code.
  - **Paid entry:** `open_paid(...)` opens one guarded session per purpose (`root/<purpose>/`), and only with `--confirm-paid` plus an owner approval covering **every** purpose the methods need: `v2_stage3`; `v2_published_memlineage` (MemLineage, S2-ID); `v2_published_amemguard`; `v2_published_sanitiser`; `v2_backbone_answer` (Haiku). Each session's existing exclusive lock enforces the single writer.
  - **Transport:** 3 new guarded purposes `v2_published_*`, reusing the dev scopes' exact request-shape checks. The code upper caps ($0.50 / $20 / $10) are limits only; the owner's approval sets the actual cap.
  - **CLI:** `scripts/run_protocol_v2.py precompute | paid`.
  - **Checks:** `tests/test_v2_pipeline.py` (10, written first):
    - internal arms reproduce `runner.run` row for row;
    - all 16 methods run end to end on mocks;
    - precompute prompt hashes = paid prompt hashes;
    - restart is exact;
    - approval, confirm and single-writer gates;
    - a guarded mock-wire run sends each distinct request once, and its restart sends none;
    - the CLI refuses before loading anything.
    Suite 725 passed. No real evaluation, no paid call.
  - **Open for 2.2:** the paid CLI should also check the approval's `protocol_v2_digest` against the freeze `verify` output (today only its presence is checked).
- ✅ **1.9** **Analysis code v2:**
  - every metric (target ASR, judge ASR, strict utility, unaudited exposure, useful-fact exposure, relay exposure/ASR, innocent utility, worst case);
  - Holm over 8 contrasts, IUT, gatekeeping;
  - group cluster bootstrap + multi-way cluster sensitivity analysis;
  - **renderers for Tables 1–8 + appendix + figures**.

  Validated on existing dev data (labelled dev). *(14 Nov)*
  - **Cap fix first (owner request):** an approved cap above the code ceiling is now rejected in `pipeline.open_paid`, never lowered (1 new test).
  - **Module:** `src/ams/research/protocol_v2/analysis.py`. **CLI:** `scripts/analyse_protocol_v2.py` (read-only journals, hash-checked; refuses held-out rows without `--allow-heldout`, reserved for the post-freeze run).
  - **Metrics:** each has one level, answer-level or retrieval exposure. They are never mixed in a column; this is enforced when the module loads.
  - **Estimates:** per group (draws averaged, H4 cells weighted equally), then the mean over groups.
  - **Statistics:**
    - paired group bootstrap (10,000, percentile);
    - p by bound inversion;
    - Holm over 8 contrasts;
    - IUT p = the largest p of a contrast's parts;
    - fixed-sequence key secondaries;
    - multi-way bootstrap (groups × attack family × benign source);
    - worst case with a CI of the maximum;
    - covariates.
  - **Decisions pending review at 2.1 (NOT approved; see the 2.1 checklist):**
    1. H1 ASR non-inferiority per contrast against its own comparator;
    2. key-secondary margins = the primary's margin;
    3. H3 = IUT over the 4 published methods;
    4. non-estimable contrast → p = 1, still in Holm m = 8;
    5. Tables 3–5 split into answer-level and retrieval-exposure panels (§5 rule over the §10 cell spec);
    6. worst-case parenthesis = paired metric in the worst cell;
    7. Table 7 baseline-selection rule;
    8. bootstrap seed 20261114 is a placeholder.
  - **Problems:**
    - the MPBench file is not JSONL, so the existing reader is reused;
    - empty sweep plots on dev now show "no data";
    - **multi-way fragility:** dev H5 flips (8 relay probes / 5 families), and benign source has only 2 levels on held-out; noted for 2.1.
  - **Checks:**
    - `tests/test_v2_analysis.py` (19, written first; synthetic only, with exact enumeration, scipy and a textbook Holm example);
    - an independent recomputation on dev matches exactly;
    - 354/354 values match the earlier dev analysis.
    Suite **745 passed**. Dev (not evidence): H1×2, H2 and H5 pass; H3, H4 and H6 cannot be estimated on dev. No held-out data, no paid call.
- ✅ **1.10** **Ablation runner** (dev): gate thresholds {2, 3}/{3, 4, 6}, withhold threshold {0.15, 0.25, 0.35}, τ {0.7, 0.8, 0.9}, audit budget {3, 5, 10}, boundary verification on/off.
  *(14 Nov)*
  - **Module:** `src/ams/research/protocol_v2/ablations.py`. **CLI:** `scripts/run_ablations_v2.py` (free, exposure only, no network, dev groups only).
  - **How it works:** one knob at a time, as a scoped runtime override restored on exit, the pattern of `evidence_memoization`. Runs go through the unchanged `pipeline.evaluate`. No frozen file is edited.
  - **Checks:** `tests/test_v2_ablations.py` (11, written first):
    - the default gates equal the frozen `active_scopes` on every origin;
    - each variant changes only its own scope;
    - the overrides are restored, also on error;
    - default-valued variants reproduce the pipeline row for row;
    - a budget of 5 rebuilds the stored localized audits exactly;
    - budget 3/10 tickets and an end-to-end budget run;
    - the full free runner and summary;
    - the CLI refuses non-dev groups;
    - the prompt mirror.
    Suite **756 passed**.
  - **Problem:** old dev stores refuse to load ("Prompt files changed since checkpoint") because the 4 v2 generator prompts were added to `prompts/` later; nothing used by the memory changed. **Fix:** `checkpoint_prompts` mirrors exactly the checkpointed files (hash-verified) and points the in-memory store at them, so the frozen check still runs. Pending decision at 2.1.
  - **Dev run:** `research_data/protocol_v2_ablations_dev_v3_20261114/` was **still running when the session hit its usage limit**. Check `ablations.md` exists; if the folder is incomplete, delete it and rerun the CLI.
  - Pending choices are listed under 2.1 (not approved).
  - **Verified 14 Nov:**
    - **Run:** the dev run completed (exit 0, 1 h 47 min); all 11 journals have the expected row counts (boundary verification 50,400); `ablations.md` and `.json` were written. Nothing deleted or rerun.
    - **Findings** (dev, exposure, descriptive):
      - **withhold 0.35** opens localized (0 → 97) and distributed (0 → 94); **0.15** cuts uninformative utility exposure (−22). Cause: S's penalties are exactly 0.25 on localized, so the frozen threshold sits on the boundary;
      - **budget 3** raises localized unaudited exposure 0 → 64 (relay +15); budget 10 has no effect;
      - **context gate 3** changes only uninformative (+13 exposure, +8 utility);
      - the **source gate and τ** had no effect in the tested cells;
      - **boundary verification** helps only random_spread (−24).
- ✅ **1.11** **Human-judge validation kit:** sampling script (fixed seed, stratified 150 hits / 150 misses), blind annotation sheet, written guidelines, adjudication, κ and judge precision/recall computation.
  *(14 Nov)*
  - **Code:**
    - module `src/ams/research/protocol_v2/judge_validation.py`;
    - CLI `scripts/judge_validation_v2.py` with `sample | adjudicate | analyse`. It refuses held-out rows without `--allow-heldout`, which is reserved for the post-run sample;
    - guidelines and design: `reports/JUDGE_VALIDATION_GUIDELINES_V2_DRAFT.md`.
  - **Design:**
    - frame = every judged decision of the table and appendix methods;
    - 150 judge hits + 150 misses, allocated within each verdict over method group × attack family in proportion to the frame (≥ 1 per stratum);
    - identical (question, instruction, answer) items are drawn once;
    - each item carries the design weight N_h/n_h.
  - **Annotation:**
    - two blind sheets (question, planted instruction, answer only), each in its own seeded order;
    - a private key and a manifest;
    - returned sheets are checked: complete, binary, each annotator's own;
    - a blind adjudication sheet with only the disagreements.
  - **Metrics:**
    - Cohen's κ on the sample;
    - judge precision and NPV, conditional on the verdict;
    - recall and specificity **weighted by the design**; the unweighted values are shown labelled and are biased;
    - stratified bootstrap CIs;
    - the pre-declared corrected ASR = P(judge hit)·PPV + P(judge miss)·(1 − NPV), per method group; for target ASR, PPV/NPV come from restating answers. It is a sensitivity analysis only.
  - **Checks:**
    - `tests/test_v2_judge_validation.py` (11, written first): κ textbook example (0.4); a weighted confusion table worked by hand (weighted recall 0.50 vs biased unweighted 0.80); allocation; reproducible and order-free sampling; blindness (no method, condition, verdict or family in a sheet); a copied sheet is refused; adjudication; the correction formula; the CLI held-out guard;
    - dev feasibility draw (no annotation): `research_data/protocol_v2_judge_kit_dev_DEMO_families_20261114/`. An earlier draw without families, `..._DEMO_20261114/`, is kept and superseded;
    - a CLI dry run with **simulated** annotators, in the scratchpad only.
    Suite **767 passed**.
  - **Problems found:**
    - the sampling CLI lacked MPBench families; fixed with `--mpbench`;
    - dev holds only 85 distinct judge hits (65 short of 150; the kit reports the shortfall and does not pad);
    - **NPV transportability:** a group-level NPV inflates the corrected ASR of secure methods (dry run: 0 → about 0.10), because their misses are mostly unexposed;
    - **few "ours" hits** (7 distinct on dev).
    Both design points are pending under 2.1.
- ✅ **1.12** **Dry-run cost estimate** with mocks for every paid stage (3.1, 3.3, 3.5, 4.2–4.5, 6.2), plus a runtime estimate → budget proposal to the owner.
  - **Done 14 Nov (free; no paid call, no held-out data, no algorithm change).** Report: `reports/COST_ESTIMATE_V2_20261114.md`. Code: `protocol_v2/cost.py`, `scripts/estimate_cost_v2.py` (`measure`, `estimate`). Data: `research_data/protocol_v2_cost_measure_dev_v3_20261114/` (`estimate.json`, `estimate.md`).
  - **Method:** measured cost per call (dev guarded ledger and published dev summaries); measured distinct prompts from the free precompute of 7 internal methods × 272 conditions on 4 dev groups; strict upper bounds for methods that cannot run free.
  - **Measured:**
    - 631 distinct answer prompts per group (of ≈ 66,600 rows), 297 judged;
    - Original SAFE-Mem's retrieval and RandEC's output are identical in all conditions, so the published defences are paid once per question;
    - Sonnet generation $22.76–29.05 (guess was $2–8).
  - **Scope scenarios (low–high; sum of caps at high × 1.3):**
    - A full plan $43.52–81.65 (caps $108.60; generation and Haiku caps above their ceilings);
    - **B MPBench only (v4, 24 groups) $4.44–11.86 (caps $16.40, fits the ≈ $26.57 left)**;
    - C MPBench v4 + 32 generated groups $17.08–31.87 (caps $42.80).
  - **Runtime:** the paid stage is one process that, in the current code, recomputes retrieval and RandEC per condition: 48–49 days for 96 groups, 12 days for 24. Two proposed result-identical fixes (below) bring it to 25–49 h for 96 groups and 6–12 h for 24.
  - ✅ **Runtime fixes, part 2 (15 Nov):** Fix 2 (three steps) exact and implemented; PYTHONHASHSEED = 0; B ≈ 25–54 h paid process.
  - ✅ **Runtime fixes (same day, owner-approved):**
    - Fix 1 (RandEC cache) implemented and verified identical;
    - Fix 2 stopped (prompt equivalence fails); see step 2.1;
    - corrected runtime for B with Fix 1: 4.6–5.8 days.
  - ⚠️ **Runtime correction (same day):** B current code ≈ 14.4–15.6 days (not 12); both fixes ≈ 1.0–2.2 days paid + ≈ 12 h free precompute (not 6–12 h). The estimate had omitted the published methods' retrieval and their own calls. Cost unaffected.
  - **Also:** RandEC now loads from the local Hugging Face cache (offline precompute fixed); an order-dependent test made deterministic; 17 tests; the tests caught 2 cost-model bugs (fixed).

### Phase 2: Freeze protocol v2

- ✅ **2.1** Final protocol text, **option B, revision 5** (15 Nov): `reports/PROTOCOL_V2_OPTION_B_20261115.md`. Every pending item below is resolved there (§12 decision table D-35 … D-FG); decision 35 implemented (registry v2: worst case 46 cells, "no-signal control" †); option-B labels, footnotes, Table 6 panels, Table 7 rows, A13 implemented (analysis v2); power at N = 24 computed (`research_data/protocol_v2_freeze_optionB_20261115/power_n24/`). Found and fixed at 2.3 (tests first): the Haiku paid run would have failed at its first answer (pipeline v2). One optional scope item left to the owner: ablation cells for source gate and τ (+$0.74–2.97, default not added).
  - *History of this step, kept for the record:* the original to-do was "Final protocol text (rev N): exact budget, caps, seeds, condition registry, analysis plan."
  - ⚠️ **Pending methodological review before the freeze. NOT approved** (owner, 14 Nov: "Do not treat the eight statistical choices from Step 1.9 as approved yet"). The code implements these as provisional defaults only.
    - **Step 1.9 analysis choices:**
      1. H1 ASR non-inferiority per contrast against its own comparator (protocol text names only S − C);
      2. 🔍 **key-secondary margins** = the primary's margin on the other level (H1 +3, H2 +5 NI, H3/H4/H6 0). The protocol defines only H5's. **Flagged for review:** reusing a utility margin (+3) for an exposure endpoint, and an NI margin for H2's exposure, are choices, not protocol text;
      3. H3 = intersection-union over the 4 published methods;
      4. non-estimable contrast → p = 1, still counted in Holm m = 8;
      5. Tables 3–5 split into answer-level / retrieval-exposure panels;
      6. worst-case parenthesis = the paired metric in the worst cell;
      7. Table 7 baseline-selection rule (best internal within 5 pt of S's target ASR);
      8. bootstrap seed (placeholder 20261114).
    - 🔍 **Multi-way bootstrap, flagged for review:** benign source type has only 2 levels, so about half of all resamples drop one source entirely, and attack families are few. The intervals can be very wide, and on dev H5 flipped (Holm p 0.001 → 0.15). Options:
      - keep it as specified (sensitivity only; decisions stay on the group bootstrap);
      - resample only the factors with ≥ 5 levels;
      - replace the benign-source factor by a stratified (within-source) group bootstrap.
      Decide before the freeze.
    - **Step 1.10 ablation choices:**
      - which cells each knob runs on (gates and withhold threshold: localized, distributed, uninformative; τ and budget: localized);
      - the budget definitions (3 = random 3 of the 5 oracle tickets; 10 = 5 oracle + 5 random benign or scored items with true verdicts; 6 draws);
      - the context-gate variant changes only the context scope (the source gate's qualifying-context rule stays frozen);
      - exposure-only until the paid step 6.2;
      - the replication split is not run yet (owner: dev only);
      - 🔍 the source gate and τ never decided anything in the tested cells: consider adding Sybil and laundering cells for those knobs;
      - 🔍 **Judge validation (step 1.11):**
        - (a) **NPV transportability:** stratify and correct by exposure (target in context yes/no), assuming true misses when the target is absent;
        - (b) a **minimum per method group** within each verdict, or pooled PPV, because secure methods have few hits;
        - (c) static assigned to the "internal" group;
        - (d) the frame includes appendix methods and relay probes;
        - (e) the correction's CI reflects annotation uncertainty only.
      - 🔍 **withhold-threshold boundary:** S's localized and distributed penalties equal the frozen 0.25, so security rests on the ≥ boundary. Decide how this is reported (no algorithm change).
    - **Prompt checkpoint (found in 1.10):** old stores (dev, v4 replication) list fewer prompt files than `prompts/` now holds, because the 4 v2 generator prompts were added later. They load only through `ablations.checkpoint_prompts` (a verified mirror). Decide: keep the mirror for every rerun on old stores (Table 7 row 3 replication included), or move the generator prompts out of `prompts/`.
    - **From step 1.12 (cost and runtime):**
      - 💰 **Scope (decision 31):** A full plan, B MPBench only, or C MPBench + 32 generated groups (`reports/COST_ESTIMATE_V2_20261114.md` §3, §5). Only B fits the current allowance. The owner's stated preference "for now" is the MPBench replication table; **not yet a decision.**
      - **Code ceilings:** A needs generation $10 → $38 and Haiku $10 → $19; C needs generation $10 → $13. Raising a ceiling is a code change that needs approval.
      - ⚙️ **Runtime fixes (result-identical engineering, not algorithm changes):**
        1. cache RandEC by input text (deterministic, condition-invariant input);
        2. the paid stage reads contexts from the verified free-precompute journals instead of recomputing retrieval.

        Without them, even B's paid stage takes about 12 days in one process. **Pending approval;** to be implemented tests-first, with a check that the outputs are identical.

        **Update (14 Nov, owner approved both as runtime optimizations):**
        - **Fix 1: ✅ implemented and verified identical** (700 dev rows, 0 differing; 7 + 1 tests). With it, B's paid process takes ≈ 4.6–5.8 days; current code takes 14.4–15.6.
        - **Fix 2: ⛔ stopped.** Real "contradict" conflict replies add a "contested" mark to prompts, so the placeholder precompute cannot reproduce them exactly.
          - 🔍 **Decide:** the two-phase exact alternative (report §4b): a tiny paid conflict pass, then a free replay precompute, then the paid stage reads it.
        - 🔍 **Decide:** fix `PYTHONHASHSEED` for all v2 runs. RandEC's sampling depends on it across processes; this is pre-existing.
        **Update (15 Nov, owner approved the three-step Fix 2 and PYTHONHASHSEED):**
        - **Fix 2: ✅ implemented (three steps, `two_phase.py`), exact.** Identical journals, requests and spend in the tests. On real dev G-D00: 2,800 rows identical with real replies, and again with every reply "contradict" (119 contested contexts).
        - **PYTHONHASHSEED = 0: ✅** enforced by both v2 scripts. It changes no frozen output (seeds 0/1/2 identical; equal to the step-1.12 journals).
        - **Runtime B:** paid process 25–54 h, plus ≈ 96 CPU-h of free parallel precompute.
        - At the paid stage, step 1 (conflict checks only, v2_stage3) needs its approval like every paid stage.
      - **Uninformative (decision 35):** implement the "no-signal control" label and exclusion from the worst case.
- ✅ **2.2** Freeze script v2 (15 Nov): `src/ams/research/protocol_v2/freeze.py`, `scripts/freeze_protocol_v2.py prepare | verify`; manifest **prepared, not active**: `research_data/protocol_v2_freeze_optionB_20261115/protocol_v2_optionB.json`, digest `1845a84d73b1961201dd63884e43807f363ed89b08a84662b2d1fb43922e4903`. The paid commands now require `--freeze` (verify + approval names the digest + frozen dataset only). v1 archive verified (224 files); pre-v2 snapshot: 0 changed, 3 missing = the approved 15 Nov cleanup; v4 bundle = the v1-freeze hashes; all 24 v4 and 8 dev Stage-1 stores = the 13 Nov fingerprints; all 35 checkpointed prompts unchanged.
- ✅ **2.3** 🔒 **Owner approved the freeze** and the paid caps (15 Nov; `owner_approval_optionB.json`). Execution: `research_data/protocol_v2_optionB_run_v1/`. Originally: draft `research_data/protocol_v2_freeze_optionB_20261115/owner_approval_optionB.DRAFT.json` (unsigned; the gates refuse it). Commands and order: `research_data/protocol_v2_freeze_optionB_20261115/RUNBOOK.md`.

### Phase 3: Create the held-out data

> **Option B (decision 36): not part of the current evaluation.** Phase 3 is the future v5 plan, kept unchanged; it needs its own freeze before any generation.

- ⬜ **3.1** 🔒💰 Generate attacks (~~≈ 960~~ **1,440 specs**, rev 4) and benign documents (~~≈ 1,610~~ **1,957 specs**, rev 4) with Claude Sonnet.
- ⬜ **3.2** Local exclusions E1–E4 (free); funnel report.
- ⬜ **3.3** 🔒💰 Inclusion I1 (original SAFE-Mem write path, GPT-4o-mini).
- ⬜ **3.4** Build the 96 groups + generation-check subset; untouched check; hashes recorded.
- ⬜ **3.5** 🔒💰 Stage 1 memory building for the 96 groups (+ replication stores already exist).
- ⬜ **3.6** Stage 2 input validation (free; inputs only, never outcomes).

### Phase 4: Evaluation (each a separate approval)

> **Option B mapping (decision 36; RUNBOOK):** free precompute + contexts on v4 (= 4.1) → 🔒💰 **P-B1** conflict pass → 🔒💰 **P-B2** GPT-4o-mini, all 62 cells × 16 methods on v4 (= 4.2 + 4.3 + 4.4) → 🔒💰 **P-B3** Claude Haiku, 8 cells × 11 methods (= 4.5) → free analysis once (= 5.1, `--evidence replication`).

- 🔄 **4.1** Free parallel retrieval precompute. *(Option B: precompute ✅ 24/24; P-B1 ✅ $0.00095; contexts ✅ 24/24; P-B2 running since 16 Nov.)*
- ⬜ **4.2** 🔒💰 Internal methods (original SAFE-Mem, R, C, M, S, SL, S2-ID, S2-BS) × all conditions: answers + judge.
- ⬜ **4.3** 🔒💰 Published methods (MemLineage classifier, A-MemGuard, LLM sanitiser, RandEC) + their answers; "+R" variants.
- ⬜ **4.4** 🔒💰 Replication on the old v4 test split.
- ⬜ **4.5** 🔒💰 Second backbone (Claude Haiku), Table 1 + hypothesis conditions.

### Phase 5: Analysis (free; run **once** with frozen code)

- ⬜ **5.1** Tables 1–8 + figures; H1–H6 decisions (✓/✗, whatever the outcome).
- ⬜ **5.2** Multi-way cluster sensitivity analysis; covariates (benign source, domain).
- ⬜ **5.3** Results report + README + RESEARCH_OVERVIEW update (old tables kept separate).

### Phase 6: Validation and appendix

- ⬜ **6.1** Human judge validation (needs 0.4): 300 cases, κ, judge precision/recall.
- ⬜ **6.2** 🔒💰 Ablations on dev.
- ⬜ **6.3** Appendix tables: S2-BS, "+R", boundary verification, judge ASR, cost/runtime, locked test v1, dev.

### Phase 7: Optional strengthening (owner decision needed)

- ⏸ **7.1** Second independent benchmark (e.g. MINJA / AgentPoison in `third_party/`): free feasibility check first.
- ⏸ **7.2** Formal proposition on the propagation-granularity trade-off ("every scope has a matching evasion").

### Phase 8: Paper writing (can start in parallel with Phase 1)

- ⬜ **8.1** Outline in the ICML template.
- ⬜ **8.2** Related work (SAFE-Mem, MemLineage, A-MemGuard, reputation/trust systems, memory poisoning).
- ⬜ **8.3** Method section (S, SL, S2-ID; pseudo-code).
- ⬜ **8.4** Threat model and setup.
- ⬜ **8.5** Results (Tables 1–8, figures).
- ⬜ **8.6** Limitations, ethics, reproducibility statement.
- ⬜ **8.7** Appendix.
- ⬜ **8.8** Reproducible code and data release package.

---

## 4. How to resume in a new session

1. Read this file, then `README.md` §10 (newest entries), then `reports/PROTOCOL_V2_DRAFT_20261113.md`.
2. Continue with the first ⬜ step whose prerequisites are ✅. **Stop at every 🔒.**
3. Integrity checks before any paid step:
   - `scripts/archive_locked_protocol.py verify --protocol research_data/workload_freeze_v4_20261108/locked_protocol_v1.json`
   - `scripts/archive_snapshot.py verify --out research_data/archive_pre_protocol_v2_20261113` (expected since 15 Nov: 0 changed, 3 missing = the approved cleanup)
   - `scripts/freeze_protocol_v2.py verify --protocol research_data/protocol_v2_freeze_optionB_20261115/protocol_v2_optionB.json`
4. Environment: `export VIRTUAL_ENV=` then `uv run …`. Long CPU jobs: run in parallel foreground shards (background jobs were about 10× slower on this Mac). Paid stages: one process (single-writer session), under `caffeinate`.

## 5. Budget log

| Item | USD |
|---|---:|
| All research spend up to 13 Nov 2026 | 3.3941325 |
| Unresolved holds (accepted) | 0.01974 (old session) + 0.0198144 (session v2) |
| Current session | `research_data/controlled_workload_session_v3_20261112` (used $0.00517845) |
| Remaining allowance (of $30) | ≈ 26.57 |
| Option B run: P-B1 (15 Nov 2026) | $0.0009528 (`v2_stage3`, 60 conflict checks); remaining ≈ 26.57 |
| Option B run: P-B2 first run, halted (16 Nov 2026) | $0.9486 settled (6/24 groups + G-T06 partial) + $0.0193 held (unknown billing, actual ≈ $0.0002); kept as record |
| Option B run: P-B1 re-sent into `sessions_rerun1` (17 Nov 2026) | $0.0009528; remaining ≈ 25.62 |
| Option B run: P-B2 rerun 1, halted (17 Nov 2026) | $1.2080 settled (8/24 groups + G-T08 partial) + $0.0193 held; kept as record; remaining ≈ 24.41 |
| Option B run: P-B1 re-sent into sessions_rerun2 + P-B2 rerun 2, halted (17 Nov 2026) | $0.0009528 + $0.9097 settled (6/24 groups + G-T06 partial) + $0.0193 held; kept as record; remaining ≈ 23.48 |
| Option B run: P-B1 re-sent into sessions_rerun3 (17 Nov 2026) | $0.0009528; remaining ≈ 23.48 before rerun 3 |
| Option B run: P-B2 rerun 3, halted at 23/24 + G-T23 partial (19 Nov 2026) | $3.2159 settled + $0.0193 held; remaining ≈ 20.24 |
| Option B run: P-B2 rerun 3 **complete** (20 Nov 2026, 01:17 local) | $3.2507 total (stage3 $2.1105, A-MemGuard $1.0114, sanitiser $0.1160, MemLineage $0.0127); remaining ≈ 20.22 |
| **Option B (decision 36), proposed for owner approval** | P-B1 ≈ $0.001; P-B2 + P-B3 $4.19–10.82 in total. Caps (≈ 2× high, fixed per purpose at first use): v2_stage3 $10.00, A-MemGuard $4.50, sanitiser $0.60, MemLineage $0.05, Haiku $8.00; **sum $23.15**. Ablations later, separately ($0.26–1.05) |
| Protocol v2 total estimate (step 1.12; low–high, sum of caps) | A full plan $43.52–81.65 (caps $108.60) · **B MPBench only $4.44–11.86 (caps $16.40)** · C MPBench + 32 generated $17.08–31.87 (caps $42.80). Scope: owner decision at 2.1 |

## 6. Progress log (newest first)

- **16 Nov 2026:** free contexts done (24/24, fingerprints = precompute; Mac slept on battery overnight, paused only); integrity re-verified; 💰 **P-B2 started** 09:25 UTC (detached; caps confirmed in ledgers; a first attempt with a too-wide glob was stopped before any paid call and fixed). Next: P-B2 runs 25–54 h, then 💰 P-B3.
- **16 Nov 2026 (13:11 UTC):** P-B2 stopped after 4/24 groups ($0.61): `database is locked`, caused by my read-locking progress check; journal consistent; status check made lock-free; P-B2 restarted (resume, $0 replays). Pace ≈ 48 min and ≈ $0.125 per group.
- **16 Nov 2026 (14:50 UTC):** P-B2 replay done at $0 extra; 5/24 groups complete (152,320 rows each), $0.75 spent in total; on AC power. The status check now counts rows on a copy-on-write clone, because a lock-free scan of the live journal reads torn pages during inserts (the clone passes `quick_check`).
- **16 Nov 2026 (19:06 UTC):** ⛔ P-B2 halted at 6/24 groups (+ G-T06 partial): the Mac slept on battery mid-call, the call ended with unknown billing ($0.01932 held), and the guard blocked `v2_stage3` as designed. $0.9486 settled. Journal intact. **Owner decision needed** on how to continue (README §10).
- **17 Nov 2026 (~00:30 local):** owner chose option 1. Credits checked (key $166 left, account $405); P-B1 re-sent into fresh `sessions_rerun1/` ($0.00095; 60/60 replies identical, so the contexts stay valid); integrity OK. P-B2 rerun 1 (→ `gpt_rerun1/`) starts automatically on AC power. Projection ≈ $3.4.
- **17 Nov 2026 (00:46 local):** 💰 P-B2 rerun 1 started on AC power; healthy after 10 min ($0.03, 0 errors).
- **17 Nov 2026 (07:00 local):** P-B2 rerun 7/24 groups, $0.98. Disk 3.0 GB → archived `precompute/` and halted `gpt/` (SHA-256 verified, owner-approved) → 4.7 GB. Mac on battery since 01:41 (charger not charging).
- **17 Nov 2026 (07:38 local):** P-B2 rerun paused safely (no call in flight) so the owner can travel with the lid closed; resume with `scripts/resume_pb2.sh` once online. $1.11 spent.
- **17 Nov 2026 (09:34 local):** ⛔ P-B2 rerun 1 halted at 8/24 (+ G-T08 partial): one call hit `APIConnectionError` (network drop on university Wi-Fi), unknown billing, guard blocked stage3. $1.21 settled. Owner decision needed.
- **17 Nov 2026 (~10:00 local):** owner chose rerun 2 at home. Prepared (paths, integrity, conflict requests restored from archive); starts with `scripts/start_pb2_rerun2.sh` when the owner is home on AC.
- **17 Nov 2026 (10:38 local):** 💰 P-B2 rerun 2 started at home on AC (P-B1 $0.00095, 60/60 identical).
- **17 Nov 2026 (16:57 local):** ⛔ P-B2 rerun 2 halted at 6/24 (+ G-T06 partial): `APIConnectionError` 17 ms after sending (short home network drop, Mac on AC and awake), unknown billing, guard blocked stage3. $0.91 settled. Owner decision needed (third single-failure halt).
- **17 Nov 2026 (17:49 local):** owner chose the retry fix. Freeze revision 6 (transport only; never-connected attempts retried ≤10×30 s; tests first, 831 passed; protocol §15). 💰 P-B2 rerun 3 started at home on AC (P-B1 $0.00095, 60/60 identical).
- **19 Nov 2026 (02:01 local):** ⛔ P-B2 rerun 3 halted at 23/24 + G-T23 112,074 rows: one judge call timed out after sending (`APITimeoutError`), unknown billing, guard blocked stage3. $3.22 settled + $0.0193 held. Owner decision needed.
- **19 Nov 2026 (12:03 local):** owner chose the recovery fix. Freeze revision 7 (reviewed unknown transport failures booked at full worst case, failed row kept in `superseded_dispatches`, same request re-sent; tests first, 833 passed; protocol §15). Review booked $0.019272; 💰 P-B2 rerun 3 resumed in the same session to finish G-T23.
- **19 Nov 2026 (17:42 local):** owner wrote "stop". P-B2 rerun 3 stopped safely (ledgers clean, journal ok) during the $0 replay, after 5 h 38 min; no new paid call since the resume. Replay was slow (8 GB RAM, heavy swap). Spend unchanged $3.2352. Continue with `start_resume_pb2.sh` (replay restarts from the beginning).
- **19 Nov 2026 (19:17 local):** owner wrote "start"; resumed in the same session.
- **20 Nov 2026 (01:17 local):** ✅ **P-B2 complete.** 24/24 groups × 152,320 = 3,655,680 rows (unique keys, journal quick_check ok, 0 rows without answer/outcome); `gpt_rerun3/paid_summary.json`. Replay ≈ 4.8 h at $0, then 139 new stage3 calls ($0.0155) finished G-T23. Total P-B2 spend $3.2507; ledgers clean (no open/unknown, held 0, not blocked); 0 connect retries; no new errors. Integrity after P-B2 as expected (rev7 freeze verified 320 files; 224 verified; differs changed 0 missing 3; `logs/integrity_after_PB2_rerun3.txt`). Stopped here as the owner asked; **P-B3 waits for the owner.**
- **20 Nov 2026 (~03:10 local):** owner chose **"Analyse now"**: frozen analysis on the complete GPT-4o-mini journal before P-B3 → `analysis_gpt_early/` (free). Deviation recorded in `logs/deviation_early_gpt_analysis.md` (protocol §15 entry after P-B3, because the protocol text is in the rev7 freeze). Result (09:08, ≈ 6 h on 8 GB): 3,655,680 rows, 24 groups, 16 methods; `tables.md`, `appendix.md`, `per_cell.md`, 3 figures. Table 8 (replication, not confirmatory): H1 vs C ✓, H1 vs M ✓, H2 ✓, H3 ✓, H4 ✓, H5 ✓; **H6 vs C ✗, H6 vs M ✗** (innocent utility under 1% false-positive audits: S = C = M = 92). Localized: S target ASR 0 with utility 91 (original SAFE-Mem 63/91; best published MemLineage 44/91; C, M 0/66). Negatives: S fails under audit-aware batch shift (target ASR 66 vs 0 for C, M), Sybil k≥4 and laundering r=1 (64–66, no better than original); worst case S 66 vs MemLineage 44 (S2-ID 47); framing harms innocents (S 53 vs 92 original); distributed utility 66 (same as C, M). Label note: Table 7 prints "not run (needs fresh v5 data)" also for the pending Claude Haiku row (generic frozen text; Haiku is pending P-B3, not v5).
- **21 Nov 2026:** **Cleanup (21 Nov, owner: "most unnecessary ones delete, less necessary compact"):** deleted `.venv-minja/` (909 MB, package list saved), 4 dry-run/mock folders (≈ 20 MB, SHA-256 recorded, mostly in git), `README_BEFORE_RESEARCH_20261101.md` (in git) and caches; compacted the halted P-B2 attempts (sessions, rerun1, rerun2 ledgers, `gpt_rerun2`, old prompt mirrors and conflict replies, aborted precompute, `archive_20261119`) from 1.2 GB to a verified 297 MB archive `archive_20261121/halted_attempts_20261121.tar.gz`. Not touched: current run, frozen inputs, first-phase folders read by code/tests, paid caches. After: rev7 freeze verified (320), locked v1 verified (224), snapshot changed 0 / missing 25 (new expected value, RUNBOOK §1 updated), ledgers clean, **833 tests passed**. Freed ≈ 1.9 GiB (repo 19.2 → 17.3 GiB). Record: `reports/CLEANUP_AUDIT_20261121.md`.
- **21 Nov 2026:** **Pushed to GitHub (21 Nov, owner: "push all necessary things with result"):** commit `255fad7` on `LalaHuseynova/sdp`, branch `protocol-v2-option-b-freeze` (code rev6/rev7 + tests, freeze manifests and approvals, protocol, RUNBOOK, README, plan, P-B2 scripts/requests/replies/summary, early GPT-4o-mini analysis, cleanup records). Kept local only (too big for GitHub or ignored): `gpt_rerun3/queries.sqlite` (3.9 GB), `contexts/` (2.8 GB), `sessions_rerun3/*.sqlite`, the four `.tar.gz` archives (250-360 MB each), `provisional_extension_results_v1_20261101/queries.sqlite.tar.gz` (210 MB), `logs/` (except the deviation note and integrity record), `CLAUDE_MEMORY_TRANSFER.md` (outdated; update before a move).
- **21 Nov 2026:** **Merged into `main` (21 Nov, 15:30 local; owner did not see the results on the GitHub front page):** PR #1 had been merged before commits `255fad7`/`a022914`, so `main` lacked the P-B2 results. Merged `protocol-v2-option-b-freeze` into `sdp/main` (no conflicts; kept the owner's `047d085` method figure) → merge `4466227`, pushed. No large files, no secrets added.
- **15 Nov 2026 (later):** free precompute done (24/24 groups, 66,640 rows each, 60 conflict requests); integrity re-verified; 💰 **P-B1 done, $0.0009528** (60 checks, `v2_stage3`); free contexts started (4 shards). Next: 💰 P-B2.
- **15 Nov 2026:** owner approved option B, the freeze and the caps; option B run started (free precompute, 6 shards). Next: P-B1 conflict pass.

- **15 Nov 2026:** Phase 2 free work done (steps 2.1, 2.2; 2.3 waits for the owner):
  - option B protocol, revision 5 (`reports/PROTOCOL_V2_OPTION_B_20261115.md`): every pending decision resolved and documented (§12), replication labelling, power at N = 24 (H2/H4/H6 underpowered, stated);
  - code, tests first: decision 35 (registry v2), option-B renderers (analysis v2), freeze module + `--freeze` gate in every paid command, prompt mirror for old stores, Haiku paid-run fix (pipeline v2);
  - freeze manifest prepared (not active), digest `1845a84d73b1961201dd63884e43807f363ed89b08a84662b2d1fb43922e4903`; integrity checks all pass;
  - draft approval + runbook prepared; full suite 827 passed (810 before + 17 new), 58 subtests.

  Next: 🔒 owner approves the freeze and the caps; then the RUNBOOK, starting with the free precompute.

- **15 Nov 2026:** table-format preview for owner approval (`reports/TABLE_PREVIEW_V2_20261115.md`):
  - option-B labelling proposed: reused v4 split, replication, not confirmatory;
  - Table 7 fresh rows need v5;
  - A13 proposed (Haiku, all 11 methods).

  Next: owner approval.
- **15 Nov 2026:** cleanup tiers 1 + 2 executed (owner-approved):
  - 3.05 GiB freed;
  - the 2 SQLite journals archived with SHA-256-verified restores (`ARCHIVED.md`);
  - protected data untouched.

  Next: step 2.1.
- **15 Nov 2026:** checkpoint and temporary-file audit (proposal only; nothing deleted):
  - tier 1 ≈ 1.0 GB, tier 2 archive ≈ 2.1 GB, tier 3 optional;
  - paid ledgers and caches, v4 data and previous results kept.

  Report: `reports/CLEANUP_AUDIT_20261115.md`. Next: owner approval.
- **15 Nov 2026:** step 1.12 runtime fixes, part 2 (owner-approved, free):
  - Fix 2 three-step implemented tests-first, exact (unit, guarded and real-dev checks; contested labels included);
  - PYTHONHASHSEED = 0 enforced, with no effect on frozen outputs;
  - B paid process ≈ 25–54 h;
  - 810 tests pass; not committed, not frozen.

  Next: the owner reviews the changes.
- **14 Nov 2026:** step 1.12 runtime fixes (owner-approved, free):
  - Fix 1 (RandEC cache) implemented, tests first; verified identical on 700 dev rows;
  - Fix 2 stopped: real conflict replies change prompt text, so exact equivalence fails; a two-phase alternative is proposed;
  - runtime formula corrected: B ≈ 4.6–5.8 days with Fix 1;
  - 793 tests pass; not committed.

  Next: owner decisions at 2.1.
- **14 Nov 2026:** step 1.12 done (dry-run cost and runtime estimate, free: measured on 4 dev groups; A $43.52–81.65, B MPBench only $4.44–11.86, C $17.08–31.87; only B fits ≈ $26.57; generation dominates A; paid stage needs 2 result-identical runtime fixes (pending approval); RandEC offline fix; flaky test fixed; decision 35 recorded; 17 tests). Next: owner decisions at step 2.1 (scope, ceilings, runtime fixes, all pending items).

- **14 Nov 2026:** step 1.11 done (judge validation kit: blind sheets, design-weighted metrics, adjudication, κ, correction; 11 tests; 767 pass; dev feasibility draw only, no annotation; NPV transportability and few-'ours'-hits flagged under 2.1). Next: step 1.12.

- **14 Nov 2026:** step 1.10 dev run verified (complete, row counts exact; withhold threshold sits on S's penalty boundary; source gate and τ inert in tested cells; pending decisions under 2.1). Next: step 1.11.

- **14 Nov 2026:** step 1.10 done (ablation runner, free and dev-only, scoped overrides, 11 tests; 756 pass; dev run launched, result to verify; pending decisions under 2.1). Next: step 1.11.

- **14 Nov 2026:** step 1.9 done (analysis code v2: metrics, Holm/IUT/gatekeeping, group and multi-way bootstrap, Tables 1–8 + appendix + figures; validated on dev; over-ceiling caps now rejected; 745 tests pass; no paid call). Next: step 1.10.

- **14 Nov 2026:** step 1.8 done (offline-tested evaluation pipeline for all 16 methods, per-purpose owner approval gates; 725 tests pass; nothing run, no paid call). Next: step 1.9.

- **14 Nov 2026:** step 1.7 done (condition registry: 62 cells / 272 runtime conditions, worst case 47 cells; 715 tests pass; scale flagged for 1.12). Next: step 1.8.

- **14 Nov 2026:** step 1.6 done (72 imperfect-audit conditions + late-audit runner support; 709 tests pass). Next: step 1.7.

- **14 Nov 2026:** step 1.5 done (workload v5 builder; protocol rev 4: generated `seed_a`, 963 unused MPBench benign, 1,440 attack / 1,957 benign specs; dry run on real pools valid; 701 tests pass).

- **14 Nov 2026:** step 1.4 done (exclusions/inclusion + funnel; E2 moved to the paid inclusion stage).
- **14 Nov 2026:** step 1.3 done (generation prompts, specs, E1 parsers).
- **14 Nov 2026:** step 1.2 done (Haiku backbone router; judge stays GPT-4o-mini).
- **14 Nov 2026:** step 1.1 done (approved-model allowlist + guarded v2 generation scope, 680 tests pass).
- **14 Nov 2026:** owner accepted all 34 defaults; plan.md created; step 0.3 (protocol rev 3) done.
- **13 Nov 2026:** steps 0.1, 0.2 done.
