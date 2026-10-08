#!/usr/bin/env bash
# Return to the baseline after a demo run: back to main, drop loop branches and run artifacts.
set -e
cd "$(dirname "$0")/.."
git checkout -q main
git branch --list 'loop/*' | xargs -r git branch -D
rm -rf .loop/runs .loop/*.csv .loop/*.txt
git status --short
