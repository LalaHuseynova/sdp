## 1. When Should Distrust Spread?

This presentation focuses on our extension: what we built, why scope selection matters, how the controlled comparison was executed, and what it did and did not show. Original SAFE-Mem is background only. We reproduced one model arm on the full release; the proposed defense has only a limited development evaluation. The central finding is currently negative: S did not outperform C or M on attack outcomes. Human validation remains pending, and no model training or fine-tuning was performed.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- README.md

## 2. A real MPBench memory-poisoning example

Original SAFE-Mem provides typed memory and authority checks; MPBench supplies memory-writing inputs and later retrieval questions. Our teammates cover that architecture separately. This real example is ADV_000, attack_type repetition_injection, adversarial_goal data_exfiltration, in data/mpbench/adversarial_data.jsonl.jsonl. The payload repeats a roster-inclusion instruction through several email replies. The evaluator target is “Include client roster in all summaries.” The slide quotes actual fields and one exact context excerpt; omitted email headers and replies are not rewritten. The source thread includes named attachments, but this record does not demonstrate executed file exfiltration. We do not claim a per-case success or label every extracted statement unsafe.

SOURCES
- data/mpbench/adversarial_data.jsonl.jsonl — ADV_000
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §3

## 3. Our Original SAFE-Mem reproduction

The completed reproduction ingested all 6,240 source cases into a shared pool. There were 3,241 attack inputs and 2,999 benign inputs, with 244 write-only cases overall. Read evaluation covered 2,999 attack and 2,997 benign questions. Of the benign questions, 249 contribute to explicit-retention recall and 2,607 to restraint; 141 readable benign cases do not enter that annotated utility denominator. This is a reproduction of GPT-4o-mini through the existing OpenRouter alias, not every backbone or competing method from the paper. Local MiniLM embeddings, flat index, withhold, hops=0, k=4, m=4, at most six claims, and the 200-token answer limit were retained. Original core memory/authority/prompt files remain unchanged. Infrastructure journals preserve actual writes and responses instead of treating the final shared-cache winner as replay evidence.

SOURCES
- reports/safemem_full_mpbench/RUN_REPORT.md
- configs/openrouter_mpbench_safemem.yaml
- src/ams/data/mpbench.py
- src/ams/eval/lifecycle.py

## 4. Full-release reproduction versus the paper

Paper Table 1, GPT-4o-mini column M: ASR 6.2%, recall 85.9%, restraint 50.6%. Reproduction: 176/2,999=5.87%; 213/249=85.54%; 1,273/2,607=48.83%; combined annotated benign utility (213+1,273)/2,856=52.03%. The paper does not report this combined metric in that table, so it is unavailable rather than zero. S is deliberately last and all its full-pool cells are unavailable. The reproduction ASR is 0.33 percentage points lower, retention 0.36 points lower and restraint 1.77 points lower. These are descriptive differences, not a test of equivalence. Model alias/backend, transport/cache replay and stochastic outputs limit exact replication. The full-pool historical ASR must not be used as the causal comparator for the new small-pool conditions. The supplied paper PDF was checked locally; no new paper-model results were invented.

SOURCES
- safe-mem_paper.pdf — Table 1, p.6
- reports/safemem_full_mpbench/RUN_REPORT.md
- output/pdf/research_result_tables_20261101/source_data.json

## 5. Our question: how far should evidence spread?

Our starting idea was to identify a contributor, lower trust after a dangerous memory, and penalize that contributor’s other memories. That is feasible but weak as a standalone novelty claim. SuperLocalMemory already discusses provenance, equal initial trust and behavioral reputation updates; A-MemGuard uses defensive lessons. We therefore sharpened the question to the scope of transfer: batch, contributor/context, or contributor. Our candidate S is a concrete support-gated heuristic, not a proved new estimator. The important comparator is M with the same metadata, as well as contextual reputation C; beating record-only R alone would not isolate the contribution of selective scope. We have not shown efficacy or novelty in the preliminary comparison.

