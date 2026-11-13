# Complete implementation illustration

The figure covers the implemented research workflow, from MPBench preparation to private answer evaluation. It replaces the earlier narrow concept view for the purpose of this request. Existing project figures were not overwritten.

- `selective_evidence_propagation_full_implementation.png`: final figure, 1500 × 1049 pixels.
- `CAPTION.md`: suggested paper caption.
- `PROMPTS.md`: exact built-in image-generation prompt and two correction prompts.
- `image_manifest.json`: dimensions, checksum, provenance and visual checks.

The image is a raster PNG. It is not an editable vector figure. Its pixel dimensions are recorded as generated; it was not enlarged to suggest additional detail.

## Reading the figure

1. Preparation recovers saved claims and reconstructs source chunks offline. It adds source links and synthetic grouping metadata, then freezes a common memory store.
2. Five shared contribution/use audit tickets reveal saved AI assessments. The ledger records their scope, deduplicates known incidents and supports corrections.
3. R, C, M and S use different propagation scopes. Only S requires the displayed support gates before using a broader scope.
4. Retrieval checks authority, permissions, direct findings and policy penalties before sending eligible text to the answer model. Private evaluation receives the answers and supplies no trust feedback.

## Details summarized in the artwork

`U` and `Safe` are counts of distinct directly audited incident roots in the relevant group. Unresolved reviews add neither count. The penalty is a scoring heuristic, not a calibrated probability.

For S, batch support requires one unsafe incident. Context support requires at least two unsafe incidents from two batches of the same contributor/context. Contributor support requires at least four unsafe incidents, including at least two spanning both batches in each of two contexts. S uses the maximum penalty over its supported scopes.

One unsafe incident with no safe observations gives a penalty of 1/6, below the 0.25 hard gate. Support does not by itself imply withholding every related memory. Exact safe-use exceptions bypass reputation penalties while remaining subject to original authority and permissions. Unsafe findings apply to the reviewed record/content/use/policy scope.

Claims and chunks remain separate records. Principal-authored statements retain principal ownership. A batch groups four independent contributions; it does not establish copying. Synthetic identities assume trusted attribution within the experiment and do not authenticate real people.

The three overlay conditions describe offline study construction. Their names, hidden profiles, original case labels and unrevealed verdicts are not inputs to the online policy. The current development groups control original attack-input frequency, not independently verified unsafe-memory frequency.

The supported retrieval path is flat indexing, withhold mode and hops=0. Original external-evidence admission remains in force. The full-dataset SAFE-Mem reproduction and the limited evaluation of S are separate experiments. This figure contains no performance claims; the preliminary comparison did not show an ASR improvement over C or M.

## Code map

| Figure section | Main implementation locations |
| --- | --- |
| 1. Preparation and provenance | `src/ams/research/recovery/`, `provisional/`, `native/` |
| 2. Revealed reviews and evidence | `src/ams/research/provisional_run/preparation.py`, `dynamic/ledger.py` |
| 3. Propagation policies | `src/ams/research/dynamic/policies.py`, `dynamic/ledger.py` |
| 4. Retrieval, execution and analysis | `src/ams/research/retrieval/`, `sequential/`, `execution/`, `comparison.py` |

Generation used the built-in image tool. No benchmark evaluation, training or OpenRouter request was run to make this asset. Only this new output folder was written.
