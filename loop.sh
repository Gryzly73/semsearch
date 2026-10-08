#!/usr/bin/env sh
# POSIX wrapper. The loop itself is cross-platform Python.
set -eu
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python -m harness.loop "$@"
fi
exec python3 -m harness.loop "$@"
