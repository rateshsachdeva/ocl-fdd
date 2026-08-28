"""Small deterministic checkpoint contract for resumable OCL workbook runs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

CHECKPOINT_VERSION = "1.0"
STAGES = {"PART1_READY", "ANALYSIS_READY", "INTERPRETATION_READY", "READY"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_directory(root: Path) -> str:
    """Hash relative paths and bytes for the exact published package."""
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def sha256_named_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted((Path(item) for item in paths), key=lambda item: item.name.casefold()):
        name = path.name.encode("utf-8")
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        if path.is_file():
            digest.update(b"\x01")
            digest.update(bytes.fromhex(sha256_file(path)))
        else:
            digest.update(b"\x00")
    return digest.hexdigest()


def load_checkpoint(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("checkpoint_version") != CHECKPOINT_VERSION:
        return {}
    if payload.get("completed_stage") not in STAGES:
        return {}
    return payload


def write_checkpoint(path: Path, payload: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    complete = {"checkpoint_version": CHECKPOINT_VERSION, **payload}
    if complete.get("completed_stage") not in STAGES:
        raise ValueError(f"Unsupported workflow checkpoint stage: {complete.get('completed_stage')!r}")
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def checkpoint_matches(checkpoint: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    """Validate input identity and every referenced artifact by content hash."""
    if not checkpoint:
        return False, "checkpoint is missing or invalid"
    for key in ("package_id", "package_fingerprint", "semantic_handoff_hash", "judgment_config_hash"):
        if checkpoint.get(key) != expected.get(key):
            return False, f"{key} changed"
    # The default bridge knows the raw-source fingerprint, while an explicitly
    # supplied standardized package may not publish it in its manifest. Treat
    # the source fingerprint as an additional check when both invocations know
    # it; exact package bytes remain mandatory in every invocation mode.
    checkpoint_source = checkpoint.get("source_fingerprint")
    expected_source = expected.get("source_fingerprint")
    if checkpoint_source is not None and expected_source is not None and checkpoint_source != expected_source:
        return False, "source_fingerprint changed"
    workbook = Path(str(checkpoint.get("working_databook_path") or ""))
    if not workbook.is_file():
        return False, "working databook is missing"
    if checkpoint.get("working_databook_hash") != sha256_file(workbook):
        return False, "working databook hash changed"
    if checkpoint.get("completed_stage") in {"ANALYSIS_READY", "INTERPRETATION_READY", "READY"}:
        evidence = Path(str(checkpoint.get("analysis_evidence_path") or ""))
        if not evidence.is_file():
            return False, "analysis evidence is missing"
        if checkpoint.get("analysis_evidence_hash") != sha256_file(evidence):
            return False, "analysis evidence hash changed"
    if checkpoint.get("completed_stage") in {"INTERPRETATION_READY", "READY"}:
        interpretation = Path(str(checkpoint.get("analysis_interpretation_path") or ""))
        if not interpretation.is_file():
            return False, "analysis interpretation is missing"
        if checkpoint.get("analysis_interpretation_hash") != sha256_file(interpretation):
            return False, "analysis interpretation hash changed"
    if checkpoint.get("completed_stage") == "PART1_READY" and checkpoint.get("part1_only_qa"):
        qa = Path(str(checkpoint.get("final_qa_path") or ""))
        if not qa.is_file() or checkpoint.get("final_qa_hash") != sha256_file(qa):
            return False, "Part 1 QA artifact changed"
    if checkpoint.get("completed_stage") == "READY":
        qa = Path(str(checkpoint.get("final_qa_path") or ""))
        if not qa.is_file():
            return False, "final QA artifact is missing"
        if checkpoint.get("final_qa_hash") != sha256_file(qa):
            return False, "final QA artifact hash changed"
        published = Path(str(checkpoint.get("published_databook_path") or ""))
        if not published.is_file():
            return False, "published databook is missing"
        if checkpoint.get("published_databook_hash") != sha256_file(published):
            return False, "published databook hash changed"
        qa_databook_hash = checkpoint.get("qa_databook_hash")
        if qa_databook_hash is not None and qa_databook_hash != checkpoint.get("published_databook_hash"):
            return False, "final QA and published databook hashes differ"
        if qa_databook_hash is not None and qa_databook_hash != checkpoint.get("working_databook_hash"):
            return False, "final QA and working databook hashes differ"
    return True, "checkpoint matches current inputs"
