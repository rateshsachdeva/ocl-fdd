# How This OCL Skill Works

## What you do

Put the raw Excel files in `references/source/` and start the root workflow:

```bash
python run_all.py
```

## What happens internally

```text
RAW CLIENT EXCEL
        ↓
Python profiles structure and preserves source hashes
        ↓
AI understands the logical datasets
        ↓
AI writes the deterministic processing plan
        ↓
Python validates and executes the plan
        ↓
Python proves completeness and lineage
        ↓
STANDARDIZED LONG / FLAT DATABASE
work/data_prep/output/latest/
        ↓
AI understands which standardized data supports OCL
        ↓
AI reviews OCL scope / mapping / hierarchy / WC-debt / normality
        ↓
Python runs hard controls and builds the dynamic databook
        ↓
analysis + management questions
        ↓
professional FDD styling + final QA
        ↓
output/OCL_Databook.xlsx
```

`output/OCL_Report.pptx` is secondary and uses the same reconciled OCL model.

## The important boundary

`fdd-data-preparation/` is responsible for messy client formats. It uses AI understanding plus deterministic Python to normalize those formats into a reliable database.

`ocl_agent` does not parse the original workbook. It starts from the published database and applies OCL/FDD meaning.

So a different client workbook layout should normally change the AI-authored processing plan, **not** require another OCL parser or hard-coded header alias.

## When the workflow pauses

A plain terminal can execute Python but cannot itself perform an AI reasoning checkpoint. In that case `run_all.py` prints `Next actor: AI_HOST`, the handoff file and the required artifact(s).

When the skill is being run by a capable coding/agent AI, that host should read the handoff, perform the reasoning, write the required artifact(s), and rerun the same root workflow automatically. Human input is reserved for genuine material ambiguity or approval, not internal workflow steps.

## Dynamic workbook rule

```text
STANDARDIZED DATA + REVIEWED OCL JUDGMENT
        ↓
DYNAMIC WORKBOOK STRUCTURE
        ↓
DETERMINISTIC FORMULAS AND CONTROLS
        ↓
FDD PRESENTATION LAYER
```

There is no fixed `Template.xlsx`, fixed period range or legacy category list. Applicable controls must pass; unsupported controls are explicit `NOT_APPLICABLE`; failed controls are never hidden with plugs.
