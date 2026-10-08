"""beforeShellExecution hook: deny dangerous commands, tell the agent why.

Reads the hook payload (JSON) from stdin and writes a decision (JSON) to stdout.
"""

import json
import re
import sys

DENY = [
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r", "recursive delete"),
    (r"\bgit\s+push\b", "pushing is done by a human"),
    (
        r"\bgit\s+(commit|reset\s+--hard|checkout\s+--|clean\s+-[a-z]*f)",
        "git history is owned by loop.sh",
    ),
    (r"\b(curl|wget)\b.*\|\s*(sh|bash)", "pipe to shell"),
    (r"\bsudo\b", "no sudo"),
    (r"\bpip\s+install\b(?!.*-e\s+\.)", "no new dependencies: stdlib only"),
]


def decide(command: str) -> dict:
    for pattern, reason in DENY:
        if re.search(pattern, command):
            return {
                "permission": "deny",
                "user_message": f"Blocked by harness: {reason}",
                "agent_message": f"Denied by the harness ({reason}). Pick another approach.",
            }
    return {"permission": "allow"}


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(decide(payload.get("command", ""))))
