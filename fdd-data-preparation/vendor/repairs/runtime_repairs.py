"""Idempotent generic repairs applied to the materialized upstream runtime.

The runtime is stored as a validated vendor archive. These small textual
repairs keep the original archive immutable while making repository-owned,
reviewable extensions reproducible in a clean clone.
"""
from __future__ import annotations

from pathlib import Path


def apply_runtime_repairs(project: Path) -> None:
    project = Path(project)
    _repair_executor(project / "src" / "fdd_data" / "executor.py")
    _repair_source_reader(project / "src" / "fdd_data" / "source_data.py")
    _repair_processing_plan_instruction(project / "instructions" / "processing_plan.md")


def _repair_executor(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '"UNPIVOT", "PARSE_NUMERIC"',
        '"UNPIVOT", "MAP_VALUES", "PARSE_NUMERIC"',
        path,
    )
    text = _replace_once(
        text,
        '''        elif step.get("operation") == "PARSE_NUMERIC":
            for field in step.get("fields", []):
''',
        '''        elif step.get("operation") == "MAP_VALUES":
            _apply_value_mapping(record, step)
        elif step.get("operation") == "PARSE_NUMERIC":
            for field in step.get("fields", []):
''',
        path,
    )
    mapping_function = '''def _apply_value_mapping(record: dict[str, Any], step: dict[str, Any]) -> None:
    """Apply only the exact source-value mapping declared in the approved plan."""
    source_field = str(step.get("source_field") or "").strip()
    target_field = str(step.get("target_field") or source_field).strip()
    mappings = step.get("mappings")
    if not source_field or not target_field or not isinstance(mappings, dict) or not mappings:
        raise ProcessingPlanValidationError(
            "MAP_VALUES requires source_field, target_field and a non-empty mappings object."
        )
    source_value = record.get(source_field)
    key = "" if source_value is None else str(source_value).strip()
    exact = {str(item).strip(): value for item, value in mappings.items()}
    if key in exact:
        record[target_field] = exact[key]
        return
    casefold_map = {item.casefold(): value for item, value in exact.items()}
    folded = key.casefold()
    if folded in casefold_map:
        record[target_field] = casefold_map[folded]
        return
    unmapped = str(step.get("unmapped") or "ERROR").upper()
    if unmapped == "PRESERVE":
        record[target_field] = source_value
    elif unmapped == "BLANK":
        record[target_field] = None
    elif unmapped == "ERROR":
        raise ProcessingPlanValidationError(
            f"MAP_VALUES has no mapping for {source_field} value {key!r}."
        )
    else:
        raise ProcessingPlanValidationError(
            "MAP_VALUES unmapped must be ERROR, PRESERVE or BLANK."
        )
'''
    mapping_start = text.find("def _apply_value_mapping(")
    filter_start = text.find("def _matches_filter_exclusion(")
    if filter_start < 0:
        raise RuntimeError(f"Runtime repair precondition failed for {path}: filter helper is missing.")
    if mapping_start >= 0:
        text = text[:mapping_start] + mapping_function + "\n\n" + text[filter_start:]
    else:
        text = text[:filter_start] + mapping_function + "\n\n" + text[filter_start:]

    assertion_function = '''def _assert_supported_operations(plan: dict[str, Any]) -> None:
    for output in plan.get("proposed_outputs", []):
        for step in output.get("transformations", []) + output.get("operation_steps", []):
            if step.get("operation") not in SUPPORTED_OPERATIONS:
                raise UnsupportedOperationError(str(step.get("operation")))
            if step.get("operation") == "MAP_VALUES":
                source_field = str(step.get("source_field") or "").strip()
                target_field = str(step.get("target_field") or source_field).strip()
                mappings = step.get("mappings")
                if not source_field or not target_field or not isinstance(mappings, dict) or not mappings:
                    raise ProcessingPlanValidationError(
                        "MAP_VALUES requires source_field, target_field and a non-empty mappings object."
                    )
                normalized_keys = [str(key).strip().casefold() for key in mappings]
                if len(normalized_keys) != len(set(normalized_keys)):
                    raise ProcessingPlanValidationError(
                        "MAP_VALUES mappings contain duplicate keys after trim/case normalization."
                    )
                if str(step.get("unmapped") or "ERROR").upper() not in {"ERROR", "PRESERVE", "BLANK"}:
                    raise ProcessingPlanValidationError(
                        "MAP_VALUES unmapped must be ERROR, PRESERVE or BLANK."
                    )
'''
    assertion_start = text.find("def _assert_supported_operations(")
    create_start = text.find("def _create_execution_directory(")
    if assertion_start < 0 or create_start < 0:
        raise RuntimeError(f"Runtime repair precondition failed for {path}: operation assertion helper is missing.")
    text = text[:assertion_start] + assertion_function + "\n\n" + text[create_start:]
    path.write_text(text, encoding="utf-8")


