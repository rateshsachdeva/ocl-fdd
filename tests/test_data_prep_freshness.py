import json
from pathlib import Path

import pytest

from ocl_agent import data_prep_bridge
from ocl_agent.end_to_end import _activate_source_package


class _FakeFddData:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def run_databook(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return dict(self.status)


class _FakeBootstrap:
    def __init__(self, status, knowledge_report=None):
        self.fdd_data = _FakeFddData(status)
        self.knowledge_report = knowledge_report or {"accepted_rows": 0, "quarantined_rows": 0}
        self.knowledge_sync_calls = []
        self.activation_calls = 0

    def activate_full_runtime(self):
        self.activation_calls += 1
        return Path("runtime"), self.fdd_data

    def sync_runtime_knowledge(self, **kwargs):
        self.knowledge_sync_calls.append(dict(kwargs))
        return dict(self.knowledge_report)


def _source(tmp_path: Path, text: str = "source-v1") -> Path:
    source = tmp_path / "source"
    source.mkdir(parents=True, exist_ok=True)
    (source / "client.xlsx").write_bytes(text.encode("utf-8"))
    return source


def _package_root(work_root: Path, source_dir: Path) -> Path:
    fingerprint = data_prep_bridge.source_package_fingerprint(source_dir)
    return work_root / "source_packages" / fingerprint[:16]


def _write_latest(
    work_root: Path,
    source_dir: Path,
    execution_id: str,
    final_execution_status: str = "COMPLETED",
    *,
    create_output: bool = True,
) -> Path:
    latest = _package_root(work_root, source_dir) / "output" / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    if create_output:
        (latest / "standardized.csv").write_text("Category,Amount\nBonus,1\n", encoding="utf-8")
    (latest / "execution_manifest.json").write_text(
        json.dumps(
            {
                "execution_id": execution_id,
                "final_execution_status": final_execution_status,
                "outputs_created": ["standardized.csv"],
            }
        ),
        encoding="utf-8",
    )
    return latest


def test_source_fingerprint_changes_with_source_contents_paths_and_membership(tmp_path: Path):
    source = _source(tmp_path, "one")
    first = data_prep_bridge.source_package_fingerprint(source)

    (source / "client.xlsx").write_bytes(b"two")
    changed = data_prep_bridge.source_package_fingerprint(source)
    assert changed != first

    (source / "other.xlsx").write_bytes(b"three")
    added = data_prep_bridge.source_package_fingerprint(source)
    assert added != changed

    (source / "other.xlsx").rename(source / "renamed.xlsx")
    renamed = data_prep_bridge.source_package_fingerprint(source)
    assert renamed != added

    (source / "~$client.xlsx").write_bytes(b"office-lock")
    assert data_prep_bridge.source_package_fingerprint(source) == renamed


def test_old_latest_is_not_visible_to_changed_source_package(tmp_path: Path, monkeypatch):
    work_root = tmp_path / "data_prep"
    source = _source(tmp_path, "old")
    old_latest = _write_latest(work_root, source, "EX_OLD")

    (source / "client.xlsx").write_bytes(b"new")
    status = {
        "state": "AWAITING_AI_PLANNING",
        "run_id": "RUN_NEW_SOURCE",
        "next_actor": "AI_HOST",
        "next_action": "UNDERSTAND_AND_PLAN",
        "must_continue": True,
    }
    bootstrap = _FakeBootstrap(status)
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: bootstrap)

    result = data_prep_bridge.run_full_data_preparation(tmp_path, source, work_root)

    assert result.state == "DATA_PREP_AWAITING_AI_PLANNING"
    assert result.standardized_output is None
    assert result.ready is False
    assert result.output_root != old_latest.parent
    assert result.source_fingerprint == data_prep_bridge.source_package_fingerprint(source)
    assert len(bootstrap.fdd_data.calls) == 1
    assert bootstrap.knowledge_sync_calls == []