SOURCES
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §§1,9
- README.md §1
- https://arxiv.org/html/2603.02240v1#S4
- https://arxiv.org/abs/2510.02373

## 6. The research layer we added

The added code is predominantly under src/ams/research/. Preparation/recovery/provisional modules produce separate sidecars and review materials. dynamic/ implements typed event inputs, journal projections and four policies. retrieval/ binds native claims/chunks to logical provenance, enforces inherited permissions and applies ranking/gates before model exposure. sequential/ preserves ordered state, exact saved responses and restart checks. native/ constructs newly frozen stores from offline recovered material, not a full historical graph replay. planning/ and execution/ handle matched study manifests, durable request IDs and shared spending limits. The evaluator can see labels and targets; the defense cannot. This separation is enforced through allowlisted objects and request checks, not an operating-system security sandbox.

SOURCES
- src/ams/research/dynamic/ledger.py
- src/ams/research/retrieval/adapter.py
- src/ams/research/sequential/runner.py
- src/ams/research/provisional_run/preparation.py

## 7. Recovering the memories we actually evaluate

Claims were recovered from saved reproduction writes. Chunks depend on embedding-sensitive source segmentation; a naive fixed-length text split would not reproduce the original algorithm. Existing cached MiniLM embeddings/configuration and original logic were used, with checks against saved retrieval text, IDs and cache commitments. The reported total is 124,090 chunks: 318 directly saved, 123,772 reconstructed and checked. We do not claim that reconstructing chunk text replays every old graph mutation, conflict decision or final-cache response. Partially recovered bundles are not promoted to complete without all required components. Principal statements and external spans remain different provenance roots. Recovery does not supply human safety labels. Preparation produced 2,114 blinded review packets containing 52,716 record/use items. Later provisional tooling produced 2,831 utility drafts for 1,722 contributions. These are drafts, not ground truth; chunk-only support may be blocked by the frozen external_evidence=false setting.

SOURCES
- reports/RECOVERY_20261029_REPORT.md
- src/ams/research/recovery/
- reports/RESEARCH_AUDIT_20261101_REPORT.md

## 8. Provisional group composition and planned balance

Actual provisional selection is implemented by deterministic bipartite matching over seeded candidate orderings, not ad hoc manual outcome selection. Each duplicate/template component has capacity one across all 20 bags; generic/large groups flagged for manual review are excluded. Per domain, each bag has 10 attack inputs, one explicit-retention benign and five suggestive benign inputs. The protocol’s future Z-controlled design instead requires eight independently unsafe attack bundles, two independently safe attack bundles and six independently safe benign bundles per domain. These happen to preserve the same case totals but are scientifically different. Current provisional groups control Y_case placement and cannot establish a true unsafe-memory rate. D00–D07 are development, not an untouched confirmatory set. D08–D19 are prepared but were not used for this comparison.

SOURCES
- src/ams/research/provisional/episodes.py
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §4
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md

## 9. The provenance objects and their boundaries

Contribution, artifact, claim, evidence chunk and incident root are separate objects. Stable opaque IDs and SHA-256 content versions bind records to source spans. Claims use actual source-parent links; ambiguous heuristic attribution is unknown. Chunks inherit all relevant parent restrictions. Principal turns stay assigned to the existing user principal, not to a synthetic external contributor. An innocent relay/uploader is not automatically the origin. Known provenance defines common roots for copies; identical text alone does not make independent submissions one incident. Batches are synthetic statistical groups, not derivation edges. The controlled “authenticated_external” enum means the trusted synthetic mapping is accepted in this experiment; it is not a claim that real authors were authenticated. Missing/cyclic permissions and inconsistent mappings fail closed.

SOURCES
- src/ams/research/retrieval/metadata.py
- src/ams/research/dynamic/models.py
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §6

## 10. One 32-case group: identities, contexts and batches

