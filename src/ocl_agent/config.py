"""Repository paths and non-destructive human-owned configuration handling."""

from __future__ import annotations

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
