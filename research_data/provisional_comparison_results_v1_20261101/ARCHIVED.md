# ARCHIVED: `queries.sqlite` (compressed in place, 15 Nov 2026)

`queries.sqlite`, the result journal of this run, was compressed to save disk space. The owner approved it (tier 2 of `reports/CLEANUP_AUDIT_20261115.md`). **Nothing was lost.** The other files in this directory are unchanged.

| | File | Bytes | SHA-256 |
|---|---|---|---|
| Original (removed after verification) | `queries.sqlite` | 309,731,328 | `1801ce783a9e6544f54d1a32dc9b771965e238dd54bd9e74c72d12e9ad40d785` |
| Archive (kept here) | `queries.sqlite.tar.gz` | 29,924,851 | `ebd5927b9839a8b0ca06ba94576f679b2fc3b87236566929a61df461ec49fbeb` |

**Verification before the original was removed:**
- The archive extracted successfully.
- The restored file's SHA-256 equals the original's (`1801ce783a9e6544f54d1a32dc9b771965e238dd54bd9e74c72d12e9ad40d785`).
- `PRAGMA integrity_check` on the restored file returned `ok`.

Script: `research_data/cleanup_20261115/archive_sqlite.sh`. Log: `research_data/cleanup_20261115/tier2_archives.txt`.

## Restore

```bash
cd research_data/provisional_comparison_results_v1_20261101
tar -xzf queries.sqlite.tar.gz          # recreates queries.sqlite here (the archive is kept)
shasum -a 256 queries.sqlite            # must print 1801ce783a9e6544f54d1a32dc9b771965e238dd54bd9e74c72d12e9ad40d785
```

macOS and Linux `tar` both read `.tar.gz`; nothing extra needs installing. Restore before running any script that reads this journal: `scripts/inspect_research_state.py`, `scripts/report_development_comparison.py`, `scripts/diagnose_provisional_attacks.py`. No test and no protocol-v2 code reads it. Restoring needs about 0.31 GB of free disk.
