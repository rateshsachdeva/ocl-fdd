import json
from pathlib import Path

import pytest

from ocl_agent.part1_databook.input_contract import InputContractError, discover_standardized_package


def test_discovers_published_standardized_dataset(tmp_path: Path):
    (tmp_path / "trial_balance.csv").write_text("Account,Amount\nA,1\n", encoding="utf-8")
    (tmp_path / "lineage.csv").write_text("Source_ID,Source_Row\nS,1\n", encoding="utf-8")
    (tmp_path / "execution_manifest.json").write_text(json.dumps({"final_execution_status": "COMPLETED"}), encoding="utf-8")
    package = discover_standardized_package(tmp_path)
    assert [path.name for path in package.datasets] == ["trial_balance.csv"]
    assert package.lineage is not None


def test_rejects_non_publishable_upstream_execution(tmp_path: Path):
    (tmp_path / "trial_balance.csv").write_text("A\n1\n", encoding="utf-8")
    (tmp_path / "execution_manifest.json").write_text(json.dumps({"final_execution_status": "FAILED_VALIDATION"}), encoding="utf-8")
    with pytest.raises(InputContractError):
        discover_standardized_package(tmp_path)
