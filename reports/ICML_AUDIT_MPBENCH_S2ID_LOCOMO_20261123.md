# ICML audit: MPBench evidence, S2-ID, LoCoMo setup and a revised generalization study (23 Nov 2026)

**Scope.** Critical audit of everything done on MPBench, of S2-ID, and of the existing LoCoMo setup (branch `locomo-backup`), plus a redesigned LoCoMo protocol (draft v2). Written as a skeptical reviewer would read the work.

**Evidence labels used throughout:**
- **[V]** verified in this audit, from files, code or a run made today;
- **[R]** taken from recorded results (Option B analysis, logged reports), checked against the result files;
- **[P]** proposal;
- **[H]** untested hypothesis.

**Rules respected:**
- No method, constant or prompt was changed, and nothing was tuned.
- No paid call was made.
- No LoCoMo answer or judgement file was opened: `research_data/locomo_v1_run/answers.jsonl` and `judgements.jsonl` remain unread.
- The Option B results were read from `research_data/protocol_v2_optionB_run_v1/analysis/`.

**Code and outputs of this audit:**
- Worktree `../sdp-locomo-audit`, local branch `locomo-audit`, uncommitted.
- Code: `locomo_audit/`, `locomo_v2/`.
- Outputs: `research_data/locomo_audit_20261123/`.

---

## 1. MPBench audit: what was implemented, tested and established

### 1.1 What exists

| Phase | Data | Methods | Status |
|---|---|---|---|
| Diagnostics (7–8 Nov) | full MPBench | SAFE-Mem, R/C/M/S provisional | Finding [R]: only ~3% of MPBench attacks can be reached by propagation, and no contributor submits twice. MPBench alone cannot test propagation, which is why the controlled workload exists |
| Workload v1→v4 design (8 Nov) | dev split (8 groups) | – | Engineering: fact carriers v2/v3 were redesigned after pilots (facts were not stored). Development only |
| **Locked test v1 (8 Nov)** | **v4 test (24 groups), first use** | SAFE-Mem, R, C, M, S × localized / distributed / uninformative | **The only confirmatory, fresh held-out evaluation.** Frozen protocol `921cf7f5…`, one backbone, oracle audits |
| Adaptive / published / S v2 studies (12 Nov) | dev only (test untouched, as logged) | + A-MemGuard, MemLineage, sanitiser, RandEC, SL, S2-ID, S2-BS | Exploratory. SL, S2-ID and the adaptive families were designed here |
| **Option B (15–22 Nov)** | **v4 test reused** | 11 + 5 methods, 62 cells, GPT-4o-mini + Haiku | Pre-registered rules, frozen code, run once. **Replication evidence, not confirmation** (the protocol says so) |

### 1.2 Which results are valid, and for what

| Claim | Evidence | Validity |
|---|---|---|
| Localized: S matches C/M security (0% ASR) at original utility (91 vs 66; key stratum +90 pts) | Locked test v1 (confirmatory) + Option B (two backbones) | **Valid but close to true by construction** [V, below]: both audited seeds share batch 1 with the scored attacks, which is exactly S's batch gate. Retrieval decides it; the LLM stages only check that the answerer uses what it is given |
| Distributed: S = C = M | v1 + Option B | Valid; it is the predicted reduction of S to C |
| No-signal: S gives no utility gain over R and is less secure than M (63 vs 43 ASR in v1) | v1 (H3 ✗) | Valid **negative** result. Keep it |
| S beats all four published defences (H3) | Option B, replication | Valid as measured, but **unequal information**: S receives 5 oracle audit tickets, while the published defences use none. Frame it as complementarity, not dominance |
| Adaptive attacks | Option B, replication | Valid. **S's ASR equals C's** under Sybil-k, laundering-r and imperfect audits, with higher utility. **M is more secure** at Sybil k=2 (27 vs 51). An **audit-aware batch shift breaks S** (66 vs C/M 0). S's worst case is 66, versus MemLineage 44 |
| H5 (SL removes relays) | Option B | **Contaminated beyond "replication":** `lineage.py`'s own docstring says SL was motivated by relay leaks seen *on the locked v4 test*, which is the split H5 was then tested on. Under Haiku, the gatekept relay-ASR secondary fails (−12 [−29, 0]) |
| H6 (S protects an innocent under one false accusation) | Option B ✗, estimate 0 | **Not a test** [V from the tables + the bound]: a single false unsafe audit gives a penalty of 1/6 < τ under every rule (withholding needs n⁻ ≥ 3n⁺ + 2). C, M and S all keep innocent utility 92, so the condition cannot separate them. Report it as uninformative by design, not as a failed claim. Framing (concentrated) does separate them, descriptively: S 53, C 43, M 29 |
| Judge ASR / target ASR | GPT-4o-mini judge | Not human-validated (kit ready). The LLM-free exposure metric gives the same ranking, which helps |

