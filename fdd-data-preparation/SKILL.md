# Embedded FDD Data Preparation

## Purpose

Convert raw client Excel files from the parent repository's `references/source/` folder into standardized, lineage-preserving long/flat dataset(s) for downstream OCL FDD.

## Architecture

```text
raw source
  → Deterministic Python discovery/profile/staging
  → AI host dataset understanding
  → AI host Dataset Map + Processing Plan
  → Deterministic Python validation/execution
  → completeness + lineage
  → published output/latest
```

The AI host performs contextual reasoning. Python does not call an LLM API.

## Contract

- Treat source workbooks as read-only and bind the workflow to SHA-256 hashes.
- Profile workbook/sheet/region structure before interpretation.
- Understand fields from current source context, samples, primitive characteristics, neighboring fields and related sheets/files; never from a heading alone.
- Use stable physical field IDs as deterministic execution keys.
- Allow one logical dataset to span multiple files/sheets/regions when supported by current evidence.
- AI creates `dataset_map.json` and a source-bound `processing_plan.json`; Python validates them before execution.
- Python executes deterministic reshaping such as direct mapping, union and unpivot exactly as planned.
- Preserve blank versus zero and source grain unless an approved plan explicitly changes them.
- Do not create balancing plugs or silently discard source material.
- Every relevant source region/row must be retained or explicitly excluded.
- Every published record must retain valid `Source_Record_ID` lineage.
- Publication requires source/output/lineage completeness to pass.

## Boundary with OCL

Data preparation stops after standardized dataset(s), metadata, manifest and lineage are published. OCL-specific scope, taxonomy, hierarchy, WC/debt-like treatment, normality, analysis and questions belong to `ocl_agent`.

The repository-root `python run_all.py` is the normal launcher. The upstream state machine may ask the active AI host to create reasoning artifacts; only genuine material ambiguity should reach a human.
