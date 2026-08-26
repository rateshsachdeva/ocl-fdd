# OCL Configuration

This folder contains **portable default OCL judgment templates**. It is not the reusable data-preparation learning store and it is not the package-specific working folder.

## What lives here

The active runtime consumes these files:

- `judgment_scope.csv` — reviewed default scope decisions.
- `mapping.csv` — reviewed default category / parent-category mappings.
- `judgment_wc_debt.csv` — reviewed default working-capital / debt-like / normality decisions.

The repository ships these as empty templates. Do not put confidential engagement-specific decisions here merely to make one client run work.

## How these defaults are used

For each standardized source package, the workflow creates:

```text
work/ocl_config/<package_id>/
```

On the first run for that package, files from root `config/` are copied into the package-specific working folder.

After that, the package-specific copy is preserved. A later edit to root `config/` does **not** overwrite reviewed decisions already made for an existing package. This protects engagement-specific review work from being silently changed by a global/default edit.

`semantic_handoff.json` is deliberately package-specific and is never seeded from root `config/`.

## This is separate from reusable learning

Reusable source-understanding knowledge is owned by the embedded `fdd-data-preparation` layer and is persisted locally at:

```text
work/data_prep/knowledge/
```

That store contains the runtime knowledge assets:

- `field_knowledge.csv`
- `structure_knowledge.csv`
- `corrections.csv`

Those files are loaded into later data-preparation runs so previous source-structure / field-understanding experience can be reused as evidence. They are not OCL scope, mapping, WC/debt-like or normality decisions.

## Context datasets

Revenue, payroll and expense context is no longer supplied through files in root `config/`. If those datasets are present in the user's source package, data preparation standardizes them and the semantic handoff explicitly binds them as `REVENUE_CONTEXT`, `PAYROLL_CONTEXT` or `EXPENSE_CONTEXT` for supported analysis.

## Confidentiality and portability

`work/` is intentionally gitignored. Therefore package-specific decisions and locally accumulated reusable knowledge remain on that workspace and do not automatically travel with a Git clone.

If reusable learning is later to be shared across users, it should be exported/promoted through a deliberate sanitized knowledge-pack process rather than by committing engagement-specific `work/` contents.
