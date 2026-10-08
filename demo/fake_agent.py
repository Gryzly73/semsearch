"""Scripted stand-in for `cursor-agent`, for rehearsal and for testing the harness offline.

Usage: AGENT_CMD='python3 demo/fake_agent.py' ./loop.sh
It behaves like a real agent would: tries the smallest change, runs the check, and replans
(adds a subtask to PLAN.md) when the check fails for a reason outside the task.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = os.environ.get("LOOP_TASK_ID", "")
ITER = os.environ.get("LOOP_ITER", "?")


def sh(cmd: str) -> int:
    return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True).returncode


def log(line: str) -> None:
    with open(ROOT / "PROGRESS.md", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def add_subtask(parent: str, sub_id: str, title: str, check: str) -> None:
    plan = ROOT / "PLAN.md"
    lines = plan.read_text(encoding="utf-8").splitlines()
    inserted = False
    final, i = [], 0
    while i < len(lines):
        final.append(lines[i])
        if lines[i].strip().startswith(f"- [ ] {parent} ") and i + 1 < len(lines):
            final.append(lines[i + 1])
            final.append(f"  - [ ] {sub_id} {title}")
            final.append(f"    - done when: `{check}`")
            inserted = True
            i += 1
        i += 1
    assert inserted
    plan.write_text("\n".join(final) + "\n", encoding="utf-8")


INDEX_PY = '''"""In-memory vector index with cosine search."""

import json
from pathlib import Path

from .corpus import Document
from .embed import Embedder


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class Index:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self.docs: list[Document] = []
        self.vectors: list[list[float]] = []

    def add(self, doc: Document) -> None:
        self.docs.append(doc)
        self.vectors.append(self.embedder.embed(doc.text))

    def add_many(self, docs: list[Document]) -> None:
        for doc in docs:
            self.add(doc)

    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        """Top-k documents by cosine similarity (vectors are unit length)."""
        q = self.embedder.embed(query)
        scored = [(doc, _dot(q, vec)) for doc, vec in zip(self.docs, self.vectors, strict=True)]
        scored.sort(key=lambda pair: (-pair[1], pair[0].id))
        return [(d, s) for d, s in scored[:k] if s > 0.0]

    def save(self, path: str | Path) -> None:
        payload = {
            "docs": [{"id": d.id, "text": d.text, "lang": d.lang} for d in self.docs],
            "vectors": self.vectors,
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path, embedder: Embedder) -> "Index":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        index = cls(embedder)
        index.docs = [Document(**d) for d in payload["docs"]]
        index.vectors = payload["vectors"]
        return index
'''

CLI_PY = '''"""Command line interface.

Output format of `search` (one line per hit): <doc_id>\\t<score:.3f>\\t<first 60 chars of text>
"""

import argparse
import sys
from pathlib import Path

from .corpus import load_jsonl
from .embed import HashingEmbedder
from .index import Index

DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus.jsonl"


def _cmd_index(args: argparse.Namespace) -> int:
    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(args.corpus))
    index.save(args.out)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    if args.index:
        index = Index.load(args.index, HashingEmbedder())
    else:
        index = Index(HashingEmbedder())
        index.add_many(load_jsonl(args.corpus))
    for doc, score in index.search(args.query, k=args.k):
        print(f"{doc.id}\\t{score:.3f}\\t{doc.text[:60]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minisearch")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_index = sub.add_parser("index", help="build and save an index")
    p_index.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    p_index.add_argument("--out", required=True)
    p_index.set_defaults(func=_cmd_index)

    p_search = sub.add_parser("search", help="search the corpus or a saved index")
    p_search.add_argument("query")
    p_search.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    p_search.add_argument("--index")
    p_search.add_argument("-k", type=int, default=3)
    p_search.set_defaults(func=_cmd_search)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
'''

TOKENIZE_REGEX_ONLY = '''"""Text -> tokens."""

import re

_TOKEN = re.compile(r"[a-zа-яё0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase the text and split it into alphanumeric tokens."""
    return _TOKEN.findall(text.lower())
'''

TOKENIZE_FULL = '''"""Text -> tokens (English + Russian)."""

import re

_TOKEN = re.compile(r"[a-zа-яё0-9]+")
_STOP = frozenset(
    "как что для при из за на в во с со и а о об по к от до не ли же бы у но или это есть".split()
)
_SUFFIXES = sorted(
    (
        "ами ями ого его ому ему ыми ими ией ах ях ов ев ой ей ом ем ам ям ую юю ая яя ое ее "
        "ые ие ых их ым им ть ет ит ют ут ат ят ешь ишь ется ится ла ло ли на ны ни ну ню "
        "а я о е ы и у ю ь й"
    ).split(),
    key=len,
    reverse=True,
)


