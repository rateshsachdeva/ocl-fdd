"""Repository paths and lightweight runtime discovery."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoPaths:
    root: Path
    assets: Path
    config: Path
    output: Path
    references: Path
    source: Path
    other: Path


def repo_paths(root: Path | None = None) -> RepoPaths:
    base = (root or Path(__file__).resolve().parents[2]).resolve()
    return RepoPaths(
        root=base,
        assets=base / "assets",
        config=base / "config",
        output=base / "output",
        references=base / "references",
        source=base / "references" / "source",
        other=base / "references" / "other",
    )


def ensure_runtime_folders(root: Path | None = None) -> RepoPaths:
    paths = repo_paths(root)
    for path in (paths.assets, paths.config, paths.output, paths.source, paths.other):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def discover_data_prep_output(paths: RepoPaths, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).resolve()
    candidates: list[Path] = []
    environment_path = os.getenv("FDD_DATA_PREP_OUTPUT")
    if environment_path:
        candidates.append(Path(environment_path).expanduser().resolve())
    sibling = paths.root.parent / "fdd-data-preparation" / "output" / "latest"
    if sibling.is_dir():
        candidates.append(sibling.resolve())
    if paths.source.is_dir() and any(paths.source.glob("*.csv")):
        candidates.append(paths.source.resolve())
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    if len(unique) == 1:
        return unique[0]
    if not unique:
        raise FileNotFoundError(
            "No fdd-data-preparation output was found automatically. Pass --data-prep-output once, or place the repos side-by-side."
        )
    raise ValueError("Multiple possible standardized output directories were found; pass --data-prep-output explicitly.")
