"""Reusable cross-source knowledge lifecycle for the embedded data-preparation runtime.

This module is the single repository-level owner of reusable knowledge storage,
rehydration, promotion filtering and audit metadata. The embedded runtime may
read/update its own ``knowledge/*.csv`` files while processing a source package;
only knowledge that passes this promotion boundary is retained for later source
packages.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

KNOWLEDGE_ASSETS = (
    "field_knowledge.csv",
    "structure_knowledge.csv",
    "corrections.csv",
)
BASELINE_DIR = "_baseline"
QUARANTINE_DIR = "quarantine"
MANIFEST_FILE = "manifest.json"
POLICY_VERSION = "generic-cross-source-v1"

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL_RE = re.compile(r"\b(?:https?://|www\.)", re.IGNORECASE)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_LONG_NUMERIC_RE = re.compile(r"(?<!\d)\d{6,}(?!\d)")
_WINDOWS_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|\\\\[^\\\s]+\\)")
_POSIX_USER_PATH_RE = re.compile(r"(?:/Users/|/home/)", re.IGNORECASE)


@dataclass(frozen=True)
class AssetPromotion:
    asset: str
    retained_rows: int
    newly_accepted_rows: int
    quarantined_rows: int
    schema_reset: bool = False


@dataclass(frozen=True)
class PromotionReport:
    policy_version: str
    source_fingerprint: str | None
    assets: tuple[AssetPromotion, ...]

    @property
    def accepted_rows(self) -> int:
        return sum(asset.newly_accepted_rows for asset in self.assets)

    @property
    def quarantined_rows(self) -> int:
        return sum(asset.quarantined_rows for asset in self.assets)

    def as_dict(self) -> dict:
        return {
            "policy_version": self.policy_version,
            "source_fingerprint": self.source_fingerprint,
            "accepted_rows": self.accepted_rows,
            "quarantined_rows": self.quarantined_rows,
            "assets": [asdict(asset) for asset in self.assets],
        }


def default_store(repo_root: Path) -> "KnowledgeStore":
    return KnowledgeStore(Path(repo_root) / "work" / "data_prep" / "knowledge")


def hydrate_runtime(runtime_project: Path, repo_root: Path, *, refresh_baseline: bool = False) -> None:
    default_store(repo_root).hydrate(runtime_project, refresh_baseline=refresh_baseline)


def promote_runtime(
    runtime_project: Path,
    repo_root: Path,
    *,
    source_dir: Path | None = None,
    source_fingerprint: str | None = None,
) -> dict:
    report = default_store(repo_root).promote(
        runtime_project,
        source_dir=source_dir,
        source_fingerprint=source_fingerprint,
    )
    return report.as_dict()


class KnowledgeStore:
    """Persist reusable data-understanding knowledge across source packages."""

    def __init__(self, root: Path):
        self.root = Path(root)

    @property
    def baseline_root(self) -> Path:
        return self.root / BASELINE_DIR

    @property
    def quarantine_root(self) -> Path:
        return self.root / QUARANTINE_DIR

    def hydrate(self, runtime_project: Path, *, refresh_baseline: bool = False) -> None:
        """Load previously promoted knowledge into the current runtime.

        A baseline snapshot is captured before the first run (and refreshed when
        a new vendored runtime is extracted). That snapshot lets promotion
        distinguish shipped knowledge from knowledge newly created by a source
        package.
        """
        runtime_knowledge = Path(runtime_project) / "knowledge"
        if not runtime_knowledge.is_dir():
            return

        self.root.mkdir(parents=True, exist_ok=True)
        self.baseline_root.mkdir(parents=True, exist_ok=True)

        for name in KNOWLEDGE_ASSETS:
            runtime_path = runtime_knowledge / name
            if not runtime_path.exists():
                continue

            baseline_path = self.baseline_root / name
            if refresh_baseline or not baseline_path.exists():
                shutil.copy2(runtime_path, baseline_path)

            persistent_path = self.root / name
            if not persistent_path.exists():
                continue

            runtime_header, _ = _read_csv(runtime_path)
            persistent_header, _ = _read_csv(persistent_path)
            if runtime_header and persistent_header and runtime_header != persistent_header:
                # A runtime schema change must not be hidden by an older local
                # snapshot. Leave the new runtime baseline in place; the next
                # successful promotion will rebuild the persistent file.
                continue
            shutil.copy2(persistent_path, runtime_path)

    def promote(
        self,
        runtime_project: Path,
        *,
        source_dir: Path | None = None,
        source_fingerprint: str | None = None,
    ) -> PromotionReport:
        """Promote only reusable rows after a successful published run.

        Previously promoted rows and shipped baseline rows are trusted. Rows
        newly introduced by the current source package are screened for obvious
        engagement-specific identifiers. Rejected rows remain available in a
        local gitignored quarantine for review, but are not rehydrated into the
        next source package.
        """
        runtime_knowledge = Path(runtime_project) / "knowledge"
        if not runtime_knowledge.is_dir():
            return PromotionReport(POLICY_VERSION, source_fingerprint, ())

        self.root.mkdir(parents=True, exist_ok=True)
        self.baseline_root.mkdir(parents=True, exist_ok=True)
        source_tokens = _source_tokens(source_dir)
        asset_reports: list[AssetPromotion] = []

        for name in KNOWLEDGE_ASSETS:
            runtime_path = runtime_knowledge / name
            if not runtime_path.exists():
                continue

            header, runtime_rows = _read_csv(runtime_path)
            if not header:
                continue

            baseline_path = self.baseline_root / name
            if not baseline_path.exists():
                shutil.copy2(runtime_path, baseline_path)
            baseline_header, baseline_rows = _read_csv(baseline_path)
            if baseline_header != header:
                # Baseline belongs to an older runtime schema. Refresh it from
                # the current runtime before evaluating future additions.
                shutil.copy2(runtime_path, baseline_path)
                baseline_rows = list(runtime_rows)

            persistent_path = self.root / name
            persistent_header: list[str] = []
            persistent_rows: list[list[str]] = []
            schema_reset = False
            if persistent_path.exists():
                persistent_header, persistent_rows = _read_csv(persistent_path)
                if persistent_header != header:
                    schema_reset = True
                    self._quarantine_schema_mismatch(name, persistent_path, source_fingerprint)
                    persistent_rows = []

            trusted = {_row_key(row) for row in (*baseline_rows, *persistent_rows)}
            retained_rows: list[list[str]] = []
            rejected_rows: list[tuple[int, list[str], str]] = []
            newly_accepted = 0

            for csv_row, row in enumerate(runtime_rows, start=2):
                if _row_key(row) in trusted:
                    retained_rows.append(row)
                    continue
                reason = _unsafe_reason(row, source_tokens)
                if reason:
                    rejected_rows.append((csv_row, row, reason))
                    continue
                retained_rows.append(row)
                newly_accepted += 1

            _write_csv(persistent_path, header, retained_rows)
            if rejected_rows:
                self._quarantine_rows(
                    name,
                    header,
                    rejected_rows,
                    source_fingerprint=source_fingerprint,
                )

            asset_reports.append(
                AssetPromotion(
                    asset=name,
                    retained_rows=len(retained_rows),
                    newly_accepted_rows=newly_accepted,
                    quarantined_rows=len(rejected_rows),
                    schema_reset=schema_reset,
                )
            )

        report = PromotionReport(POLICY_VERSION, source_fingerprint, tuple(asset_reports))
        (self.root / MANIFEST_FILE).write_text(
            json.dumps(report.as_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return report

    def _quarantine_rows(
        self,
        asset: str,
        header: list[str],
        rejected_rows: list[tuple[int, list[str], str]],
        *,
        source_fingerprint: str | None,
    ) -> None:
        key = (source_fingerprint or "unknown-source")[:16]
        destination = self.quarantine_root / key
        destination.mkdir(parents=True, exist_ok=True)
        _write_csv(destination / asset, header, [row for _, row, _ in rejected_rows])
        reasons = [
            {"csv_row": csv_row, "reason": reason}
            for csv_row, _row, reason in rejected_rows
        ]
        (destination / f"{asset}.reasons.json").write_text(
            json.dumps(reasons, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _quarantine_schema_mismatch(
        self,
        asset: str,
        persistent_path: Path,
        source_fingerprint: str | None,
    ) -> None:
        key = (source_fingerprint or "unknown-source")[:16]
        destination = self.quarantine_root / key / "schema_mismatch"
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(persistent_path, destination / asset)


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _write_csv(path: Path, header: list[str], rows: Iterable[list[str]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _row_key(row: Iterable[str]) -> tuple[str, ...]:
    return tuple(str(value or "").strip() for value in row)


def _source_tokens(source_dir: Path | None) -> tuple[str, ...]:
    if source_dir is None:
        return ()
    root = Path(source_dir)
    if not root.is_dir():
        return ()

    tokens: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        name = path.name.strip().casefold()
        stem = path.stem.strip().casefold()
        if len(name) >= 4:
            tokens.add(name)
        if len(stem) >= 4 and not stem.isdigit():
            tokens.add(stem)
    return tuple(sorted(tokens, key=len, reverse=True))


def _unsafe_reason(row: Iterable[str], source_tokens: tuple[str, ...]) -> str | None:
    text = " | ".join(str(value or "") for value in row)
    folded = text.casefold()

    for token in source_tokens:
        if token and token in folded:
            return "current_source_identifier"
    if _EMAIL_RE.search(text):
        return "email_address"
    if _URL_RE.search(text):
        return "url"
    if _WINDOWS_PATH_RE.search(text) or _POSIX_USER_PATH_RE.search(text):
        return "local_or_network_path"
    if _UUID_RE.search(text):
        return "uuid_like_identifier"
    if _LONG_NUMERIC_RE.search(text):
        return "long_numeric_identifier"
    return None


def file_sha256(path: Path) -> str:
    """Small public helper for audit/debug tooling."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
