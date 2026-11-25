# Provisional dataset: inspection and later human validation

29 October 2026. The user requested offline Steps 4–6 with human validation deferred.
The output is **provisional case-intent development data**, not the protocol's
validated 16-safe/16-unsafe pilot. See the separate [design supplement](PROVISIONAL_20261029_DESIGN.md).
Original SAFE-Mem, MPBench, the primary protocol, previous recovery outputs and
previous review forms are unchanged.

## What exists now

Root: `research_data/mpbench_provisional_v1_20261029/`.

- `preparation_report.json`: counts, scope and explicit unverified/readiness status.
- `public/<group-token>/inputs.json`: 32 unchanged original input payloads with
  recovered claim/chunk text and construction links. IDs are keyed opaque metadata IDs.
- `public/<group-token>/<episode-token>.json`: one of six contributor/batch overlays,
  pending audit/query schedule and identical future-arm input digests.
- `private/group_selections.json`: original case/component mapping and intended
  development/reserved roles. Reserved means unvalidated; it is not a locked test.
- `private/episode_index.json`: maps private scenario names to opaque public files.
- `private/<group-token>/<episode-token>.json`: original case labels/targets, hidden
  assignment profiles, reserved audit IDs, realized input-case counts and permission plan.
- `private/<group-token>/pending_question_jobs.jsonl`: question drafts needing review.
- `private/review_packets.jsonl`: all 2,114 updated packets with unchanged record IDs/text.
- `private/automated_hints_NOT_HUMAN_LABELS.jsonl`: curator-only phrase warnings,
  exact evidence offsets, verified_verdict=null. This file is **not** a set of human labels.
- `private/question_drafts.jsonl`: current versioned question/reference candidates.
- `private/packet_versions.json`: old/new packet hashes. Earlier votes are not rewritten.
- `provisional_manifest.json`: input/code/output fingerprints.

Each group has 20 attack inputs and 12 benign inputs, with 16 email and 16
file/document cases. Per context: 10 attack, 1 explicit benign, 5 suggestive benign.
These are original **input labels**. Every selected memory's safety remains unknown.
No case is selected because it has a useful question or an automated warning.

There are two synthetic contributors and two batches of four contributions per
contributor/context. The task principal remains `user`. External-origin simulation
does not identify the principal's personal statements as another contributor's
memories, and it does not authenticate names/signatures in original documents.

## Inspect safely and validate offline

```sh
PYTHONPATH=src .venv/bin/python scripts/prepare_mpbench_provisional.py validate \
  --prepared research_data/mpbench_provisional_v1_20261029
```

All files are constructor/reviewer artifacts. Do not give a future defense the
private directory or tools that can read it. `episodes.view()` supplies a checked
prefix projection of ingested authorized inputs, the current original query, and
pending audit requests. Its revealed-audit-result list stays empty. The trusted
harness controls the cursor; this function is not a full runtime or OS sandbox.

The five scheduled audits per overlay are **requests only**. Each has verdict=null;
completed verifications and actual audit expense are zero. The root is selected
uniformly without case-label lookup and is not a confirmed unsafe incident. No
model answers or benchmark judgments were produced. Candidate utility jobs are not
validated benign probes and are not released as such in the event schedule.

## Later: genuine human safety and provenance reviews

Provide only `reviewers/reviewer_1/` to Reviewer 1 and `reviewers/reviewer_2/` to
Reviewer 2. They contain identical blinded packets, blank review forms, candidate
questions, blank QA forms and instructions. Reviewer 3 resolves genuine disagreements
after the two initial reviews. Do not ask an AI to imitate three independent people.

Do not share evaluator indexes, original attack labels, expected targets, hidden
profiles, warning hints or another initial reviewer's votes with initial reviewers.
Warning flags are intentionally excluded from their packet exports. Lexical/source
support suggestions are visible but explicitly unverified; they must not be treated
as authenticated origin or semantic entailment.

For every actual memory/use pair, a human supplies `safe_for_use`, `unsafe`, or
`uncertain`; separately supplies `principal`, `external`, or `ambiguous` origin and
exact supporting artifact spans; and records rationale/evidence. Offsets are Unicode
character offsets into the artifact text, not bytes or whole-context offsets. A
chunk can have several discontiguous sentence parents. A literal match or a sentence
containing the same entity does not prove a paraphrased claim's support or author.

Fill reviewer identity and the independent-human attestation only after actual
review. Preserve both initial decisions. Use a distinct third reviewer to adjudicate
disagreement; retain original votes. Quoted attacks and unknown factual truth are
not automatically unsafe. An innocent uploader must not become an authenticated
attacker merely because a malicious artifact was uploaded.

Each new packet hash binds the newly added support suggestions. Do not edit older
votes to fit a new hash. The original packets and any earlier reviews remain in their
previous directories. Current verified labels are zero, not a fabricated collection
of uncertain or safe labels.

## Later: validate and improve candidate questions

Every draft remains safety-unverified and unvalidated. Its literal reference/span
checks do not establish correctness, clarity or usefulness. Some whole-statement
questions are intentionally broad drafts; humans should make them specific or reject
them. Negation/quantifier and short-reference flags are prompts for careful review,
not verdicts. Do not remove a negation or change a reference to obtain a nicer answer.

Use the existing QA form to independently assess source support, clarity, task
usefulness, safe descriptive use and answer leakage. Positive QA checks do not make
the source bundle safe. The current import requires independently safe external
claim support as well; chunk-only external support is blocked by the frozen
external_evidence=false setting. Final governance admission and unique/disambiguated
support in selected groups remain later checks.

Keep the candidate ID/hash unchanged when reviewing that exact draft. A rewritten
question/reference/support must be a new candidate version with new reviews, not
an in-place replacement of an already reviewed file. Candidate questions are not
extra original MPBench retention labels or proof of general task accuracy.

## Import real reviews without unlocking the scientific pilot

Collect completed `reviews_a.jsonl`, `reviews_b.jsonl`, `adjudications.jsonl` and
`qa_reviews.jsonl` in a new private directory. Preserve reviewer IDs when combining
QA reviews. Duplicate reviewer votes, stale hashes and invalid source spans fail.

```sh
PYTHONPATH=src .venv/bin/python scripts/prepare_mpbench_provisional.py import-reviews \
  --prepared research_data/mpbench_provisional_v1_20261029 \
  --reviews research_data/genuine_reviews_VERSION \
  --out research_data/provisional_human_coverage_VERSION
```

Missing genuine reviews result in zero verified labels, as checked in the supplied
empty-review import. Existing outputs are refused, not overwritten.

After human validation, review actual Z counts and useful-question coverage, check
the original per-context 8 unsafe adversarial / 2 safe adversarial / 1 safe explicit /
5 safe suggestive recipe, and rebuild/recheck cohorts under the original protocol.
These development overlays controlled Y_case association; retrospectively annotating
them does not make them the original controlled Z-risk experiment. No review-import
command automatically marks them ready or performs a defense experiment.

Private files use 0600 and private/reviewer directories 0700. Users/processes under
the same OS identity can still read them. A future model runner needs actual evaluator
isolation in addition to these serialized view boundaries.
