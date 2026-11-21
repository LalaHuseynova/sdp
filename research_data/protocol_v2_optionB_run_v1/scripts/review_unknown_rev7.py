"""Revision 7 owner review (19 Nov 2026): book the unknown transport-failure attempt(s) of one
guarded session at their full worst case, clear its stop, and move the failed dispatch row(s)
to `superseded_dispatches` so the same request can be sent again. Run only with P-B2 stopped.

    uv run python research_data/protocol_v2_optionB_run_v1/scripts/review_unknown_rev7.py SESSION_DIR REASON
"""

import sys
from pathlib import Path

from ams.research.workload.transport import ConstructionSession


def show(s, label):
    snap = s.guard.snapshot()
    failed = s.db.execute("SELECT count(*) FROM dispatches WHERE status!='completed'").fetchone()[0]
    print(f"{label}: blocked={snap['blocked']} reason={snap['blocked_reason']!r} "
          f"used=${snap['used_usd']} held=${snap['held_usd']} counts={snap['counts']} "
          f"not-completed dispatches={failed}")  # fmt: skip


def main(session, reason):
    with ConstructionSession(Path(session)) as s:
        show(s, "before")
        if s.guard.snapshot()["blocked"]:
            ids = s.guard.resolve_unknown_at_worst_case(reason)
            print("booked at worst case:", ids)
        moved = s.supersede_reviewed_failures(reason)
        print("failed rows moved to superseded_dispatches:", moved)
        show(s, "after")


if __name__ == "__main__":
    main(*sys.argv[1:3])
