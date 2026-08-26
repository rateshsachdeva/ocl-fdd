from __future__ import annotations

import importlib.util
from pathlib import Path

from ocl_agent.end_to_end import _prepare_package_config


def _load_bootstrap(repo_root: Path):
    path = repo_root / "fdd-data-preparation" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("knowledge_audit_bootstrap", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_embedded_runtime_has_explicit_reusable_knowledge_consumption():
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap = _load_bootstrap(repo_root)
    project = bootstrap.ensure_full_runtime()

    files = [*project.glob("src/fdd_data/**/*.py"), *project.glob("instructions/**/*.md")]
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files)

    # These are the three knowledge assets that bootstrap deliberately persists
    # across source packages. The embedded runtime must also know how to consume
    # them; otherwise persistence would be cosmetic only.
    for name in ("field_knowledge.csv", "structure_knowledge.csv", "corrections.csv"):
        assert name in text, f"Embedded runtime does not reference reusable knowledge asset {name}"


def test_bootstrap_preserves_and_rehydrates_runtime_knowledge(tmp_path: Path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap = _load_bootstrap(repo_root)
    persistent = tmp_path / "persistent"
    monkeypatch.setattr(bootstrap, "PERSISTENT_KNOWLEDGE", persistent)

    project = tmp_path / "runtime_project"
    knowledge = project / "knowledge"
    knowledge.mkdir(parents=True)
    expected = {
        "field_knowledge.csv": "field,meaning\nCat,category\n",
        "structure_knowledge.csv": "pattern,meaning\nFY tabs,annual partitions\n",
        "corrections.csv": "item,correction\nMap1,category\n",
    }
    for name, content in expected.items():
        (knowledge / name).write_text(content, encoding="utf-8")

    bootstrap._preserve_runtime_knowledge(project)
    assert {path.name for path in persistent.iterdir()} == set(expected)

    for path in knowledge.iterdir():
        path.unlink()
    bootstrap._overlay_persistent_knowledge(project)

    for name, content in expected.items():
        assert (knowledge / name).read_text(encoding="utf-8") == content


def test_root_config_is_seed_only_and_package_config_is_stable(tmp_path: Path):
    root_config = tmp_path / "config"
    package_config = tmp_path / "work" / "ocl_config" / "PACKAGE_A"
    root_config.mkdir(parents=True)

    (root_config / "mapping.csv").write_text("source_label,category\nBonus,Employee\n", encoding="utf-8")
    (root_config / "semantic_handoff.json").write_text('{"status":"SHOULD_NOT_COPY"}', encoding="utf-8")

    _prepare_package_config(root_config, package_config)
    assert (package_config / "mapping.csv").read_text(encoding="utf-8") == "source_label,category\nBonus,Employee\n"
    assert not (package_config / "semantic_handoff.json").exists()

    # Package-specific review decisions must not be silently overwritten by a
    # later edit to global/default config.
    (package_config / "mapping.csv").write_text("source_label,category\nBonus,Reviewed Package Decision\n", encoding="utf-8")
    (root_config / "mapping.csv").write_text("source_label,category\nBonus,Changed Global Default\n", encoding="utf-8")
    _prepare_package_config(root_config, package_config)

    assert (package_config / "mapping.csv").read_text(encoding="utf-8") == "source_label,category\nBonus,Reviewed Package Decision\n"


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
