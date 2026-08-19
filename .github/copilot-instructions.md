Use `AGENTS.md` as the canonical operating instructions for this repository.

When running the skill, continue automatically through any `Workflow coordination` checkpoint where `next_actor` is `AI_HOST` and `must_continue` is true: read the referenced full fdd-data-preparation or OCL instruction/evidence, write the required artifacts, rerun `python run_all.py`, and repeat until `READY`, `HUMAN`, or `FAILED`.

Do not add raw-client Excel layout parsing to `ocl_agent`. Raw-source understanding belongs to the full embedded `fdd-data-preparation` workflow; OCL starts from its published standardized package.
