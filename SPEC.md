# SPEC: minisearch

## Goal
A tiny search library over short texts (English and Russian) with no network and no model files.
The target is a *measurable* search quality, not "it runs".

## Acceptance (global, checked on every iteration by `make check`)
- `ruff check .` is clean
- `pytest -q` (unit tests in `tests/unit`) passes
- `python -m minisearch.evaluate --set en --min-recall 0.8` passes (no regression for English)

## Features (see PLAN.md for the order)
1. Persistence: an index built in one process can be searched from another.
2. Russian: recall@3 on `eval/ru.jsonl` is at least 0.9, and English does not regress.
3. Language filter in the API and the CLI.

## Constraints
- Standard library only at runtime. No new runtime dependencies.
- Search CLI output format: `<doc_id>\t<score:.3f>\t<first 60 chars>`.

## Protected (agent must not modify; the harness reverts changes)
`tests/acceptance/`, `eval/`, `data/`, `SPEC.md`, `harness/`, `loop.sh`, `.cursor/`
