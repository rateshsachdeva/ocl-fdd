# Embedded FDD Data Preparation

## Purpose

Convert raw client Excel files from the parent repository's `references/source/` folder into standardized, lineage-preserving long/flat dataset(s) for downstream OCL FDD.

## Architecture

```text
raw source
  → deterministic discovery/profile/staging
  → AI dataset understanding
  → AI deterministic processing plan
  → Python validation/approval gate
  → deterministic execution
  → completeness + lineage
  → published output/latest
```

The active AI host performs contextual reasoning. Python does not call an LLM API.

## Non-negotiables

- Source workbooks are read-only; capture and re-check SHA-256.
- Understand workbook, worksheet, region, preamble, field samples and related-source context together; do not infer meaning from heading alone.
- Use stable physical `field_id` values as execution keys.
- Allow one logical dataset to span multiple files/sheets/regions when current evidence supports it.
- AI creates `dataset_map.json` and a source-bound `processing_plan.json`; Python validates both before execution.
- Use deterministic reshaping such as direct mapping, union and unpivot according to the approved plan.
- Preserve blank versus zero and source grain unless the plan explicitly and safely says otherwise.
- Never create balancing plugs or silently discard source material.
- Every relevant physical source region/row must be retained or explicitly excluded.
- Every published record must retain valid source lineage via `Source_Record_ID`.
- Publication requires source/output/lineage completeness to pass.

## Boundary with OCL

Data preparation stops after publishing standardized dataset(s), metadata, manifest and lineage. It must not decide OCL scope, taxonomy, hierarchy, WC/debt-like treatment, normality, findings or management questions. Those belong to `ocl_agent`.

The parent `python run_all.py` is the normal launcher; this subfolder is an internal upstream capability.
