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

For an already-open Codex or Claude Code session, use:

```bash
python run_all.py --ai-host external
```

## What happens internally

```text
RAW CLIENT EXCEL
        ↓
Python: discover, fingerprint and structurally profile source
Python: prepare bounded evidence + relevant knowledge
        ↓
AI #1: UNDERSTAND_AND_PLAN
        │
        └─ Dataset Map + Processing Plan + any genuine blocking questions
        ↓
Python: validate plan
Python: execute union / unpivot / reshape / derive operations
Python: prove completeness + preserve lineage
        ↓
STANDARDIZED LONG / FLAT DATASETS
        ↓
Python: carry canonical dataset semantics forward
Python: apply/review OCL judgments
Python: build shared reconciled OCL model + hard controls
Python: render formula-driven databook foundation + analytical tables
        ↓
AI #2: WRITE_FDD_PARTNER_ANALYSIS
        │
        └─ Deal Issues + Key Findings + Management Q&A from Python evidence
        ↓
Python: render narratives + one final workbook presentation pass + independent final QA
        ↓
output/OCL_Databook_vN.xlsx
```

For a normal canonical package, those are the only two AI reasoning passes. A semantic-review or control-investigation AI step is an exception path only when the evidence genuinely cannot be resolved by the canonical contract and deterministic controls.

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

AI performs contextual reasoning, not deterministic processing or financial calculation.

```text
Python prepared evidence
       ↓
AI contextual understanding / planning
       ↓
Python deterministic execution / proof / calculations
       ↓
AI FDD-partner interpretation of Python tables
       ↓
Python final rendering / QA
```

No external model API is embedded in the financial Python core.

Normal PowerShell/terminal use invokes GitHub Copilot CLI only at explicit `AI_HOST` checkpoints. The child Copilot process is restricted to reading referenced evidence and writing the requested artifacts; it does not execute Python or shell commands itself. When Codex or Claude Code is already the active orchestrator, `--ai-host external` lets that active agent satisfy the same reasoning checkpoints.

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
