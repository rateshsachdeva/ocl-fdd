"""Deterministic, read-only discovery of supported Excel source files."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path

from .models import ProfilingCapability, SourceFile
from .source_provider import SourceProvider

DISCOVERABLE_EXCEL_EXTENSIONS = frozenset({".xlsx", ".xlsm", ".xltx", ".xltm", ".xlsb", ".xls"})
FULLY_PROFILEABLE_EXCEL_EXTENSIONS = frozenset({".xlsx", ".xlsm", ".xltx", ".xltm"})
SUPPORTED_EXCEL_EXTENSIONS = DISCOVERABLE_EXCEL_EXTENSIONS


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a file without altering it."""
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_source_files(provider: SourceProvider) -> list[SourceFile]:
    """Discover supported Excel files while ignoring temporary Office lock files."""
    source_files: list[SourceFile] = []
    for path in provider.iter_files():
        extension = path.suffix.lower()
        if path.name.startswith("~$") or extension not in DISCOVERABLE_EXCEL_EXTENSIONS:
            continue

        stat = path.stat()
        file_hash = sha256_file(path)
        provider_root = getattr(provider, "source_directory", None)
        try:
            relative_identity = path.resolve().relative_to(Path(provider_root).resolve()).as_posix()
        except (TypeError, ValueError):
            relative_identity = path.name
        source_identity = hashlib.sha256(
            f"{relative_identity}\0{file_hash}".encode("utf-8")
        ).hexdigest()
        source_files.append(
            SourceFile(
                source_id=f"source:{source_identity}",
                filename=path.name,
                path=path,
                extension=extension,
                size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                sha256=file_hash,
                profiling_capability=(
                    ProfilingCapability.FULL
                    if extension in FULLY_PROFILEABLE_EXCEL_EXTENSIONS
                    else ProfilingCapability.DEFERRED_UNSUPPORTED
                ),
            )
        )
    return source_files
