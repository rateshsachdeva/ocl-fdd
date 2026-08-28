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
    _repair_processing_plan(project / "src" / "fdd_data" / "processing_plan.py")
    _repair_processing_plan_schema(project / "schemas" / "processing_plan.schema.json")
    _repair_source_reader(project / "src" / "fdd_data" / "source_data.py")
    _repair_processing_plan_instruction(project / "instructions" / "processing_plan.md")


def _repair_executor(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '        "operations_executed": [], "validation_checks": [], "warnings": [], "errors": [],',
        '        "operations_executed": [], "validation_checks": [], "control_bindings": [], "warnings": [], "errors": [],',
        path,
    )
    text = _replace_once(
        text,
        '''        if plan_errors:
            raise ProcessingPlanValidationError("\\n".join(plan_errors))
        manifest["source_snapshot_status"] = assert_execution_allowed(plan, source_directory, for_stage5=True)["comparison_result"]
''',
        '''        if plan_errors:
            raise ProcessingPlanValidationError("\\n".join(plan_errors))
        manifest["control_bindings"] = plan.get("control_bindings", [])
        manifest["source_snapshot_status"] = assert_execution_allowed(plan, source_directory, for_stage5=True)["comparison_result"]
''',
        path,
    )
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
    target_field = str(step.get("target_field") or "").strip()
    mappings = step.get("mappings")
    unmapped = str(step.get("unmapped") or "").upper()
    if (
        not source_field
        or not target_field
        or not isinstance(mappings, dict)
        or not mappings
        or unmapped not in {"ERROR", "PRESERVE", "BLANK"}
    ):
        raise ProcessingPlanValidationError(
            "MAP_VALUES requires source_field, target_field, a non-empty mappings object, "
            "and an explicit unmapped policy of ERROR, PRESERVE or BLANK."
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
        for declaration in output.get("transformations", []):
            if declaration.get("operation") not in SUPPORTED_OPERATIONS:
                raise UnsupportedOperationError(str(declaration.get("operation")))
        for step in output.get("operation_steps", []):
            operation = step.get("operation")
            if operation not in SUPPORTED_OPERATIONS:
                raise UnsupportedOperationError(str(operation))
            if step.get("operation") == "MAP_VALUES":
                source_field = str(step.get("source_field") or "").strip()
                target_field = str(step.get("target_field") or "").strip()
                mappings = step.get("mappings")
                unmapped = str(step.get("unmapped") or "").upper()
                if (
                    not source_field
                    or not target_field
                    or not isinstance(mappings, dict)
                    or not mappings
                    or unmapped not in {"ERROR", "PRESERVE", "BLANK"}
                ):
                    raise ProcessingPlanValidationError(
                        "MAP_VALUES requires source_field, target_field, a non-empty mappings object, "
                        "and an explicit unmapped policy of ERROR, PRESERVE or BLANK."
                    )
                normalized_keys = [str(key).strip().casefold() for key in mappings]
                if len(normalized_keys) != len(set(normalized_keys)):
                    raise ProcessingPlanValidationError(
                        "MAP_VALUES mappings contain duplicate keys after trim/case normalization."
                    )
'''
    assertion_start = text.find("def _assert_supported_operations(")
    create_start = text.find("def _create_execution_directory(")
    if assertion_start < 0 or create_start < 0:
        raise RuntimeError(f"Runtime repair precondition failed for {path}: operation assertion helper is missing.")
    text = text[:assertion_start] + assertion_function + "\n\n" + text[create_start:]
    path.write_text(text, encoding="utf-8")


def _repair_processing_plan(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '    for index, item in enumerate(plan.get("non_output_logical_datasets", [])):\n',
        '''    _validate_control_bindings(plan, errors)
    for index, item in enumerate(plan.get("non_output_logical_datasets", [])):
''',
        path,
    )
    helper = '''def _validate_control_bindings(plan: dict[str, Any], errors: list[str]) -> None:
    """Validate exact downstream TB-control semantics carried by the approved plan."""
    bindings = plan.get("control_bindings", [])
    if not isinstance(bindings, list):
        errors.append("control_bindings must be an array.")
        return
    outputs = {
        str(output.get("filename") or ""): {
            str(column.get("Output_Column") or "")
            for column in output.get("output_columns", [])
            if isinstance(column, dict)
        }
        for output in plan.get("proposed_outputs", [])
        if isinstance(output, dict)
    }
    seen: set[str] = set()
    for index, binding in enumerate(bindings):
        path = f"control_bindings[{index}]"
        if not isinstance(binding, dict):
            errors.append(f"{path} must be an object.")
            continue
        control_id = str(binding.get("control_id") or "").strip()
        dataset_file = str(binding.get("dataset_file") or "").strip()
        period_field = str(binding.get("period_field") or "").strip()
        amount_field = str(binding.get("amount_field") or "").strip()
        if control_id != "chk_listing_vs_tb":
            errors.append(f"{path}.control_id must be chk_listing_vs_tb.")
        elif control_id in seen:
            errors.append(f"Duplicate control binding: {control_id}.")
        else:
            seen.add(control_id)
        if dataset_file not in outputs:
            errors.append(f"{path}.dataset_file must reference a proposed output filename.")
            available: set[str] = set()
        else:
            available = outputs[dataset_file]
        for field_name, field_value in (("period_field", period_field), ("amount_field", amount_field)):
            if not field_value or field_value not in available:
                errors.append(f"{path}.{field_name} must reference an output column.")
        whole_dataset = binding.get("whole_dataset") is True
        filters = binding.get("filters") or {}
        if not isinstance(filters, dict):
            errors.append(f"{path}.filters must be an object.")
            filters = {}
        if whole_dataset == bool(filters):
            errors.append(f"{path} requires exactly one of whole_dataset=true or non-empty filters.")
        for column, values in filters.items():
            if column not in available:
                errors.append(f"{path}.filters references missing output column {column!r}.")
            if isinstance(values, str):
                normalized = [values]
            elif isinstance(values, list) and all(isinstance(value, str) for value in values):
                normalized = values
            else:
                errors.append(f"{path}.filters[{column!r}] must be a string or list of strings.")
                continue
            if not normalized or any(not value.strip() for value in normalized):
                errors.append(f"{path}.filters[{column!r}] must contain non-blank values.")
'''
    marker = "def validate_processing_plan_file("
    start = text.find("def _validate_control_bindings(")
    marker_start = text.find(marker)
    if marker_start < 0:
        raise RuntimeError(f"Runtime repair precondition failed for {path}: plan file validator is missing.")
    if start >= 0:
        text = text[:start] + helper + "\n\n" + text[marker_start:]
    else:
        text = text[:marker_start] + helper + "\n\n" + text[marker_start:]
    path.write_text(text, encoding="utf-8")


def _repair_processing_plan_schema(path: Path) -> None:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("properties", {})["control_bindings"] = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["control_id", "dataset_file", "period_field", "amount_field"],
            "properties": {
                "control_id": {"const": "chk_listing_vs_tb"},
                "dataset_file": {"type": "string", "minLength": 1},
                "period_field": {"type": "string", "minLength": 1},
                "amount_field": {"type": "string", "minLength": 1},
                "whole_dataset": {"type": "boolean"},
                "filters": {
                    "type": "object",
                    "additionalProperties": {
                        "oneOf": [
                            {"type": "string", "minLength": 1},
                            {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
                        ]
                    },
                },
            },
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
    if "## Source-bound value mapping" not in text:
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
    if "## Explicit downstream TB control binding" not in text:
        text = text.rstrip() + """

## Explicit downstream TB control binding

When an approved output is explicitly established as the OCL trial-balance
control population, add a top-level `control_bindings` entry using the existing
`chk_listing_vs_tb` contract. Reference the exact output filename, period field,
amount field, and either `whole_dataset: true` or exact source-backed `filters`.
Do not infer an OCL control from liability descriptions or require a literal
source value such as `OCL`. Leave the binding absent when the population is
ambiguous.
"""
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _replace_once(text: str, old: str, new: str, path: Path, *, count: int = 1) -> str:
    if new in text:
        return text
    observed = text.count(old)
    if observed != count:
        raise RuntimeError(
            f"Runtime repair precondition failed for {path}: expected {count} occurrence(s), found {observed}."
        )
    return text.replace(old, new, count)
