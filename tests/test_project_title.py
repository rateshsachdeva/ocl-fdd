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


def test_title_uses_explicit_evidenced_readme_company_label():
    package = _Package({
        "logical_datasets": [{
            "metadata": [{
                "metadata_type": "DATASET_PURPOSE",
                "status": "EVIDENCED",
                "confidence": "HIGH",
                "source_context": "Finance_Pack.xlsx / Read me / A1:B6",
                "value": "Finance extract context",
                "evidence": "Read me region identifies Harbour Leisure Group, finance extract and management reporting source.",
            }]
        }]
    })

    assert resolve_project_title(package=package) == "Harbour Leisure Group - Other Current Liabilities"


def test_title_does_not_infer_identity_from_arbitrary_dataset_or_transaction_descriptions():
    arbitrary = _Package({
        "logical_datasets": [{
            "metadata": [{
                "metadata_type": "DATASET_PURPOSE",
                "status": "EVIDENCED",
                "source_context": "Transactions.xlsx / Detail",
                "value": "Customer transactions",
                "evidence": "The transaction descriptions identify Example Customer, Example Vendor and Example Project.",
            }]
        }]
    })

    assert resolve_project_title(package=arbitrary) == DEFAULT_PROJECT_TITLE