def _repair_source_reader(path: Path) -> None:
    """Preserve the already-proven generic headerless-region and path repairs."""
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '''        _validate_exact_headers(worksheet, header_row, fields)
        rows: list[tuple[int, dict[str, Any]]] = []
''',
        '''        if header_row is not None:
            _validate_exact_headers(worksheet, header_row, fields)
        first_data_row = header_row + 1 if header_row is not None else int(region["start_row"])
        rows: list[tuple[int, dict[str, Any]]] = []
''',
        path,
    )
    text = _replace_once(text, "min_row=header_row + 1,", "min_row=first_data_row,", path, count=2)
    text = _replace_once(text, "start=header_row + 1,", "start=first_data_row,", path, count=2)
    text = _replace_once(
        text,
        '''    _validate_exact_headers(worksheet, header_row, fields)
    allowed_rows = _allowed_data_rows(region)
''',
        '''    if header_row is not None:
        _validate_exact_headers(worksheet, header_row, fields)
    first_data_row = header_row + 1 if header_row is not None else int(region["start_row"])
    allowed_rows = _allowed_data_rows(region)
''',
        path,
    )
    text = _replace_once(text, "def _header_row(region: dict[str, Any]) -> int:", "def _header_row(region: dict[str, Any]) -> int | None:", path)
    text = _replace_once(text, "return primary[0]", "return max(primary)", path)
    text = _replace_once(
        text,
        'return max(candidates) if candidates else int(region["start_row"])',
        "return max(candidates) if candidates else None",
        path,
    )
    text = _replace_once(
        text,
        'return hashlib.sha256(region_id.encode("utf-8")).hexdigest()',
        '''# Keep run-local staging paths below the legacy Windows MAX_PATH limit.
    # The manifest still binds the file to the full region_id and source hashes.
    return hashlib.sha256(region_id.encode("utf-8")).hexdigest()[:24]''',
        path,
    )
    path.write_text(text, encoding="utf-8")


def _repair_processing_plan_instruction(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "## Source-bound value mapping"
    if marker in text:
        return
    text = text.rstrip() + """

## Source-bound value mapping

Use `MAP_VALUES` only when the current source evidence supports an explicit
value-to-value mapping. Declare `source_field`, `target_field`, a non-empty
`mappings` object, and `unmapped` (`ERROR`, `PRESERVE`, or `BLANK`) in the
source-bound Processing Plan. Never place engagement transaction codes or
client-specific value maps in deterministic Python. Canonical movement outputs
must publish `Movement_Type` as `OPENING`, `FLOW`, or `CLOSING` together with an
explicit numeric `Movement_Multiplier`.
"""
    path.write_text(text + "\n", encoding="utf-8")


def _replace_once(text: str, old: str, new: str, path: Path, *, count: int = 1) -> str:
    if new in text:
        return text
    observed = text.count(old)
    if observed != count:
        raise RuntimeError(
            f"Runtime repair precondition failed for {path}: expected {count} occurrence(s), found {observed}."
        )
    return text.replace(old, new, count)
