.PHONY: check lint test eval-en
check: lint test eval-en

lint:
	ruff check .

test:
	pytest -q

eval-en:
	python -m minisearch.evaluate --set en --min-recall 0.8
