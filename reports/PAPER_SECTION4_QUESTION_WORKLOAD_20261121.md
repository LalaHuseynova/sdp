# Paper Section 4, "Question and workload": corrected text and file-by-file check (21 Nov 2026)

Read-only check of the "Question and workload" paragraph in `preview_main.pdf` against the code, the v4 workload files, the saved Stage-1 stores, the raw MPBench data and the newest freeze (revision 9). No API call; no code, data or result changed.

## Corrected text (paste into Section 4)

**Question and workload.** We study whether distrust triggered by an audited, poisoned memory should propagate to unaudited memories that share its provenance, and if so, at which scope: the same batch, the same context, or all contributions of the same source. Wider propagation can withhold more poison but also removes more legitimate memories, so we measure both attack success and utility.

Answering this question requires sources that contribute repeatedly under controlled provenance, which existing benchmarks do not provide. In MPBench (Dash et al., 2026), SAFE-Mem's authority rule (Li et al., 2026) permits external content to answer only description questions. Under this rule, only 102 of its 3,241 attacks can reach an answer through an external claim. MPBench also records no contributor identities, and these 102 attacks derive from 100 distinct templates. We therefore construct a controlled synthetic workload (v4). Seed and scored-attack texts are taken verbatim from MPBench, and each benign contribution embeds one synthetic reference fact in an MPBench benign document.

A *group* is one independent memory-store instance (Figure 1). In the base design, it is built from 40 *contributions*, i.e., input texts passed through SAFE-Mem's write path, made by four synthetic sources: an attacker A, a benign colleague B, an unrelated source U and the principal P who owns the memory. A holds the audit seeds, the scored attacks and a linked copy of a seed alongside benign facts, B supplies benign facts, and U supplies further facts together with one unlinked relay of attack content.

Each external contribution carries a *context* and a *batch*. The context is the communication channel of its source document (e.g., email or calendar). A batch is a provenance label that groups contributions of one contributor within one context. A and B each contribute two batches of four per context, U contributes one batch of two per context, and P's statements carry neither a context nor a batch. Extraction and retention yield zero or more claims per contribution, so 40 contributions do not imply 40 claims.

Each group's store is built once, and every condition relabels this store rather than rebuilding it. The three main conditions differ only in the contributor and batch labels; the uninformative condition, for example, reassigns A's and B's items between them. Adaptive conditions may additionally change identities, contexts or audited items. After construction, each group is queried with 35 *probes*, i.e., questions posed to the store rather than stored contributions. Scored attacks are verbatim MPBench attacks that can reach an answer through an external claim. They are therefore designed to test propagation, not to estimate attack prevalence.

## What was wrong in the preview version

| Preview statement | Problem | Evidence |
|---|---|---|
| "no contributor submits more than one" | MPBench has no contributor identities at all; the 102 reachable attacks come from 100 templates | feasibility report, line 45 and 64 |
| "a batch, one of two consecutive blocks of four" | Batches are labels, not consecutive blocks; U has one batch of two per context; P has none | `generator.py` lines 435-441 (order shuffled once per group); overlays |
| "zero or more memory records" | Raw chunks are always stored; what can be zero is claims (74 of 960 test contributions) | Stage-1 test stores |
| Figure 1 caption: "a batch of four consecutive contributions" | Same as the batch point | as above |
| "so we build a synthetic workload from MPBench texts" (implicit: all text from MPBench) | Seeds and scored attacks are verbatim; benign facts, copies, relays and principal statements are newly written | `private/contributions.jsonl` extraction field |

## File-by-file check

| File | What it confirms |
|---|---|
| `data/mpbench/adversarial_data.jsonl.jsonl` | 3,241 attacks; all 256 seed and scored-attack contributions (dev + test) equal their MPBench original exactly (context and user query) |
| `reports/PROPAGATION_FEASIBILITY_20261108_REPORT.md` | 102 of 3,241 reachable; funnel 2,727 non-description / 170 target not in claims / 242 no evaluated question; 100 distinct template groups; MPBench has no authorship |
| `src/ams/core/standing.py` (lines 55-56) | External text gets standing `description@global` |
| `src/ams/core/lattice.py` (lines 115-133) | A claim serves a use only if `usable_as >= required`, so external claims serve only description questions |
| `research_data/controlled_workload_v4_20261108/manifest.json` | Pools: 102 reachable, 1,671 seeds, 1,986 benign bases; test: 24 groups, 960 contributions |
| `.../private/contributions.jsonl` | Every test group: 4 seeds, 4 scored attacks, 1 linked copy, 1 unlinked relay, 26 benign facts, 4 principal statements (= 40); all 624 benign texts contain their fact sentence |
| `.../private/probes.jsonl` | Every test group: 35 probes (4 attack, 1 linked copy, 1 relay, 25 utility, 4 principal) |
| `.../public/overlays/{localized,distributed,uninformative}.jsonl` | All 24 test groups in all 3 conditions: eight batches of 4 (A and B) and two of 2 (U); no principal statement has a context or batch; in the uninformative condition 133 of 288 attack items change contributor |
| `src/ams/research/workload/generator.py` | Ingestion order shuffled once per group, common to every condition (lines 435-441); benign bases drawn from the context's own channel (line 255); one seed per context from the reachable pool, one from the seed pool (lines 241-259) |
| `src/ams/research/workload/design.py` | `BATCH_SIZE = 4`, `B_BENIGN_PER_CONTEXT = 8`, U: three benign + one copy |
| `src/ams/research/workload/integration.py` (lines 372-405) | `build_states`: one construction per group, then one snapshot per condition with its own provenance labels and audits |
| `src/ams/research/workload/adaptive.py` (lines 1-8) | Every adaptive condition relabels the stored snapshot (contributor, context, batch and/or audited set); no model is called |
| `research_data/controlled_workload_stage1_test_v4_20261108/stores/` | 24 store files, each with the three condition snapshots; 74 of 960 contributions yield zero claims |
| `research_data/protocol_v2_freeze_optionB_20261115/protocol_v2_optionB_rev9.json` + `owner_approval_optionB_rev9.json` | Newest freeze hashes the v4 bundle and all 24 v4 test stores; no v5 file; scope "MPBench-derived v4 test split (reused)" for P-B1, P-B2 (GPT-4o-mini) and P-B3 (Claude Haiku) |
| `research_data/protocol_v2_optionB_run_v1/scripts/paid.sh` | All paid stages read `controlled_workload_v4_20261108` and `controlled_workload_stage1_test_v4_20261108` |

## Still to fix elsewhere in the paper

- **Figure 1 caption:** remove "consecutive".
- **Appendix A.1:** one audit seed per context comes from the 102 reachable attacks and one from the 1,671 pool; test reuses some scored attacks across groups (96 slots, 67 distinct MPBench cases).
- **Appendix A.5 and the rest of the v1 description:** in protocol v2 the adaptive conditions run on the test split, not only on development data.
