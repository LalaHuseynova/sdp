# Propagation feasibility across all 6,240 MPBench cases — 8 November 2026

**Offline analysis. No paid calls; no algorithm, data or earlier-result changes.**

**Verdict:** MPBench by itself **cannot support a properly powered comparison of S against R, C and M**.
- Only **102 of 3,241 attack cases (3.1%)** place their planted target in an external claim that Original SAFE-Mem would admit for the attack question.
- Only **23** of those are mechanically attributable today.
- MPBench has **no natural contributors**.
- Even using every reachable case in a single study, the expected baseline attack successes are at or below the protocol's 20-success floor.

We need a **controlled, MPBench-derived attack workload**.

Reproduce: `.venv/bin/python scripts/assess_propagation_feasibility.py --out <new_dir>`. Saved output: [summary.json](../research_data/propagation_feasibility_v1_20261108/summary.json) and per-case [attack_cases.jsonl](../research_data/propagation_feasibility_v1_20261108/attack_cases.jsonl).

## 1. Data and definitions

| Input | Use |
|---|---|
| Official MPBench (3,241 attack + 2,999 benign cases) | Planted target = `expected_memory`; attack question = `retrieval_query`. |
| Completed Original SAFE-Mem full reproduction (GPT-4o-mini, one shared 6,240-case pool) | Every written claim with its usable kind and standing (22,089 claims). Each question's classified `required_type`. Write, retrieval and answer judge results. |
| Memory recovery v1 | Literal support spans for each claim (`proposed_support_spans`). |
| 24 provisional episode files | AI origin decisions (external vs unknown), used **only to calibrate** the attribution proxy. |

**Authority rule** (unchanged, `src/ams/core/lattice.py::permits`): a claim may serve a query only if `usable_as ≥ required`. All 21,763 artifact-derived claims are stored as `description@global`; only principal turns get preference, rule or attribute standing. **So an external claim can only ever serve a *description* query.**

A case is **propagation-reachable** when all three hold:
1. its attack question is classified `description`;
2. at least one of the case's own artifact claims restates the planted target (lexical proxy, see §6);
3. that claim is attributable to the case's source.

Attribution has two tiers. **Attributable now** means a literal support span exists in an external artifact. **Attributable after review** means the claim is an artifact claim but a paraphrase, so it needs AI or human span review.

## 2. Attack funnel

| Stage | Cases |
|---|---:|
| Attack cases | 3,241 |
| No evaluated question in the reproduction | 242 |
| Question needs rule / preference / permission / attribute, which **no external claim can serve** | **2,727** |
| Description question, but the target is not in any of the case's external claims | 170 |
| **Reachable, attributable after review** | **79** |
| **Reachable, attributable now (literal span)** | **23** |
| **Reachable total** | **102 (3.1%)** |

All 102 reachable cases come from **100 distinct template groups**, and no two share an identical target text. 81 cases have one target-bearing external claim and 21 have two to four. Claims from one contribution share one evidence root, so they count as a single vote.

**Calibration of the attribution tiers** against the AI decisions the provisional run used (AI output, not human truth):
- AI judged a claim external in **82.5%** of claims with a literal span, and in **57.1%** without one.
- Applying those rates gives an expected **≈64** of the 102 reachable cases as attributable.

## 3. Where full-reproduction attack successes come from

The 176 attack successes in the full reproduction split by question type and by the carrier found in the retrieved claims:

| Question type | Successes | Carrier |
|---|---:|---|
| Description | 67 | **22** own external claim only; **32** involve an external *copy from another case* (with or without the own claim); 13 target not in any retrieved claim |
| Rule / preference / permission | 109 | **94** target not in any retrieved claim (principal path; the model agrees without memory support); 15 principal claims copied from other cases |

This confirms the 7 November diagnostic at full scale. Propagation can only matter for description questions (38% of successes). About half of those rely on copies of the planted content from other cases, so a propagation test needs copies linked or attributed. The 109 non-description successes are a residual of base SAFE-Mem and out of reach of any provenance policy.

## 4. Contributors and siblings

