# Reusable Knowledge System

This folder is the single repository-level home for reusable-learning lifecycle code used by the embedded data-preparation layer.

## Responsibilities

`store.py` owns:

- locating the persistent learning store;
- capturing the runtime baseline knowledge snapshot;
- rehydrating previously promoted knowledge into later source-package runs;
- deciding which newly learned rows are safe to retain across engagements;
- quarantining obviously source-specific candidates;
- writing promotion audit metadata.

The embedded vendored runtime still owns **when and how it reasons from knowledge** while understanding a dataset. This folder owns the boundary between one engagement's runtime learning and cross-source reusable learning.

## Data locations

Code:

```text
fdd-data-preparation/knowledge_system/
```

Persistent learned data:

```text
work/data_prep/knowledge/
```

Runtime working knowledge:

```text
fdd-data-preparation/runtime/fdd-data-preparation/knowledge/
```

The persistent store remains gitignored.

## Promotion rule

A completed source-package run may create or update knowledge inside the runtime. After the standardized financial package has been successfully published, the knowledge system compares those rows with the trusted baseline / previously promoted rows.

New rows are promoted only if they pass the deterministic cross-source safety screen. Rows containing obvious current-source identifiers such as source filenames, email addresses, URLs, local/network paths, UUID-like values or long numeric identifiers are quarantined instead.

Quarantined rows remain under:

```text
work/data_prep/knowledge/quarantine/
```

so they can be inspected without being carried into the next engagement.

This is intentionally conservative. Passing the filter means a row is eligible to be reused as evidence; it does **not** turn that knowledge into a rule. Current source evidence and deterministic validation always remain authoritative.

## Separation from OCL judgments

Do not store client-specific OCL conclusions here.

Scope, category/hierarchy, working-capital/debt-like and normality decisions belong to:

```text
work/ocl_config/<package_id>/
```

Reusable knowledge should describe source structures, field meanings and generic corrections that may help understand a future dataset.
