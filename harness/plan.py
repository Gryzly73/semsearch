"""PLAN.md parser. The harness (not the agent) decides what is next and what is done.

Usage:
  python harness/plan.py next              -> prints JSON {id,title,check}
                                              exit 1: nothing left, 3: invalid, 4: blocked
  python harness/plan.py done <ID>         -> ticks the checkbox of task <ID>
  python harness/plan.py block <ID>        -> marks task <ID> as [!]
  python harness/plan.py status            -> one-line summary
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PLAN = Path(__file__).resolve().parents[1] / "PLAN.md"
TASK_RE = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>[ x!])\] (?P<id>T[\d.]+)\s+(?P<title>.*)$")
CHECK_RE = re.compile(r"^\s*- done when: `(?P<cmd>.+)`\s*$")


@dataclass
class Task:
    id: str
    title: str
    mark: str
    depth: int
    line: int
    check: str | None = None


def parse(text: str) -> list[Task]:
    tasks: list[Task] = []
    for n, raw in enumerate(text.splitlines()):
        m = TASK_RE.match(raw)
        if m:
            tasks.append(
                Task(m["id"], m["title"].strip(), m["mark"], len(m["indent"]) // 2, n)
            )
            continue
        c = CHECK_RE.match(raw)
        if c and tasks and tasks[-1].check is None:
            tasks[-1].check = c["cmd"]
    return tasks


def next_leaf(tasks: list[Task]) -> Task | None:
    """First unchecked task that has no unchecked descendants."""
    for i, t in enumerate(tasks):
        if t.mark != " ":
            continue
        has_open_child = False
        for u in tasks[i + 1 :]:
            if u.depth <= t.depth:
                break
            if u.mark == " ":
                has_open_child = True
                break
        if not has_open_child:
            return t
    return None


def set_mark(text: str, task_id: str, mark: str) -> str:
    out = []
    for raw in text.splitlines():
        m = TASK_RE.match(raw)
        if m and m["id"] == task_id:
            raw = f"{m['indent']}- [{mark}] {m['id']} {m['title']}"
        out.append(raw)
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    text = PLAN.read_text(encoding="utf-8")
    tasks = parse(text)
    if cmd == "next":
        blocked = [t for t in tasks if t.mark == "!"]
        t = next_leaf(tasks)
        if t is None:
            return 4 if blocked else 1
        if not t.check:
            print(f"task {t.id} has no 'done when' command", file=sys.stderr)
            return 3
        print(json.dumps({"id": t.id, "title": t.title, "check": t.check}, ensure_ascii=False))
        return 0
    if cmd in {"done", "block"}:
        PLAN.write_text(set_mark(text, argv[2], "x" if cmd == "done" else "!"), encoding="utf-8")
        return 0
    if cmd == "status":
        done = sum(t.mark == "x" for t in tasks)
        print(f"{done}/{len(tasks)} done, {sum(t.mark == '!' for t in tasks)} blocked")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
