# OCL AI-host interpretation workflow

This folder defines the **vendor-neutral reasoning contract** for the OCL-specific layer.

The full `fdd-data-preparation` workflow has already handled raw Excel structure before this layer starts. Therefore the OCL AI host works from the **published standardized package**, its metadata/lineage, and OCL review artifacts. It must not reparse raw client workbooks or create another source-normalization layer.

## Ownership boundary

### Full fdd-data-preparation already owns

- source discovery and workbook/region profiling;
- contextual dataset understanding;
- Dataset Map and Processing Plan;
- deterministic reshape/union/unpivot execution;
- completeness proof;
- row/field lineage and metadata publication.

### OCL AI host owns contextual OCL interpretation

The AI host may interpret:

- which published logical dataset(s) contain OCL/current-liability records;
- which dataset(s) are monthly, movements, TB/control, revenue, payroll or explicit expense context;
- semantic field roles within those published datasets;
- OCL scope meaning;
- source-present category/hierarchy proposals;
- management and FDD WC/debt-like view proposals;
- normal/one-off proposals;
- FDD-partner-level Deal Issues, Key Findings and Management Q&A from validated Python evidence.

### Deterministic Python owns

- financial amounts and arithmetic;
- source-linked workbook formulas;
- record construction from explicit field bindings;
- controls and reconciliation;
- roll-forward math;
- monthly/annual tie checks;
- materiality metrics;
- seasonality, volatility and year-end run-rate calculations;
- recurrence/persistence and normalization reference calculations;
- movement-based utilisation/release/reversal analysis where explicit movements exist;
- context ratios where the semantic handoff explicitly binds the relevant context;
- final workbook/PPT rendering and QA.

## Coordination rule

`python run_all.py` returns a `Workflow coordination` object whenever OCL reasoning or review is required.

When:

```json
{"next_actor": "AI_HOST", "must_continue": true}
```

an agent host should continue automatically:

1. read the exact `relevant_instruction` and `handoff_path`;
2. create/update the requested artifact;
3. do not overwrite an existing reviewed human decision;
4. rerun `python run_all.py`;
5. repeat until `READY`, a genuine `HUMAN` checkpoint or `FAILED`.

## Semantic handoff

When the state is `AWAITING_SEMANTIC_HANDOFF`, create the exact runtime-config artifact identified in `required_artifacts`, normally `semantic_handoff.json`, with `status: CONFIRMED`.

Allowed dataset usages are:

- `OCL_RECORDS`
- `MONTHLY_RECORDS`
- `MOVEMENT_RECORDS`
- `TB_CONTROL`
- `REVENUE_CONTEXT`
- `PAYROLL_CONTEXT`
- `EXPENSE_CONTEXT`
- `IGNORE`

For OCL/monthly records bind, using actual published fields:

- `source_record_id`
- `period`
- `amount`
- `source_label`

Optional roles include `source_code`, `entity`, `currency` and relevant dimensions.

Movement records also require `movement_type`. Use exact source movement values and explicit roles/multipliers. Do not infer a sign convention from a word when source evidence contradicts it.

Context datasets require explicit `period` and `amount` bindings. `EXPENSE_CONTEXT` should be used only when the published dataset is genuinely a relevant P&L/expense measure; do not repurpose revenue, payroll or a generic numeric column as an expense denominator.

Bind TB/scope controls only to exact published datasets/fields/filters that the evidence supports. Do not keyword-search for a convenient total and call it a control.

Use upstream Dataset Map / metadata as strong evidence. Never infer field meaning from a heading alone when samples, context, lineage or upstream interpretation are available.

## OCL judgment review

Scope, category/hierarchy, WC/debt-like and normality are reviewable financial-due-diligence judgments.

- Existing reviewed config is authoritative.
- AI may prepare evidence-based proposals when the coordination state allows it.
- Do not mark an unsupported judgment as reviewed simply to force the pipeline forward.
- Trade payable and financing items may remain in the reconciled population while being excluded from OCL.
- Categories are source-present and dynamic; do not impose a legacy category list.
- If a genuine residual within a parent cannot be assigned to a supported child, surface it explicitly rather than using a hidden plug.

A `HUMAN` checkpoint is intentional where reviewed judgment is required.

## Evidence-aware analysis coverage

The workbook contains an `Analysis Coverage` view so the deal team can distinguish what the supplied evidence genuinely supports.

Examples:

- monthly balances can support seasonality, volatility, year-end build/unwind and balance-persistence / normalization-reference analysis;
- explicit movement data can support utilisation/release and reversal-pattern analysis;
- explicit expense context can support accrual-to-expense ratios;
- unchanged monthly balances can support only a stale-balance **proxy**, not true obligation aging;
- adequacy, missing-accrual and double-counting conclusions require richer obligation/completeness evidence and must remain unsupported when that evidence is absent.

Never promote a `PARTIAL`, `REFERENCE_ONLY` or `UNSUPPORTED` analysis into a definitive conclusion merely because the user expects a complete workbook.

## Deal Issues, Key Findings and Q&A

When `next_action` is `WRITE_FDD_PARTNER_ANALYSIS`, follow `FDD_PARTNER_ANALYSIS.md` exactly.

Python first creates `analysis_evidence.json` containing the authoritative metrics, deterministic findings and table rows. The active Codex / Claude Code / Copilot host then writes one hash-bound `analysis_interpretation.json` containing:

- Deal Issues;
- Key Findings;
- Management Q&A.

Think as an experienced FDD partner. Focus on transaction implications rather than restating variances. Use only supplied evidence; do not recalculate financial metrics or invent explanations. Questions should request one focused factual point that helps the deal team resolve the issue. Do not ask management to make deal-treatment judgments.

If the evidence supports no material issue or no management question, say so explicitly in the artifact rather than leaving workbook sections blank or writing filler.

## Prohibited shortcuts

Do not:

- re-open raw Excel to create a second normalization scheme;
- add client-specific heading aliases to OCL production code;
- invent source amounts, categories or balancing figures;
- calculate financial outputs in the AI prompt and hard-code them into Excel;
- claim an unsupported adequacy/completeness/aging test was performed;
- bypass a failed control;
- overwrite reviewed human config.
