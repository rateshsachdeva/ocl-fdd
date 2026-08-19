# Claude Code instructions

Read and follow `AGENTS.md` as the canonical operating contract for this repository.

In particular, when `python run_all.py` returns `Workflow coordination` with:

```json
{"next_actor": "AI_HOST", "must_continue": true}
```

continue the workflow in the same Claude Code session: read the referenced instruction and evidence, create the required Dataset Map / Processing Plan / OCL semantic artifact without inventing financial values, rerun `python run_all.py`, and repeat until `READY`, a genuine `HUMAN` checkpoint, or `FAILED`.

Do not add raw-client Excel layout parsing to `ocl_agent`. The full embedded `fdd-data-preparation` workflow owns source understanding and standardization; OCL starts from its published standardized package.