This is a structural diagram of the actual provisional layout, not a fabricated dataset example. Public IDs are opaque episode-specific tokens; short Contributor 1/2 and Batch 1/2 labels here are display aliases. Contexts are fixed source domains, email and file_and_doc, not random task labels and not a query-selected context that could evade history. Every contributor has two four-case batches in both contexts. Assigning identities/batches lets us vary correlation while holding payloads and ingestion order fixed. MPBench does not contain natural repeated author episodes with authenticated identities, so the provenance arrangement is explicitly synthetic. All selected inputs are readable by the requester in the primary comparison; ACL-only security gains cannot explain its primary results.

SOURCES
- src/ams/research/provisional/episodes.py
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §5
- reports/PROVISIONAL_20261029_DESIGN.md

## 11. Three arrangements of the same real cases

The dots are read directly from D01 public assignment overlays and the private original-case label map. Each context contains ten attack and six benign inputs across all three conditions. Dot positions within a batch are sorted by opaque contribution ID for display, not original ingestion order. Display contributor aliases are sorted public contributor IDs; batch aliases are sorted batch IDs. These are actual finite realizations: a null allocation can contain clusters by chance, and distributed can still have uneven batch counts. No rejection sampling was used to force a prettier picture. The localized condition increases a batch weight as well as source/context weight; it does not guarantee that every attack is in one batch. The runtime never receives these label colors, profile bits or condition names. This is a case-intent-controlled experiment, not evidence that every red dot yielded unsafe memory.

SOURCES
- src/ams/research/provisional/episodes.py
- research_data/mpbench_provisional_v1_20261029/private/g_119618b1f6801d98f0a881f7/ep_4bab0c8b31957aa041863b39.json
- research_data/mpbench_provisional_v1_20261029/private/g_119618b1f6801d98f0a881f7/ep_43547fc840a2c88dacd18bd7.json
- research_data/mpbench_provisional_v1_20261029/private/g_119618b1f6801d98f0a881f7/ep_58f322bb18cbd29b59326e82.json

## 12. How the controlled assignments are drawn

assignments() uses rational weights and the exact weighted_subset distribution rather than independent Bernoulli decisions or an arbitrary sequential weighted sampler. It selects ten Y_case-adversarial positions among sixteen slots per context for the provisional version. In the future Z-controlled protocol the corresponding count is eight unsafe slots, requiring verified record/use annotations. One contributor is high-profile in Email and the other in File/Document, balancing expected total risk and preventing a simple global source blacklist from solving the intended layout. Each contributor/context has one hidden hot batch. All arms use one frozen policy configuration across regimes. Shared COMMON case order avoids changes in graph IDs or conflict history being confounded with the metadata overlay. Public object allowlists exclude Y_case, expected_memory, h/z profiles, scenario labels and unrevealed audit results.

SOURCES
- src/ams/research/provisional/episodes.py
- src/ams/research/phase1_scenarios.py
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §§4.4,5.2,7

## 13. The matched five-ticket experiment

The relational audit schedule uses the same root contribution across overlays, but A1–A4 can change when its metadata placement changes. Within a regime all four policies receive identical ticket contents and labels, initial state, query order, permissions and resource accounting. Across regimes, the five reserved cases and thus the 27 scored probes may differ. All 32 contributions remain in memory; audits restrict particular uses rather than deleting another method’s data. Each method uses a separate reset. Existing AI proposals supply simulated feedback; the initial ticket was unsafe in five development bags, safe in D02/D03, unresolved in D07. No verdict was forced to satisfy the future protocol’s confirmed-unsafe-seed condition. All five audits precede the query sequence in this comparison. B=1/B=3 and fixed-audit-ID cross-regime controls are future robustness work, not current results.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- src/ams/research/provisional/episodes.py
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §8

## 14. The evidence ledger records events, not a source blacklist

