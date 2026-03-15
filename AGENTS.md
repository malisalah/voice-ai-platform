# Agent Behavior Rules

## Parallelism
- Scaffold service folders in parallel
- Never write to shared/ from a sub-agent without confirming with parent
- Each sub-agent works only within its assigned service directory

## File Safety
- Never delete files — only create or modify
- Always read existing file before editing it
- If a file already exists, extend it — never overwrite

## When Stuck
- Do not guess at missing config values — insert TODO comment
- Do not install packages not in requirements.txt — add a note instead
- Stop and report blockers rather than inventing solutions