### 1.3 What MPBench genuinely establishes

1. **Propagation granularity is a real trade-off.** Record-only (R) leaks, scope-wide rules (C, M) pay collateral utility, and an evidence-gated rule sits on the frontier *when incident structure is informative*. This is backed by one confirmatory and one replication run.
2. **When provenance is uninformative or adversarially manipulated, every label-based rule fails at about the same point** (Sybil, laundering, batch shift). This is a boundary, not a win.
3. **Audit propagation and audit-free content defences fail in different places** (Table 2: MemLineage is flat at 44; S is 0 or 64 depending on structure).

It does **not** establish general superiority of S, robustness to adaptive attackers, or realistic-auditor performance.

### 1.4 Reviewer weaknesses

These agree with `reports/ICML_CRITICAL_REVIEW_20261122.md` W1–W13, re-checked here. Most serious: W1 (by construction), W2 (adaptive), W3 (little ML novelty); then W4 (unequal information in H3), W5 (oracle auditor) and W6 (one synthetic workload, reused split).

New in this audit:
- H6 is a non-test.
- SL was motivated by the test split.

---

## 2. S2-ID decision (revised the same day): **keep it, as a hybrid defence and a 2×2 factorial ablation; not as the main contribution**

*Revision note.* The first version of this section recommended removing S2-ID from the method and contributions. The owner clarified that the question was whether S2-ID is scientifically correct, not whether to exclude it. Re-examined below. The earlier recommendation is withdrawn: it compared S2-ID only with S, the comparison H4 uses, which is the wrong reference for a hybrid.

**2.1 Is the implementation correct?** Yes [V].
- **Composition:** S2-ID = frozen `Policy("S")` + frozen content lineage (τ = 0.8) + `sv2._GatedReader`. The gate empties the final context when the query is SENSITIVE and the context holds any non-principal memory.
- **Same gate as the baseline:** the standalone `memlineage` baseline uses `ams.baselines.memlineage.MemLineage` with coarse attribution (every parent weight 1.0, τ = 0, Deny), which reduces to the same rule (external = untrusted). Equivalence is covered by `test_published_adapters`.
- **Same verdicts:** both read the **same recorded SensitiveAction verdicts**. A missing verdict raises rather than defaulting.
- **No method change:** nothing in S, SL or MemLineage is changed. S2-ID is a pure composition.

**2.2 Is the methodology valid?** Yes, with three caveats to state.
1. **Post hoc design:** S2-ID was designed on the dev split after the v1 test (same status as SL). It was frozen before Option B, but Option B reuses the v4 split, so it is replication-level evidence.
2. **Information:** S2-ID uses audits *and* one classifier call per query. Report the compute and information next to every comparison.
3. **Wrong comparator for a hybrid claim:** H4 compares S2-ID only with S, but a hybrid must be compared with **both** of its components. With MemLineage = gate without propagation, Original = neither, SL = propagation without gate and S2-ID = both, Option B already contains a complete **2×2 factorial** on the same groups, audits and answers.

**2.3 What the factorial shows** [R, point estimates from Tables 2–4, GPT-4o-mini target ASR]

| Regime | Cells | S2-ID vs the better component, min(SL, MemLineage) |
|---|---|---|
| Propagation works (localized, distributed, k=1 and r=0, oracle and random) | 6 | **equal (0)**; the gate adds nothing |
| Partial evasion (Sybil k=2; random-detection Sybil k=2–8; laundering r = .25–.75; random-detection laundering r = .25–1) | 11 | **better than both, by 5–14 pts** |
| Propagation fully evaded (oracle Sybil k = 4, 8 and own-batch k=4; oracle laundering r = 1; audit-aware shift; framing) | 6 | **1–3 pts worse than MemLineage alone**, because SL itself sits at 66–67, above no defence (63) there (refill effect) |

