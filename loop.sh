#!/usr/bin/env bash
# Outer loop: goal (SPEC.md) -> plan (PLAN.md) -> iterate with a fresh agent session each time.
# The agent edits code and may add subtasks. The HARNESS verifies, ticks checkboxes and commits.
#
# Env: MAX_ITER=12  MAX_FAILS=3  ITER_TIMEOUT=600  AGENT_CMD='cursor-agent -p --force --output-format text'
set -uo pipefail
cd "$(dirname "$0")"

MAX_ITER=${MAX_ITER:-12}
MAX_FAILS=${MAX_FAILS:-3}
ITER_TIMEOUT=${ITER_TIMEOUT:-600}
AGENT_CMD=${AGENT_CMD:-cursor-agent -p --force --output-format text}
PROTECTED='tests/acceptance eval data SPEC.md harness loop.sh .cursor'

git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo: run 'git init && git add -A && git commit -m baseline'"; exit 3; }
[ -z "$(git status --porcelain)" ] || { echo "working tree is dirty: commit or stash first"; exit 3; }

BRANCH="loop/$(date +%m%d-%H%M%S)"
git checkout -q -b "$BRANCH"
mkdir -p .loop/runs
echo "iter,task,task_check,regression,plan_changed,violations,seconds" > .loop/metrics.csv
declare -A FAILS=()
echo "branch: $BRANCH"

for i in $(seq 1 "$MAX_ITER"); do
  nxt=$(python3 harness/plan.py next); rc=$?
  if [ $rc -eq 1 ]; then
    echo "✅ plan complete after $((i-1)) iterations ($(python3 harness/plan.py status))"; exit 0
  elif [ $rc -eq 4 ]; then echo "⛔ only blocked tasks left: human needed"; exit 2
  elif [ $rc -ne 0 ]; then echo "⛔ invalid plan (task without 'done when'): human needed"; exit 3
  fi
  id=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$nxt")
  title=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["title"])' "$nxt")
  check=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["check"])' "$nxt")
  echo; echo "=== iter $i/$MAX_ITER  $id: $title"; echo "    done when: $check"

  plan_before=$(sha1sum PLAN.md | cut -d' ' -f1)
  prompt="$(cat .cursor/commands/next-task.md)

ITERATION: $i
TASK: $id $title
DONE WHEN (harness runs this, exit code 0 = done): $check"

  start=$(date +%s)
  LOOP_ITER=$i LOOP_TASK_ID=$id timeout "$ITER_TIMEOUT" $AGENT_CMD "$prompt" \
    2>&1 | tee ".loop/runs/iter-$i.log" | tail -n 15
  secs=$(( $(date +%s) - start ))

  # 1. protection: harness reverts edits to protected paths
  viol=0
  for p in $PROTECTED; do
    if ! git diff --quiet -- "$p" 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard -- "$p")" ]; then
      echo "🚫 protected path touched: $p (reverted)"; viol=$((viol+1))
      git checkout -q -- "$p" 2>/dev/null; git clean -fdq -- "$p" 2>/dev/null
    fi
  done

  # 2. objective verification, outside the agent
  bash -c "$check" >.loop/last_check.txt 2>&1; task_ok=$?
  make check >.loop/last_regress.txt 2>&1; reg_ok=$?
  plan_after=$(sha1sum PLAN.md | cut -d' ' -f1)
  replanned=0; [ "$plan_before" != "$plan_after" ] && replanned=1

  if [ $task_ok -eq 0 ] && [ $reg_ok -eq 0 ]; then
    python3 harness/plan.py done "$id"; rm -f .loop/last_failure.txt
    FAILS[$id]=0; status="DONE"
  else
    status="FAIL"
    { echo "iteration $i, task $id: task_check_exit=$task_ok regression_exit=$reg_ok"
      echo "--- task check output (tail):"; tail -n 25 .loop/last_check.txt
      echo "--- make check output (tail):"; tail -n 15 .loop/last_regress.txt
    } > .loop/last_failure.txt
    # a replan is progress, not a failure of the same task
    if [ $replanned -eq 1 ]; then FAILS[$id]=0; else FAILS[$id]=$(( ${FAILS[$id]:-0} + 1 )); fi
  fi

  echo "$i,$id,$task_ok,$reg_ok,$replanned,$viol,$secs" >> .loop/metrics.csv
  echo "    -> $status  (task_check=$task_ok regression=$reg_ok replanned=$replanned violations=$viol, ${secs}s)"
  git add -A && git commit -q -m "iter $i: $id $status$([ $replanned -eq 1 ] && echo ' [replanned]')" || true

  if [ "${FAILS[$id]:-0}" -ge "$MAX_FAILS" ]; then
    python3 harness/plan.py block "$id"; git commit -qam "iter $i: $id BLOCKED after $MAX_FAILS failures"
    echo "⛔ $id failed $MAX_FAILS times without replanning: escalating to a human"; exit 2
  fi
done
echo "🛑 iteration budget ($MAX_ITER) exhausted; $(python3 harness/plan.py status)"; exit 1
