#!/usr/bin/env python3
"""Run existing tests with networking blocked and macOS spawn support.

Example:
    .venv/bin/python scripts/check_research_offline.py -q tests

Use a real main file: multiprocessing's spawn mode cannot reload a stdin script.
This command neither installs dependencies nor loads API credentials.
"""

import sys

import pytest

from ams.research.recovery.offline import no_network


def main():
    with no_network():
        return pytest.main(sys.argv[1:] or ["-q", "tests"])


if __name__ == "__main__":
    raise SystemExit(main())
