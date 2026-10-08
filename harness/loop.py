"""Cross-platform autonomous development loop.

The agent may edit product code and refine PLAN.md. This harness owns task
selection, protected paths, objective checks, commits, and stop conditions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOOP_DIR = ROOT / ".loop"
RUNS_DIR = LOOP_DIR / "runs"
PROTECTED = (
    "tests/acceptance",
    "eval",
    "data",
    "SPEC.md",
    "harness",
    "loop.sh",
    "loop.ps1",
    ".cursor",
)
REGRESSION_CHECKS = (
    ("lint", (sys.executable, "-m", "ruff", "check", ".")),
    ("tests", (sys.executable, "-m", "pytest", "-q")),
    (
        "eval-en",
        (sys.executable, "-m", "minisearch.evaluate", "--set", "en", "--min-recall", "0.8"),
    ),
)


def run(
    args: list[str] | tuple[str, ...],
    *,
    capture: bool = True,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=capture,
        text=True,
        check=check,
        env=env,
    )


def git(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run(("git", *args), check=check)


def plan(command: str, task_id: str | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, "-m", "harness.plan", command]
    if task_id:
        args.append(task_id)
    return run(args)


def plan_hash() -> str:
    return hashlib.sha1((ROOT / "PLAN.md").read_bytes()).hexdigest()


def parse_agent_command(value: str) -> list[str]:
    args = shlex.split(value, posix=os.name != "nt")
    if not args:
        raise ValueError("AGENT_CMD is empty")
    return args


def parse_check(command: str) -> list[list[str]]:
    """Parse a PLAN check into allowlisted argv lists, never a shell command."""
    if any(token in command for token in (";", "|", ">", "<", "`", "\n", "\r", "$(")):
        raise ValueError("shell operators are not allowed in done-when checks")
    chunks = [chunk.strip() for chunk in command.split("&&")]
    if not chunks or any(not chunk for chunk in chunks):
        raise ValueError("empty command in done-when check")

    parsed: list[list[str]] = []
    for chunk in chunks:
        args = shlex.split(chunk, posix=True)
        if not args:
            raise ValueError("empty done-when command")
        if args[0] in {"pytest", "python", "python3"}:
            if args[0] == "pytest":
                args = [sys.executable, "-m", "pytest", *args[1:]]
            elif args[1:3] == ["-m", "minisearch.evaluate"]:
                args[0] = sys.executable
            else:
                raise ValueError(
                    "done-when allows only pytest or python -m minisearch.evaluate"
                )
        else:
            raise ValueError("done-when allows only pytest or python -m minisearch.evaluate")
        parsed.append(args)
    return parsed


def run_check_commands(commands: list[list[str]], output_path: Path) -> int:
    sections: list[str] = []
    result_code = 0
    for args in commands:
        result = run(args)
        sections.append(f"$ {shlex.join(args)}\n{result.stdout}{result.stderr}")
        if result.returncode:
            result_code = result.returncode
            break
    output_path.write_text("\n".join(sections), encoding="utf-8")
    return result_code


def run_regression(output_path: Path) -> int:
    sections: list[str] = []
    result_code = 0
    for name, args in REGRESSION_CHECKS:
        result = run(args)
        sections.append(f"## {name}\n$ {shlex.join(args)}\n{result.stdout}{result.stderr}")
        if result.returncode and result_code == 0:
            result_code = result.returncode
    output_path.write_text("\n".join(sections), encoding="utf-8")
    return result_code


def run_agent(args: list[str], prompt: str, env: dict[str, str], timeout: int, log: Path) -> int:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        [*args, prompt],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        creationflags=creationflags,
        start_new_session=os.name != "nt",
    )
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGTERM)
        output, _ = process.communicate()
        output += f"\nAgent timed out after {timeout}s\n"
    log.write_text(output, encoding="utf-8")
    for line in deque(output.splitlines(), maxlen=15):
        print(line)
    return process.returncode or 0


def changed(path: str) -> bool:
    return bool(git("status", "--porcelain", "--", path).stdout.strip())


def restore_protected() -> int:
    violations = 0
    for path in PROTECTED:
        if not changed(path):
            continue
        print(f"PROTECTED path touched: {path} (reverted)")
        violations += 1
        git("checkout", "-q", "--", path)
        git("clean", "-fdq", "--", path)
    return violations


def tail(path: Path, count: int) -> str:
    if not path.exists():
        return ""
    return "\n".join(deque(path.read_text(encoding="utf-8").splitlines(), maxlen=count))


def commit_iteration(iteration: int, task_id: str, status: str, replanned: bool) -> None:
    git("add", "-A", check=True)
    message = f"iter {iteration}: {task_id} {status}"
    if replanned:
        message += " [replanned]"
    result = git("commit", "-q", "-m", message)
    if result.returncode and "nothing to commit" not in f"{result.stdout}{result.stderr}":
        raise RuntimeError(result.stderr.strip() or "git commit failed")


def ensure_repository_ready() -> None:
    if git("rev-parse", "--git-dir").returncode:
        raise RuntimeError("not a git repo: initialize it and create a baseline commit")
    if git("status", "--porcelain").stdout.strip():
        raise RuntimeError("working tree is dirty: commit or stash first")


def main() -> int:
    max_iter = int(os.environ.get("MAX_ITER", "12"))
    max_fails = int(os.environ.get("MAX_FAILS", "3"))
    iteration_timeout = int(os.environ.get("ITER_TIMEOUT", "600"))
    agent_command = parse_agent_command(
        os.environ.get("AGENT_CMD", "cursor-agent -p --force --output-format text")
    )

    try:
        ensure_repository_ready()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 3

    branch = time.strftime("loop/%m%d-%H%M%S")
    if git("checkout", "-q", "-b", branch).returncode:
        print(f"could not create branch {branch}", file=sys.stderr)
        return 3

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = LOOP_DIR / "metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as metrics_file:
        writer = csv.writer(metrics_file)
        writer.writerow(
            ["iter", "task", "task_check", "regression", "plan_changed", "violations", "seconds"]
        )

    failures: dict[str, int] = {}
    print(f"branch: {branch}")

    for iteration in range(1, max_iter + 1):
        next_task = plan("next")
        if next_task.returncode == 1:
            status = plan("status").stdout.strip()
            print(f"plan complete after {iteration - 1} iterations ({status})")
            return 0
        if next_task.returncode == 4:
            print("only blocked tasks left: human needed")
            return 2
        if next_task.returncode != 0:
            print("invalid plan (task without a valid done when): human needed")
            return 3

        task = json.loads(next_task.stdout)
        task_id, title, check_text = task["id"], task["title"], task["check"]
        try:
            check_commands = parse_check(check_text)
        except ValueError as exc:
            print(f"invalid done when for {task_id}: {exc}")
            return 3

        print(f"\n=== iter {iteration}/{max_iter}  {task_id}: {title}")
        print(f"    done when: {check_text}")
        before = plan_hash()
        command_text = (ROOT / ".cursor/commands/next-task.md").read_text(encoding="utf-8")
        prompt = (
            f"{command_text}\n\nITERATION: {iteration}\nTASK: {task_id} {title}\n"
            f"DONE WHEN (harness runs this, exit code 0 = done): {check_text}"
        )

        started = time.monotonic()
        env = {**os.environ, "LOOP_ITER": str(iteration), "LOOP_TASK_ID": task_id}
        run_agent(
            agent_command,
            prompt,
            env,
            iteration_timeout,
            RUNS_DIR / f"iter-{iteration}.log",
        )
        seconds = int(time.monotonic() - started)

        violations = restore_protected()
        task_ok = run_check_commands(check_commands, LOOP_DIR / "last_check.txt")
        regression_ok = run_regression(LOOP_DIR / "last_regress.txt")
        replanned = before != plan_hash()

        failure_path = LOOP_DIR / "last_failure.txt"
        if task_ok == 0 and regression_ok == 0:
            plan("done", task_id)
            failure_path.unlink(missing_ok=True)
            failures[task_id] = 0
            status = "DONE"
        else:
            status = "FAIL"
            failure_path.write_text(
                f"iteration {iteration}, task {task_id}: "
                f"task_check_exit={task_ok} regression_exit={regression_ok}\n"
                f"--- task check output (tail):\n{tail(LOOP_DIR / 'last_check.txt', 25)}\n"
                f"--- regression output (tail):\n{tail(LOOP_DIR / 'last_regress.txt', 15)}\n",
                encoding="utf-8",
            )
            failures[task_id] = 0 if replanned else failures.get(task_id, 0) + 1

        with metrics_path.open("a", newline="", encoding="utf-8") as metrics_file:
            csv.writer(metrics_file).writerow(
                [
                    iteration,
                    task_id,
                    task_ok,
                    regression_ok,
                    int(replanned),
                    violations,
                    seconds,
                ]
            )
        print(
            f"    -> {status} (task_check={task_ok} regression={regression_ok} "
            f"replanned={int(replanned)} violations={violations}, {seconds}s)"
        )
        commit_iteration(iteration, task_id, status, replanned)

        if failures.get(task_id, 0) >= max_fails:
            plan("block", task_id)
            git("add", "PLAN.md", check=True)
            git("commit", "-q", "-m", f"iter {iteration}: {task_id} BLOCKED")
            print(f"{task_id} failed {max_fails} times without replanning: human needed")
            return 2

    print(f"iteration budget ({max_iter}) exhausted; {plan('status').stdout.strip()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