@pytest.mark.parametrize("published_status", ["COMPLETED", "COMPLETED_WITH_WARNINGS"])
def test_exact_source_reuses_publishable_latest_without_new_ai_planning(
    tmp_path: Path,
    monkeypatch,
    published_status: str,
):
    work_root = tmp_path / "data_prep"
    source = _source(tmp_path)
    latest = _write_latest(work_root, source, "EX_PREVIOUS", published_status)
    status = {
        "state": "AWAITING_AI_PLANNING",
        "run_id": "RUN_SHOULD_NOT_BE_CREATED",
        "next_actor": "AI_HOST",
        "next_action": "UNDERSTAND_AND_PLAN",
        "must_continue": True,
    }
    bootstrap = _FakeBootstrap(status)
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: bootstrap)

    result = data_prep_bridge.run_full_data_preparation(tmp_path, source, work_root)

    assert result.state == "DATA_PREP_READY"
    assert result.upstream_state == "PUBLISHED_CACHE_REUSED"
    assert result.standardized_output == latest
    assert result.ready is True
    assert result.coordination["next_actor"] == "NONE"
    assert result.coordination["next_action"] == "WORKFLOW_COMPLETE"
    assert bootstrap.activation_calls == 0
    assert bootstrap.fdd_data.calls == []
    assert bootstrap.knowledge_sync_calls == [
        {
            "source_dir": source.resolve(),
            "source_fingerprint": data_prep_bridge.source_package_fingerprint(source),
        }
    ]


@pytest.mark.parametrize(
    "published_status",
    ["FAILED", "FAILED_VALIDATION", "EXECUTION_BLOCKED", ""],
)
def test_incomplete_or_failed_latest_is_not_reused(
    tmp_path: Path,
    monkeypatch,
    published_status: str,
):
    work_root = tmp_path / "data_prep"
    source = _source(tmp_path)
    _write_latest(work_root, source, "EX_INVALID", published_status)
    status = {
        "state": "AWAITING_AI_PLANNING",
        "run_id": "RUN_NEW",
        "next_actor": "AI_HOST",
        "next_action": "UNDERSTAND_AND_PLAN",
        "must_continue": True,
    }
    bootstrap = _FakeBootstrap(status)
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: bootstrap)

    result = data_prep_bridge.run_full_data_preparation(tmp_path, source, work_root)

    assert result.state == "DATA_PREP_AWAITING_AI_PLANNING"
    assert result.standardized_output is None
    assert bootstrap.activation_calls == 1
    assert len(bootstrap.fdd_data.calls) == 1


def test_publishable_manifest_with_missing_output_is_not_reused(tmp_path: Path, monkeypatch):
    work_root = tmp_path / "data_prep"
    source = _source(tmp_path)
    _write_latest(work_root, source, "EX_INCOMPLETE", create_output=False)
    status = {
        "state": "AWAITING_AI_PLANNING",
        "run_id": "RUN_NEW",
        "next_actor": "AI_HOST",
        "next_action": "UNDERSTAND_AND_PLAN",
        "must_continue": True,
    }
    bootstrap = _FakeBootstrap(status)
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: bootstrap)

    result = data_prep_bridge.run_full_data_preparation(tmp_path, source, work_root)

    assert result.state == "DATA_PREP_AWAITING_AI_PLANNING"
    assert result.standardized_output is None
    assert len(bootstrap.fdd_data.calls) == 1


def test_published_latest_is_not_reused_across_source_fingerprints(tmp_path: Path, monkeypatch):
    work_root = tmp_path / "data_prep"
    source_a = tmp_path / "source-a"
    source_a.mkdir()
    (source_a / "client.xlsx").write_bytes(b"same-looking-source")
    latest_a = _write_latest(work_root, source_a, "EX_SOURCE_A")

    source_b = tmp_path / "source-b"
    source_b.mkdir()
    (source_b / "renamed.xlsx").write_bytes(b"same-looking-source")
    status = {
        "state": "AWAITING_AI_PLANNING",
        "run_id": "RUN_SOURCE_B",
        "next_actor": "AI_HOST",
        "next_action": "UNDERSTAND_AND_PLAN",
        "must_continue": True,
    }
    bootstrap = _FakeBootstrap(status)
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: bootstrap)

    result = data_prep_bridge.run_full_data_preparation(tmp_path, source_b, work_root)

    assert data_prep_bridge.source_package_fingerprint(source_a) != result.source_fingerprint
    assert result.output_root != latest_a.parent
    assert result.state == "DATA_PREP_AWAITING_AI_PLANNING"
    assert result.standardized_output is None
    assert len(bootstrap.fdd_data.calls) == 1


