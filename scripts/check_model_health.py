"""CLI check for online model health alerts.

Exit codes:
- 0: no warning/critical alerts
- 2: warning alerts present
- 3: critical alerts present
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.monitoring.model_health import get_model_health_snapshot


def main() -> int:
    snapshot = get_model_health_snapshot()
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))

    severities = {a.get("severity") for a in snapshot.get("alerts", [])}
    if "critical" in severities:
        return 3
    if "warning" in severities:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
