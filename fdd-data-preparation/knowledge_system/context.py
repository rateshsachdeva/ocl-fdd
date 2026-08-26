"""Build a compact reusable-knowledge packet for the AI data-understanding checkpoint.

The source-controlled knowledge pack is intentionally broader than any one client.
This module matches that pack to the deterministic profile for the current source
package and writes a short context file. AI therefore reads relevant prior
knowledge rather than a large synthetic-training prompt or the whole repository.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BUILTIN_PATTERNS = Path(__file__).with_name("builtin_patterns.json")
MAX_PROFILE_BYTES = 2_000_000
MAX_MATCHED_PATTERNS = 14
MIN_PATTERN_HITS = 2


def build_context_packet(
    repo_root: Path,
    runs_root: Path,
    source_dir: Path,
    source_fingerprint: str,
) -> Path:
    """Create a concise source-bound knowledge packet and return its path."""
    repo_root = Path(repo_root).resolve()
    runs_root = Path(runs_root).resolve()
    source_dir = Path(source_dir).resolve()

    knowledge = _load_builtin_knowledge()
    profile_path = _latest_profile(runs_root)
    evidence_text = _evidence_text(source_dir, profile_path)
    matched = _match_patterns(knowledge.get("patterns", []), evidence_text)

    context_dir = repo_root / "work" / "data_prep" / "knowledge" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    output = context_dir / f"{source_fingerprint[:16]}.md"

    source_names = sorted(
        path.name
        for path in source_dir.rglob("*")
        if path.is_file() and not path.name.startswith("~$")
    )
    lines: list[str] = [
        "# Reusable Data-Understanding Context",
        "",
        f"Knowledge version: {knowledge.get('version', 'unknown')}",
        f"Source fingerprint: {source_fingerprint}",
        f"Source files in this package: {', '.join(source_names) if source_names else '(none)'}",
        f"Profile used for matching: {profile_path if profile_path else '(profile not yet located)'}",
        "",
        "## How to use this",
        "",
        "This is reusable prior knowledge, not a source-of-truth mapping and not an answer key.",
        "Use it to recognize familiar structural/accounting patterns quickly, but current-source evidence always wins.",
        "Do not force a prior interpretation when the current profile/samples disagree.",
        "",
        "## Core principles",
        "",
    ]
    for principle in knowledge.get("core_principles", []):
        lines.append(f"- {principle}")

    lines.extend(["", "## Patterns relevant to this source", ""])
    if matched:
        for score, item in matched:
            lines.append(f"### {item['id']}  (match score {score})")
            lines.append("")
            lines.append(str(item["guidance"]))
            lines.append("")
    else:
        lines.extend(
            [
                "No source-specific pattern reached the corroborating-evidence threshold.",
                "Apply the core principles and reason from the current profile/samples without guessing.",
                "",
            ]
        )

    lines.extend(
        [
            "## Fast-planning protocol",
            "",
            "1. Start from the deterministic profile/handoff; do not browse the repository broadly.",
            "2. Use the matched patterns above to resolve already-familiar structure quickly.",
            "3. Spend reasoning effort only on genuine ambiguities, changed grains, conflicting field meanings or unsupported relationships.",
            "4. Do not inspect every month/file independently when deterministic evidence establishes a common schema or conceptual dataset.",
            "5. Preserve supporting datasets and join keys that may enable OCL analysis (P&L, payroll, mapping, movements, AP/subsequent payments, contracts/projects) without deeply analysing them during planning.",
            "6. Produce the required Dataset Map / Processing Plan directly from the prepared evidence; do not run code inside the AI checkpoint.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _load_builtin_knowledge() -> dict[str, Any]:
    if not BUILTIN_PATTERNS.exists():
        raise FileNotFoundError(f"Built-in knowledge pack is missing: {BUILTIN_PATTERNS}")
    payload = json.loads(BUILTIN_PATTERNS.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Built-in knowledge pack must be a JSON object.")
    return payload


def _latest_profile(runs_root: Path) -> Path | None:
    candidates = [path for path in runs_root.rglob("profile.json") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def _evidence_text(source_dir: Path, profile_path: Path | None) -> str:
    parts = [
        path.name
        for path in source_dir.rglob("*")
        if path.is_file() and not path.name.startswith("~$")
    ]
    if profile_path is not None:
        with profile_path.open("rb") as handle:
            raw = handle.read(MAX_PROFILE_BYTES)
        parts.append(raw.decode("utf-8", errors="replace"))
    return _normalise("\n".join(parts))


def _match_patterns(patterns: list[dict[str, Any]], evidence_text: str) -> list[tuple[int, dict[str, Any]]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in patterns:
        keywords = [str(value).strip() for value in item.get("keywords", []) if str(value).strip()]
        if not keywords:
            continue
        hits = sum(1 for keyword in keywords if _normalise(keyword) in evidence_text)
        if hits >= MIN_PATTERN_HITS:
            ranked.append((hits, item))
    ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("id", ""))))
    return ranked[:MAX_MATCHED_PATTERNS]


def _normalise(value: str) -> str:
    text = value.casefold().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text)
