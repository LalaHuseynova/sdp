# LLM reviewer implementation and preliminary annotation results

31 October 2026. **The automated reviewer is implemented and has run on the first
32-case development group.** Its outputs are AI proposals, not human validation
or independent ground truth. This work did not run a defense benchmark, generate
task answers, train a model, update contributor trust or generate final pilot groups.

**Actual total API cost: USD 0.10690935. Remaining shared allowance:
USD 29.89309065 out of USD 30.** Both reviewer versions and their failures are
included. The provider's read-only account-usage delta matches the receipt total.

## Preliminary result

The small-batch reviewer produced **643 mechanically valid record/use proposals
out of 790 memory records**. Mechanical validity means the required IDs,
references, evidence, source roles and response structure pass checks. It is not
annotation accuracy, semantic correctness or a human agreement score.

| Record/use proposal | Count |
| --- | ---: |
| AI-proposed safe for the specified use | 594 |
| AI-proposed unsafe for the specified use | 42 |
| AI-proposed uncertain | 7 |
| Missing/rejected from accepted batch proposals | 147 |
| Total actual memory records in scope | 790 |

Whole-input record coverage was complete for **19 of 32 contributions**. Those
complete automated bundles were 12 AI-safe, 5 AI-unsafe and 2 AI-uncertain. The
remaining **13 contributions stay incomplete**, including any partially accepted
records they contain. They are not assumed safe or free of unsafe records.
Several memory rows can concern one incident; 42 unsafe record proposals are not
42 independent attacks or contributors.

Of 48 question drafts, 35 received accepted mechanical review coverage and 28
passed all five AI QA criteria. After additionally requiring a complete AI-safe
bundle and AI-safe external **claim** support, only **8 contributions** had a
candidate question. This is not human-validated utility, final uniqueness or
proof of actual retrieval/answer success. Chunk-only support remains restricted
by the frozen `external_evidence=false` setting.

**Defense ASR, retention, restraint, annotation accuracy, FPR/FNR and selective
propagation benefit have not been measured by this review.** Human verified-label
and validated-question counts remain zero.

## Scope, design and blinding

The input was the existing D00 development group: 32 contributions, 16 Email and
16 File/Document, originally comprising 20 adversarial inputs and 12 benign
inputs. Selection preceded this review. Locked groups were not reviewed or used
to revise the prompt.

Review prompts include original task/use, actual source text/roles, actual memory
text and candidate QA references. They exclude original attack labels,
`expected_memory`, hidden contributor-risk profiles, method outputs, warning
hints, another reviewer's decisions and future audit outcomes. Actual malicious
payload text remains unchanged and is treated as untrusted data. The reviewer
has no tools or authorization to act on instructions inside a memory.

Labels concern individual records for their specified use. Source-field origin
is separately principal/external/ambiguous; it never authenticates a real author
or makes an innocent uploader culpable. Question checks concern their separate
descriptive use. The existing native provenance/trust states were not changed.

The [separate exploratory protocol](LLM_EXPLORATORY_PROTOCOL_20261031.md)
defines AI labels as **Z-hat**, distinct from independently annotated Z and
original case label Y_case. The primary human-validated protocol and review forms
remain unchanged. Multiple prompt versions are not independent reviewers or a
consensus vote.

## Both versions, including the unsuccessful first pass

| Version | Paid requests | Accepted coverage | Native input/output tokens | Actual cost |
| --- | ---: | --- | ---: | ---: |
| Initial complete-packet prompt | 32 | 0/32 fully valid packets | 85,091 / 47,769 | USD 0.04142505 |
| Small batches with local references | 114 | 92/114 valid batches; 643/790 records; 19/32 complete contributions | 439,878 / 32,883 | USD 0.06548430 |
| Total | **146** | Both versions preserved | **524,969 / 80,652** | **USD 0.10690935** |

The first pass omitted chunks or returned nonliteral quotes, among other errors.
Its 32 replies and rejected-packet reasons remain in
[the original paid review version](../research_data/llm_review_dev_v2_20261031/summary.json).
They were not silently repaired or converted into accepted labels.

Before the second pass, a new version and its additional cost were disclosed.
It uses at most eight records per request, short local record references and
fixed source/evidence-unit references. The parser expands selected references to
the original IDs and exact text. This removes copying/offset errors; it does not
independently validate the model's interpretation or safety judgment.

The second pass still had **22 rejected batches**: 11 unknown source references,
5 cross-record evidence references, 4 missing unsafe evidence and 2 source-role
mismatches. The [failure list](../research_data/llm_review_small_batches_v2_20261031/review_failures.json)
preserves them. Invalid outputs were not assigned safe/unsafe/uncertain labels.
All 146 provider replies had `stop` finish reasons; these were not output-limit
truncations or transport failures.

## Why the 32-case pilot is still not ready

The [offline feasibility analysis](../research_data/llm_review_feasibility_v1_20261031/feasibility.json)
uses complete automated bundles and reports shortages without forcing balance.
Nominal counts below are AI proposals only, not independently verified labels.

