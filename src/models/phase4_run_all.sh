#!/usr/bin/env bash
# Phase 4 training driver: 4 configurations x 3 seeds, sequentially.
#
# Seed-major order is deliberate: after the first pass every configuration has
# one completed run, so an interrupted budget still leaves a comparable (if
# single-seed) C1-C4 set rather than three seeds of C1 and nothing else.
#
# Run:  bash src/models/phase4_run_all.sh
set -u
cd "$(dirname "$0")/../.."
LOG=reports/phase4_train.log
: > "$LOG"
for seed in 1 2 3; do
  for cfg in C1 C2 C3 C4; do
    out="reports/phase4_run_${cfg}_seed${seed}.json"
    if [ -f "$out" ]; then
      echo "SKIP ${cfg} seed${seed} (already complete)" | tee -a "$LOG"
      continue
    fi
    echo "=== START ${cfg} seed${seed} $(date +%H:%M:%S) ===" | tee -a "$LOG"
    python src/models/phase4_train.py --config "$cfg" --seed "$seed" --workers 2 \
      >> "$LOG" 2>&1
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "=== FAILED ${cfg} seed${seed} rc=$rc ===" | tee -a "$LOG"
    else
      echo "=== DONE ${cfg} seed${seed} $(date +%H:%M:%S) ===" | tee -a "$LOG"
    fi
  done
done
echo "=== ALL RUNS FINISHED $(date +%H:%M:%S) ===" | tee -a "$LOG"
