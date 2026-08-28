"""Materialize and activate the full source-controlled fdd-data-preparation runtime.

The supplied full project is vendored as a base64 runtime archive. The archive's
old standalone ``run_databook.py`` member is not part of the imported runtime and
is known to be damaged in the historical bundle; the repository now provides a
clean standalone wrapper outside the bundle. All required runtime modules still
receive full CRC/decompression validation before activation.

Reusable knowledge persistence/promotion is intentionally delegated to
``knowledge_system/store.py`` so bootstrap remains focused on runtime lifecycle.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
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
IGNORED_BUNDLE_MEMBERS = {"fdd-data-preparation/run_databook.py"}
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
_KNOWLEDGE_MODULE_NAME = "_ocl_fdd_knowledge_system_store"


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
        _apply_runtime_repairs(project)
        _assert_required_runtime(project)
        _knowledge_module().hydrate_runtime(project, ROOT.parent, refresh_baseline=False)
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
                unexpected_bad = [name for name in bad_members if name not in IGNORED_BUNDLE_MEMBERS]
                if unexpected_bad:
                    raise RuntimeError(
                        "The vendored fdd-data-preparation runtime failed ZIP CRC/decompression validation. "
                        f"Bad runtime members: {', '.join(unexpected_bad)}. Observed bundle SHA-256: {digest}."
                    )
                for info in package.infolist():
                    if info.filename in IGNORED_BUNDLE_MEMBERS:
                        continue
                    package.extract(info, extracted)
        except BadZipFile as error:
            raise RuntimeError(
                "The vendored fdd-data-preparation runtime is not a valid ZIP archive. "
                f"Observed bundle SHA-256: {digest}."
            ) from error
        candidate = extracted / "fdd-data-preparation"
        _assert_required_runtime(candidate)
        _apply_runtime_repairs(candidate)
        if RUNTIME.exists():
            # Reusable knowledge is promoted only after a successful published
            # workflow. Do not persist possibly partial runtime edits here.
            shutil.rmtree(RUNTIME)
        RUNTIME.mkdir(parents=True, exist_ok=False)
        shutil.move(str(candidate), str(project))
        marker.write_text(digest + "\n", encoding="utf-8")
        (RUNTIME / ".bundle_reference_sha256").write_text(
            f"reference={REFERENCE_BUNDLE_SHA256}\nobserved={digest}\n",
            encoding="utf-8",
        )
    _knowledge_module().hydrate_runtime(project, ROOT.parent, refresh_baseline=True)
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


def sync_runtime_knowledge(
    *,
    source_dir: Path | None = None,
    source_fingerprint: str | None = None,
) -> dict:
    """Promote safe reusable knowledge after a successfully published run."""
    return _knowledge_module().promote_runtime(
        RUNTIME / "fdd-data-preparation",
        ROOT.parent,
        source_dir=source_dir,
        source_fingerprint=source_fingerprint,
    )


def _knowledge_module():
    loaded = sys.modules.get(_KNOWLEDGE_MODULE_NAME)
    if loaded is not None:
        return loaded
    path = ROOT / "knowledge_system" / "store.py"
    if not path.exists():
        raise FileNotFoundError("Reusable knowledge subsystem is missing from fdd-data-preparation.")
    spec = importlib.util.spec_from_file_location(_KNOWLEDGE_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the reusable knowledge subsystem.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_KNOWLEDGE_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _apply_runtime_repairs(project: Path) -> None:
    """Apply small, source-controlled repairs to the materialized vendor runtime."""
    path = ROOT / "vendor" / "repairs" / "runtime_repairs.py"
    spec = importlib.util.spec_from_file_location("_ocl_fdd_runtime_repairs", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load fdd-data-preparation runtime repairs.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.apply_runtime_repairs(project)


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


if __name__ == "__main__":
    print(ensure_full_runtime())
