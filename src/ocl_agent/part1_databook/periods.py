"""Explicit period continuity without inferring calendar/fiscal semantics."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from ocl_agent.schemas import CheckStatus, ControlResult, OCLRecord


def continuity_control(records: tuple[OCLRecord, ...], handoff_path: Path) -> ControlResult:
    payload = json.loads(Path(handoff_path).read_text(encoding="utf-8"))
    annual_expected = _sequence(payload.get("expected_annual_periods"))
    monthly_expected = _sequence(payload.get("expected_monthly_periods"))
    if not annual_expected and not monthly_expected:
        return ControlResult("chk_continuity", CheckStatus.NOT_APPLICABLE, message="No explicit expected period sequence was supplied; period labels are not guessed.")
    annual_actual = {row.period for row in records if row.dimensions.get("record_usage") != "MONTHLY_RECORDS"}
    monthly_actual = {row.period for row in records if row.dimensions.get("record_usage") == "MONTHLY_RECORDS"}
    missing_annual = [period for period in annual_expected if period not in annual_actual]
    missing_monthly = [period for period in monthly_expected if period not in monthly_actual]
    missing = len(missing_annual) + len(missing_monthly)
    return ControlResult(
        "chk_continuity",
        CheckStatus.PASS if missing == 0 else CheckStatus.FAIL,
        Decimal(missing),
        Decimal("0"),
        Decimal(missing),
        message="All explicitly expected annual/monthly periods are present." if missing == 0 else "One or more explicitly expected periods are missing.",
        evidence={"missing_annual": missing_annual, "missing_monthly": missing_monthly},
    )


def _sequence(value) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    result = tuple(str(item).strip() for item in value if str(item).strip())
    return result if len(set(result)) == len(result) else ()
