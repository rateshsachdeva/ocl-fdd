"""Atomically publish immutable versioned OCL databooks."""
from __future__ import annotations

import re
import shutil
import hashlib
from dataclasses import dataclass
from pathlib import Path

_VERSION_PATTERN = re.compile(r"^OCL_Databook_v(\d+)\.xlsx$", re.IGNORECASE)


@dataclass(frozen=True)
class PublishedDatabook:
    version: int
    databook: Path


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


def publish_versioned_databook(
    databook: Path,
    output_dir: Path,
    *,
    expected_sha256: str | None = None,
) -> PublishedDatabook:
    """Publish one immutable databook version using an atomic final rename."""
    databook = Path(databook)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not databook.is_file():
        raise FileNotFoundError(f"Completed databook is missing: {databook}")

    version = next_output_version(output_dir)
    databook_target = output_dir / f"OCL_Databook_v{version}.xlsx"
    if databook_target.exists():
        raise FileExistsError(f"Refusing to overwrite historical deliverable: {databook_target}")
    temp = output_dir / f".{databook_target.name}.publishing"
    try:
        if temp.exists():
            temp.unlink()
        shutil.copy2(databook, temp)
        if expected_sha256 is not None and _sha256_file(temp) != expected_sha256:
            raise RuntimeError("Published databook copy does not match the exact final-QA workbook bytes.")
        temp.replace(databook_target)
    except Exception:
        if temp.exists():
            temp.unlink()
        raise

    return PublishedDatabook(version=version, databook=databook_target)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