dynamic/models.py defines allowlisted Register, Audit and Retract event types. The single-writer ledger appends events in revealed-time order and derives immutable snapshots from a committed prefix. Hash chains detect corruption; they are not digital signatures against a malicious trusted host. Audit findings contain record ID, content hash, use ID and policy version. Direct unsafe findings override separately active safe findings for that same record/use. Aggregate group observations count at most one informative observation per root, with unsafe precedence across active uses/versions. Retractions rebuild evidence contributions; a corrected false accusation can clear its source penalty without refunding the ticket or erasing unrelated ACL restrictions. Repairing text creates a new content version without pretending a genuine earlier incident never occurred. Unknown/principal roots cannot generate source reputation penalties. These correction/copy/noise mechanics have offline tests; answer-level robustness studies are still pending.

SOURCES
- src/ams/research/dynamic/ledger.py
- src/ams/research/dynamic/models.py

## 15. Reputation is a score derived from direct audits

U and Ssafe count distinct directly audited unsafe and safe independent roots, not model confidence, extracted claim count, or number of copies. The Beta(1,1) form is used only as a scoring convention. Under correlated/adaptive observations it is not claimed to be a calibrated posterior. The table values are exact consequences of the implemented formula: no audits gives r=1/2 and d=0; one unsafe gives d=1/6 and a 1/12 score decrease at lambda=0.5; two unsafe/no safe gives d=1/4 and triggers the inclusive threshold if the scope applies. A safe audit can reduce d without making uninspected siblings safe. C/M/S share lambda=0.5, tau=0.25. R sets lambda=0 and disables source gating. Fractions are used for group penalties and threshold comparison to avoid floating boundary drift. The two-unsafe rows are also realized in the D01 trace on the next slides.

SOURCES
- src/ams/research/dynamic/policies.py
- src/ams/research/dynamic/ledger.py
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §9

## 16. R, C, M and S differ in propagation scope

Policy is a pure decision function over a typed Candidate and immutable EvidenceSnapshot. It first rejects ACL-denied, authority-denied or exact unsafe-use candidates. A separately safe finding provides only an exact content/use/policy exception from reputation; it cannot raise original authority or permissions. R then has no sibling effect. C uses full-history contributor/context counts. M always considers batch, context and contributor maxima and therefore controls for receiving the richer metadata. S considers the maximum only among supported scopes. Group overlaps are not combined as independent probabilities. An active scope does not invent a new safety label for its members. Recent-four history C and fixed convex-mixture M variants are specified for an expanded study but not implemented in this minimum evaluation. We do not report A-MemGuard or other paper-baseline rows as run if they were not faithfully adapted.

SOURCES
- src/ams/research/dynamic/policies.py
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §9.2

## 17. A recorded audit sequence shows why the policies differ

This is calculated from actual frozen D01 localized audits, not an invented favorable scenario. A0 and A1 are unsafe in the same batch b_dd704abeae1662df44385e36, context file_and_doc, contributor u_e85e0fff0e154802f5a27517. Both are independent roots. With U=2 and no safe audits, batch/context/source d=0.25. For an uninspected candidate in the root batch, C/M/S reach the gate. For the other batch in that context, C and M apply 0.25, while S has no context support because both findings came from one batch. For this contributor’s other context, M’s global-source maximum gates at 0.25 while C and S have zero. R never propagates. Peer-contributor candidates remain unaffected. These are policy penalties for eligible candidate classes, not claims about actual changed answers or confirmed danger. AI findings are simulated feedback, not human ground truth.

SOURCES
- research_data/provisional_extension_freeze_v1_20261101/private/ep_43547fc840a2c88dacd18bd7.json
- src/ams/research/dynamic/ledger.py
- src/ams/research/dynamic/policies.py

## 18. Selective support grows only when evidence spans scopes

The implementation recomputes support from active independent unsafe roots after each event. Batch support needs any unsafe root in that batch. Contributor/context support requires two independent unsafe roots with at least two different batches. Contributor-wide support requires four unsafe roots and two qualifying contexts, each with at least two unsafe roots spanning two batches. Counts alone do not set the scope; counts determine d within the supported scope. In the actual D01 localized sequence, A0 unsafe and A1 unsafe are in one File/Document batch; A2 unsafe is in the other File/Document batch and activates context support. A3 unsafe is in one Email batch. A4 in the other Email batch is unresolved, so Email lacks two unsafe batches and source scope never activates despite four unsafe observations overall. An unresolved event still consumes its ticket. A later correction would recompute support. These thresholds are heuristics, not statistically certified cutoffs.

