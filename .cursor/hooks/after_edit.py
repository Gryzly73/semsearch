"""afterFileEdit hook: keep style objectively consistent without spending agent tokens."""

import json
import subprocess
import sys

if __name__ == "__main__":
    payload = json.load(sys.stdin)
    path = payload.get("file_path", "")
    if path.endswith(".py"):
        subprocess.run(["ruff", "check", "--fix", "--quiet", path], check=False)
        subprocess.run(["ruff", "format", "--quiet", path], check=False)
