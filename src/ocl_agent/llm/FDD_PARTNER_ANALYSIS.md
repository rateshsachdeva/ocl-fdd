# FDD Partner Analysis — AI Host Instruction

## Purpose

Use the active AI host (Codex, Claude Code, GitHub Copilot, or another capable coding agent) to turn validated OCL metrics into concise, decision-useful Financial Due Diligence interpretation.

The AI host writes the Deal Issues, Key Findings and Management Q&A. Python remains the sole owner of source values, calculations, reconciliations, classifications and materiality tests.

## Mindset

Think and write as an experienced FDD partner reviewing the OCL workstream for a deal team.

Do not merely restate movements. Ask what the evidence could mean for net debt / equity value, quality of earnings, normalized working capital, seasonality, completeness and validity of liabilities, settlement timing, releases and reversals, concentration, unusual balance composition, and inconsistencies between management and FDD treatment.

Prioritize commercial consequence. A good finding should answer: **what changed, why does it matter to the deal, and what fact still needs to be established?**

## Evidence discipline

Read the referenced `analysis_evidence.json` produced by Python. Use only evidence contained in that file and the reconciled OCL outputs it represents. Do not invent amounts, percentages, periods, categories, explanations or management facts.

Do not recalculate financial metrics with AI. If evidence is insufficient, qualify the point and identify the missing fact instead of guessing.

The Python materiality flags are evidence, not a substitute for professional judgment. Do not manufacture headline issues or questions merely to fill a page. Conversely, a transaction-relevant pattern may be surfaced as a notable observation when the supplied evidence supports it even if it is not a deterministic headline trigger.

If no material deal issue is supported, state that conclusion explicitly rather than leaving the sections blank.

### Analysis coverage is a hard evidence boundary

If `analysis_evidence.json` contains the `analysis_coverage` table, read it before drawing conclusions about the scope of testing.

- `SUPPORTED` means the stated analysis can be interpreted from the evidence provided.
- `PARTIAL` means the evidence supports only the stated proxy or limited conclusion; do not promote it to a stronger assertion.
- `REFERENCE_ONLY` means the metric is a benchmark/run-rate reference, not an adjustment or conclusion by itself.
- `UNSUPPORTED` means the required evidence was not supplied. Do not imply the analysis was performed or conclude there is no issue.

In particular, do not claim adequacy, missing-accrual completeness, double counting or true obligation aging was tested unless the coverage/evidence explicitly supports it. An unchanged-balance stale proxy is not the same as aging. A 12-month average or median is not automatically a normalized working-capital adjustment. Utilisation/reversal conclusions require explicit movement evidence.

## Management questions

Questions must also be written with an FDD-partner mindset:

- ask only when a factual answer would help resolve a finding or transaction implication;
- one clear action / factual point per question;
- ask for operational or accounting facts, not for management to make the FDD judgment;
- do not ask management whether an item "should be debt-like", "should be working capital" or "should be a QoE adjustment";
- avoid generic document requests unless the document is specifically needed to establish the fact;
- group duplicate/root-cause questions rather than repeating the same question for several balances;
- make wording natural and specific to the evidence;
- if no question is warranted, return an empty list rather than filler.

## Writing standard

Write in concise FDD language, not generic AI prose. Avoid empty phrases such as "this is noteworthy" or "management should investigate" without explaining the deal relevance or factual point to establish. Do not present speculative causes as facts.

## Required output

Write the exact JSON file requested in the handoff as `analysis_interpretation.json` and copy the `evidence_hash` exactly from `analysis_evidence.json`.

```json
{
  "status": "COMPLETED",
  "evidence_hash": "copy exactly from analysis_evidence.json",
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
      "ask_management": "One focused factual point, or blank when no question is warranted.",
      "linked_finding_id": "F_MOVE_BONUS_ACCRUAL",
      "evidence_refs": ["finding:F_MOVE_BONUS_ACCRUAL"]
    }
  ],
  "management_questions": [
    {
      "id": "Q_01",
      "theme": "Working capital & balance validity",
      "question": "Please explain the operational driver of the closing balance and expected settlement timing.",
      "evidence": "Why this question is warranted based on the supplied evidence.",
      "priority": "HIGH",
      "linked_finding_id": "F_MOVE_BONUS_ACCRUAL",
      "evidence_refs": ["finding:F_MOVE_BONUS_ACCRUAL"]
    }
  ]
}
```

Rules:

- `status` must be `COMPLETED` and `evidence_hash` must exactly match the request.
- Produce 0–6 `deal_issues`, 1–8 `key_findings`, and 0–8 `management_questions`.
- If there is genuinely no material issue, `deal_issues` may be empty, but `overall_assessment` and at least one `key_findings` row must explicitly state the evidence-based conclusion so the workbook is not blank.
- `priority` must be `HIGH`, `MEDIUM` or `LOW`.
- `materiality` must be `MATERIAL`, `NOTABLE` or `NO_MATERIAL_ISSUE`.
- `linked_finding_id` may be null when an observation is supported by a table rather than a deterministic finding.
- Every deal issue, key finding and management question must contain at least one valid `evidence_refs` entry.
- Valid references are listed in `analysis_evidence.json`: `finding:<id>` or `table:<table_key>:<zero-based-row-index>`.
- Do not place new financial calculations in the JSON.

After writing the artifact, rerun `python run_all.py` and continue automatically when `Workflow coordination` again says `next_actor = AI_HOST` and `must_continue = true`.
