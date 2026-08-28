from __future__ import annotations

import base64
import io
import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest


def _load_bootstrap(repo_root: Path):
    path = repo_root / "fdd-data-preparation" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("embedded_fdd_data_prep_bootstrap", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_data_preparation_runtime_materializes_and_contains_ai_python_workflow():
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap = _load_bootstrap(repo_root)
    project = bootstrap.ensure_full_runtime()

    required = [
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
    ]
    assert all((project / relative).exists() for relative in required)

    orchestration = (project / "src/fdd_data/orchestration.py").read_text(encoding="utf-8")
    assert '"AWAITING_AI_PLANNING": ("AI_HOST", "UNDERSTAND_AND_PLAN")' in orchestration
    assert '"AWAITING_DATASET_UNDERSTANDING": ("AI_HOST", "DATASET_UNDERSTANDING")' in orchestration
    assert '"AWAITING_PROCESSING_PLAN": ("AI_HOST", "PROCESSING_PLAN")' in orchestration
    assert "execute_processing_plan(" in orchestration

    ai_instructions = (project / "instructions/AI_HOST_ORCHESTRATION.md").read_text(encoding="utf-8")
    assert "AI_HOST" in ai_instructions
    assert "must_continue" in ai_instructions


def test_map_values_is_generic_and_plan_bound():
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap = _load_bootstrap(repo_root)
    _project, fdd_data = bootstrap.activate_full_runtime()
    executor = importlib.import_module("fdd_data.executor")
    step = {
        "operation": "MAP_VALUES",
        "source_field": "Source_Movement",
        "target_field": "Movement_Type",
        "mappings": {"source opening": "OPENING", "source activity": "FLOW"},
        "unmapped": "ERROR",
    }
    plan = {"proposed_outputs": [{"transformations": [], "operation_steps": [step]}]}

    executor._assert_supported_operations(plan)
    record = {"Source_Movement": "source activity"}
    executor._apply_operations(record, plan["proposed_outputs"][0]["operation_steps"])

    assert record["Movement_Type"] == "FLOW"
    with pytest.raises(fdd_data.ProcessingPlanValidationError, match="has no mapping"):
        executor._apply_operations({"Source_Movement": "unmapped"}, [step])


def test_processing_plan_instruction_requires_source_bound_mappings():
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap = _load_bootstrap(repo_root)
    project = bootstrap.ensure_full_runtime()
    instruction = (project / "instructions/processing_plan.md").read_text(encoding="utf-8")

    assert "source-bound Processing Plan" in instruction
    assert "Movement_Multiplier" in instruction


def test_runtime_repairs_apply_to_pristine_vendor_members(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    parts = repo_root / "fdd-data-preparation" / "vendor" / "runtime_parts"
    archive = base64.b64decode("".join(path.read_text(encoding="ascii").strip() for path in sorted(parts.glob("part_*.b64"))))
    project = tmp_path / "fdd-data-preparation"
    members = (
        "src/fdd_data/executor.py",
        "src/fdd_data/source_data.py",
        "instructions/processing_plan.md",
    )
    with ZipFile(io.BytesIO(archive)) as package:
        for relative in members:
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(package.read(f"fdd-data-preparation/{relative}"))
    repair_path = repo_root / "fdd-data-preparation" / "vendor" / "repairs" / "runtime_repairs.py"
    spec = importlib.util.spec_from_file_location("test_runtime_repairs", repair_path)
    assert spec and spec.loader
    repairs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repairs)

    repairs.apply_runtime_repairs(project)
    repairs.apply_runtime_repairs(project)

    executor = (project / "src/fdd_data/executor.py").read_text(encoding="utf-8")
    source_data = (project / "src/fdd_data/source_data.py").read_text(encoding="utf-8")
    instruction = (project / "instructions/processing_plan.md").read_text(encoding="utf-8")
    assert '"MAP_VALUES"' in executor
    assert executor.count("def _apply_value_mapping") == 1
    assert "first_data_row" in source_data
    assert "hexdigest()[:24]" in source_data
    assert instruction.count("## Source-bound value mapping") == 1
