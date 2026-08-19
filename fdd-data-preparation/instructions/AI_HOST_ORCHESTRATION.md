# AI-Host Data-Preparation Loop

The data-preparation workflow deliberately combines **AI understanding** with **deterministic Python execution**. Do not add a model-provider API to the Python runtime. The active coding/agent host performs the reasoning checkpoints.

When asked to run the OCL workflow, keep advancing without talking to the user between internal checkpoints: run root `python run_all.py`; if `next_actor` is `AI_HOST`, open `handoff_path`, perform `next_action`, write every `required_artifacts` file, and immediately rerun; if `next_actor` is `PYTHON`, rerun immediately. Stop only for `next_actor: HUMAN`, a genuine validation/failure state, or successful completion.

For `AWAITING_AI_PLANNING`, create `dataset_map.json`, `processing_plan.json`, and `approval_questions.json` from the current profile/evidence package in one reasoning cycle. For complex packages, `AWAITING_DATASET_UNDERSTANDING` creates the Dataset Map first and `AWAITING_PROCESSING_PLAN` creates the plan next. Use bounded `fdd_data.inspection.inspect_source` only where profile evidence is insufficient.

Current source evidence overrides prior assumptions. Never infer meaning from a heading alone. Stable `field_id` values are execution keys; header text is evidence only. Preserve blank versus zero. No balancing plugs. Do not aggregate, net, change signs, exclude material rows, or alter grain without explicit evidence. Python validates Dataset Map, Processing Plan, exact source snapshot, completeness and lineage before publication. The published `output/latest/` long/flat dataset is the handoff to OCL.