SOURCES
- research_data/provisional_extension_freeze_v1_20261101/private/ep_43547fc840a2c88dacd18bd7.json
- src/ams/research/dynamic/ledger.py active_scopes()
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §9.2

## 19. Where the defense enters retrieval

GovernedRetrieval uses original query classification, relevance embeddings and authority admission, with exact binding sidecars for logical IDs, record versions and artifact parents. Current ACL grants are intersected over parent relationships before candidate text can reach conflict, detector or answer model contexts. Direct record/use findings are common to all R/C/M/S, then policies adjust cosine scores and optionally gate. Rank/refill uses shared slots and candidate universe. Original authority remains decisive: external_evidence=false blocks the external chunks that many source-grounded draft questions depend on. The effect-disabled all-allow adapter reproduces original selection/rendering, including source caps and underfill behavior; all 648 static query context/governance hashes matched. Active policy paths use the shared refill rule. Unsupported modes are rejected. No private labels, hidden profiles or policy traces are appended to answering prompts.

SOURCES
- src/ams/research/retrieval/adapter.py
- src/ams/research/retrieval/metadata.py
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md

## 20. Code we introduced and code we preserved

The original typed memory, lattice/authority implementation and prompt files remain in src/ams/memory/, src/ams/core/ and prompts. The latest audit checked 54 tracked files against Git HEAD. Existing surrounding files changed: data/mpbench.py introduces split-qualified internal IDs to avoid attack/benign collisions while retaining raw IDs/content; eval/lifecycle.py adds observation callbacks and saved fields; scripts/run_mpbench.py adds shared-pool coverage checks and write/outcome journals; configuration YAMLs route model roles to OpenRouter; providers/openai_client.py and pricing.py add guarded native billing and accounting. MINJA compatibility scripts are earlier infrastructure work, separate from this dynamic MPBench evaluation. The research code is largely added rather than edits inside original memory rules. The release package is not yet complete; untracked files and ignored reports/tests must be packaged deliberately before sharing.

SOURCES
- README.md §5
- reports/RESEARCH_AUDIT_20261101_REPORT.md
- src/ams/research/retrieval/adapter.py

## 21. Ordered execution, replay and spending checks

sequential/state.py uses explicit JSON serialization for original graph, vector index, chunks, permissions, caches and RNG state; it does not deserialize arbitrary pickle. The sequential journal orders intents, requests and commits and resumes from exact saved responses. The live provisional runner uses compact ordered query journals and reconstructs from frozen stores plus saved replies. Unknown provider completion does not justify an exactly-once API claim: it stops for reconciliation. The controlled runtime memoization/restart amendment changed hash reuse, not policy semantics, and preserved previous outcomes. Latest audit: 612 collected tests across 42 files, not the sum of overlapping earlier reports. All 3,888 outcomes, 648 static baseline contexts/governance states and prior delivery counts were verified. Fourteen outputs ended at the original token limit and remain scored; there were no answer-judge fallbacks. Known issue: the legacy Phase 1 producer fingerprint accidentally includes unrelated added modules, so regeneration/import commands need a versioned dependency fix; later saved native/provisional freezes pass checks.

SOURCES
- reports/RESEARCH_AUDIT_20261101_REPORT.md
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- src/ams/research/sequential/runner.py
- src/ams/research/execution/session.py

## 22. The evaluation we actually completed