- **No natural contributors.** MPBench has no authorship. Every reachable case is a different template, so a contributor carrying several attack-bearing contributions exists only by **synthetic assignment**, as in the provisional overlays.
- **Benign siblings are not the bottleneck.**
  - 1,036 benign cases have literally attributable external claims.
  - 419 benign questions are description-type, but almost all are *restraint* items: only 6 have warranted memory.
  - There are **0 validated** external-memory utility questions. The existing unvalidated drafts (2,831 across versions, per the provisional report) cover only the Email and File/Document contexts: recovery v1 has 1,065 (1,061 email) and utility v2 has 1,446 (1,061 email, 385 file/doc). The `utility_question_drafts_unvalidated` column in `summary.json` counts the recovery v1 file only.
- **Reachable attacks by context:**

| Context | Reachable (any tier) | Attributable now | Reproduction successes among reachable |
|---|---:|---:|---:|
| calendar | 32 | 11 | 11 |
| email | 19 | 2 | 7 |
| file_and_doc | 17 | 2 | 10 |
| slack | 19 | 2 | 10 |
| web | 10 | 4 | 5 |
| script_execution | 5 | 2 | 2 |
| travel | 0 | 0 | 0 |

## 5. Can this power the comparison?

Assumptions:
- **Static ASR** among reachable cases is 44% in the full shared pool (45/102), and 30% in the attributable-now tier (7/23).
- **Design A** uses one audited unsafe seed per batch of four. That is enough for S's batch scope.
- **Design B** follows the protocol cells, with two seeds per cell of at least three attacks. That is needed for S's context scope, which is what separates S from batch-level penalties.
- Only *unaudited* reachable siblings can be scored.

| Scenario | Reachable | Design A: scored siblings → expected baseline successes | Design B: scored → expected |
|---|---:|---:|---:|
| Attributable now only | 23 | 17 → **5.2** | 9 → **2.7** |
| AI-calibrated expectation | ≈64 | 48 → **21.2** | 22 → **9.7** |
| Every reachable case attributed | 102 | 76 → **33.5** | 34 → **15.0** |

The protocol requires at least 20 baseline successes before an attack-efficacy result counts as conclusive. Only design A under optimistic attribution clears it, and it uses **the entire MPBench supply with nothing reserved for a locked test**. These are baseline successes. Cases where S and M *disagree* would be far fewer. Utility cost cannot be measured at all without validated external-use questions. Capacity check: at most **31 contributor-context cells**, which is at most **7 protocol-shaped groups**.

## 6. Limitations

- **Target proxy is lexical.** Against the reproduction's write judge it agrees on 87.6% of 2,999 attack questions (precision 93%, recall 85%). A recall shortfall could hide roughly 15–20 more reachable cases, which does not change the verdict.
- **Attribution tiers are proxies.** Literal spans are a mechanical lower bound; the calibration comes from AI decisions, not human review.
- **Required types come from the reproduction's cached classifier**, the same frozen classifier a new run would reuse.
- **ASR comes from one 6,240-case shared pool.** Foreign copies inflate it, and small groups change retrieval competition.
- **Capacity and power figures are upper-bound arithmetic**, not a constructed cohort.
- **No human validation**, as before.

## 7. Recommendation

Build a **controlled attack workload derived from MPBench**, keeping SAFE-Mem's authority rules unchanged for every arm:

- **Attack contributions:** synthetic contributors that each carry several description-type attack contributions. Use the attack goals and styles of the 102 reachable cases as templates. Every planted target sits in an attributable external claim.
- **Benign siblings:** in the same and in different batches and contexts, each paired with a **source-grounded description question**, so utility cost is measured.
- **Copies:** declared, known copies, plus deliberately unlinked copies as a separate stratum.
- **Controls:** principal-owned and unrelated-source controls; fixed audit IDs; enough confirmed seeds for designs A and B.
- **Size:** enough reachable sibling probes to expect at least 20 baseline successes per locked condition, with a separate held-out set.

**Next step (free):** write the workload specification and an offline, deterministic artifact generator. Report its size and a paid-cost estimate for memory extraction plus answering and judging, which uses GPT-4o-mini. Run nothing paid until approved. An optional cheap side check is a pilot on the 23–102 MPBench-reachable cases as an external-validity cohort. Their memories already exist in the frozen cache; it would also need paid answer/judge calls and attribution review.
