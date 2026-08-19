# AI-host boundary and workflow

This folder contains vendor-neutral instructions for the AI host. Do not add OpenAI, Anthropic, Azure OpenAI, Copilot or Claude API calls to the deterministic Part 1 core.

## What the AI host does

The AI host interprets current engagement evidence and proposes dataset usage/field roles, OCL scope, actual category and parent hierarchy, management and FDD WC/debt-like treatment, normal versus one-off treatment, and later findings/questions. It does **not** calculate workbook financial totals.

## Evidence hierarchy

Use, in order: current standardized data and `Source_Record_ID` lineage; current metadata/manifest; current workbook/field context and sample values; existing human-reviewed config; prior memory only as supporting evidence.

Never infer meaning from a column heading alone. Never overwrite a human `REVIEWED` decision merely because the AI would classify it differently.

## Semantic handoff

When `run_all.py` returns `AWAITING_SEMANTIC_HANDOFF`:

1. Read `output/semantic_handoff_draft.json` and `output/OCL_Input_Review.xlsx`.
2. Inspect upstream metadata and only targeted standardized rows as needed.
3. Assign dataset usages and field roles.
4. Add monthly-to-annual alignments only when supported.
5. If a TB control is available, bind its exact dataset, period field, amount field and exact filter values; do not use fuzzy keyword filters.
6. Save as `config/semantic_handoff.json` with `status: CONFIRMED`.
7. Rerun.

## OCL judgment review

When the state is `AWAITING_JUDGMENT_REVIEW`:

1. Read `output/OCL_Review_Context.json` first; use the Excel review where useful.
2. Preserve all existing reviewed config rows.
3. Add only genuinely needed current-source keys, using source label + source code + entity when that grain is necessary.
4. Mark AI-created decisions `PROPOSED` unless the user already explicitly approved the decision.
5. Do not create categories just because they existed in a prior workbook.
6. Do not force every row into OCL: trade payables, financing and out-of-scope items remain explicit scope outcomes.

A final Part 1 databook is not published while required judgments remain proposed/unresolved.
