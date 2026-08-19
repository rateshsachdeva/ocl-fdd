"""AI-neutral approval-question contracts and persisted user decision handling."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


QUESTION_CATEGORIES = {
    "BLOCKING_USER_DECISION",
    "NON_BLOCKING_ASSUMPTION",
    "INFORMATION_ONLY",
}
QUESTION_STATUSES = {"OPEN", "ANSWERED", "NOT_APPLICABLE"}
INTERACTION_TYPES = {"CHOICE", "FREE_TEXT"}


class ApprovalQuestionValidationError(ValueError):
    """Raised when an AI-host approval question artifact is structurally invalid."""


def validate_approval_questions(
    artifact: dict[str, Any], workflow_run_id: str, plan: dict[str, Any]
) -> list[str]:
    """Validate artifact structure and plan identity without judging AI reasoning."""
    errors: list[str] = []
    required = {
        "workflow_run_id",
        "plan_id",
        "plan_version",
        "blocking_questions",
        "non_blocking_assumptions",
        "information_items",
        "generated_at",
    }
    missing = required - set(artifact)
    errors.extend(f"approval_questions.{key} is required." for key in sorted(missing))
    if artifact.get("workflow_run_id") != workflow_run_id:
        errors.append("approval_questions.workflow_run_id does not match the workflow.")
    metadata = plan.get("plan_metadata", {})
    if artifact.get("plan_id") != metadata.get("plan_id"):
        errors.append("approval_questions.plan_id does not match the Processing Plan.")
    if artifact.get("plan_version") != metadata.get("plan_version"):
        errors.append("approval_questions.plan_version does not match the Processing Plan.")
    identifiers: set[str] = set()
    for index, question in enumerate(artifact.get("blocking_questions", [])):
        path = f"blocking_questions[{index}]"
        required_question = {
            "question_id", "topic", "question", "reason", "why_it_matters", "interaction_type",
            "options", "recommended_option_id", "recommendation_reason", "allow_other",
            "multi_select", "decision_effect", "affected_plan_elements", "status", "user_answer",
        }
        if not isinstance(question, dict):
            errors.append(f"{path} must be an object.")
            continue
        errors.extend(f"{path}.{key} is required." for key in sorted(required_question - set(question)))
        question_id = question.get("question_id")
        if not isinstance(question_id, str) or not question_id:
            errors.append(f"{path}.question_id must be a non-empty string.")
        elif question_id in identifiers:
            errors.append(f"Duplicate approval question_id: {question_id}.")
        else:
            identifiers.add(question_id)
        if question.get("status") not in QUESTION_STATUSES:
            errors.append(f"{path}.status is invalid.")
        interaction_type = question.get("interaction_type")
        if interaction_type not in INTERACTION_TYPES:
            errors.append(f"{path}.interaction_type is invalid.")
        options = question.get("options")
        if not isinstance(options, list):
            errors.append(f"{path}.options must be a list.")
            options = []
        option_ids: set[str] = set()
        for option_index, option in enumerate(options):
            option_path = f"{path}.options[{option_index}]"
            if not isinstance(option, dict):
                errors.append(f"{option_path} must be an object.")
                continue
            for key in ("option_id", "label", "short_description"):
                if not isinstance(option.get(key), str) or not option[key].strip():
                    errors.append(f"{option_path}.{key} must be a non-empty string.")
            option_id = option.get("option_id")
            if isinstance(option_id, str) and option_id:
                if option_id in option_ids:
                    errors.append(f"Duplicate option_id in {path}: {option_id}.")
                option_ids.add(option_id)
        if interaction_type == "CHOICE" and not option_ids:
            errors.append(f"{path} requires at least one structured option for CHOICE interaction.")
        if interaction_type == "FREE_TEXT" and options:
            errors.append(f"{path}.options must be empty for FREE_TEXT interaction.")
        recommended_option_id = question.get("recommended_option_id")
        recommendation_reason = question.get("recommendation_reason")
        if recommended_option_id is not None:
            if interaction_type != "CHOICE" or recommended_option_id not in option_ids:
                errors.append(f"{path}.recommended_option_id must identify a declared choice option.")
            if not isinstance(recommendation_reason, str) or not recommendation_reason.strip():
                errors.append(f"{path}.recommendation_reason is required when recommending an option.")
        elif recommendation_reason not in {None, ""}:
            errors.append(f"{path}.recommendation_reason requires a recommended_option_id.")
        for flag in ("allow_other", "multi_select"):
            if not isinstance(question.get(flag), bool):
                errors.append(f"{path}.{flag} must be a boolean.")
        if not isinstance(question.get("decision_effect"), str) or not question["decision_effect"].strip():
            errors.append(f"{path}.decision_effect must be a non-empty string.")
        if question.get("status") == "ANSWERED" and not question.get("user_answer"):
            errors.append(f"{path}.user_answer is required when status is ANSWERED.")
    for category in ("non_blocking_assumptions", "information_items"):
        for index, item in enumerate(artifact.get(category, [])):
            if not isinstance(item, dict):
                errors.append(f"{category}[{index}] must be an object.")
                continue
            for key in ("topic", "statement", "confidence", "evidence"):
                if key not in item:
                    errors.append(f"{category}[{index}].{key} is required.")
    return errors


def unresolved_blocking_questions(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Return material questions not answered or explicitly marked not applicable."""
    return [
        question
        for question in artifact.get("blocking_questions", [])
        if question.get("status") == "OPEN"
    ]


