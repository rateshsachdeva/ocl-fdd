# Dataset Understanding

Use deterministic `profile.json`, bounded targeted inspection when needed, and current source evidence to create `dataset_map.json`. This is an understanding artifact only; do not perform the transformation here.

Consider workbook/sheet context, regions, preambles, headings, representative values, primitive characteristics, cardinality, formatting and related sheets/files together. Never infer field meaning from heading alone. Preserve uncertainty rather than guessing.

Identify logical datasets and classify physical material as `PRIMARY_DATA`, `SUPPORTING_DATA`, `CONTEXT`, `PRESENTATION_IGNORE`, or `UNKNOWN`. A logical dataset may span multiple source regions/files. Propose grain only when supported.

For every conceptual field record a canonical name, stable `source_field_ids`, source references, proposed role, interpretation and confidence. Context-derived fields such as period/entity inferred from worksheet/file/preamble must remain distinguishable from directly present fields.

Capture useful dataset metadata with evidence: purpose, currency/basis, unit scale, reporting frequency, period coverage, entity/geography, scenario, main measures, key dimensions and grain. Use `UNKNOWN`/`UNRESOLVED` rather than inventing values.

When profile evidence is insufficient, inspect only the bounded source area needed to resolve the ambiguity. Create a Dataset Map conforming to `schemas/dataset_map.schema.json` and ensure all source/field references validate against the current profile.
