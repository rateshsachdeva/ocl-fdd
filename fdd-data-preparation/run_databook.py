"""Standalone entry point for the embedded data-preparation runtime."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fdd_data import prepare_source_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare raw FDD source files for the integrated OCL workflow.")
    parser.add_argument("--source", type=Path, default=ROOT.parent / "references" / "source")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "work" / "data_prep" / "latest")
    args = parser.parse_args()
    result = prepare_source_package(args.source, args.output)
    print(json.dumps({
        "state": "COMPLETED_WITH_WARNINGS" if result.warnings else "COMPLETED",
        "output_dir": str(result.output_dir),
        "datasets": [path.name for path in result.datasets],
        "warnings": list(result.warnings),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
