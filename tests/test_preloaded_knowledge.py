from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import run_all
from ocl_agent.ai_host_cli import _build_prompt


def _load_context_module(repo_root: Path):
    path = repo_root / "fdd-data-preparation" / "knowledge_system" / "context.py"
    spec = importlib.util.spec_from_file_location("preloaded_knowledge_context_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builtin_pack_contains_core_reusable_training_lessons():
    repo_root = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (repo_root / "fdd-data-preparation" / "knowledge_system" / "builtin_patterns.json").read_text(encoding="utf-8")
    )
    ids = {item["id"] for item in payload["patterns"]}

    assert "AMBIGUOUS_FIELD_NAMES" in ids
    assert "MULTIPLE_DATASETS_ONE_SHEET" in ids
    assert "WIDE_MONTHLY_ACTUAL_BUDGET_VARIANCE" in ids
    assert "PROJECT_ACCRUAL_ROLLFORWARD" in ids
    assert "ANALYSIS_SUPPORT_MATRIX" in ids
    assert "FDD_PARTNER_OUTPUT" in ids
    assert any("current source evidence" in principle.casefold() for principle in payload["core_principles"])


def test_context_packet_matches_only_relevant_profile_patterns(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    context = _load_context_module(repo_root)
    runs_root = tmp_path / "runs"
    run = runs_root / "RUN_001"
    run.mkdir(parents=True)
    (run / "profile.json").write_text(
        json.dumps(
            {
                "workbook": "client_pack.xlsx",
                "sheets": [
                    {
                        "name": "Monthly BS",
                        "headers": ["Actual", "Budget", "Variance", "Jan-25", "Feb-25"],
                    },
                    {
                        "name": "Liability Detail",
                        "headers": ["Nominal", "Description", "Map1", "Cat", "Closing Balance"],
                        "notes": "blank rows then a different header and site-level records",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    source = tmp_path / "source"
    source.mkdir()
    (source / "client_pack.xlsx").write_bytes(b"not-a-real-xlsx-needed-for-context-test")

    output = context.build_context_packet(tmp_path, runs_root, source, "a" * 64)
    text = output.read_text(encoding="utf-8")

    assert "AMBIGUOUS_FIELD_NAMES" in text
    assert "WIDE_MONTHLY_ACTUAL_BUDGET_VARIANCE" in text
    assert "MULTIPLE_DATASETS_ONE_SHEET" in text
    assert "PROJECT_ACCRUAL_ROLLFORWARD" not in text
    assert "current source evidence always wins" in text.casefold()


def test_ai_prompt_uses_compact_context_and_rejects_training_answer_keys():
    prompt = _build_prompt(
        {
            "next_actor": "AI_HOST",
            "next_action": "UNDERSTAND_AND_PLAN",
            "reusable_knowledge_context": "work/data_prep/knowledge/context/abc.md",
            "required_artifact": "work/example/dataset_map.json",
        }
    )

    assert "read that compact context FIRST" in prompt
    assert "Current profile/sample/source evidence always overrides reusable knowledge" in prompt
    assert "Expected_Results" in prompt
    assert "NOT an answer key" in prompt


def test_one_source_staging_copies_only_selected_source_and_preserves_original(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "references" / "source"
    source_root.mkdir(parents=True)
    selected = source_root / "Finance_Pack.xlsx"
    selected.write_bytes(b"immutable-source-bytes")
    (source_root / "Other_Source.xlsx").write_bytes(b"other-source")

    monkeypatch.setattr(run_all, "ROOT", tmp_path)
    resolved = run_all._resolve_learning_source(source_root, Path("Finance_Pack.xlsx"))
    before = selected.read_bytes()
    stage = run_all._stage_learning_source(resolved, source_root)

    assert selected.read_bytes() == before
    staged_files = list(stage.iterdir())
    assert [path.name for path in staged_files] == ["Finance_Pack.xlsx"]
    assert staged_files[0].read_bytes() == before
    assert not (stage / "Other_Source.xlsx").exists()


def test_learning_source_must_stay_inside_source_folder(tmp_path: Path):
    source_root = tmp_path / "references" / "source"
    source_root.mkdir(parents=True)
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(b"outside")

    try:
        run_all._resolve_learning_source(source_root, outside)
    except ValueError as error:
        assert "inside references/source" in str(error)
    else:  # pragma: no cover
        raise AssertionError("Expected outside learning source to be rejected")


def test_external_learning_resume_command_preserves_learning_mode():
    command = run_all._learning_resume_command(Path("Balance_Sheet_Detail.xlsx"), "external")
    assert '--learn-source "Balance_Sheet_Detail.xlsx"' in command
    assert "--ai-host external" in command
