"""Evidence-driven management questions.

Questions are created only when a finding gives a reason to ask. Each question
requests one focused operational explanation/evidence item; management is not
asked to decide FDD deal treatment.
"""
from __future__ import annotations

from ocl_agent.schemas import AnalysisResult, ManagementQuestion

MAX_QUESTIONS = 30
SPECIAL_TYPES = {"NEW_ITEM", "CLIFF", "STALE_BALANCE"}


def build_questions(analysis: AnalysisResult) -> tuple[ManagementQuestion, ...]:
    special_categories = {str(item.metrics.get("category")) for item in analysis.findings if item.finding_type in SPECIAL_TYPES and item.metrics.get("category")}
    questions: list[ManagementQuestion] = []
    for finding in analysis.findings:
        if finding.finding_type == "CATEGORY_MOVEMENT" and str(finding.metrics.get("category")) in special_categories:
            continue
        draft = _question_for_finding(finding.finding_type, finding.metrics)
        if draft is None:
            continue
        text, rationale = draft
        questions.append(ManagementQuestion(f"Q_{finding.finding_id}", text, rationale, finding.evidence_references, finding.finding_id, finding.priority))
    return tuple(_dedupe(questions)[:MAX_QUESTIONS])


def _question_for_finding(kind: str, metrics: dict):
    if kind == "TOTAL_CHANGE":
        previous, latest = metrics.get("previous_period"), metrics.get("latest_period")
        return (
            f"Please explain the principal operational or accounting drivers of the overall OCL movement between {previous} and {latest}.",
            "The closing OCL balance changed materially and the schedule alone does not explain the business drivers.",
        )
    if kind == "CATEGORY_MOVEMENT":
        category, previous, latest = metrics.get("category"), metrics.get("previous_period"), metrics.get("latest_period")
        return (
            f"Please explain the primary underlying driver of the movement in {category} between {previous} and {latest}.",
            "The category movement is material relative to the closing OCL balance and requires an operational explanation.",
        )
    if kind == "NEW_ITEM":
        label, latest = metrics.get("source_label"), metrics.get("latest_period")
        return (
            f"Please explain the specific event or calculation that gave rise to the new {label} balance in {latest}.",
            "The item was nil in the prior period and appears as a new closing obligation.",
        )
    if kind == "CLIFF":
        label, previous, latest = metrics.get("source_label"), metrics.get("previous_period"), metrics.get("latest_period")
        return (
            f"Please confirm how the {label} balance recorded in {previous} was settled or released before {latest}.",
            "The balance falls to nil and the schedule does not show whether this reflects cash settlement, reversal or release.",
        )
    if kind == "STALE_BALANCE":
        label, start, end = metrics.get("source_label"), metrics.get("start_period"), metrics.get("end_period")
        return (
            f"Please confirm whether the unchanged {label} balance from {start} to {end} remains a valid outstanding obligation.",
            "The balance has remained unchanged across multiple monthly closes, which may indicate a stale accrual or genuinely long-dated obligation.",
        )
    if kind == "CONCENTRATION":
        category, share = metrics.get("category"), metrics.get("share_pct")
        return (
            f"Please provide a breakdown of the principal obligations within {category}, including their expected settlement timing; this category represents approximately {share:.1f}% of closing OCL.",
            "The category is concentrated and a single summary balance may mask obligations with different settlement profiles.",
        )
    if kind == "MONTHLY_VARIABILITY":
        category, peak_period = metrics.get("category"), metrics.get("peak_period")
        return (
            f"Please explain the primary operational driver of the monthly volatility in {category}, including the peak in {peak_period}.",
            "The monthly schedule shows material variability that is not explained by the recorded balances alone.",
        )
    if kind == "DEBT_LIKE":
        period, amount = metrics.get("period"), metrics.get("amount")
        return (
            f"Please provide a breakdown of the obligations and expected settlement dates for the items classified in the FDD review as debt-like at {period} (total {amount}).",
            "The reviewed classification requires factual support on the underlying obligation and timing; management is not being asked to determine deal treatment.",
        )
    if kind == "ONE_OFF":
        period, amount = metrics.get("period"), metrics.get("amount")
        return (
            f"Please explain the specific events giving rise to the items classified as one-off/non-recurring at {period} (total {amount}).",
            "The reviewed normality classification identifies balances that may not reflect recurring operations; the factual origin should be confirmed.",
        )
    return None


def _dedupe(questions: list[ManagementQuestion]) -> list[ManagementQuestion]:
    seen: set[str] = set()
    result: list[ManagementQuestion] = []
    for question in questions:
        key = question.question.casefold().strip()
        if key not in seen:
            seen.add(key)
            result.append(question)
    return result
