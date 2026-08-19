"""Read-only retrieval from user-editable knowledge CSV stores."""

import csv
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re
import os
from typing import Iterable


@dataclass(frozen=True, slots=True)
class KnowledgeStorePaths:
    field_knowledge: Path
    structure_knowledge: Path
    corrections: Path


PRIOR_OBSERVATIONS_DISCLAIMER = (
    "Prior observations are contextual evidence only. Determine applicability independently from the current source."
)
CONFIRMED_SYNTHETIC_FIELD_ROWS = (
    ("Customer", "customer", "PRIMARY_DATA dataset with 2 interpreted fields"),
    ("M01", "m01", "PRIMARY_DATA dataset with 2 interpreted fields"),
)


def assert_writable_knowledge_store(path: Path) -> None:
    """Reject pytest attempts to mutate the repository's permanent knowledge stores."""
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        return
    repository_knowledge = Path(__file__).resolve().parents[2] / "knowledge"
    try:
        Path(path).resolve().relative_to(repository_knowledge.resolve())
    except ValueError:
        return
    raise PermissionError("Pytest must use isolated temporary KnowledgeStorePaths; repository knowledge is read-only during tests.")


def remove_confirmed_synthetic_field_rows(field_path: Path) -> list[dict[str, str]]:
    """Remove only provenance-confirmed synthetic field rows from a selected store."""
    assert_writable_knowledge_store(field_path)
    with Path(field_path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    targets = set(CONFIRMED_SYNTHETIC_FIELD_ROWS)
    removed = [
        row for row in rows
        if (row.get("Observed_Name"), row.get("Concept"), row.get("Dataset_Context")) in targets
    ]
    retained = [row for row in rows if row not in removed]
    with Path(field_path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(retained)
    return removed


def find_relevant_knowledge(
    query: str | Iterable[str],
    paths: KnowledgeStorePaths,
    *,
    dataset_context: str | None = None,
    minimum_score: float = 0.55,
    limit: int = 20,
) -> dict[str, object]:
    """Retrieve active observations using normalized text and fuzzy matching only."""
    queries = [_normalise(item) for item in ([query] if isinstance(query, str) else query) if _normalise(item)]
    context = _normalise(dataset_context or "")
    matches = []
    for store_name, path in (
        ("field_knowledge", paths.field_knowledge),
        ("structure_knowledge", paths.structure_knowledge),
        ("corrections", paths.corrections),
    ):
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if not _is_active(row.get("Active")):
                    continue
                searchable = " ".join(value or "" for value in row.values())
                score = _match_score(queries, _normalise(searchable))
                if context:
                    score = max(score, _match_score([context], _normalise(searchable)))
                if score >= minimum_score:
                    matches.append({
                        "store": store_name,
                        "score": round(score, 3),
                        "priority": _knowledge_priority(store_name, row),
                        "observation": row,
                    })
    return {
        "disclaimer": PRIOR_OBSERVATIONS_DISCLAIMER,
        "matches": _rank_matches(matches)[:limit],
    }


def _is_active(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"true", "1", "yes", "y"}


def _normalise(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _match_score(queries: list[str], searchable: str) -> float:
    if not queries or not searchable:
        return 0.0
    return max(
        max(
            1.0 if query in searchable else 0.0,
            SequenceMatcher(None, query, searchable).ratio(),
        )
        for query in queries
    )


def _knowledge_priority(store_name: str, row: dict[str, str]) -> int:
    confirmed = str(row.get("User_Confirmed") or "").strip().casefold() in {"true", "1", "yes", "y"}
    confidence = str(row.get("Confidence") or "").strip().upper()
    if store_name == "corrections" and confirmed:
        return 0
    if confirmed:
        return 1
    if confidence == "HIGH" and int(row.get("Times_Seen") or 0) > 1:
        return 2
    return 3


def _rank_matches(matches: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(
        matches,
        key=lambda item: (
            item["observation"].get("Last_Seen") or item["observation"].get("Date") or "",
        ),
        reverse=True,
    )
    ranked = sorted(ranked, key=lambda item: item["score"], reverse=True)
    ranked = sorted(ranked, key=lambda item: int(item["observation"].get("Times_Seen") or 0), reverse=True)
    return sorted(ranked, key=lambda item: item["priority"])
