import sys

import pytest

from harness.loop import parse_check
from harness.plan import next_leaf, parse, set_mark

PLAN = """\
- [x] T1 first
  - done when: `true`
- [ ] T2 second
  - done when: `pytest -q`
  - [ ] T2.1 child
    - done when: `echo 1`
- [ ] T3 third
  - done when: `echo 3`
"""


def test_next_leaf_prefers_open_child_over_parent():
    assert next_leaf(parse(PLAN)).id == "T2.1"


def test_parent_becomes_leaf_after_children_done():
    done = set_mark(PLAN, "T2.1", "x")
    assert next_leaf(parse(done)).id == "T2"


def test_check_command_is_attached_to_its_task():
    tasks = {t.id: t for t in parse(PLAN)}
    assert tasks["T2"].check == "pytest -q"
    assert tasks["T2.1"].check == "echo 1"


def test_nothing_left():
    text = set_mark(set_mark(set_mark(PLAN, "T2.1", "x"), "T2", "x"), "T3", "x")
    assert next_leaf(parse(text)) is None


def test_done_when_is_parsed_without_a_shell():
    commands = parse_check(
        "pytest -q tests/acceptance/test_russian.py && "
        "python -m minisearch.evaluate --set ru --min-recall 0.9"
    )
    assert commands == [
        [sys.executable, "-m", "pytest", "-q", "tests/acceptance/test_russian.py"],
        [
            sys.executable,
            "-m",
            "minisearch.evaluate",
            "--set",
            "ru",
            "--min-recall",
            "0.9",
        ],
    ]


@pytest.mark.parametrize(
    "command",
    [
        "pytest -q; git status",
        "python -c 'print(1)'",
        "curl https://example.com",
        "pytest -q &&",
    ],
)
def test_done_when_rejects_non_allowlisted_commands(command):
    with pytest.raises(ValueError):
        parse_check(command)