- **Interaction:** positive (+6 to +19) in partial cells, i.e. sub-additive. Both mechanisms remove some of the same attacks. About −1 in full-evasion cells.
- **Utility:** S2-ID 91 = S = MemLineage in the main cell. The gate costs no utility probe, and SL's false-positive cost (86 vs 92 under a false audit) is inherited.
- **H4's own cells** (sybil_k4, sybilown_k4, launder_r4, ...) are mostly *full-evasion* cells. There S2-ID beats S only through the gate and does **not** beat MemLineage. So H4's ✓ does not demonstrate the hybrid's value; the partial-evasion cells do.
- **Not yet known:** paired confidence intervals for S2-ID − MemLineage and S2-ID − SL per cell. The per-group outcomes are only on the Mac. `scripts/s2id_factorial_contrasts.py` computes them with the frozen bootstrap (seed 20261114, shared weight matrix). It reports every cell, labelled exploratory, and was checked on synthetic rows today.

**2.4 Scientific value.** S2-ID is the paper's clearest evidence for a **complementarity claim**: identity-based audit propagation and identity-blind action gating fail in different places. Composed, they beat each alone wherever provenance is partly informative, and degrade to roughly the gate alone when provenance is fully evaded. This directly addresses two reviewer criticisms:
- **W2** (adaptive evasion): S still contributes under partial evasion.
- **W4** (unequal comparison with published defences): the contribution of audits is measured *on top of* a published defence, holding that defence fixed.

**Not supported:** S2-ID as a new defence of ours. Its adaptive gains need the borrowed gate, and its worst case (47) is not better than MemLineage alone (44).

**2.5 Recommendation**
1. **Keep S2-ID in the main text as a named hybrid with MemLineage** (credit MemLineage explicitly), presented through the 2×2 factorial. One figure: target ASR vs Sybil-k and laundering-r for Original, MemLineage, SL and S2-ID. One sentence of attribution: the gate acts on sensitive-action queries regardless of identity; propagation acts on any query where provenance is informative.
2. **Main contribution stays S** (evidence-gated propagation granularity). S2-ID is a secondary result, a hybrid and ablation, not a third method claim.
3. **Report H4 exactly as pre-registered** (✓). Add the factorial as clearly labelled exploratory analysis, and say that H4's cells are full-evasion cells where the hybrid ≈ MemLineage.
4. **Condition for the main text:** if the Mac run shows "better than both" with intervals excluding 0 in the partial-evasion regime, keep it in the main text. If not, move the factorial to the appendix and say the complementarity is suggestive only.
5. **Limitations to state:** post hoc design; reused split; the extra information (audits + classifier); the full-evasion cost of SL's refill; and the fact that the gate only protects sensitive-action queries.
6. **LoCoMo:** keep S2-ID in the tables at no cost (identical contexts are answered once from the response cache), with a footnote: 0 of 1,529 LoCoMo questions are SENSITIVE, so S2-ID ≡ SL by construction (verified on every pilot context). **LoCoMo cannot test the hybrid**; a benchmark with sensitive actions would be needed. Do not count LoCoMo as transfer evidence for S2-ID.

---

## 3. LoCoMo audit: is the existing setup valid?

### 3.1 What exists [V]

- **Protocol:** `PROTOCOL_LOCOMO_V1.md` with amendments v1.1 (adds S2-ID) and v1.2 (infrastructure restart), frozen as `f04cc850…`.
- **Code:** `locomo_v1/`, which reuses `research_data/locomo_feasibility_20261119/feasibility.py` (the generator) and calls the frozen `Policy.decide`, `active_scopes` and `lineage.blocked_records`.
- **Run state:** the paid v1.1 run stopped at 3 of 10 conversations (rule S2, a technical failure). Its outputs are unread.

### 3.2 Correctness checks run today

