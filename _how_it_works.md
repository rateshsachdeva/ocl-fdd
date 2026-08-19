# How This OCL Skill Works

## What you do

Put raw client Excel files in:

```text
references/source/
```

Then run:

```bash
python run_all.py
```

## What happens internally

```text
RAW CLIENT EXCEL
        ↓
FULL fdd-data-preparation
        │
        ├─ Python: discover files and bind SHA-256
        ├─ Python: profile workbooks / worksheets / regions / fields
        ├─ AI host: understand logical datasets and field meaning
        ├─ AI host: create Dataset Map + Processing Plan
        ├─ Python: validate plan against source evidence
        ├─ Python: execute union / unpivot / reshape / derive operations
        ├─ Python: prove completeness
        └─ Python: publish metadata + row/field lineage
        ↓
STANDARDIZED LONG / FLAT DATASETS
work/data_prep/output/latest/
        ↓
OCL semantic interpretation
        ↓
reviewable OCL judgments
        ↓
shared reconciled OCL model
        ↓
hard controls
        ↓
dynamic workbook blueprint
        ↓
formula-driven Excel rendering
        ↓
analysis + management questions
        ↓
professional workbook styling
        ↓
independent final QA
        ↓
output/OCL_Databook.xlsx
```

The secondary `output/OCL_Report.pptx` is produced from the same reconciled model.

## Why this solves changing client formats

`ocl_agent` never needs to know whether a client provided:

- one worksheet per year;
- years across columns;
- months down rows;
- multiple entity blocks;
- several related source files;
- preambles, merged titles or unusual field names.

Those are upstream data-understanding / Processing Plan matters. Different source structures may result in different Dataset Maps and Processing Plans, but the downstream OCL skill continues to receive standardized datasets with lineage.

Do not solve a new client format by adding another header alias to OCL code.

## Where AI sits

AI is part of the full data-preparation design.

```text
Python structural evidence
       ↓
AI contextual understanding / planning
       ↓
Python deterministic execution / proof
```

The AI host is provider-neutral. The active host may be Codex, Claude Code, GitHub Copilot or another capable coding agent. The deterministic financial Python does not call an external model API.

When Python reaches an AI reasoning checkpoint, it returns a coordination object containing the next actor/action, relevant instruction, handoff/evidence path and required artifacts. Coding agents follow `AGENTS.md` and continue these checkpoints automatically before rerunning the workflow.

A plain terminal cannot itself perform contextual AI reasoning, so `python run_all.py` may visibly stop at an `AI_HOST` checkpoint if no coding agent is driving it. That is an intentional safety boundary, not a parsing failure.

## OCL judgment boundary

After standardized data is published, OCL owns:

- OCL / trade-payable / financing / outside-scope disposition;
- source-present categories and hierarchy;
- WC / debt-like / neither treatment;
- normal / one-off judgment;
- reconciliations;
- analysis and management questions.

Existing reviewed human config is the highest authority.

## Dynamic workbook rule

```text
STANDARDIZED DATA + REVIEWED OCL JUDGMENT
        ↓
DYNAMIC WORKBOOK STRUCTURE
        ↓
DETERMINISTIC FORMULAS
        ↓
FDD PRESENTATION LAYER
```

There is no fixed `Template.xlsx`, fixed period range or legacy category universe.

## Controls

The workflow never hides a mismatch with a balancing plug. Applicable controls must pass. Unsupported controls are `NOT_APPLICABLE`; unresolved evidence remains visible and can require review.
