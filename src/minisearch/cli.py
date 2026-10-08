"""Command line interface.

Output format of `search` (one line per hit): <doc_id>\t<score:.3f>\t<first 60 chars of text>
"""

import argparse
import sys
from pathlib import Path

from .corpus import load_jsonl
from .embed import HashingEmbedder
from .index import Index

DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus.jsonl"


def _cmd_search(args: argparse.Namespace) -> int:
    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(args.corpus))
    for doc, score in index.search(args.query, k=args.k):
        print(f"{doc.id}\t{score:.3f}\t{doc.text[:60]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minisearch")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="search the corpus")
    p_search.add_argument("query")
    p_search.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    p_search.add_argument("-k", type=int, default=3)
    p_search.set_defaults(func=_cmd_search)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
