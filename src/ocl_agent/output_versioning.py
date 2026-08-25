"""Version final OCL deliverables without disturbing in-progress working files."""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

_VERSION_PATTERN = re.compile(r"^OCL_(?:Databook|Report)_v(\d+)\.(?:xlsx|pptx)$", re.IGNORECASE)


@dataclass(frozen=True)
class PublishedDeliverables:
    version: int
    databook: Path
    report: Path | None = None


def next_output_version(output_dir: Path) -> int:
    """Return the next global deliverable version in the output folder."""
    output_dir = Path(output_dir)
    highest = 0
    if output_dir.exists():
        for path in output_dir.iterdir():
            if not path.is_file():
                continue
            match = _VERSION_PATTERN.match(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def publish_versioned_deliverables(
    databook: Path,
    report: Path | None,
    output_dir: Path,
) -> PublishedDeliverables:
    """Publish one immutable versioned snapshot of the completed deliverables.

    The unversioned workbook/report remain working files while the workflow is
    still moving through Python and AI checkpoints. Only after a run is ready do
    we copy the finished files to a new matching vN pair. Existing versioned
    outputs are never overwritten.
    """
    databook = Path(databook)
    report = Path(report) if report is not None else None
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not databook.is_file():
        raise FileNotFoundError(f"Completed databook is missing: {databook}")
    if report is not None and not report.is_file():
        raise FileNotFoundError(f"Completed report is missing: {report}")

    version = next_output_version(output_dir)
    databook_target = output_dir / f"OCL_Databook_v{version}.xlsx"
    report_target = output_dir / f"OCL_Report_v{version}.pptx" if report is not None else None

    targets = [(databook, databook_target)]
    if report is not None and report_target is not None:
        targets.append((report, report_target))

    for _source, target in targets:
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite historical deliverable: {target}")

    temp_pairs: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        for source, target in targets:
            temp = output_dir / f".{target.name}.publishing"
            if temp.exists():
                temp.unlink()
            shutil.copy2(source, temp)
            temp_pairs.append((temp, target))

        for temp, target in temp_pairs:
            temp.replace(target)
            committed.append(target)
    except Exception:
        for temp, _target in temp_pairs:
            if temp.exists():
                temp.unlink()
        for target in committed:
            if target.exists():
                target.unlink()
        raise

    return PublishedDeliverables(
        version=version,
        databook=databook_target,
        report=report_target,
    )
