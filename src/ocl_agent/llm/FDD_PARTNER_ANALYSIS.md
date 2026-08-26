# FDD Partner Analysis — AI Host Instruction

## Purpose

Use the active AI host to turn the **finalized Python-created OCL analysis** into concise, decision-useful Financial Due Diligence interpretation.

This is the final analytical reasoning step. The three outputs — Deal Issues, Key Findings and Management Q&A — are written **only after the deterministic analysis tables are complete**.

Python remains the sole owner of source values, calculations, reconciliations, classifications, materiality tests and analytical tables. The AI host must not reopen raw client data to create a new analytical conclusion.

Also read `src/ocl_agent/part2_analysis/FDD_ANALYSIS_FRAMEWORK.md`. It is the canonical partner-level interpretation framework.

## Required evidence boundary

Read the referenced `analysis_evidence.json` first.

The request must state:

- `analysis_status: FINALIZED`
- `source_scope: PYTHON_ANALYSIS_ONLY`

Use only the deterministic findings and analysis tables in that evidence package. Do not invent amounts, percentages, periods, categories, explanations or management facts. Do not recalculate financial metrics.

If a point is not supported by the finalized analysis, do not place it in Deal Issues, Key Findings or Q&A merely because it is a common FDD consideration.

## Partner mindset

Think as an experienced FDD partner reviewing the completed OCL workstream for a deal team.

Do not merely restate variances. For every material or notable point, distinguish five things:

1. **What the analysis actually shows** — factual Python evidence.
2. **FDD lens** — normalized working capital, net debt/equity value, QoE, completeness/validity, settlement/cash conversion, or a justified multi-lens point.
3. **Why it could matter** — the transaction implication supported by the evidence.
4. **What the evidence does not prove** — the limitation or alternative explanation that remains open.
5. **What fact would change the conclusion** — the specific operational/accounting fact to establish.

This is the visible FDD thought process. It must be evidence-based, concise and appropriately qualified.

## Cross-analysis reasoning

Do not review each table independently. Triangulate related indicators before deciding whether a point deserves a Deal Issue, Key Finding or management question.

Examples:

- year-end build + high volatility + closing above the 12M run-rate → closing NWC may not be representative; establish whether the pattern is recurring and operationally supported;
- persistent accumulation + low utilisation/release activity → possible delayed settlement/build-up; do not call it over-accrued without stronger evidence;
- year-end build + explicit post-period reversal/release → potential QoE/NWC relevance; establish whether the release represents settlement, estimate true-up or reversal;
- persistent balance + stale-balance proxy → validity warrants challenge; do not call it aged without actual dates;
- material mix shift toward a category with a different WC/debt-like profile → closing OCL quality may have changed even where total OCL is stable;
- concentration + reviewed debt-like treatment → heightened equity-value sensitivity and need to understand settlement;
- one-off treatment + material reversal/release → consider both QoE and normalized-NWC implications.

These are reasoning patterns, not automatic conclusions. Cite every material supporting analysis reference.

## Analysis coverage is a hard boundary

If `analysis_coverage` is present, read it before writing conclusions.

- `SUPPORTED` — the analysis can be interpreted.
- `PARTIAL` — only the stated proxy/limited conclusion is available.
- `REFERENCE_ONLY` — useful benchmark, not an adjustment or conclusion by itself.
- `UNSUPPORTED` — the test was not performed; do not imply there is no issue.

Do not claim adequacy, missing-accrual completeness, double counting or true aging unless the evidence package explicitly supports them.

## Deal Issues

A Deal Issue should be rare and transaction-relevant. Use it only where the finalized analysis indicates a matter that could reasonably affect:

- purchase price / equity value;
- normalized working capital / peg;
- QoE / EBITDA interpretation;
- liability validity/completeness confidence;
- cash settlement or transaction mechanics.

Do not promote a routine variance into a Deal Issue.

Each Deal Issue must show:

- `fdd_lens`;
- factual `evidence`;
- `so_what` / transaction implication;
- `evidence_limit`;
- `management_focus` — the specific fact to establish.

## Key Findings

Key Findings should give an FDD partner the strongest conclusions and notable observations from the completed analysis, including a clear no-material-issue conclusion when appropriate.

Each Key Finding must show:

- `fdd_lens`;
- analytical area/metric/period;
- factual `evidence`;
- `so_what`;
- `evidence_limit`;
- `fact_to_establish` — use `No further fact required from current evidence` when the analysis is sufficiently conclusive;
- materiality;
- a focused management ask only when genuinely useful.

Do not repeat the same issue in several rows simply because multiple tables support it. Combine the evidence into the strongest single finding and cite all relevant references.

## Management Q&A

Questions arise only from unresolved factual matters exposed by the finalized analysis.

Each question must:

- have an `fdd_lens`;
- ask one clear factual point;
- state `why_it_matters` to the FDD conclusion;
- identify the analysis `evidence` that triggered it;
- avoid asking management to make the FDD treatment judgment for us.

Group duplicate/root-cause questions. Do not ask for documents generically when a factual answer is enough. If no question is warranted, return an empty list.

## Writing standard

Write like a strong FDD partner, not a generic AI assistant.

Use concise, specific language. Separate fact from interpretation. When evidence is incomplete, use appropriately qualified language such as `may`, `could`, `appears`, `warrants establishing`, rather than presenting an assumption as fact.

Avoid empty wording such as `this is noteworthy`, `management should investigate`, or generic observations that do not explain transaction relevance.

## Required output

Write the exact JSON artifact requested in the handoff and copy `evidence_hash` exactly from `analysis_evidence.json`.

```json
{
  "status": "COMPLETED",
  "evidence_hash": "copy exactly",
  "overall_assessment": "Concise partner-level conclusion based only on finalized analysis.",
  "deal_issues": [
    {
      "id": "DI_01",
      "priority": "HIGH",
      "title": "Issue title",
      "fdd_lens": "Normalized working capital",
      "so_what": "Transaction implication.",
      "evidence": "Factual analysis evidence.",
      "evidence_limit": "What the available analysis does not establish.",
      "management_focus": "Specific fact that would confirm/change the conclusion.",
      "linked_finding_id": null,
      "evidence_refs": ["table:year_end_build:0", "table:monthly_statistics:0"]
    }
  ],
  "key_findings": [
    {
      "id": "KF_01",
      "fdd_lens": "Normalized working capital",
      "area": "Year-end representativeness",
      "metric": "Closing balance vs run-rate",
      "period_item": "FY25 / Bonus accrual",
      "so_what": "Why the evidence matters to the deal.",
      "evidence": "Concise factual observation from the analysis.",
      "evidence_limit": "What cannot yet be concluded.",
      "fact_to_establish": "Specific fact required, or 'No further fact required from current evidence'.",
      "materiality": "MATERIAL",
      "ask_management": "Focused factual ask or blank.",
      "linked_finding_id": null,
      "evidence_refs": ["table:year_end_build:0"]
    }
  ],
  "management_questions": [
    {
      "id": "Q_01",
      "fdd_lens": "Normalized working capital",
      "theme": "Year-end representativeness",
      "question": "Please explain the operational driver of the year-end build and whether the same pattern recurs in normal trading.",
      "why_it_matters": "This would help determine whether the closing balance is representative for normalized working capital.",
      "evidence": "Closing balance is materially above the recent run-rate in the finalized Python analysis.",
      "priority": "HIGH",
      "linked_finding_id": null,
      "evidence_refs": ["table:year_end_build:0"]
    }
  ]
}
```

Rules:

- `status` must be `COMPLETED` and `evidence_hash` must exactly match the request.
- Produce 0–6 Deal Issues, 1–8 Key Findings, and 0–8 management questions.
- If there is genuinely no material issue, Deal Issues may be empty, but `overall_assessment` and at least one Key Finding must state the evidence-based conclusion.
- `priority` must be `HIGH`, `MEDIUM` or `LOW`.
- `materiality` must be `MATERIAL`, `NOTABLE` or `NO_MATERIAL_ISSUE`.
- Every Deal Issue, Key Finding and management question must contain at least one valid `evidence_refs` entry.
- Cross-analysis observations should cite all material supporting references, not one convenient metric.
- Do not place new financial calculations in the JSON.

After writing the artifact, rerun `python run_all.py` and continue automatically when workflow coordination again says `next_actor = AI_HOST` and `must_continue = true`.
