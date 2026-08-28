# Reusable Knowledge System

This folder is the single repository-level home for reusable-learning lifecycle code and built-in source-understanding knowledge used by the embedded data-preparation layer.

## What lives here

- `store.py` — persistence, rehydration, safe promotion, quarantine and audit metadata.
- `BUILTIN_FDD_SOURCE_KNOWLEDGE.md` — source-controlled FDD pattern library used to accelerate `UNDERSTAND_AND_PLAN` on difficult source packs.

The built-in knowledge pack contains generic structural and evidence lessons from deliberately difficult synthetic FDD benchmark designs. It does **not** contain their golden answers, expected amounts or client-specific conclusions.

## Responsibilities

`store.py` owns:

- locating the persistent learning store;
- capturing the runtime baseline knowledge snapshot;
- rehydrating previously promoted knowledge into later source-package runs;
- deciding which newly learned rows are safe to retain across engagements;
- quarantining obviously source-specific candidates;
- writing promotion audit metadata.

The OCL bridge automatically references `BUILTIN_FDD_SOURCE_KNOWLEDGE.md` on the `UNDERSTAND_AND_PLAN` checkpoint and sets `fast_start_mode=true`. The AI host is instructed to read deterministic profile/samples plus the built-in pattern library first, then use targeted inspection only for material unresolved ambiguities.

## Knowledge layers

```text
Built-in source-controlled knowledge
    fdd-data-preparation/knowledge_system/BUILTIN_FDD_SOURCE_KNOWLEDGE.md
                  ↓
Reusable promoted local learning
    work/data_prep/knowledge/
                  ↓
Runtime working knowledge
    fdd-data-preparation/runtime/fdd-data-preparation/knowledge/
                  ↓
Current deterministic source evidence
    always authoritative
```

Built-in and reusable knowledge are hypotheses/evidence, never rules that override the current source.

## Persistent learned data

The reusable runtime knowledge assets remain under:

```text
work/data_prep/knowledge/
```

The persistent store remains gitignored.

## Promotion rule

A completed source-package run may create or update knowledge inside the runtime. After the standardized financial package has been successfully published, the knowledge system compares those rows with the trusted baseline / previously promoted rows.

New rows are promoted only if they pass the deterministic cross-source safety screen. Rows containing obvious current-source identifiers such as source filenames, email addresses, URLs, local/network paths, UUID-like values or long numeric identifiers are quarantined instead.

Quarantined rows remain under:

```text
work/data_prep/knowledge/quarantine/
```

Passing the filter means a row is eligible to be reused as evidence; it does **not** turn that knowledge into a rule. Current source evidence and deterministic validation always remain authoritative.

## Separation from OCL judgments

Do not store client-specific OCL conclusions here.

Scope, category/hierarchy, working-capital/debt-like and normality decisions belong to:

```text
work/ocl_config/<package_id>/
```

Reusable knowledge should describe source structures, field meanings and generic corrections that may help understand a future dataset.
