"""Main OCL workflow entry point.

Compatibility rule: `python run_all.py` remains the public launcher.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ocl_agent.config import ensure_runtime_folders
from ocl_agent.part1_databook.run import prepare_foundation


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OCL FDD workflow.")
    parser.add_argument(
        "--data-prep-output",
        type=Path,
        help="Approved fdd-data-preparation publication directory (for example output/latest).",
    )
    parser.add_argument("--foundation-only", action="store_true", help="Validate the Part 1 foundation handoff only.")
    args = parser.parse_args()

    paths = ensure_runtime_folders()
    if args.data_prep_output is None:
        parser.error("--data-prep-output is required until automatic upstream handoff discovery is implemented.")

    foundation = prepare_foundation(args.data_prep_output, paths.config)
    print(f"Standardized datasets: {len(foundation.package.datasets)}")
    print(f"Reviewed/configured labels: {len(foundation.judgments.by_source_label)}")
    print("Part 1 foundation handoff: READY")

    if args.foundation_only:
        return 0

    print("Full Part 1 semantic adaptation and Parts 2-4 are not yet enabled in this foundation milestone.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
