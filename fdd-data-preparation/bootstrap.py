"""Materialize and activate the full source-controlled fdd-data-preparation runtime.

The full project supplied for this skill is vendored as a base64-encoded runtime
archive split into small text chunks under ``vendor/runtime_parts``. The archive
contains the real profiler, AI-host orchestration, Dataset Map / Processing Plan
contracts, deterministic executor, completeness controls, lineage and generic
knowledge stores. It is expanded locally on first use into ``runtime/``.
"""
from __future__ import annotations

import base64
import hashlib
import shutil
import sys
import tempfile
import zlib
from pathlib import Path
from zipfile import BadZipFile, ZipFile

REFERENCE_BUNDLE_SHA256 = "27c75c2047bb1156f42dc5eebcaffac3f8c2a84c9262662c64377cbecf8c700f"
ROOT = Path(__file__).resolve().parent
PARTS = ROOT / "vendor" / "runtime_parts"
RUNTIME = ROOT / "runtime"
PERSISTENT_KNOWLEDGE = ROOT.parent / "work" / "data_prep" / "knowledge"
REQUIRED_RUNTIME_PATHS = (
    "src/fdd_data/orchestration.py",
    "src/fdd_data/profiler.py",
    "src/fdd_data/dataset_map.py",
    "src/fdd_data/processing_plan.py",
    "src/fdd_data/executor.py",
    "src/fdd_data/completeness.py",
    "src/fdd_data/lineage.py",
    "instructions/AI_HOST_ORCHESTRATION.md",
    "instructions/dataset_understanding.md",
    "instructions/processing_plan.md",
    "schemas/dataset_map.schema.json",
    "schemas/processing_plan.schema.json",
)


def ensure_full_runtime() -> Path:
    """Return the extracted full project root, recreating it only when stale."""
    chunks = sorted(PARTS.glob("part_*.b64"))
    if not chunks:
        raise FileNotFoundError("Full fdd-data-preparation runtime parts are missing from the repository.")
    encoded = "".join(path.read_text(encoding="ascii").strip() for path in chunks)
    try:
        archive = base64.b64decode(encoded, validate=True)
    except Exception as error:  # pragma: no cover
        raise RuntimeError(f"The vendored fdd-data-preparation runtime is not valid base64: {error}") from error
    digest = hashlib.sha256(archive).hexdigest()

    project = RUNTIME / "fdd-data-preparation"
    marker = RUNTIME / ".bundle_sha256"
    if project.is_dir() and marker.exists() and marker.read_text(encoding="utf-8").strip() == digest:
        _assert_required_runtime(project)
        _overlay_persistent_knowledge(project)
        return project

    ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fdd_data_prep_", dir=ROOT) as temporary_directory:
        temporary = Path(temporary_directory)
        archive_path = temporary / "runtime.zip"
        archive_path.write_bytes(archive)
        extracted = temporary / "extracted"
        try:
            with ZipFile(archive_path) as package:
                bad_members = _bad_zip_members(package)
                if bad_members:
                    raise RuntimeError(
                        "The vendored fdd-data-preparation runtime failed ZIP CRC/decompression validation. "
                        f"Bad members: {', '.join(bad_members)}. Observed bundle SHA-256: {digest}."
                    )
                package.extractall(extracted)
        except BadZipFile as error:
            raise RuntimeError(
                "The vendored fdd-data-preparation runtime is not a valid ZIP archive. "
                f"Observed bundle SHA-256: {digest}."
            ) from error
        candidate = extracted / "fdd-data-preparation"
        _assert_required_runtime(candidate)
        if RUNTIME.exists():
            _preserve_runtime_knowledge(project)
            shutil.rmtree(RUNTIME)
        RUNTIME.mkdir(parents=True, exist_ok=False)
        shutil.move(str(candidate), str(project))
        marker.write_text(digest + "\n", encoding="utf-8")
        (RUNTIME / ".bundle_reference_sha256").write_text(
            f"reference={REFERENCE_BUNDLE_SHA256}\nobserved={digest}\n",
            encoding="utf-8",
        )
    _overlay_persistent_knowledge(project)
    return project


def activate_full_runtime() -> tuple[Path, object]:
    project = ensure_full_runtime()
    source = project / "src"
    source_text = str(source)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    loaded = sys.modules.get("fdd_data")
    if loaded is not None:
        loaded_file = str(getattr(loaded, "__file__", "") or "")
        if source_text not in loaded_file:
            for name in [name for name in sys.modules if name == "fdd_data" or name.startswith("fdd_data.")]:
                del sys.modules[name]
    import fdd_data  # type: ignore
    return project, fdd_data


def sync_runtime_knowledge() -> None:
    _preserve_runtime_knowledge(RUNTIME / "fdd-data-preparation")


def _bad_zip_members(package: ZipFile) -> list[str]:
    bad: list[str] = []
    for info in package.infolist():
        if info.is_dir():
            continue
        try:
            package.read(info)
        except (BadZipFile, EOFError, OSError, RuntimeError, zlib.error):
            bad.append(info.filename)
    return bad


def _assert_required_runtime(project: Path) -> None:
    missing = [relative for relative in REQUIRED_RUNTIME_PATHS if not (project / relative).exists()]
    if missing:
        raise RuntimeError(
            "Vendored runtime archive does not contain the expected full fdd-data-preparation project: "
            + ", ".join(missing)
        )


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
    print(ensure_full_runtime())
