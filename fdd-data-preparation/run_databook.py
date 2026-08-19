"""Standalone entry point for the full embedded fdd-data-preparation workflow.

Normal OCL use should run the repository-root ``run_all.py``. This entry point is
kept only for direct data-preparation testing/debugging and uses the exact same
full AI-understanding + deterministic-Python runtime as the OCL bridge.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bootstrap import activate_full_runtime

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full embedded FDD data-preparation workflow.")
    parser.add_argument("--source", type=Path, default=ROOT.parent / "references" / "source")
    parser.add_argument("--work-root", type=Path, default=ROOT.parent / "work" / "data_prep" / "runs")
    parser.add_argument("--output-root", type=Path, default=ROOT.parent / "work" / "data_prep" / "output")
    parser.add_argument("--approval-mode", choices=("AUTONOMOUS", "REVIEW"), default="AUTONOMOUS")
    args = parser.parse_args()

    _project, fdd_data = activate_full_runtime()
    status = fdd_data.run_databook(
        args.source,
        args.work_root,
        args.output_root,
        approval_mode=args.approval_mode,
    )
    print(json.dumps(status, indent=2, ensure_ascii=False, default=str))

    coordination = status.get("coordination", {}) if isinstance(status, dict) else {}
    actor = str(coordination.get("next_actor") or "").upper()
    if actor == "AI_HOST":
        return 3
    if actor == "HUMAN":
        return 4
    if str(status.get("state") or "").upper() in {"FAILED", "FAILED_VALIDATION"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