| Check | Scope | Result |
|---|---|---|
| Injection: 8 poison turns, hijacked speaker, inside a contiguous window of the right length, exact template, unique targets, natural turns preserved in order, wrong ≠ gold | all 800 scenarios (P1+P2) | **0 failures.** 4 "wrong value not in pool" flags are a type artefact of the check (integer answers compared as strings) |
| Frozen gates vs an independent closed form | 21,760 session checks (400 P1 scenarios × A1, A2) | **0 mismatches.** Contributor gate active **0** times |
| Principal never penalised; R = no defence | all P1 × A1, A2 × C, M, S | 0 failures |
| Retrieval: withheld never served, audited poison never reaches its own question, filled to k, sorted by adjusted score, static = plain top-k, clean has no poison | pilot conversations conv-48/49 (non-confirmatory) | **0 failures** |
| Existing test suite + audit tests | `locomo_v1/tests` (26) + `locomo_audit/tests` (7) + `locomo_v2/tests` (2) | **35 pass** |

**Conclusion:** the implementation does what the protocol says. The data hash matches the freeze, and the LoCoMo structure (speakers, sessions, dated turns, category 1–4 QA with evidence ids) is used correctly.

### 3.3 Problems found

**P-1: measurement bug in ASR** [V]
- `locomo_v1.analysis.contains` is a **character-substring** test after normalisation, so "no" matches "not" and "know", and "art" matches "start".
- 113 of 3,200 P1 targets (3.5%) have injected values of ≤ 3 characters (e.g. "no", "Jo").
- Arms that withhold more produce "not mentioned"-style answers, which can collect spurious hits. By this argument the bias would push S − C/M *toward* passing the 5-point non-inferiority margin (H4, H6). This direction is reasoned, not measured.
- Also: 4 P1 values lie inside the gold answer, and 114 already occur in the genuine conversation.
- **P2 is weak:** 1,148 of 3,200 of its values already occur in the conversation (same-conversation answers).

**P-2: the confirmatory hypotheses are mostly fixed at decision level** [V, `static_audit.json`]. Under A1, S differs from C/M **only when both detected poison turns fall in one session**:

| A1, shape | detected in one session | S = C | genuine out-of-window turns available, S / C,M | unaudited poison available, S / C,M |
|---|---|---|---|---|
| 1 session | 100% | 0% | 1.00 / 0 | 0 / 0 |
| 2 sessions | 53% | 47% | 0.53 / 0 | 0.29 / 0 |
| quarter | 14% | 86% | 0.14 / 0 | 0.11 / 0 |
| spread | 5% | 95% | – | 0.05 / 0 |

