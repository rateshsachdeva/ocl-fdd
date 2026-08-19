"""Source-location abstractions used by deterministic discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class SourceProvider(ABC):
    """Provides local paths for source-file discovery without modifying them."""

    @abstractmethod
    def iter_files(self) -> Iterable[Path]:
        """Return files available for discovery."""


@dataclass(frozen=True, slots=True)
class LocalFolderSourceProvider(SourceProvider):
    """Provides files from a single local source directory and its subdirectories."""

    source_directory: Path

    def __post_init__(self) -> None:
        directory = Path(self.source_directory)
        if not directory.exists():
            raise FileNotFoundError(f"Source directory does not exist: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"Source path is not a directory: {directory}")
        object.__setattr__(self, "source_directory", directory)

    def iter_files(self) -> Iterable[Path]:
        return (path for path in sorted(self.source_directory.rglob("*")) if path.is_file())
