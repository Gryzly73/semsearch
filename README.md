# minisearch: demo target for an agentic harness

A tiny search library (hashing embedder + cosine, English and Russian, stdlib only) built to be
**developed by an agent inside a harness**: goal -> plan -> loop, with objective checks.

```
SPEC.md      goal + global acceptance          .cursor/rules/      workflow + replanning rules
PLAN.md      tasks, each with `done when:`     .cursor/commands/   /next-task, /replan
PROGRESS.md  decision / replan log             .cursor/hooks*      command guard, auto-format
harness/loop.py  cross-platform outer loop     harness/plan.py     plan parser, ticks boxes
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
git init -b main && git add -A && git commit -m baseline
make check            # green at baseline
```

## Run
```bash
# Windows PowerShell
.\loop.ps1
$env:AGENT_CMD = "py -3 demo/fake_agent.py"; .\loop.ps1
.\demo\reset.ps1

# Linux / macOS
./loop.sh
AGENT_CMD='python3 demo/fake_agent.py' ./loop.sh
./demo/reset.sh
```
Env: `MAX_ITER=12 MAX_FAILS=3 ITER_TIMEOUT=600 AGENT_CMD=...`

The Python loop runs `done when` checks without a shell. It accepts `pytest` and
`python -m minisearch.evaluate`, including chains joined with `&&`.

## Who does what
- Agent: edits code, may add subtasks to PLAN.md, logs to PROGRESS.md.
- Harness: picks the next task, protects `tests/acceptance eval data SPEC.md harness loop.sh .cursor`,
  runs the `done when` command and `make check` itself, ticks boxes, commits to a `loop/*` branch,
  stops on budget / repeated failures / blocked tasks.
