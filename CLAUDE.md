# OCL FDD

Read and follow `SKILL.md`. `SKILL.md` is authoritative.

When asked to run the skill, execute the complete workflow as the external AI host using:

`python run_all.py --ai-host external`

Continue automatically through checkpoints where `next_actor=AI_HOST` and `must_continue=true`, and stop only at `READY`, `FAILED` or a genuine `HUMAN` judgment checkpoint.

Do not duplicate methodology here.