def test_quarantined_learning_is_visible_as_nonblocking_warning(tmp_path: Path, monkeypatch):
    work_root = tmp_path / "data_prep"
    source = _source(tmp_path)
    _write_latest(work_root, source, "EX_CURRENT")
    status = {
        "state": "KNOWLEDGE_UPDATED",
        "run_id": "RUN_CURRENT_SOURCE",
        "execution_id": "EX_CURRENT",
        "next_actor": "NONE",
        "next_action": "WORKFLOW_COMPLETE",
        "must_continue": False,
    }
    bootstrap = _FakeBootstrap(status, {"accepted_rows": 2, "quarantined_rows": 1})
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: bootstrap)

    result = data_prep_bridge.run_full_data_preparation(tmp_path, source, work_root)

    assert result.ready is True
    assert any("quarantined 1" in warning for warning in result.warnings)


def test_changed_source_gets_distinct_upstream_runs_and_output_roots(tmp_path: Path, monkeypatch):
    work_root = tmp_path / "data_prep"
    source = _source(tmp_path, "version-a")
    status = {
        "state": "AWAITING_AI_PLANNING",
        "run_id": "RUN",
        "next_actor": "AI_HOST",
        "next_action": "UNDERSTAND_AND_PLAN",
    }
    bootstrap = _FakeBootstrap(status)
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: bootstrap)

    first = data_prep_bridge.run_full_data_preparation(tmp_path, source, work_root)
    first_call = bootstrap.fdd_data.calls[-1][0]

    (source / "client.xlsx").write_bytes(b"version-b")
    second = data_prep_bridge.run_full_data_preparation(tmp_path, source, work_root)
    second_call = bootstrap.fdd_data.calls[-1][0]

    assert first.source_fingerprint != second.source_fingerprint
    assert first_call[1] != second_call[1]  # runs_root
    assert first_call[2] != second_call[2]  # output_root


def test_source_change_removes_old_principal_deliverables(tmp_path: Path):
    runtime_work = tmp_path / "work"
    output = tmp_path / "output"
    runtime_work.mkdir()
    output.mkdir()
    (runtime_work / "active_source_package.json").write_text(
        json.dumps({"source_fingerprint": "OLD", "status": "READY"}),
        encoding="utf-8",
    )
    (runtime_work / "final_qa.json").write_text("{}", encoding="utf-8")
    (output / "OCL_Databook.xlsx").write_bytes(b"old workbook")
    (output / "OCL_Report.pptx").write_bytes(b"old report")

    _activate_source_package(runtime_work, output, "NEW")

    assert not (output / "OCL_Databook.xlsx").exists()
    assert not (output / "OCL_Report.pptx").exists()
    assert not (runtime_work / "final_qa.json").exists()
    marker = json.loads((runtime_work / "active_source_package.json").read_text(encoding="utf-8"))
    assert marker == {"source_fingerprint": "NEW", "status": "IN_PROGRESS"}


def test_same_source_does_not_delete_current_deliverables(tmp_path: Path):
    runtime_work = tmp_path / "work"
    output = tmp_path / "output"
    runtime_work.mkdir()
    output.mkdir()
    (runtime_work / "active_source_package.json").write_text(
        json.dumps({"source_fingerprint": "SAME", "status": "READY"}),
        encoding="utf-8",
    )
    workbook = output / "OCL_Databook.xlsx"
    workbook.write_bytes(b"current workbook")

    _activate_source_package(runtime_work, output, "SAME")

    assert workbook.read_bytes() == b"current workbook"
