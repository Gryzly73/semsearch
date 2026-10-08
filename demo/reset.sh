#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python -m demo.reset "$@"
fi
exec python3 -m demo.reset "$@"
