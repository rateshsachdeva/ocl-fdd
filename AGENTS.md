# OCL FDD — Agent Operating Instructions

## Product goal

The user experience is one repository and one launcher:

```text
references/source/ -> python run_all.py -> output/OCL_Databook_vN.xlsx + output/OCL_Report_vN.pptx
```

The implementation is deliberately split internally:

1. **Full fdd-data-preparation** owns raw Excel discovery, structural profiling, contextual dataset understanding, processing planning, deterministic reshaping, completeness, lineage and publication.
2. **ocl_agent** starts only from the published standardized package and owns OCL scope, taxonomy/hierarchy, WC/debt-like and normality judgments, controls, analysis, management questions, workbook rendering and reporting.

Never add client-specific raw-Excel parsing to `ocl_agent`.

## AI host continuation rule

`python run_all.py` supports two ways to satisfy `AI_HOST` checkpoints.

### Normal PowerShell / terminal use

The default is:

```text
python run_all.py
```

Normal terminal use delegates explicit `AI_HOST` checkpoints to the installed/authenticated GitHub Copilot CLI. Python continues to own routine processing, calculations, reconciliations, controls and rendering.

When the workflow returns:

```json
{"next_actor": "AI_HOST", "must_continue": true}
```

the root Python process delegates that one checkpoint to GitHub Copilot CLI, then resumes the deterministic workflow automatically. The child AI host must not run `python run_all.py` itself.

If Copilot CLI is unavailable or unauthenticated, the workflow must stop safely at the checkpoint rather than inventing or bypassing the required artifact.

### Already-open coding-agent session

If Codex, Claude Code or another capable coding agent is already orchestrating the repository interactively, use:

```text
python run_all.py --ai-host external
```

This avoids spawning a nested Copilot process. In `external` mode, when `next_actor=AI_HOST` and `must_continue=true`, the current agent session must:

1. read `relevant_instruction`;
2. read `handoff_path`, `run_directory`, review context and any other referenced evidence;
3. create or update exactly the artifacts listed in `required_artifacts` or required by the referenced instruction;
4. do not invent source values or use AI arithmetic as a substitute for deterministic Python;
5. rerun `python run_all.py --ai-host external`;
6. repeat until the workflow reaches `READY`, a genuine `HUMAN` checkpoint, or `FAILED`.

Therefore, when the user says **“run the skill”** from an already-open Codex or Claude Code session, treat that as an instruction to run the repository end to end in `external` mode and autonomously satisfy each `AI_HOST` checkpoint until a genuine human judgment is required or the deliverables are ready.

The common AI checkpoints include:

- `DATASET_UNDERSTANDING`
- `UNDERSTAND_AND_PLAN`
- `PROCESSING_PLAN`
- `CONFIRM_OCL_SEMANTIC_HANDOFF`
- `INVESTIGATE_OCL_CONTROL_ALIGNMENT` only when a control genuinely requires investigation
- `WRITE_FDD_PARTNER_ANALYSIS`
- knowledge-review preparation after publication when requested by the upstream workflow

For `WRITE_FDD_PARTNER_ANALYSIS`, follow `src/ocl_agent/llm/FDD_PARTNER_ANALYSIS.md`. Write Deal Issues, Key Findings and Management Q&A from the supplied Python evidence as an experienced FDD partner. Do not revert to deterministic boilerplate wording and do not leave the sections blank simply because no deterministic headline trigger fired; where there is no material issue, write the explicit evidence-based conclusion requested by the instruction.

Use the full data-preparation runtime's own instructions and schemas. Do not replace them with a header-alias parser.

## Analysis boundary

The analysis layer follows this flow:

```text
formula-linked foundation
        -> Python metrics / materiality / reconciliations
        -> AI_HOST FDD-partner interpretation
        -> Deal Issues + Key Findings + Q&A
        -> deterministic workbook/PPT rendering
```

Python owns all analytical numbers and calculates them once from the reconciled OCL model. The AI host owns qualitative FDD interpretation and question wording, but it must never recalculate, override or invent an amount, percentage, classification or materiality result.

The AI-host mindset is an experienced FDD partner: focus on deal implications, normalized working capital, net debt/equity value, QoE, representativeness of closing balances, validity/completeness, settlement/release risk and the specific facts still needed from management. Avoid robotic variance commentary and filler questions.

Materiality has two deterministic review levels:

- **Databook review:** absolute movement >= 100,000 **OR** percentage movement >= 10%.
- **Headline trigger:** absolute movement >= 100,000 **AND** percentage movement >= 30%.

These thresholds guide evidence prioritization. They do not authorize the AI host to invent issues; nor should an evidence-supported transaction-relevant observation be hidden merely because it is not a deterministic headline trigger. Such observations must be clearly presented as notable rather than as an unsupported conclusion.

Where the underlying data supports them, the workbook should expose:

- Balance by Category / annual movement review;
- Roll-forward;
- Checks;
- Seasonality / year-end representativeness;
- Item Monthly Charts with monthly balances and LTM 12-month average;
- Deal Issues;
- structured Key Findings;
- Q&A grouped by commercial theme.

Management questions must be focused factual questions. Do not ask management to decide whether an item should be debt-like, working capital or a QoE adjustment. Ask for the underlying facts that allow the deal team to reach that conclusion.

Analytical financial figures in Excel should link back to the formula-driven foundation wherever practicable.

## Source-package freshness

The upstream data-preparation workflow fingerprints the exact files currently in `references/source/`. A changed, added or removed source file must create/resume the workflow for that new fingerprint. Never reuse an older standardized package merely because an older published output exists. The OCL bridge accepts published output only when its execution ID belongs to the current source-bound workflow.

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
