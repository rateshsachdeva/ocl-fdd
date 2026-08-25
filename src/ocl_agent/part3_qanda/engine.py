"""Evidence-driven management questions for material OCL findings.

Questions are created only when a material finding gives a reason to ask. Each
question requests one focused operational explanation or factual confirmation;
management is not asked to decide FDD deal treatment.
"""
from __future__ import annotations

from ocl_agent.schemas import AnalysisResult, ManagementQuestion

MAX_QUESTIONS = 30
SPECIAL_TYPES = {"NEW_ITEM", "CLIFF", "STALE_BALANCE"}


def build_questions(analysis: AnalysisResult) -> tuple[ManagementQuestion, ...]:
    special_categories = {
        str(item.metrics.get("category"))
        for item in analysis.findings
        if item.finding_type in SPECIAL_TYPES and item.metrics.get("category")
    }
    questions: list[ManagementQuestion] = []
    for finding in analysis.findings:
        if str(finding.metrics.get("materiality") or "MATERIAL").upper() != "MATERIAL":
            continue
        if finding.finding_type == "CATEGORY_MOVEMENT" and str(finding.metrics.get("category")) in special_categories:
            continue
        draft = _question_for_finding(finding.finding_type, finding.metrics)
        if draft is None:
            continue
        text, rationale = draft
        questions.append(
            ManagementQuestion(
                f"Q_{finding.finding_id}",
                text,
                rationale,
                finding.evidence_references,
                finding.finding_id,
                finding.priority,
            )
        )
    return tuple(_dedupe(questions)[:MAX_QUESTIONS])


def _question_for_finding(kind: str, metrics: dict):
    if kind == "TOTAL_CHANGE":
        previous, latest = metrics.get("previous_period"), metrics.get("latest_period")
        return (
            f"Please explain the principal operational or accounting drivers of the overall OCL movement between {previous} and {latest}.",
            "The overall closing OCL movement is material and should reconcile to identifiable category-level drivers.",
        )
    if kind == "CATEGORY_MOVEMENT":
        category, previous, latest = metrics.get("category"), metrics.get("previous_period"), metrics.get("latest_period")
        return (
            f"Please explain the primary underlying driver of the movement in {category} between {previous} and {latest}, and whether the closing level is expected to recur.",
            "The movement meets the focused findings materiality threshold and requires an operational explanation.",
        )
    if kind == "NEW_ITEM":
        label, latest = metrics.get("source_label"), metrics.get("latest_period")
        return (
            f"Please explain the specific event or calculation that gave rise to the new {label} balance in {latest}.",
            "The item was nil in the prior period and appears as a material new closing obligation.",
        )
    if kind == "CLIFF":
        label, previous, latest = metrics.get("source_label"), metrics.get("previous_period"), metrics.get("latest_period")
        return (
            f"Please explain whether the {label} balance recorded in {previous} was settled, released or reversed before {latest}, and the basis for that treatment.",
            "The material balance falls to nil and the schedule alone does not explain the nature of the reduction.",
        )
    if kind == "STALE_BALANCE":
        label, start, end = metrics.get("source_label"), metrics.get("start_period"), metrics.get("end_period")
        return (
            f"Please confirm whether the unchanged {label} balance from {start} to {end} remains a valid outstanding obligation and when it is expected to settle.",
            "The material balance has remained unchanged across multiple monthly closes and may be stale or genuinely long-dated.",
        )
    if kind == "CONCENTRATION":
        category, share = metrics.get("category"), metrics.get("share_pct")
        return (
            f"Please explain the principal obligations and settlement profile within {category}; this category represents approximately {share:.1f}% of closing OCL.",
            "The balance is concentrated and different underlying obligations may have different working-capital or deal implications.",
        )
    if kind == "MONTHLY_VARIABILITY":
        category, peak_period = metrics.get("category"), metrics.get("peak_period")
        return (
            f"Please explain the primary operational driver of the monthly volatility in {category}, including the peak in {peak_period}.",
            "The monthly pattern is materially variable and a single balance-sheet date may not be representative.",
        )
    if kind == "SEASONALITY":
        category = metrics.get("category")
        period = metrics.get("period")
        return (
            f"Please explain why the {category} balance at {period} differs materially from its trailing 12-month average and whether the year-end level is representative.",
            "The year-end balance differs materially from the normal in-year level and may affect working-capital interpretation.",
        )
    if kind == "DEBT_LIKE":
        period, amount = metrics.get("period"), metrics.get("amount")
        return (
            f"Please describe the underlying obligations and expected settlement dates for the items identified in the FDD review as debt-like at {period} (total {amount}).",
            "The reviewed FDD classification requires factual support on the obligation and timing; management is not being asked to determine deal treatment.",
        )
    if kind == "DEBT_LIKE_GAP":
        period = metrics.get("period")
        fdd_amount = metrics.get("fdd_amount")
        management_amount = metrics.get("management_amount")
        return (
            f"Please explain the factual basis for the difference between management's debt-like view ({management_amount}) and the FDD view ({fdd_amount}) at {period}, including expected settlement timing.",
            "The classification gap is a potential deal-value reconciliation matter and should be supported by facts rather than management choosing the FDD treatment.",
        )
    if kind == "ONE_OFF":
        period, amount = metrics.get("period"), metrics.get("amount")
        return (
            f"Please explain the specific events giving rise to the items identified as one-off/non-recurring at {period} (total {amount}).",
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
