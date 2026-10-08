# PLAN

Legend: `[ ]` todo, `[x]` done (ticked by the harness only), `[!]` blocked, needs a human.
The next task is the first unchecked *leaf* (an unchecked item with no unchecked children).
Every task needs a `done when:` line with a shell command. Exit code 0 means done.

- [x] T1 Persist the index: `Index.save(path)`, `Index.load(path, embedder)`, CLI `index --corpus F --out P` and `search Q --index P`
  - done when: `pytest -q tests/acceptance/test_persistence.py`
- [ ] T2 Russian support in search quality (queries and documents in Russian)
  - done when: `pytest -q tests/acceptance/test_russian.py && python -m minisearch.evaluate --set ru --min-recall 0.9`
- [ ] T3 Language filter: `Index.search(..., lang=None)` and CLI flag `--lang`
  - done when: `pytest -q tests/acceptance/test_lang_filter.py`
