"""T3 acceptance: restrict search to one language.

DO NOT EDIT: protected by the harness.
"""

import os
import subprocess
import sys
from pathlib import Path

from minisearch import HashingEmbedder, Index, load_jsonl

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus.jsonl"


def _index() -> Index:
    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(CORPUS))
    return index


def test_filter_by_language_in_api():
    hits = _index().search("water", k=10, lang="en")
    assert hits and all(doc.lang == "en" for doc, _ in hits)


def test_no_filter_still_returns_all_languages():
    langs = {doc.lang for doc, _ in _index().search("water вода", k=20)}
    assert langs == {"en", "ru"}


def test_cli_lang_flag():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    out = subprocess.run(
        [sys.executable, "-m", "minisearch.cli", "search", "water", "--lang", "en", "-k", "5"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=True,
    ).stdout
    ids = [line.split("\t")[0] for line in out.strip().splitlines()]
    assert ids and all(i.startswith("en") for i in ids)
