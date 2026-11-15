# ARCHIVED: `queries.sqlite` (compressed in place, 15 Nov 2026)

`queries.sqlite`, the result journal of this run, was compressed to save disk space. The owner approved it (tier 2 of `reports/CLEANUP_AUDIT_20261115.md`). **Nothing was lost.** The other files in this directory are unchanged.

| | File | Bytes | SHA-256 |
|---|---|---|---|
| Original (removed after verification) | `queries.sqlite` | 2,173,308,928 | `a87764057ca5fedb163cfba17c124de6cec6ee141fa7c6e0246e3943c6e0c984` |
| Archive (kept here) | `queries.sqlite.tar.gz` | 209,754,974 | `8d90b1baa45bf765a73daf3e034a678f9390f282d43bd0eb72cc41578debbd37` |

**Verification before the original was removed:**
- The archive extracted successfully.
- The restored file's SHA-256 equals the original's (`a87764057ca5fedb163cfba17c124de6cec6ee141fa7c6e0246e3943c6e0c984`).
- `PRAGMA integrity_check` on the restored file returned `ok`.

Script: `research_data/cleanup_20261115/archive_sqlite.sh`. Log: `research_data/cleanup_20261115/tier2_archives.txt`.

## Restore

```bash
cd research_data/provisional_extension_results_v1_20261101
tar -xzf queries.sqlite.tar.gz          # recreates queries.sqlite here (the archive is kept)
shasum -a 256 queries.sqlite            # must print a87764057ca5fedb163cfba17c124de6cec6ee141fa7c6e0246e3943c6e0c984
```

macOS and Linux `tar` both read `.tar.gz`; nothing extra needs installing. Restore before running any script that reads this journal: `scripts/inspect_research_state.py`, `scripts/report_development_comparison.py`, `scripts/diagnose_provisional_attacks.py`. No test and no protocol-v2 code reads it. Restoring needs about 2.17 GB of free disk.
