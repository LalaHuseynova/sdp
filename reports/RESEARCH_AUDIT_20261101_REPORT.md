# Research inspection — 1 November 2026

**The supported minimum prototype matches its stated R/C/M/S rules and passes the checked tests. The saved results and billing records agree with the reports. This inspection also found a legacy Phase 1 validation problem; the repository should not be described as completely finished or free of known issues.**

The current project explanation is [README.md](../README.md). The [final machine-readable checks](RESEARCH_AUDIT_20261101_ARTIFACT_CHECKS_V2.json) record the actual artifact checks, including the legacy refusal. The [earlier check](RESEARCH_AUDIT_20261101_ARTIFACT_CHECKS.json) is preserved. No paid model calls, training, installation, model download, new annotation or benchmark evaluation occurred during this inspection.

## What was checked

I reviewed the working-tree changes against Git HEAD, the proposal and protocol, preparation/recovery outputs, the ledger and policy code, retrieval and permission checks, restart handling, guarded dispatch, provisional execution and result analysis. This covers the supported local research path; it is not formal verification of every third-party component or unsupported retrieval mode.

| Check | Result |
|---|---|
| Original memory, core and prompts against Git HEAD | All 54 tracked files checked were unchanged. |
| Official MPBench bytes | Both official input files match the saved reproduction hashes. |
| Original reproduction recount | 6,240 unique writes, 22,089 claims and 5,996 saved answers checked; ASR 176/2,999, retention 213/249, restraint 1,273/2,607 and benign utility 1,486/2,856 match the report. |
| Archived Phase 1 producer and payloads | All 10 producer files and 12 payloads match their recorded hashes. See the legacy issue below. |
| Recovery outputs | All 27 recorded payloads and their reviewed-packet structural spans pass validation. |
| Provisional data | All 306 payloads, 20 groups and 120 overlays pass the existing validator. No invented audit results appear in that original preparation. |
| Native memory stores | All 62 payloads and 442 dependencies pass their recorded checks. |
| Execution freezes | Both scope manifests pass; 24 development group/condition cells remain unchanged. |
| Prior results delivery | All 99 recorded files match their previous hashes, including saved query databases. |
| Independent result recount | All 3,888 saved judgments were checked against the fixed probe categories and recounted without the comparison analyzer's metric function. All four reported metric counts match for all 18 method/condition combinations. |
| Earlier original-retrieval comparison | Its preserved records report 648 exact context/governance matches. No new answers or baseline models were run for this inspection. |
| Focused human-review workflow | Zero sealed first passes, zero second passes, no reference release or adjudication. |
| Research billing | All 3,103 dispatches and reservations are completed/settled. Used $2.09412345; no holds; remaining $27.90587655 under $30. |

## Does the implementation follow the idea?

The minimum policy code separates authority, access and empirical risk. It uses the same initial counts, direct containment and safe-use exceptions for all policies. One independent root supplies at most one source observation. Corrections remove superseded evidence and recompute scope support, while consumed audits remain charged.

S's implemented support gates are one unsafe contribution for a batch, two spanning batches for a context, and four spanning both batches in each of two contexts for contributor scope. The shared risk/score/gate rules match the minimum protocol. These are support-count heuristics, not uncertainty guarantees.

The adapter checks claims and evidence chunks before exposing selected text to conflict checking or answering. It preserves original authority and evidence restrictions. The supported path is flat/withhold/hops=0. It uses original private helpers and duplicates some narrow retrieval/rendering logic, so upstream changes require fresh parity checks.

The sequential machinery preserves ordered evidence, graph/index state, permission versions and exact replies through restart. The live provisional path uses a smaller query journal and the same saved-reply/state helpers. Paid dispatch keeps the same allowance, saves native receipts and refuses automatic redispatch after an unknown outcome. These checks do not prove authentication of contributors, human review or protection against a hostile host rewriting all files.

## Issues and unfinished work

1. **Legacy Phase 1 validator false refusal.** `implementation_fingerprints()` includes every top-level Python file under `src/ams/research`. The original manifest records ten producer files. Seven later, unrelated modules expanded that set, so `check_prepared()` rejects the existing archive even though none of the recorded producer files changed. Current tests missed this because they create manifests using the current file set. Affected paths include legacy Phase 1 validation/import and recovery/provisional regeneration commands that call it. The new inspection checks the recorded dependencies and payloads directly; it does not relax a gate, change original code, rewrite manifests or make those legacy commands ready. A versioned compatibility fix remains necessary before their reuse.
2. **Research data validity is still pending.** Current AI proposals are not human gold. Original case labels and actual record/use safety remain different. The provisional groups do not satisfy the primary protocol's independently verified 16-safe/16-unsafe composition or confirmed-unsafe-seed requirement. The earlier failed AI question-review gate remains failed; the later comparison is a separate provisional scope.
3. **The larger proposal is not fully implemented or tested.** Recent-history C, fixed-mixture M, genuine descendant safety transfer, broader reference defenses, noisy/delayed operational verification and answer-level robustness studies remain future work. No full-MPBench evaluation of our method or external benchmark validation has run.
4. **Usefulness and exposure remain weak points.** S changed 23/648 contexts without reducing ASR and lost one restraint success in each of two conditions. Refill sometimes increased unknown-origin exposure. Most original questions could not use attributed external records, and no validated source-grounded QA was scored. Detailed analysis of those changed contexts is still pending.
5. **Release packaging is unfinished.** Research code is untracked, and `.gitignore` excludes tests and reports. A normal README-only commit would omit important evidence. Raw evaluator data also needs separate handling before sharing.

No new defense behavior was added during this audit. The issue above is reported openly rather than silently changing code pinned by old experiment manifests.

## Test launch and results

The first full test launch used Python stdin. One multiprocessing budget test failed because macOS spawn tried to reopen a nonexistent `<stdin>` file. Its result is retained in [the initial JUnit file](RESEARCH_AUDIT_20261101_TESTS.xml).

I added [a file-based offline test entry point](../scripts/check_research_offline.py) and reran the same suite. **All 612 collected tests in 42 files passed, with zero failures, errors or skips**, in 68.740 seconds. [Final JUnit file](RESEARCH_AUDIT_20261101_TESTS_FILE_LAUNCH.xml). It contains 612 test-case elements; its suite counter also includes subtest reporting, so that counter is not a count of independent tests. Older 558-test and earlier counts refer to overlapping selections and must not be added together.

The test entry point blocks networking in the pytest process. The spawned budget workers exercise temporary SQLite accounting; no paid SDK request is involved. The passing rerun required no change to the budget or defense implementation.

I also added [a read-only inspection entry point](../scripts/inspect_research_state.py). It checks the recorded data and source files, exposes the legacy refusal, recounts outcomes and checks the dated billing state. It requires a new output report path and does not unlock experiments or generate annotations. Lint and format checks pass for both new scripts.

## Documentation changes

The root README now explains the question, an example, the exact implemented rule, original-code changes, data preparation, real results, limits, status, costs and where to find files. Its wording treats preservation of useful memories as a goal, not an achieved result.

The [previous local README](../README_BEFORE_RESEARCH_20261101.md) is preserved byte-for-byte. The [upstream README](../UPSTREAM_README.md) is copied from Git HEAD, retaining original setup instructions, credit and citation. Old reports, failed AI checks, experiment code, prompts, data, human forms and result outputs were not rewritten.

The [final validation record](RESEARCH_AUDIT_20261101_VALIDATION.json) records authorized changes, link checks, tests and file integrity. Human work can remain deferred for engineering; the next scientific step is diagnosis and a prospectively defined external-use study with defensible safety and utility labels.