The run covers the eight pre-existing development groups D00–D07, not all twenty prepared groups and not the full 6,240-case pool. There are 160 original attack inputs and 96 benign inputs before audits reserve five cases per group. Per method: 648 answers total, 216 per regime. Across six methods: 3,888 answer events. Repeated overlays are paired sensitivity conditions, not independent datasets. The original source-grounded benign question set was unvalidated and not scored; its unavailable metric is not zero. D00 had no originally admitted external candidate. The extension used every remaining pre-existing development bag without outcome-based selection or new tuning. Primary comparisons are S against C and M at equal feedback/resources, with R and static as additional references and no-memory as a diagnostic extreme. Statistical reporting uses paired bag bootstrap, 10,000 resamples, exploratory pointwise intervals; neither equivalence nor noninferiority is established.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- research_data/development_comparison_report_v1_20261101/comparison.json

## 23. Attack success and combined benign utility

Native editable table copied from verified saved-output analysis. Distributed: every memory method 4/134 ASR and 75/82 utility; no-memory 0/134 and 67/82. Localized: every memory method 5/131 ASR; static/R utility 77/85, C/M/S 76/85; no-memory 0/131 and 71/85. Uninformative: all memory methods 6/140 ASR; static/R utility 70/76, C/M/S 69/76; no-memory 0/140 and 62/76. Bold includes ties and diagnostic controls, so no-memory is bold on ASR despite its severe retention loss on the next slide. No-memory is not the paper’s SimpleMemory “no defense” method. The condition-specific denominators differ because relational audits reserve different cases. Three scenario variants must not be treated as independent groups. The historical full-pool 5.87% is deliberately excluded from this matched table.

SOURCES
- research_data/development_comparison_report_v1_20261101/comparison.json
- research_data/development_comparison_report_v1_20261101/RESULTS.md

## 24. Retention and restraint must be read separately

Distributed: all memory methods retention 13/14, restraint 62/68; no-memory 0/14, 67/68. Localized: all memory methods retention 12/13; static/R restraint 65/72, C/M/S 64/72; no-memory 0/13, 71/72. Uninformative: all memory methods retention 12/13; static/R restraint 58/63, C/M/S 57/63; no-memory 0/13, 62/63. This separates the strong restraint of ignoring all memory from the ability to retain explicitly warranted facts. S did not improve over C or M; S lost one restraint success versus static/R in localized and null. Retention targets in these eight bags admit no attributed external candidate under original rules, so the tied retention rates do not establish preservation of useful external-source contributions. The combined metric on the prior slide is a weighted pool, not general answer accuracy.

SOURCES
- research_data/development_comparison_report_v1_20261101/comparison.json
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md

## 25. The rule ran, but had few external candidates to affect

The admission audit counts questions with at least one originally admissible attributed external candidate: 14, 16 and 18 of 216 for distributed, localized and uninformative. This is different from the number of selected external records or unsafe records. S changes the full rendered retrieval-context hash on 5, 8 and 10 queries, total 23/648. C changes 5/7/12, total 24; M changes 6/10/13, total 29; R changes none. The counts are direct diagnostics in the verified report. The chart is a native editable PowerPoint chart with an embedded worksheet. It compares counts measured over the same per-condition 216 queries, but a changed context need not contain or remove an unsafe record. Original authority sharply limits attributed external memory exposure. We have not completed a blinded per-context causal failure analysis, so do not interpret every difference as transfer to an uninspected sibling.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- research_data/development_comparison_report_v1_20261101/comparison.json

## 26. What we observed, and what remains unexplained

Across all three conditions static selects 2,327 principal, 106 external and 86 unknown-origin record occurrences; S selects the same 2,327 principal occurrences, 92 external and 100 unknown occurrences. The reduction of 14 known external exposures and increase of 14 unknown exposures indicates that refill can change source composition without guaranteeing safety. Those repeated selected-record occurrences are not unique memories or independent observations. The report supports aggregate changes and the one-event restraint losses in two conditions, not a completed causal explanation. Potential contributors to the null ASR effect include scarce admissible external candidates, only four to six baseline successes per condition, feedback uncertainty and mismatch between case-intent placement and actual memory risk. These are hypotheses and design limitations, not experimentally isolated causes. No source-grounded utility endpoint is available to show preservation of useful external facts.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- research_data/development_comparison_report_v1_20261101/comparison.json

