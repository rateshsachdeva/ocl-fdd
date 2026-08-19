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
