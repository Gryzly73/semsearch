"""Retrieval quality: hit-rate@k over a labelled query set.

Usage: python -m minisearch.evaluate --set ru --min-recall 0.85
Exit code 1 if the metric is below --min-recall.
"""

import argparse
import json
import sys
from pathlib import Path

from .corpus import load_jsonl
from .embed import HashingEmbedder
from .index import Index

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus.jsonl"
EVAL_DIR = ROOT / "eval"


def recall_at_k(index: Index, queries: list[dict], k: int = 3) -> float:
    """Share of queries whose top-k results contain at least one relevant document."""
    if not queries:
        return 0.0
    hits = 0
    for q in queries:
        found = {doc.id for doc, _ in index.search(q["query"], k=k)}
        if found & set(q["relevant"]):
            hits += 1
    return hits / len(queries)


def load_queries(name: str) -> list[dict]:
    path = EVAL_DIR / f"{name}.jsonl"
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="en", choices=["en", "ru"])
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--min-recall", type=float, default=0.0)
    args = parser.parse_args(argv)

    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(CORPUS))
    score = recall_at_k(index, load_queries(args.set), k=args.k)
    print(f"recall@{args.k} [{args.set}] = {score:.3f} (min {args.min_recall:.3f})")
    return 0 if score >= args.min_recall else 1


if __name__ == "__main__":
    sys.exit(main())
