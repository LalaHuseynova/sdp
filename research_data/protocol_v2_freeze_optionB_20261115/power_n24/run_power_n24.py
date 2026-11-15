"""Power of the option-B design (24 groups), using the frozen protocol-v2 power code
(scripts/power_protocol_v2b.py, unchanged) with its group grid set to N = 24.
Free, offline, read-only; the same calibration data as rev 2 (dev + locked test v1)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
import power_protocol_v2b as PB  # noqa: E402

PB.NS = (24,)
sys.argv = ["power_protocol_v2b.py", "--out", str(Path(__file__).parent / "power_analysis_n24.json")]
PB.main()