## 27. What the preliminary comparison cannot establish

The future primary study requires independently validated Z(record,use), confirmed attributable unsafe seed audits and balanced safe/unsafe bundles. The current study has none of those guarantees: its eight bags balance original case labels, and some first AI verdicts are safe or unresolved. The failed AI utility-review round remains blocked and is not silently recast as qualified data; the comparison uses a separately declared provisional scope with original question metrics only. Noisy feedback, delayed audits, compromise, false accusation recovery and permissions have scenario specifications and offline mechanisms, not an executed answer-level robustness suite. The three overlays are sensitivity replications over the same inputs. The protocol’s fewer-than-20-baseline-success planning rule makes efficacy inconclusive. Tied outcomes and degenerate zero-difference bootstrap intervals do not prove equivalence or preserved utility. Synthetic provenance does not solve authentication, collusion or real account changes.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §§15–17
- reports/AI_PILOT_ADJUDICATION_20261101_REPORT.md

## 28. Next study: test transfer where external memory is usable

The next immediate analysis is a per-query review of changed contexts, including S versus R, C and M and the two benign restraint losses. It should distinguish direct audited-record containment from transfer to uninspected siblings and identify unknown-origin substitutions. For a redesigned study, prospectively select external-memory tasks based on content, provenance and intended use before viewing new model outcomes. Complete two independent human reviews and third-party adjudication of disagreements, including source-grounded utility references. The current authority rules may block chunk-only support, so eligible task definitions must be checked without silently elevating source authority. Freeze new case/template groups, shared audits, thresholds, costs and strong baselines before confirmation; previously inspected development results cannot become untouched test data. Add recent-history C and fixed-mixture M and the required robustness suite before broad paper-level claims. If M matches S at equal utility and cost, report a boundary result or revise the method rather than claiming novelty.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md Scientific decision and next work
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md §§9,15–18

## 29. Technical appendix: evidence and accounting checks

The real comparison cost reconciles 1,352 physical requests: 278 memory-answer calls, 245 no-memory-answer calls, 518 answer-judge calls and 311 entry-judge calls, with zero new verification, embedding or classification API calls. Historical review effort is charged equivalently to each arm: distributed 178 review calls, 1,729,266 input and 51,560 output tokens, $0.279660; localized 168 calls, 1,684,736/51,568 tokens, $0.273370; uninformative 168 calls, 1,700,501/51,688, $0.276572. These are saved historical full-call accounting equivalents, not newly charged amounts and not a one/two-call operational verifier experiment. The original session allowance remains $30, with no reset on restart. Current task to author this deck uses no research API calls. Release packaging, legacy validator dependency scoping and genuine review authentication remain work. These are material limits but do not silently erase saved later results.

SOURCES
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- reports/RESEARCH_AUDIT_20261101_REPORT.md
- research_data/provisional_api_receipts_v1_20261101/summary.json

## 30. Source map for supervisor questions

All tables were extracted from the saved verified source-data snapshot and comparison.json. The D01 example is traced to frozen audit events and original overlay assignments. The original dataset excerpt is ADV_000 from the official JSONL. Source SHA-256 hashes and the offline extraction/build scripts are included alongside this presentation. This appendix is intended as a practical map for technical questions; it is not a claim that sharing a README alone releases the implementation or that evaluator-only data should be publicly bundled. Relevant external context: Original SAFE-Mem arXiv:2610.22959; SuperLocalMemory arXiv:2603.02240; A-MemGuard arXiv:2510.02373. We only use those works to motivate the scope question, not to infer missing benchmark results.

SOURCES
- reports/safemem_full_mpbench/RUN_REPORT.md
- reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md
- reports/PROVISIONAL_RESULTS_20261101_REPORT.md
- research_data/development_comparison_report_v1_20261101/comparison.json
- reports/RESEARCH_AUDIT_20261101_REPORT.md
- src/ams/research/dynamic/ledger.py
- src/ams/research/dynamic/policies.py
- src/ams/research/retrieval/adapter.py