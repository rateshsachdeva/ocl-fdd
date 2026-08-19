# Processing Plan

Convert the validated Dataset Map into `processing_plan.json`: a precise deterministic recipe for the long/flat output. The AI host plans; Python executes.

For each output define source logical datasets, exact source assignments/regions, output grain, output columns, stable `Source_Field_IDs`, context-derived fields, requiredness, blank handling, transformations, exclusions and validations. Do not use header text as the execution key.

Use `unpivot` when source measures are spread across period columns. If the source is already long, map period and amount directly and omit `unpivot`. Compatible source partitions may be unioned through source assignments.

Preserve blank/zero distinctions. Do not remove duplicates merely to force uniqueness. Do not aggregate, net or change signs unless explicitly supported. Bind the plan to the exact source snapshot supplied in the handoff. Include `autonomous_approval_assessment` only when evidence supports high-confidence deterministic execution with no unresolved material issue. Python calculates the canonical plan hash and validates references before execution.