def persist_user_decisions(
    questions: dict[str, Any], responses: list[dict[str, Any]], output_path: Path
) -> dict[str, Any]:
    """Persist user responses separately; it never changes the Processing Plan."""
    known = {question["question_id"]: question for question in questions.get("blocking_questions", [])}
    decisions = []
    for response in responses:
        question_id = response.get("question_id")
        question = known.get(question_id)
        if question is None:
            raise ApprovalQuestionValidationError(f"Unknown question_id in user decision: {question_id}.")
        answer = response.get("answer")
        option_id = None
        other_answer = None
        if question.get("interaction_type") == "CHOICE":
            option_id = response.get("option_id") or answer
            if option_id is None or option_id == "":
                raise ApprovalQuestionValidationError(f"A user decision requires an option_id: {question_id}.")
            valid_options = {item.get("option_id") for item in question.get("options", [])}
            if option_id not in valid_options and not (option_id == "OTHER" and question.get("allow_other")):
                raise ApprovalQuestionValidationError(
                    f"Decision option_id is not declared for question {question_id}: {option_id}."
                )
            other_answer = response.get("other_answer")
            if option_id == "OTHER" and not other_answer:
                raise ApprovalQuestionValidationError(f"An OTHER decision requires other_answer: {question_id}.")
            answer = option_id
        elif answer is None or answer == "":
            raise ApprovalQuestionValidationError(f"A user decision requires an answer: {question_id}.")
        decisions.append({
            "question_id": question_id,
            "answer": answer,
            "option_id": option_id,
            "other_answer": other_answer,
            "timestamp": response.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "user_note": response.get("user_note"),
        })
    document = {
        "workflow_run_id": questions.get("workflow_run_id"),
        "plan_id": questions.get("plan_id"),
        "plan_version": questions.get("plan_version"),
        "decisions": decisions,
    }
    Path(output_path).write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return document


def apply_user_decisions(questions: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    """Return an approval artifact view with recorded responses; no plan change occurs."""
    answers = {item["question_id"]: item for item in decisions.get("decisions", [])}
    updated = json.loads(json.dumps(questions))
    for question in updated.get("blocking_questions", []):
        decision = answers.get(question["question_id"])
        if decision:
            question["status"] = "ANSWERED"
            question["user_answer"] = decision.get("option_id") or decision["answer"]
    return updated
