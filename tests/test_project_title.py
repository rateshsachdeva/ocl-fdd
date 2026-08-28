from ocl_agent.project_title import DEFAULT_PROJECT_TITLE, resolve_project_title


class _Package:
    def __init__(self, metadata):
        self._metadata = metadata

    def metadata_payload(self):
        return self._metadata


def test_title_uses_unique_evidenced_upstream_entity():
    package = _Package({"logical_datasets": [{"metadata": [{"metadata_type": "ENTITY", "status": "EVIDENCED", "value": "Example Group"}]}]})

    assert resolve_project_title(package=package) == "Example Group - Other Current Liabilities"


def test_title_is_neutral_when_upstream_identity_is_absent_or_ambiguous():
    absent = _Package({})
    ambiguous = _Package({"logical_datasets": [{"metadata": [{"metadata_type": "ENTITY", "status": "EVIDENCED", "value": "Entity A"}, {"metadata_type": "ENTITY", "status": "EVIDENCED", "value": "Entity B"}]}]})

    assert resolve_project_title(package=absent) == DEFAULT_PROJECT_TITLE
    assert resolve_project_title(package=ambiguous) == DEFAULT_PROJECT_TITLE
    assert "TargetCo" not in DEFAULT_PROJECT_TITLE
