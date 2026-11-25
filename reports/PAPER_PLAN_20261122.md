# ICML paper plan: selective distrust propagation in SAFE-Mem (22 Nov 2026)

Plan for plan.md Phase 8. Uses only results that already exist (P-B2 GPT-4o-mini, P-B3 Claude Haiku when finished). No new methods, no new paid runs unless the owner decides so (see "Owner decisions").

## 1. Core story (one paragraph)

When an audit finds poison in an agent's memory, the system must decide how far the distrust should spread to unaudited memories of the same provenance. Spreading to the whole contributor or context (C, M) blocks the poison but discards most legitimate memories; not spreading (R) leaves sibling attacks active. S spreads distrust only to scopes that the audit evidence supports (batch, then context, then contributor). On a controlled MPBench-derived workload with oracle audits, S matches C and M on attack success (0%) while keeping 91% utility instead of 66%, and beats four published defenses adapted to the same store. The same narrow rule is the weakness: S trusts attacker-controlled provenance labels, so batch shifts, Sybils and laundering defeat it. We report this as a characterized limit, not hide it.

## 2. Claims and the evidence for each

| # | Claim | Evidence | Status |
|---|---|---|---|
| C1 | Evidence-gated scope keeps utility without losing safety (localized) | Table 1; H1 vs C, H1 vs M: +90 key utility [+83, +95] | done (GPT); Haiku pending |
| C2 | S is not worse than M when evidence is spread out | H2: S − M ASR 0 [0, 0] (distributed) | done |
| C3 | Audit-aware propagation beats published defenses that cannot use audits | H3: S − A-MemGuard target ASR −49 [−58, −40]; Table 1 | done |
| C4 | Content lineage (SL) stops relay copies of caught content | H5: relay exposure −58 [−79, −37] | done |
| C5 | Adding MemLineage's gate (S2-ID) helps on hard attacks | H4: −14 [−20, −9]; gain comes from MemLineage's gate | done; frame honestly |
| L1 | Adaptive attacks defeat S | Tables 2-4: batch shift 66, Sybil k≥4 64, laundering r=1 66 | done; main limitation section |
| L2 | H6 (harm to innocents) could not be tested in the chosen cell | Table 8: S = C = M = 92 | report as failed, explain the cell |

Labels that must appear wherever results appear: "reused MPBench v4 split: replication evidence, not fresh held-out"; synthetic contributors; oracle audits; one run; judge not human-validated (until the 300-case check is done).

## 3. Section outline and page budget (8 pages main text)

| Section | Pages | Content | Source material |
|---|---|---|---|
| 1 Introduction | 1.0 | Problem, why propagation scope matters, contributions C1-C5 + L1 | this plan §1-2 |
| 2 Background and threat model | 0.75 | SAFE-Mem authority and provenance; attacker controls content and labels; auditor gives oracle verdicts; what S can observe | SAFE-Mem paper, README §2 |
| 3 Method | 1.25 | R, C, M baselines; S with its three gates (batch ≥1, context ≥2 in ≥2 batches, contributor ≥4 in ≥2 contexts; threshold 0.25); SL; S2-ID; pseudo-code (Algorithm 1) | `src/ams/research/dynamic/ledger.py` |
| 4 Experimental setup | 1.25 | Question and workload (done), contents/conditions/audits (done), methods and models, metrics, statistics (v2 protocol) | `reports/PAPER_SECTION4_*.txt`, protocol v2 |
| 5 Results | 2.25 | Table 1 (main), compact hypotheses table (H1-H6), Figure 2 (Sybil-k and laundering-r curves), backbone table (Haiku, Table 7) | `analysis_gpt_early/tables.md` + Haiku analysis |
| 6 Adaptive attacks: a characterized limit | 0.75 | Why S fails (labels are attacker-controlled; narrow rule = the gap); free checks: rung cap NO-GO, content similarity AUC 0.73 | HANDOFF §3-4, README §10 |
| 7 Related work | 0.5 | Memory poisoning (MPBench, A-MemGuard), provenance (MemLineage), trust/reputation systems | plan.md 8.2 |
| 8 Conclusion | 0.25 | | |

Appendix: A workload details; B protocol v2 and decision rules; C full Tables 2-6; D imperfect audits; E published-defense adapters; F protocol v1 (first frozen evaluation, H1/H2 supported, H3 not); G cost and reproducibility; H S2-BS (rejected variant).

## 4. Figures and tables

- Figure 1: workload layout (exists in the preview; fix caption: drop "consecutive").
- Figure 2 (new, from existing numbers): ASR vs Sybil k and vs laundered fraction r for S, M, MemLineage, S2-ID.
- Table 1: main result (exists). Table 2: hypotheses (from Table 8). Table 3: backbones (needs Haiku). Others go to the appendix.

## 5. Writing order (each step in order, reuse existing text)

1. Wait for P-B3 to finish (status 22 Nov 00:41: 19/24 groups done, $0 errors). Run the frozen analysis with the Haiku rows (free); fills Table 7.
2. Finish Section 4: rewrite "Methods and settings", "Metrics" and "Statistics" for protocol v2 (11 methods, H1-H6, two backbones, replication label). Fix the "??" references and Appendix A.1/A.5.
3. Section 5 Results from the frozen tables (no new analysis).
4. Section 3 Method with Algorithm 1, checked against `ledger.py`.
5. Section 6 Adaptive-attack limit.
6. Introduction, then Related work, then Conclusion and Abstract.
7. Appendix, limitations, ethics and reproducibility statements.
8. Release package (code, workload v4 public files, frozen protocol, hashes).

## 6. Owner decisions still open

1. Human judge check: name 2 annotators + 1 adjudicator for the 300-case check (open since 14 Nov). Without it, the paper must say the judge is unvalidated.
2. Fresh confirmation test (v5): full 96 groups ($43-82) does not fit the remaining budget; 32 groups ($17-32) partly fits; or skip and keep the replication label.
3. How to present protocol v1: appendix only (recommended) or a short paragraph in Section 5.
4. Paper source: the LaTeX source of `preview_main.pdf` is not in the repo; download it from Overleaf so edits can go into the real file.
