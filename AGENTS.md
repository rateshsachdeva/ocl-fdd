# OCL FDD — Agent Operating Instructions

## Product goal

The user experience is one repository and one launcher:

```text
references/source/ -> python run_all.py -> output/OCL_Databook.xlsx
```

The implementation is deliberately split internally:

1. **Full fdd-data-preparation** owns raw Excel discovery, structural profiling, contextual dataset understanding, processing planning, deterministic reshaping, completeness, lineage and publication.
2. **ocl_agent** starts only from the published standardized package and owns OCL scope, taxonomy/hierarchy, WC/debt-like and normality judgments, controls, analysis, management questions, workbook rendering and reporting.

Never add client-specific raw-Excel parsing to `ocl_agent`.

## AI host continuation rule

When you run `python run_all.py`, inspect the returned `Workflow coordination` object.

If:

```json
{"next_actor": "AI_HOST", "must_continue": true}
```

then **do not stop and ask the user to manually perform that internal checkpoint**. Continue in the same agent session:

1. read `relevant_instruction`;
2. read `handoff_path`, `run_directory`, review context and any other referenced evidence;
3. create or update exactly the artifacts listed in `required_artifacts` or required by the referenced instruction;
4. do not invent source values or use AI arithmetic as a substitute for deterministic Python;
5. rerun `python run_all.py`;
6. repeat until the workflow reaches `READY`, a genuine `HUMAN` checkpoint, or `FAILED`.

The full fdd-data-preparation AI checkpoints commonly include:

- `DATASET_UNDERSTANDING`
- `UNDERSTAND_AND_PLAN`
- `PROCESSING_PLAN`
- knowledge-review preparation after publication

Use the full runtime's own instructions and schemas. Do not replace them with a header-alias parser.

## Analysis boundary

The analysis layer follows a strict three-layer flow:

```text
formula-linked foundation -> Python metrics -> evidence-led findings / Excel analysis / Q&A
```

Python owns all analytical numbers and calculates them once from the reconciled OCL model. AI may improve the explanation or wording of the "so what", but it must never recalculate, override or invent an amount, percentage, classification or materiality result.

Materiality has two levels:

- **Databook review:** absolute movement >= 100,000 **OR** percentage movement >= 10%.
- **Findings / Q&A:** absolute movement >= 100,000 **AND** percentage movement >= 30%.

The broader threshold keeps the workbook analytically complete; the stricter threshold keeps findings and management questions focused.

Where the underlying data supports them, the workbook should expose:

- Balance by Category / annual movement review;
- Roll-forward;
- Checks;
- Seasonality / year-end representativeness;
- Item Monthly Charts with monthly balances and LTM 12-month average;
- Deal Issues;
- structured Key Findings;
- Management Questions grouped by commercial theme.

Do not create a tab or finding when the required source evidence does not exist. Analytical financial figures in Excel should link back to the formula-driven foundation wherever practicable.

## Human checkpoints

If `next_actor` is `HUMAN`, stop and surface only the specific approvals/judgments that genuinely require human review. Do not broaden the request.

For OCL, human-owned judgments include scope, mapping/hierarchy, WC/debt-like treatment and normal/one-off treatment. Existing reviewed config wins.

## Financial safety

- Raw source files are immutable.
- No balancing plugs or invented amounts.
- Every relevant input record has visible disposition and lineage.
- Applicable hard controls must pass before final publication.
- Unsupported controls are `NOT_APPLICABLE`; unresolved evidence is not silently guessed.
- The final Excel databook is the principal deliverable.
