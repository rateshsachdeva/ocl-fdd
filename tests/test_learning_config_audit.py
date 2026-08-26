from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from ocl_agent.end_to_end import _prepare_package_config


def _load_bootstrap(repo_root: Path):
    path = repo_root / "fdd-data-preparation" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("knowledge_audit_bootstrap", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_knowledge_system(repo_root: Path):
    path = repo_root / "fdd-data-preparation" / "knowledge_system" / "store.py"
    name = "knowledge_system_audit_store"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_embedded_runtime_has_explicit_reusable_knowledge_consumption():
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap = _load_bootstrap(repo_root)
    project = bootstrap.ensure_full_runtime()

    files = [*project.glob("src/fdd_data/**/*.py"), *project.glob("instructions/**/*.md")]
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files)

    for name in ("field_knowledge.csv", "structure_knowledge.csv", "corrections.csv"):
        assert name in text, f"Embedded runtime does not reference reusable knowledge asset {name}"


def test_repository_level_knowledge_code_is_centralized():
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap_text = (repo_root / "fdd-data-preparation" / "bootstrap.py").read_text(encoding="utf-8")
    store_text = (
        repo_root / "fdd-data-preparation" / "knowledge_system" / "store.py"
    ).read_text(encoding="utf-8")

    assert "knowledge_system" in bootstrap_text
    for name in ("field_knowledge.csv", "structure_knowledge.csv", "corrections.csv"):
        assert name not in bootstrap_text
        assert name in store_text


def test_safe_promotion_retains_generic_learning_and_quarantines_source_specific_rows(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    knowledge_module = _load_knowledge_system(repo_root)
    store = knowledge_module.KnowledgeStore(tmp_path / "persistent")

    project = tmp_path / "runtime_project"
    runtime_knowledge = project / "knowledge"
    runtime_knowledge.mkdir(parents=True)
    baselines = {
        "field_knowledge.csv": "field,meaning\nAmount,numeric measure\n",
        "structure_knowledge.csv": "pattern,meaning\nFY tabs,annual partitions\n",
        "corrections.csv": "item,correction\nMap1,category\n",
    }
    for name, content in baselines.items():
        (runtime_knowledge / name).write_text(content, encoding="utf-8")

    store.hydrate(project, refresh_baseline=True)

    (runtime_knowledge / "field_knowledge.csv").write_text(
        "field,meaning\n"
        "Amount,numeric measure\n"
        "Cat,category dimension\n"
        "Acme_Client.xlsx,client workbook mapping\n"
        "Account,123456789\n",
        encoding="utf-8",
    )
    source = tmp_path / "source"
    source.mkdir()
    (source / "Acme_Client.xlsx").write_bytes(b"source")

    report = store.promote(
        project,
        source_dir=source,
        source_fingerprint="f" * 64,
    )

    assert report.accepted_rows == 1
    assert report.quarantined_rows == 2
    promoted = (store.root / "field_knowledge.csv").read_text(encoding="utf-8")
    assert "Cat,category dimension" in promoted
    assert "Acme_Client.xlsx" not in promoted
    assert "123456789" not in promoted

    quarantine = store.quarantine_root / ("f" * 16) / "field_knowledge.csv"
    quarantined = quarantine.read_text(encoding="utf-8")
    assert "Acme_Client.xlsx" in quarantined
    assert "123456789" in quarantined

    manifest = json.loads((store.root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["policy_version"] == "generic-cross-source-v1"
    assert manifest["accepted_rows"] == 1
    assert manifest["quarantined_rows"] == 2


def test_promoted_knowledge_rehydrates_later_runtime(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    knowledge_module = _load_knowledge_system(repo_root)
    store = knowledge_module.KnowledgeStore(tmp_path / "persistent")

    first_project = tmp_path / "runtime_one"
    first_knowledge = first_project / "knowledge"
    first_knowledge.mkdir(parents=True)
    for name, content in {
        "field_knowledge.csv": "field,meaning\nAmount,numeric measure\n",
        "structure_knowledge.csv": "pattern,meaning\nFY tabs,annual partitions\n",
        "corrections.csv": "item,correction\nMap1,category\n",
    }.items():
        (first_knowledge / name).write_text(content, encoding="utf-8")

    store.hydrate(first_project, refresh_baseline=True)
    (first_knowledge / "field_knowledge.csv").write_text(
        "field,meaning\nAmount,numeric measure\nCat,category dimension\n",
        encoding="utf-8",
    )
    store.promote(first_project, source_fingerprint="a" * 64)

    second_project = tmp_path / "runtime_two"
    second_knowledge = second_project / "knowledge"
    second_knowledge.mkdir(parents=True)
    (second_knowledge / "field_knowledge.csv").write_text(
        "field,meaning\nAmount,numeric measure\n",
        encoding="utf-8",
    )
    (second_knowledge / "structure_knowledge.csv").write_text(
        "pattern,meaning\nFY tabs,annual partitions\n",
        encoding="utf-8",
    )
    (second_knowledge / "corrections.csv").write_text(
        "item,correction\nMap1,category\n",
        encoding="utf-8",
    )

    store.hydrate(second_project, refresh_baseline=False)

    assert "Cat,category dimension" in (
        second_knowledge / "field_knowledge.csv"
    ).read_text(encoding="utf-8")


def test_root_config_is_seed_only_and_package_config_is_stable(tmp_path: Path):
    root_config = tmp_path / "config"
    package_config = tmp_path / "work" / "ocl_config" / "PACKAGE_A"
    root_config.mkdir(parents=True)

    (root_config / "mapping.csv").write_text("source_label,category\nBonus,Employee\n", encoding="utf-8")
    (root_config / "semantic_handoff.json").write_text('{"status":"SHOULD_NOT_COPY"}', encoding="utf-8")

    _prepare_package_config(root_config, package_config)
    assert (package_config / "mapping.csv").read_text(encoding="utf-8") == "source_label,category\nBonus,Employee\n"
    assert not (package_config / "semantic_handoff.json").exists()

    (package_config / "mapping.csv").write_text(
        "source_label,category\nBonus,Reviewed Package Decision\n",
        encoding="utf-8",
    )
    (root_config / "mapping.csv").write_text(
        "source_label,category\nBonus,Changed Global Default\n",
        encoding="utf-8",
    )
    _prepare_package_config(root_config, package_config)

    assert (
        package_config / "mapping.csv"
    ).read_text(encoding="utf-8") == "source_label,category\nBonus,Reviewed Package Decision\n"


def test_legacy_config_placeholders_are_not_currently_consumed_by_ocl_python():
    repo_root = Path(__file__).resolve().parents[1]
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (repo_root / "src" / "ocl_agent").rglob("*.py")
    )
    for filename in (
        "column_memory.json",
        "line_item_notes.csv",
        "optional_payroll.csv",
        "optional_revenue.csv",
    ):
        assert filename not in text, f"{filename} is an active OCL runtime dependency and should not be treated as legacy"