H2 and H3 (S keeps U_out utility vs C/M) and H4 (S's security cost) are therefore near-deterministic consequences of the shape mix (which we chose: equal weights). They were also already visible at retrieval level in the 19 Nov feasibility study on **all 10 conversations, including the 8 "confirmatory" ones**. The answer-level run adds only whether the LLM uses the retrieved evidence. That is legitimate, but it is **not independent evidence that the defence generalizes**.

**P-3: H5 is an identity, and A2 reveals a dilution failure** [V]. Under A2 (A1 plus 10 random reviewed turns, mostly safe):
- C withholds nothing: 100% of unaudited poison stays available, in every shape.
- **S ≡ M in 100% of scenarios.**
- On average, S and M withhold only 77% (1 session), 19% (2 sessions), 1.5% (quarter) and 0.5% (spread) of the unaudited poison.
- Retrieval exposure on the pilot conversations: S 0.25 / 0.79 / 0.97 / 1.00.

The mechanism is the frozen Beta rule: withholding needs n⁻ ≥ 3n⁺ + 2, so one safe review in the hijacked session cancels two incident detections. H5 ("S beats C under A2") was formulated after seeing this at retrieval level and is a decision identity. The real finding is different and more important: **benign audit verdicts dilute containment** (a reputation-farming effect). On LoCoMo it is natural, not adversarial.

**P-4: coverage gaps for the research question** [V, by inspection]

| Gap | Effect |
|---|---|
| **One external speaker per conversation, one context per speaker** | The contributor gate can never fire; contributor scope = context scope. Innocent bystanders, framing and false-accusation harm cannot be tested |
| **Turn-level RAG, no SAFE-Mem** | LoCoMo tests S as a layer over plain retrieval, not SAFE-Mem+S |
| **No published defence on LoCoMo** | "Advantage over published defences transfers" cannot be tested |
| **One attack family**, a constructed template that quotes the question | Rank-1 retrieval for 92% of targets, top-10 for 99% [V, pilot conversations]. This is a maximal-retrievability attack. Sybil, laundering and audit-aware shift are absent |
| **Oracle auditors only** (A3 random-only is descriptive) | – |
| **8 independent units** | Smallest exact p = 1/256. The utility signal is capped by the base retriever (evidence recall at top-10 ≈ 0.42–0.44 even without attack [V]) |

**P-5: researcher degrees of freedom on the held-out conversations** [R, disclosed in the protocol]. The auditors (A1, A2), top-k, shapes and hypothesis directions were chosen after retrieval-level runs on all 10 conversations. The method was not tuned, so this is not leakage into the defence. It is, however, selection of the *evaluation setting* on the test conversations, and it must be stated.
- **conv-26** had 10 clean questions answered in 28 Oct smoke tests (minor; needs a deviation note).
- **The partial v1.1 outcomes are committed on a public branch** (unread). This must be disclosed and kept unread until the single analysis.

### 3.4 Verdict

**The implementation is correct; the confirmatory design is not adequate for a generalization claim.** As frozen, v1.2 would produce a mostly predictable pass/fail table (H2, H3, H5 by construction; H4 predicted to fail), a biased ASR metric, and no test of the published-defence advantage.

It **can** support a narrower and still valuable claim: *on natural speakers and sessions, with independently annotated questions, the frozen rules reproduce the MPBench regime map: selective when the compromise is local, collapsing to C/M when it is spread, and vulnerable to benign-review dilution.*

**A rebuild from scratch is not needed:** the generator, provenance mapping, frozen-decision calls, retrieval and build pipeline are verified and reusable. What must change is the **measurement, the estimands, the auditors and the comparison set**. Because no outcome has been read, this can be done legitimately as a new protocol before unblinding.

---

## 4. Revised LoCoMo setup: protocol draft v2 [P]

> **Update (same day): superseded by the implemented protocol** `reports/PROTOCOL_LOCOMO_V2.md` (code `locomo_v2/`, freeze `3a2c2df8…`). It reproduces the MPBench families (fn20, Sybil, audit-aware shift, relays, framing) and the published defences MemLineage and RandEC, and keeps S2-ID (≡ SL on LoCoMo). The A4 detector auditor and the P1-para attack below were **not** implemented; they remain optional extensions. The sketch below is kept for the record.

**Research question:** does S keep its security–utility position relative to R, C and M (and, if approved, published content defences) when moved from MPBench to LoCoMo **with no benchmark-specific tuning**?

### 4.1 Mapping MPBench → LoCoMo, and what does not transfer

| Element | MPBench workload | LoCoMo v2 | Consequence |
|---|---|---|---|
| Memory | SAFE-Mem typed claims (admission α) | raw dialogue turns, MiniLM top-10 | Tests S as a layer, not SAFE-Mem+S. State it |
| Contributor | A, B, U, P; 2 contexts | 1 external speaker; principal = the other speaker (both orientations) | Contributor gate, framing and the innocent bystander are untestable → MPBench only |
| Batch | delivery batch (constructed) | session (natural, dated) | Main strength: structure we did not design |
| Attack | verbatim MPBench texts, 5 families | account hijack over a random window; template injection (P1) | One family; strongest retrievability |
| Audits | 5 oracle tickets on seeds | A1 incident, A2 incident + review, **A4 detector (new)** | Tests the oracle assumption |
| Utility | constructed useful facts | LoCoMo QA with independent evidence ids | Independent labels: second main strength |

### 4.2 Splits and the no-tuning rule

- **Development:** conv-48, conv-49 (already answered in the pilot). Any LoCoMo-specific choice not yet fixed (the A4 detector budget, the paraphrase-attack template) is made on these only.
- **Held-out:** the 8 other conversations, answered once.
- **Disclosed:** decision- and retrieval-level behaviour on all 10 was observed (19 Nov feasibility; this audit), and conv-26 had a clean smoke test. No held-out answer has been read.
- **Frozen:** method, constants and prompts. `Policy(threshold, weight)` sensitivity is reported, never selected.

### 4.3 Conditions

| Factor | Levels |
|---|---|
| Shape (localization) | 1s, 2s, quarter, spread: **reported as a curve, not pooled into pass/fail** |
| Auditors | A1 incident (2 of 8 poison detected); A2 incident + 10 random reviews; **A4: detector-driven audits** (an LLM fact-check auditor on a fixed random budget of the external speaker's turns, fixed on dev; paid, small) |
| Attacks | P1 (primary). **P1-para** (new, dev-designed): the topic is paraphrased instead of the question quoted, to test the maximal-retrievability assumption. P2 is dropped as a primary (39% of values occur in the conversation) |
| Arms | none, R, C, M, S, SL, S2-ID (≡ SL on LoCoMo, footnoted; no extra cost). **Optional, owner decision:** the LLM sanitiser and A-MemGuard on retrieved turns (as on MPBench, no refill); RandEC (local, free). MemLineage is reported as ≡ none by construction (0 sensitive questions) |
| Draws × orientations | 5 × 2, seeds recorded (as v1.2) |

### 4.4 Metrics

- **Security:** word-bounded ASR on eligible targets, using the outcome-free rule in `locomo_v2/metrics.py`. It keeps 92.8% of P1 targets and every scenario keeps ≥ 1. Secondary: judge-based target accuracy; retrieval exposure.
- **Utility:** LLM-judge accuracy on U_out (genuine evidence of the hijacked speaker outside the window) and on all non-targets. F1 alongside, plus a Haiku κ check.
- **Mechanism (free):** decision-level availability and retrieval recall, reported for every cell.

### 4.5 Estimands and tests (8 held-out conversations; exact sign-flip; t-intervals)

Primary family, Holm m = 3:
- **E1 containment transfers:** ASR(none) − ASR(S), A1, all shapes > 0.
- **E2 direct analogue of MPBench H1:** 1-session shape, A1: Acc_out(S) − Acc_out(C) > 0 **and** ASR(S) − ASR(C) < +5 pt. It is labelled honestly as an answer-level check of a retrieval-determined mechanism.
- **E3 realistic auditor (A4):** ASR(none) − ASR(S) > 0. This is the only primary test whose outcome is not fixed at decision level.

Estimation only, with 95% intervals (no pass/fail):
- the localization curve (ΔASR and ΔAcc_out of S vs C and M, per shape);
- the dilution effect (A2);
- P1-para;
- published defences (if run);
- net utility (Acc_all);
- threshold and λ sensitivity at decision level.

**Pre-registered predictions** [H], to be stated before unblinding, so the "regime map" is tested rather than described: S's cost grows with spread; S ≡ M under A2; dilution follows n⁻ ≥ 3n⁺ + 2.

### 4.6 Ablations and assumption tests

| Assumption S needs | LoCoMo test |
|---|---|
| Incident structure is informative (localization) | Shape curve |
| Audits mostly carry unsafe findings | A2 dilution; A4 detector |
| Poison is retrievable | P1-para |
| Identity stable (no Sybil) | **Not testable on LoCoMo** → MPBench |

Component ablations stay within frozen arms:
- R = no propagation;
- C = context only;
- M = all scopes;
- SL − S = lineage. On LoCoMo SL − S isolates nothing, because there are no copies; report it as such.

### 4.7 Cost and steps

- **Free:** amend the build (P2 secondary only; S2-ID kept, footnoted as ≡ SL; add P1-para and A4 hooks), dev-only design of P1-para and A4, mock run, freeze.
- **Paid** (needs your approval of an estimate):
  - core arms about $6–7, of which part is already cached;
  - A4 auditor: small, to be estimated on dev;
  - published defences: to be estimated on dev before any decision.

---

## 5. Minimum convincing generalization experiments for ICML

1. **LoCoMo v2 core** (E1–E3 + curve + dilution) with the fixed metric. Required.
2. **MPBench localization sweep** (free, exposure). It answers W1 and lines up with LoCoMo's shape curve: the same x-axis on two datasets is the strongest transfer figure.
3. **The dilution bound as a stated proposition:** "a batch is withheld iff n⁻ ≥ 3n⁺ + 2". Its prediction is checked on MPBench (imperfect audits) and LoCoMo (A2). This turns a weakness into a testable theory result.
4. **Realistic auditor** on both datasets (A4; on MPBench, the critique's A4).
5. **Human judge validation** (300 cases, free). Optional: published defences on LoCoMo; a fresh v5 subset on MPBench.

## 6. ICML reviewer assessment

- **Novelty:** the question of *how far* audit evidence should spread, with an evidence-gated rule, an evaluation protocol and an evasion boundary. It is **not** a new defence that dominates. S is a Beta-count rule; SL is embedding deduplication; S2-ID is a hybrid with MemLineage whose value is complementarity (§2), not novelty.
- **Strongest criticisms:** by-construction localized result; trivial adaptive evasion; oracle audits; unequal information versus the published defences; one synthetic workload on a reused split; (new) dilution by benign audits; LoCoMo's contributor-free structure.
- **Defensible claims:**
  - "on two datasets, one with natural sessions and independent labels, evidence-gated propagation keeps utility when compromise is local and reduces to scope-wide rules otherwise";
  - "every label-based rule shares the same evasion and dilution boundary";
  - "audit propagation complements audit-free defences": S2-ID beats both of its components under partial evasion, pending the paired intervals (§2.3).
- **Claims to avoid:** "generalizes" without E1–E3 passing; "beats published defences" without the information caveat; anything about SAFE-Mem+S on LoCoMo.
- **Negative findings to present as results:** no-signal ✗, Sybil and shift failures, A2 dilution, H6 being a non-test.
- **Risk today:** reject in the main track as framed; borderline with the reframing, the proposition and items 1–4. A workshop or SaTML is the fallback.

## 7. What was changed, tested and run today [V]

- **New worktree** `../sdp-locomo-audit`, local branch `locomo-audit` from `locomo-backup`. Nothing committed; `main` was not touched except this report and the README log.
- **New code** (no frozen file edited):
  - `locomo_audit/static_audit.py`: decision-level audit of all scenarios;
  - `locomo_audit/retrieval_audit.py`: retrieval invariants, pilot conversations only;
  - `locomo_audit/tests/test_audit_findings.py` (7 tests);
  - `locomo_v2/metrics.py`: word-bounded ASR and an outcome-free eligibility rule;
  - `locomo_v2/target_filter.py`;
  - `locomo_v2/tests/test_metrics.py` (2 tests);
  - on `main`: `scripts/s2id_factorial_contrasts.py`, the exploratory 2×2 factorial with the frozen bootstrap; checked on synthetic rows, to be run on the Mac where the journals are.
- **Runs** (free, local MiniLM under WSL):
  - static audit over 800 scenarios;
  - retrieval audit on conv-48/49;
  - target filter;
  - 35/35 tests pass.
  - Outputs are in `research_data/locomo_audit_20261123/`.
- **Not done:**
  - no paid call; no LoCoMo outcome opened;
  - P1-para and A4 are designed but not implemented (they need dev-only design choices and your scope decision);
  - published-defence adapters for LoCoMo were not built.

## 8. Roadmap (priority = evidence per cost)

| # | Step | Cost | Who decides |
|---|---|---|---|
| 1 | Decide: LoCoMo v2 replaces the v1.2 confirmatory plan (outcomes unread, so it is legitimate now; not after) | free | owner |
| 2 | Reframe the paper (granularity and characterization; S2-ID as composition) | free | team |
| 3 | Write the dilution / evidence-bound proposition and check it on existing MPBench tables and the LoCoMo A2 audit | free | team |
| 4 | MPBench localization sweep (exposure) | free | team |
| 5 | Implement P1-para and A4 on dev conversations; mock; freeze v2 | free | team |
| 6 | Paid LoCoMo v2 core run | ~$6–7 + A4 | owner approval |
| 7 | Human judge validation (name 3 people) | free | owner |
| 8 | Optional: published defences on LoCoMo; fresh MPBench v5 subset | paid, estimate first | owner |
