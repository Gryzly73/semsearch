"""T1 acceptance: an index saved by one process must be searchable by another.

DO NOT EDIT: protected by the harness.
"""

import os
import subprocess
import sys
from pathlib import Path

from minisearch import HashingEmbedder, Index, load_jsonl

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus.jsonl"
QUERIES = {
    "how do I keep project dependencies separate": "en02",
    "grind size for espresso extraction": "en09",
    "turning sunlight into electricity with panels": "en10",
    "how do guitar pickups work": "en12",
}


def _run(args: list[str], seed: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONHASHSEED": seed}
    out = subprocess.run(
        [sys.executable, "-m", "minisearch.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=True,
    )
    return out.stdout


def test_save_load_roundtrip_in_process(tmp_path):
    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(CORPUS))
    path = tmp_path / "index.json"
    index.save(path)
    loaded = Index.load(path, HashingEmbedder())
    assert [d.id for d, _ in loaded.search("espresso grind", k=3)] == [
        d.id for d, _ in index.search("espresso grind", k=3)
    ]


def test_index_in_one_process_search_in_another(tmp_path):
    path = tmp_path / "index.json"
    _run(["index", "--corpus", str(CORPUS), "--out", str(path)], seed="1")
    for query, expected in QUERIES.items():
        out = _run(["search", query, "--index", str(path), "-k", "3"], seed="2")
        ids = [line.split("\t")[0] for line in out.strip().splitlines()]
        assert expected in ids, f"{query!r} -> {ids}"
