"""Return the repository to the baseline after a demo run."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True)


def main() -> int:
    git("checkout", "-q", "main")
    branches = subprocess.run(
        ["git", "branch", "--list", "loop/*"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    for branch in branches:
        git("branch", "-D", branch)

    loop_dir = ROOT / ".loop"
    shutil.rmtree(loop_dir / "runs", ignore_errors=True)
    if loop_dir.exists():
        for pattern in ("*.csv", "*.txt"):
            for path in loop_dir.glob(pattern):
                path.unlink()
    git("status", "--short")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
