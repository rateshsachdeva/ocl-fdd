# AI-host boundary and workflow

This folder contains vendor-neutral instructions for the AI host. Do not add OpenAI, Anthropic, Azure OpenAI, Copilot or Claude API calls to the deterministic core.

## Responsibility split

**Python owns:** reading standardized rows, amounts, transformations, formulas, controls, reconciliation, workbook/PPT writing.

**The AI host owns:** contextual interpretation of current evidence, proposed semantic bindings, proposed OCL judgments, and optional refinement of finding/question wording.

**Human-reviewed config owns final accounting/FDD meaning.** Existing `REVIEWED` decisions are authoritative.

## Evidence hierarchy

Use, in order:

1. current standardized data and `Source_Record_ID` lineage;
2. current `databook_metadata.json`, execution manifest and upstream dataset understanding;
3. current field context and bounded samples;
4. current human-reviewed OCL config;
5. prior knowledge only as supporting evidence.

Never infer meaning from a heading alone. Never create a category because a prior engagement used it.

## When Part 1 says `AWAITING_SEMANTIC_HANDOFF`

1. Read `output/semantic_handoff_draft.json` and `output/OCL_Input_Review.xlsx`.
2. Read current upstream metadata and inspect only targeted standardized rows needed to interpret ambiguous fields/datasets.
3. Assign each standardized dataset one or more justified usages: `OCL_RECORDS`, `MONTHLY_RECORDS`, `MOVEMENT_RECORDS`, `TB_CONTROL`, `REVENUE_CONTEXT`, `PAYROLL_CONTEXT`, or `IGNORE`.
4. Confirm exact field roles. For OCL/monthly: `source_record_id`, `period`, `amount`, `source_label`; add source code/entity/currency where present. Movement records also require `movement_type`.
5. Add `monthly_to_annual` only from supported year-end relationships.
6. If movement data exists, define exact `movement_rules` from the current source semantics. Each source movement label must have an explicit `OPENING`, `FLOW` or `CLOSING` role and multiplier. Never infer sign from the word alone. Add explicit `movement_to_annual` alignments.
7. If period completeness should be tested, add explicit `expected_annual_periods` / `expected_monthly_periods`. Do not manufacture a sequence from labels whose fiscal/calendar semantics are unclear.
8. Bind TB/scope controls using exact dataset, period field, amount field and exact filter values. Never fuzzy-match a control row.
9. For revenue/payroll context, bind period and amount only when those fields are genuinely understood.
10. Save as `config/semantic_handoff.json` with `status: CONFIRMED`, then rerun.

## When Part 1 says `AWAITING_JUDGMENT_REVIEW`

1. Read `output/OCL_Review_Context.json`; use `OCL_Stage2_Review.xlsx` where useful.
2. Preserve every existing reviewed config row.
3. Determine scope before category treatment.
4. Add only categories/hierarchy that actually occur in current data.
5. Use source label + source code + entity when the same label has different meanings at different grains.
6. Canonical WC/debt values are `working_capital`, `debt_like`, `neither`; normality values are `normal`, `one_off`.
7. AI-created decisions remain `PROPOSED` until explicitly reviewed. Do not silently promote proposals to `REVIEWED`.
8. Trade payables, financing and outside-OCL rows remain explicit scope outcomes rather than being dropped.

## When Part 1 says `AWAITING_CONTROL_ALIGNMENT`

Read the failing/review-required controls in the review workbook/context. Resolve only by supplying better source-backed evidence, exact alignment or correcting an actual classification/data issue. Never insert a balancing value or widen the tolerance to make a check pass.

## Parts 2–4

Once `DATABOOK_READY`, deterministic Python already calculates evidence, drafts focused questions and renders outputs. The AI host may improve prose if asked, but must preserve the numeric evidence and the management-question discipline in `SKILL.md`.
