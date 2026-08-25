import json
from pathlib import Path

from ocl_agent import data_prep_bridge


class _FakeFddData:
    def __init__(self, status):
        self.status = status

    def run_databook(self, *args, **kwargs):
        return dict(self.status)


class _FakeBootstrap:
    def __init__(self, status):
        self.fdd_data = _FakeFddData(status)

    def activate_full_runtime(self):
        return Path("runtime"), self.fdd_data

    def sync_runtime_knowledge(self):
        return None


def _write_latest(work_root: Path, execution_id: str) -> Path:
    latest = work_root / "output" / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "execution_manifest.json").write_text(
        json.dumps({"execution_id": execution_id, "final_execution_status": "COMPLETED"}),
        encoding="utf-8",
    )
    return latest


def test_old_latest_is_not_reused_for_new_source_workflow(tmp_path: Path, monkeypatch):
    work_root = tmp_path / "data_prep"
    _write_latest(work_root, "EX_OLD")
    status = {
        "state": "AWAITING_AI_PLANNING",
        "run_id": "RUN_NEW_SOURCE",
        "next_actor": "AI_HOST",
        "next_action": "UNDERSTAND_AND_PLAN",
        "must_continue": True,
    }
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: _FakeBootstrap(status))

    result = data_prep_bridge.run_full_data_preparation(tmp_path, tmp_path / "source", work_root)

    assert result.state == "DATA_PREP_AWAITING_AI_PLANNING"
    assert result.standardized_output is None
    assert result.ready is False


def test_current_published_execution_remains_reusable_during_later_reruns(tmp_path: Path, monkeypatch):
    work_root = tmp_path / "data_prep"
    latest = _write_latest(work_root, "EX_CURRENT")
    status = {
        "state": "KNOWLEDGE_UPDATED",
        "run_id": "RUN_CURRENT_SOURCE",
        "execution_id": "EX_CURRENT",
        "next_actor": "NONE",
        "next_action": "WORKFLOW_COMPLETE",
        "must_continue": False,
    }
    monkeypatch.setattr(data_prep_bridge, "_load_bootstrap", lambda _root: _FakeBootstrap(status))

    result = data_prep_bridge.run_full_data_preparation(tmp_path, tmp_path / "source", work_root)

    assert result.state == "DATA_PREP_READY"
    assert result.standardized_output == latest
    assert result.ready is True
