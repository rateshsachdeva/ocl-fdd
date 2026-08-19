# Processing Plan

Convert the validated Dataset Map into `processing_plan.json`: a precise deterministic recipe for the long/flat output. The AI host plans; Python executes.

For each output define:
- `output_id`, filename, source logical datasets and explicit output grain;
- `source_assignments`, each with an `assignment_id` and exact source region references;
- `output_columns` with stable `Source_Field_IDs`, source type, transformation, requiredness, blank handling and confidence;
- `transformations` as the explicit operation sequence;
- `operation_steps` only for row-level executable cleaning such as trim, parse or explicit filter/exclusion;
- period/formula handling, exclusions, validations, unresolved issues and confidence.

For a `DIRECT_COLUMN`, provide `Source_Field_IDs` covering the assigned regions and either `Source_Assignment_ID` or explicit `Source_References`. Do not use header text as an execution key.

Use `unpivot` when source measures are spread across period columns. If the source is already long, map its period and amount fields directly and omit `unpivot`. Compatible source partitions may be unioned through source assignments. Do not aggregate or net merely to create a flatter output.

Preserve blank/zero distinctions. Do not remove duplicates merely to force uniqueness. Do not change signs unless explicitly supported. Bind the plan to the exact source snapshot supplied in the handoff; Python will recalculate the canonical plan hash before approval.

For a routine deterministic plan that is safe to run without human approval, include:

```json
"autonomous_approval_assessment": {
  "status": "APPROVE",
  "confidence": "HIGH",
  "unresolved_material_issue_count": 0,
  "deterministic_transformations": true,
  "source_fidelity_prioritized": true,
  "expected_output_grain_defined": true,
  "inclusion_exclusion_explicit": true,
  "reconciliation_expectations_defined": true,
  "rationale": "Evidence-based reason the deterministic plan is safe to execute.",
  "source_evidence_summary": "Concise summary of the current-source evidence used."
}
```

Use this only when those statements are genuinely supported. Otherwise preserve the unresolved matter so the normal human escalation gate can handle it.
