from __future__ import annotations

import importlib.util
from pathlib import Path


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
