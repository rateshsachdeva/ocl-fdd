# Reusable Knowledge System

This folder is the single repository-level home for reusable source-understanding knowledge code used by the embedded data-preparation layer.

## Structure

```text
fdd-data-preparation/knowledge_system/
    builtin_patterns.json   source-controlled generic FDD/data patterns
    context.py              matches relevant patterns to the current profile
    store.py                persists/promotes/quarantines learned knowledge
    README.md               this contract
```

The code is source-controlled. Learned engagement data is not stored beside the code.

## Three knowledge layers

### 1. Built-in generic knowledge

`builtin_patterns.json` contains reusable lessons distilled from difficult synthetic training designs and general FDD/data-preparation practice. Examples include:

- title/preamble rows before real headers;
- multiple logical datasets on one worksheet;
- Actual/Budget/Variance management layouts;
- annual hierarchy/subtotal reconstruction;
- ambiguous headings such as `Cat`, `Map1`, `Description`, `Class`, `Mapping` and `Amount`;
- supporting payroll/P&L/AP/contracts/movement data;
- evidence requirements for aging, adequacy, completeness and duplicate testing;
- negative-control principles such as large/volatile/new balances not automatically being issues.

This pack intentionally contains **generic patterns, not synthetic answer labels, exact client mappings, expected issue amounts or golden-truth conclusions**.

### 2. Locally learned reusable knowledge

`store.py` owns promoted learning at:

```text
work/data_prep/knowledge/
```

The three runtime learning assets are:

```text
field_knowledge.csv
structure_knowledge.csv
corrections.csv
```

These can improve over successful source-package runs and are rehydrated into later runs.

### 3. Current-source evidence

The current deterministic profile/samples are always authoritative. Built-in and previously learned knowledge are supporting evidence only. If prior knowledge conflicts with the current source, the current source wins.

## Fast matched context

`context.py` prevents AI #1 from receiving a huge generic training prompt on every run.

It reads the deterministic profile for the current source package, matches the most relevant generic patterns and writes a compact packet under:

```text
work/data_prep/knowledge/context/<source_fingerprint>.md
```

The planning flow becomes:

```text
built-in generic knowledge
        +
previous safe learned knowledge
        +
current deterministic profile
        ↓
Python matches relevant context
        ↓
compact reusable_knowledge_context
        ↓
AI #1 UNDERSTAND_AND_PLAN
```

AI should use familiar matched patterns to avoid rediscovering the same structural lessons from scratch, then spend reasoning effort on genuine ambiguity. It must never open synthetic golden-truth/test-answer files as production evidence.

## One-source learning

A user can teach one source workbook at a time with:

```bash
python run_all.py --learn-source Finance_Pack.xlsx
```

The selected immutable source is copied to a gitignored learning package. Data preparation profiles/understands/publishes that source and safe reusable learning is promoted. The command then stops before OCL Excel/PPT construction.

This is useful for large or structurally difficult source packs. Examples:

```bash
python run_all.py --learn-source Finance_Pack.xlsx
python run_all.py --learn-source Balance_Sheet_Detail.xlsx
python run_all.py --learn-source Payroll_and_Accruals.xlsx
python run_all.py --learn-source Supporting_Schedules.xlsx
```

After desired source learning is complete, run the normal combined engagement:

```bash
python run_all.py
```

The final run still uses all relevant source files together because cross-file reconciliation, P&L linkage, settlements, completeness and other FDD analyses depend on combined evidence.

## Promotion rule

A completed source-package run may create or update knowledge inside the embedded runtime. Only after the standardized financial package has successfully published does `store.py` compare those rows with the trusted baseline / previously promoted rows.

New rows are promoted only if they pass the deterministic cross-source safety screen. Rows containing obvious current-source identifiers such as source filenames, email addresses, URLs, local/network paths, UUID-like values or long numeric identifiers are quarantined instead.

Quarantined rows remain under:

```text
work/data_prep/knowledge/quarantine/
```

so they can be inspected without being carried into the next engagement.

Passing the filter means a row is eligible to be reused as evidence; it does **not** turn that knowledge into a rule.

## Separation from OCL judgments

Do not store client-specific OCL conclusions here.

Scope, category/hierarchy, working-capital/debt-like and normality decisions belong to:

```text
work/ocl_config/<package_id>/
```

Reusable knowledge should describe source structures, field meanings and generic corrections that may help understand a future dataset.
