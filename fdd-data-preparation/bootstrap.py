"""Materialize and activate the full, source-controlled fdd-data-preparation runtime.

The original full project supplied for this skill is vendored as a checksum-bound
runtime archive split into small text chunks under ``vendor/runtime_parts``.
Keeping the archive split avoids GitHub connector binary limitations while still
preserving the exact Python source, schemas, AI-host instructions and canonical
knowledge stores. The archive is expanded locally on first use into ``runtime/``;
that generated directory is never committed.
"""
from __future__ import annotations

import base64
import hashlib
import shutil
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

BUNDLE_SHA256 = "27c75c2047bb1156f42dc5eebcaffac3f8c2a84c9262662c64377cbecf8c700f"
ROOT = Path(__file__).resolve().parent
PARTS = ROOT / "vendor" / "runtime_parts"
RUNTIME = ROOT / "runtime"
PERSISTENT_KNOWLEDGE = ROOT / "knowledge"


def ensure_full_runtime() -> Path:
    """Return the extracted full project root, recreating it only when stale."""
    project = RUNTIME / "fdd-data-preparation"
    marker = RUNTIME / ".bundle_sha256"
    if project.is_dir() and marker.exists() and marker.read_text(encoding="utf-8").strip() == BUNDLE_SHA256:
        _overlay_persistent_knowledge(project)
        return project

    chunks = sorted(PARTS.glob("part_*.b64"))
    if not chunks:
        raise FileNotFoundError("Full fdd-data-preparation runtime parts are missing from the repository.")
    encoded = "".join(path.read_text(encoding="ascii").strip() for path in chunks)
    try:
        archive = base64.b64decode(encoded, validate=True)
    except Exception as error:  # pragma: no cover - defensive corruption guard
        raise RuntimeError(f"The vendored fdd-data-preparation runtime is not valid base64: {error}") from error
    digest = hashlib.sha256(archive).hexdigest()
    if digest != BUNDLE_SHA256:
        raise RuntimeError(
            "The vendored fdd-data-preparation runtime failed its SHA-256 integrity check: "
            f"expected {BUNDLE_SHA256}, got {digest}."
        )

    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fdd_data_prep_", dir=ROOT) as temporary_directory:
        temporary = Path(temporary_directory)
        archive_path = temporary / "runtime.zip"
        archive_path.write_bytes(archive)
        extracted = temporary / "extracted"
        with ZipFile(archive_path) as package:
            package.extractall(extracted)
        candidate = extracted / "fdd-data-preparation"
        if not (candidate / "src" / "fdd_data" / "orchestration.py").exists():
            raise RuntimeError("Vendored runtime archive does not contain the expected full fdd-data-preparation project.")
        if RUNTIME.exists():
            _preserve_runtime_knowledge(project)
            shutil.rmtree(RUNTIME)
        RUNTIME.mkdir(parents=True, exist_ok=False)
        shutil.move(str(candidate), str(project))
        marker.write_text(BUNDLE_SHA256 + "\n", encoding="utf-8")
    _overlay_persistent_knowledge(project)
    return project


def activate_full_runtime() -> tuple[Path, object]:
    """Extract the full project if needed, put its ``src`` first on sys.path, and import fdd_data."""
    project = ensure_full_runtime()
    source = project / "src"
    source_text = str(source)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    # The old lightweight package must never win module resolution.
    loaded = sys.modules.get("fdd_data")
    if loaded is not None:
        loaded_file = str(getattr(loaded, "__file__", "") or "")
        if source_text not in loaded_file:
            for name in [name for name in sys.modules if name == "fdd_data" or name.startswith("fdd_data.")]:
                del sys.modules[name]
    import fdd_data  # type: ignore
    return project, fdd_data


def sync_runtime_knowledge() -> None:
    """Persist any safe learning updates from the extracted runtime across runs/upgrades."""
    project = RUNTIME / "fdd-data-preparation"
    _preserve_runtime_knowledge(project)


def _overlay_persistent_knowledge(project: Path) -> None:
    source = PERSISTENT_KNOWLEDGE
    destination = project / "knowledge"
    if not source.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("field_knowledge.csv", "structure_knowledge.csv", "corrections.csv"):
        path = source / name
        if path.exists():
            shutil.copy2(path, destination / name)


def _preserve_runtime_knowledge(project: Path) -> None:
    source = project / "knowledge"
    if not source.is_dir():
        return
    PERSISTENT_KNOWLEDGE.mkdir(parents=True, exist_ok=True)
    for name in ("field_knowledge.csv", "structure_knowledge.csv", "corrections.csv"):
        path = source / name
        if path.exists():
            shutil.copy2(path, PERSISTENT_KNOWLEDGE / name)


if __name__ == "__main__":
    runtime = ensure_full_runtime()
    print(runtime)
