# OCL Financial Due Diligence Skill

## Objective

Build a traceable, dynamically structured Other Current Liabilities financial
due-diligence databook and, in later parts, analysis, management questions and
a report from one shared reconciled OCL data model.

## Repository workflow

- `run_all.py` is the public orchestrator.
- `src/ocl_agent/part1_databook/` owns the OCL data model, reviewed judgments,
  dynamic workbook blueprint, deterministic rendering and reconciliation.
- `src/ocl_agent/part2_analysis/` owns analytical findings only.
- `src/ocl_agent/part3_qanda/` owns management questions only.
- `src/ocl_agent/part4_report/` owns PowerPoint reporting only.
- `config/` is the human-owned meaning layer.

## Databook rules

### Source fidelity

- Never invent financial amounts, balancing figures or plug numbers.
- Preserve upstream lineage to source records/cells wherever available.
- Do not silently drop unknown, unmapped or excluded rows.
- Do not alter raw client source workbooks.

### Human judgment

- Reviewed human decisions override AI suggestions.
- Scope, mapping/hierarchy, WC/debt-like treatment and normal/one-off treatment
  must be reviewable and persisted outside hidden code.
- Default config files may be created when absent but existing user edits must
  not be overwritten by regeneration.

### Dynamic workbook

Do not use `Template.xlsx` or another fixed Excel workbook as the structural
basis of the databook.  Do not hard-code legacy line items, fixed periods or
empty analytical sections.

Workbook structure must be derived from:

- the actual standardized data;
- reviewed OCL judgments;
- actual available periods;
- actual OCL category/hierarchy;
- analyses genuinely supported by the engagement data.

A separate styling guide may govern fonts, fills, number formats, hierarchy,
spacing, freeze panes, chart styling and similar presentation rules.  Styling
must never create financial content that the data does not support.

### Reconciliation

Reconciliation is a hard control.  Applicable checks must tie within defined
tolerance.  Controls whose prerequisite dataset does not exist must be reported
as `NOT_APPLICABLE`, not fabricated.

The control framework includes, where applicable:

- mapped category sums to total in-scope OCL;
- OCL listing to TB/control total;
- roll-forward closing to listing closing;
- WC/debt classification completeness;
- period continuity;
- scope reconciliation to the relevant control total;
- monthly closing to annual closing.

## Upstream boundary

The normal input is an approved publication from `fdd-data-preparation`,
including standardized CSV dataset(s) and available metadata/lineage artifacts.
Part 1 should not duplicate raw-source discovery and generic reshaping that the
upstream skill already performed.

## Current milestone

The foundation milestone implements:

- repository structure;
- shared schemas;
- standardized-package discovery/validation;
- non-destructive judgment loading;
- dynamic workbook blueprint generation;
- deterministic workbook rendering primitives;
- reconciliation primitives;
- tests and CI.

It intentionally does **not** yet hard-code an engagement-specific semantic
adapter from arbitrary standardized columns to OCL records.  That contract must
be designed from the upstream metadata/data evidence rather than guessed.
