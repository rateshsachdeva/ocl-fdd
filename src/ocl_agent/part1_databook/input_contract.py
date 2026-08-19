"""Contract for consuming an approved fdd-data-preparation publication.

Part 1 consumes standardized outputs.  It does not rediscover or reshape raw
client workbooks during the normal OCL workflow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class InputContractError(ValueError):
    pass


@dataclass(frozen=True)
class StandardizedPackage:
    root: Path
    datasets: tuple[Path, ...]
    metadata: Path | None
    execution_manifest: Path | None
    lineage: Path | None
    field_lineage: Path | None


def discover_standardized_package(root: Path) -> StandardizedPackage:
    root = Path(root).resolve()
    if not root.exists() or not root.is_dir():
        raise InputContractError(f"Standardized output directory does not exist: {root}")

    datasets = tuple(
        sorted(
            path
            for path in root.glob("*.csv")
            if path.name not in {"lineage.csv", "field_lineage.csv", "exclusions.csv", "processing_issues.csv"}
        )
    )
    if not datasets:
        raise InputContractError("No standardized CSV dataset was found in the approved publication directory.")

    manifest = root / "execution_manifest.json"
    metadata = root / "databook_metadata.json"
    lineage = root / "lineage.csv"
    field_lineage = root / "field_lineage.csv"

    if manifest.exists():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        status = payload.get("final_execution_status")
        if status not in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
            raise InputContractError(f"Upstream execution is not publishable: {status!r}")

    return StandardizedPackage(
        root=root,
        datasets=datasets,
        metadata=metadata if metadata.exists() else None,
        execution_manifest=manifest if manifest.exists() else None,
        lineage=lineage if lineage.exists() else None,
        field_lineage=field_lineage if field_lineage.exists() else None,
    )
