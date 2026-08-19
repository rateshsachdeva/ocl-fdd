"""Evidence-driven management questions.

Questions are created only when a finding gives a reason to ask.  This avoids
question-for-question's-sake output and keeps wording specific to the evidence.
"""
from __future__ import annotations

from ocl_agent.schemas import AnalysisResult, ManagementQuestion


def build_questions(analysis: AnalysisResult) -> tuple[ManagementQuestion, ...]:
    questions: list[ManagementQuestion] = []
    for finding in analysis.findings:
        question = _question_for_finding(finding.finding_type, finding.metrics)
        if question is None:
            continue
        text, rationale = question
        questions.append(ManagementQuestion(
            question_id=f"Q_{finding.finding_id}",
            question=text,
            rationale=rationale,
            evidence_references=finding.evidence_references,
            linked_finding_id=finding.finding_id,
            priority=finding.priority,
        ))
    return tuple(_dedupe(questions))


def _question_for_finding(kind: str, metrics: dict):
    if kind == "TOTAL_CHANGE":
        previous = metrics.get("previous_period")
        latest = metrics.get("latest_period")
        change = metrics.get("change")
        return (
            f"What were the main operational or accounting drivers of the OCL movement between {previous} and {latest}, and how much of the {change} change is expected to reverse in the normal course of business?",
            "The closing OCL balance changed materially; understanding the drivers and expected reversal is relevant to normalized working capital and debt-like assessment.",
        )
    if kind == "CATEGORY_MOVEMENT":
        category = metrics.get("category")
        previous = metrics.get("previous_period")
        latest = metrics.get("latest_period")
        return (
            f"What specifically drove the movement in {category} between {previous} and {latest}, and does the closing balance include any catch-up, delayed payment, estimate true-up or unusual item?",
            "The category moved materially and may reflect timing, estimation or non-recurring effects that are not visible from the ledger balance alone.",
        )
    if kind == "CONCENTRATION":
        category = metrics.get("category")
        share = metrics.get("share_pct")
        return (
            f"{category} represents approximately {share:.1f}% of the closing OCL balance. What are the principal underlying obligations, how is the balance calculated, and what is the typical settlement timing?",
            "A concentrated closing balance can have a disproportionate impact on working-capital normalization and requires clarity on composition and settlement mechanics.",
        )
    if kind == "MONTHLY_VARIABILITY":
        category = metrics.get("category")
        peak_period = metrics.get("peak_period")
        return (
            f"What explains the month-to-month volatility in {category}, including the peak in {peak_period}, and is the pattern driven by seasonality, payment timing, estimation methodology or discrete events?",
            "Material monthly variability is visible in the reconciled schedule and warrants explanation before treating a single closing balance as representative.",
        )
    if kind == "DEBT_LIKE":
        period = metrics.get("period")
        amount = metrics.get("amount")
        return (
            f"For the items classified as debt-like at {period} (totaling {amount}), please confirm the underlying obligations, expected settlement dates and whether any amounts are already reflected elsewhere in net debt or purchase-price mechanics.",
            "Reviewed FDD classification indicates potential debt-like exposure and duplicate counting should be avoided.",
        )
    if kind == "ONE_OFF":
        period = metrics.get("period")
        amount = metrics.get("amount")
        return (
            f"For the items classified as one-off/non-recurring at {period} (totaling {amount}), what gave rise to them and should any portion be excluded from a normalized working-capital benchmark?",
            "Reviewed normality judgments identify balances that may not represent the recurring operating level.",
        )
    return None


def _dedupe(questions: list[ManagementQuestion]) -> list[ManagementQuestion]:
    seen: set[str] = set()
    result: list[ManagementQuestion] = []
    for question in questions:
        key = question.question.casefold().strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(question)
    return result