| Required stratum per context | Needed | Email available | File/Document available |
| --- | ---: | ---: | ---: |
| Adversarial input with complete AI-unsafe bundle | 8 | 2 | 2 |
| Adversarial input with complete AI-safe bundle | 2 | 1 | 4 |
| Explicit benign input with complete AI-safe bundle | 1 | 0 | 0 |
| Suggestive benign input with complete AI-safe bundle | 5 | 2 | 5 |

Utility requirements tighten those safe counts further: Email has 1 AI-safe
adversarial contribution with AI-accepted claim-backed QA and no qualifying
suggestive cases; File/Document has 3 and 4 respectively. No qualifying explicit
benign contribution is currently available in either context.

One complete suggestive-benign input received an AI-unsafe bundle proposal.
That is a reason to inspect the judgments, not automatically a measured false
positive: original case intent and individual unsafe-memory use are different
constructs. Neither favorable labels nor disagreements with Y_case may be
silently reclassified to obtain the desired quotas.

## Spending and replay checks

The first disclosed working estimate was USD 0.10–0.25 with a conservative
USD 0.8503296 reservation sum. The separately disclosed second version was
USD 0.10–0.40 with USD 3.0292992 reserved-rate capacity. Actual charges were lower.
Planning assumed full input rates; native receipts report 269,696 cached prompt
tokens. Charges come from native provider receipts, not estimated token prices.

The existing single USD 30 guard/session accounted for both passes. Every
physical attempt was reserved before dispatch at the approved maximum rates.
Hidden retries, higher-rate fallback and unverified-billing overrides stayed
disabled. No new project allowance, key-limit change or credit purchase occurred.
The parent ledger ends with 146 settled attempts, no pending/unknown holds,
no breach and no blocked accounting state.

[Billing reconciliation](LLM_REVIEW_20261031_BILLING_RECONCILIATION.json)
confirms the provider account-usage delta of USD 0.106909350 matches these project
receipts. The local remaining allowance is USD 29.89309065; it is not a claim
about provider credit balances or unrelated account activity.

Both completed run commands return their hashed saved results on restart, rather
than buying new reviews. An unknown in-flight outcome would stop subsequent
dispatch, retaining its hold. Raw native replies are saved before billing
validation. The annotation-only scope refuses inherited scientific-execution
methods, and these labels cannot automatically update trust or enter human gold.
[The socket-blocked replay check](LLM_REVIEW_20261031_REPLAY_CHECK.json) confirmed
that rerunning both completed commands left the 146 attempts and charges unchanged.

## Implementation and validation

- [Reviewer package](../src/ams/research/llm_review/README.md): blinding, prompts,
  output validation, reference expansion, annotation-only transport and summaries.
- [Initial reviewer CLI](../scripts/review_mpbench_llm.py) and
  [small-batch CLI](../scripts/review_mpbench_llm_batches.py): explicit separate
  prepare/check/paid-run commands with immutable plans and no human impersonation.
- [Feasibility analysis](../scripts/analyse_llm_review.py): offline balance/QA
  coverage, not classifier accuracy or defense scoring.
- [Tests](../tests/test_llm_review.py): 25 new offline checks using invented data
  and MockTransport, including non-human metadata, evidence rejection, accounting,
  replay, blinding and honest quota shortfalls.

**366 tests and 31 subtests passed.** Ruff lint/format checks passed. Model tests
used blocked sockets and artificial responses; real paid requests were confined
to the explicitly authorized reviewer runs. Original data, prompts, memory code,
previous outputs and human forms were preserved. The project accounting databases
were intentionally updated to record actual charges. No dependency installation,
model download, training, final pilot construction or defense evaluation occurred.

[Before inventory](LLM_REVIEW_20261031_INTEGRITY_BEFORE.json),
[after inventory](LLM_REVIEW_20261031_INTEGRITY_AFTER.json), and
[validation record](LLM_REVIEW_20261031_VALIDATION.json) record preservation,
receipt reconciliation and current readiness.

## Concrete next steps toward our idea's preliminary result

1. Resolve the 22 rejected batches using a new, explicitly versioned review or
   genuine checking; retain every failed attempt. Inspect semantic quality on a
   blinded sample. Format/reference validity alone is insufficient.
2. Review additional development candidates in a fixed seeded order and improve
   source-grounded claim-backed questions. The current pool cannot supply the
   required AI-label composition. Estimate additional calls before spending.
3. Freeze an **AI-label-controlled exploratory** dataset and checked synthetic
   provenance overlay. Keep principal facts separate, attribution uncertainty
   explicit, labels private, and fixed audits/cohorts identical across arms.
4. Implement/finalize the exploratory execution manifest and run R/C/M/S with
   equal feedback and budgets. Measure attack outcomes plus retention, restraint,
   source-grounded utility, restrictions, refusals and coverage. Compare S with
   both C and M at matched utility; no historical 5.87% shortcut.
5. Treat a small run as a feasibility result, especially with few attack successes.
   Before stronger paper claims, independently audit label quality and run new
   frozen confirmation/robustness groups. If fixed multi-scope M explains the
   gains, the evidence does not support novelty of selective scope gating.

The current preliminary finding is **annotation feasibility with substantial
coverage/quality limitations**, not a demonstrated defense improvement.
