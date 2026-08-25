# FDD Partner Analysis — AI Host Instruction

## Purpose

Use the active AI host (Codex, Claude Code, GitHub Copilot, or another capable coding agent) to turn validated OCL metrics into concise, decision-useful Financial Due Diligence interpretation.

The AI host writes narrative judgment only. Python remains the sole owner of source values, calculations, reconciliations, classifications and materiality tests.

## Mindset

Think and write as an experienced FDD partner reviewing the OCL workstream for a deal team.

Do not merely restate movements. Ask what the evidence could mean for:

- net debt / equity value;
- quality of earnings;
- normalized working capital and peg considerations;
- seasonality / whether the closing balance is representative;
- completeness and validity of liabilities;
- settlement timing, releases and reversals;
- concentration and unusual balance composition;
- inconsistencies between management and FDD treatment;
- limitations in the available evidence that matter to the transaction.

Prioritize commercial consequence. A good finding should answer: **what changed, why does it matter to the deal, and what fact still needs to be established?**

## Evidence discipline

Read the referenced `analysis_evidence.json` produced by Python.

Use only evidence contained in that file and the referenced reconciled OCL outputs. Do not invent amounts, percentages, periods, categories, explanations or management facts.

Do not recalculate financial metrics with AI. If the evidence is insufficient to support a conclusion, qualify the point and identify the missing fact instead of guessing.

The Python materiality flags are evidence, not a substitute for professional judgment. Do not manufacture headline issues merely to fill a page. Conversely, a transaction-relevant pattern may be worth surfacing even when it is not a deterministic headline trigger, provided the evidence supports it and it is clearly described as a notable observation rather than an unsupported conclusion.

If no material deal issue is supported, write an explicit evidence-based conclusion rather than leaving the sections blank.

## Writing standard

Write in concise FDD language, not generic AI prose.

Avoid phrases such as:

- "This is noteworthy" without explaining why;
- "Management should investigate" without stating the factual question;
- generic commentary that merely repeats a percentage;
- speculative causes presented as facts.

Prefer formulations such as:

- "The closing accrual is materially above the trailing run-rate, which could overstate normalized working capital if the year-end position is not representative. The underlying timing driver and expected reversal profile should be confirmed."
- "A material portion of OCL has been classified as debt-like by FDD but not by management, creating a potential equity-value reconciliation item subject to the SPA definition and settlement evidence."

## Required output

Write the exact JSON file requested in the handoff as `analysis_interpretation.json`.

Use this structure:

```json
{
  "status": "COMPLETED",
  "overall_assessment": "One concise partner-level conclusion.",
  "deal_issues": [
    {
      "id": "DI_01",
      "priority": "HIGH",
      "title": "Commercial issue title",
      "so_what": "Deal implication in one or two sentences.",
      "evidence": "Factual evidence from the supplied metrics.",
      "management_focus": "The specific factual matter to establish.",
      "linked_finding_id": "F_TOTAL_CHANGE",
      "evidence_refs": ["finding:F_TOTAL_CHANGE"]
    }
  ],
  "key_findings": [
    {
      "id": "KF_01",
      "area": "Working capital & balance validity",
      "metric": "Closing balance vs run-rate",
      "period_item": "FY25 / Bonus accrual",
      "so_what": "Why the evidence matters to the transaction.",
      "evidence": "Concise factual observation.",
      "materiality": "MATERIAL",
      "ask_management": "One focused factual question.",
      "linked_finding_id": "F_MOVE_BONUS_ACCRUAL",
      "evidence_refs": ["finding:F_MOVE_BONUS_ACCRUAL", "table:movement_review:0"]
    }
  ]
}
```

Rules:

- `status` must be `COMPLETED`.
- Produce 0–6 `deal_issues` and 1–8 `key_findings` where evidence supports them.
- If there is genuinely no material issue, `deal_issues` may be empty, but `overall_assessment` and at least one `key_findings` row should explicitly state the evidence-based conclusion rather than leaving the workbook blank.
- `priority` must be `HIGH`, `MEDIUM` or `LOW`.
- `materiality` should normally be `MATERIAL`, `NOTABLE` or `NO_MATERIAL_ISSUE`.
- `linked_finding_id` may be null when the observation is supported by a table rather than a deterministic finding.
- Every item must contain at least one valid `evidence_refs` entry.
- Valid references are listed in `analysis_evidence.json`; use `finding:<id>` or `table:<table_key>:<zero-based-row-index>`.
- Do not place new financial calculations in the JSON. Narrative may quote supplied metrics, but Python remains authoritative.
- Do not ask management to decide whether something is debt-like, working capital, or a QoE adjustment. Ask for operational/accounting facts that allow the deal team to make that judgment.

After writing the artifact, rerun `python run_all.py` and continue automatically if `Workflow coordination` again says `next_actor = AI_HOST` and `must_continue = true`.