def stem(token: str) -> str:
    """Very small suffix stripper for Russian; other tokens are returned unchanged."""
    if not token or not ("а" <= token[0] <= "я"):
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase, fold ё to е, split, drop Russian stopwords, stem Russian tokens."""
    tokens = _TOKEN.findall(text.lower().replace("ё", "е"))
    return [stem(t) for t in tokens if t not in _STOP]
'''

STABLE_TEST = """import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = "from minisearch import HashingEmbedder; print(HashingEmbedder().embed('hello world'))"


def _embed(seed: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONHASHSEED": seed}
    return subprocess.run(
        [sys.executable, "-c", CODE], capture_output=True, text=True, env=env, check=True
    ).stdout


def test_embedding_does_not_depend_on_hash_seed():
    assert _embed("1") == _embed("2")
"""

src = ROOT / "src" / "minisearch"
check_cmd = "pytest -q tests/unit/test_embed_stable.py"

if TASK == "T1":
    if "def save" not in (src / "index.py").read_text(encoding="utf-8"):
        (src / "index.py").write_text(INDEX_PY, encoding="utf-8")
        (src / "cli.py").write_text(CLI_PY, encoding="utf-8")
        if sh("pytest -q tests/acceptance/test_persistence.py") != 0:
            log(
                f"iter {ITER} REPLAN T1: cross-process search returns wrong hits; "
                "embedder uses hash(), randomized per process"
            )
            add_subtask("T1", "T1.1", "Make embeddings deterministic across processes", check_cmd)
    else:
        log(f"iter {ITER} T1: nothing left to do, children fixed the root cause")
elif TASK == "T1.1":
    emb = (src / "embed.py").read_text(encoding="utf-8")
    emb = emb.replace("import math\n", "import math\nimport zlib\n")
    emb = emb.replace("hash(token)", 'zlib.crc32(token.encode("utf-8"))')
    (src / "embed.py").write_text(emb, encoding="utf-8")
    (ROOT / "tests/unit/test_embed_stable.py").write_text(STABLE_TEST, encoding="utf-8")
    log(f"iter {ITER} T1.1: replaced hash() with zlib.crc32 and added a regression test")
elif TASK == "T2":
    if "а-я" not in (src / "tokenize.py").read_text(encoding="utf-8"):
        (src / "tokenize.py").write_text(TOKENIZE_REGEX_ONLY, encoding="utf-8")
        # a careless agent also "tunes" the eval set: the harness must catch this
        with open(ROOT / "eval/ru.jsonl", "a", encoding="utf-8") as fh:
            fh.write("\n")
        if sh("python -m minisearch.evaluate --set ru --min-recall 0.9") != 0:
            log(
                f"iter {ITER} REPLAN T2: Cyrillic regex fixed but ru recall is below 0.9; "
                "inflected forms do not match, need normalization and stemming"
            )
            add_subtask(
                "T2",
                "T2.1",
                "Russian normalization: yo-folding, stopwords, stemming",
                "pytest -q tests/acceptance/test_russian.py && "
                "python -m minisearch.evaluate --set ru --min-recall 0.9",
            )
    else:
        log(f"iter {ITER} T2: nothing left to do")
elif TASK == "T2.1":
    (src / "tokenize.py").write_text(TOKENIZE_FULL, encoding="utf-8")
    log(f"iter {ITER} T2.1: added yo-folding, stopwords and a suffix stemmer")
elif TASK == "T3":
    idx = (src / "index.py").read_text(encoding="utf-8")
    idx = idx.replace(
        "    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:\n"
        '        """Top-k documents by cosine similarity (vectors are unit length)."""\n'
        "        q = self.embedder.embed(query)\n"
        "        scored = [(doc, _dot(q, vec)) for doc, vec in zip(self.docs, self.vectors, strict=True)]",
        "    def search(\n"
        "        self, query: str, k: int = 5, lang: str | None = None\n"
        "    ) -> list[tuple[Document, float]]:\n"
        '        """Top-k by cosine similarity, optionally restricted to one language."""\n'
        "        q = self.embedder.embed(query)\n"
        "        scored = [\n"
        "            (doc, _dot(q, vec))\n"
        "            for doc, vec in zip(self.docs, self.vectors, strict=True)\n"
        "            if lang is None or doc.lang == lang\n"
        "        ]",
    )
    (src / "index.py").write_text(idx, encoding="utf-8")
    cli = (src / "cli.py").read_text(encoding="utf-8")
    cli = cli.replace(
        '    p_search.add_argument("--index")\n',
        '    p_search.add_argument("--index")\n    p_search.add_argument("--lang")\n',
    )
    cli = cli.replace(
        "index.search(args.query, k=args.k)", "index.search(args.query, k=args.k, lang=args.lang)"
    )
    (src / "cli.py").write_text(cli, encoding="utf-8")
    log(f"iter {ITER} T3: added lang filter to Index.search and CLI --lang")
else:
    log(f"iter {ITER} {TASK}: no script for this task")
