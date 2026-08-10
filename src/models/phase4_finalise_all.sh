#!/usr/bin/env bash
# Everything downstream of Phase 4 training, in gated order.
#
# Each step halts the chain on failure, because every one of them is a gate as
# well as a computation: if C0 stops reproducing Phase 3, or a probability
# matrix stops agreeing with its own argmax, the right response is to stop, not
# to carry on and publish the rest.
#
# Safe to re-run: every step overwrites its own artefacts deterministically.
#
# Run:  bash src/models/phase4_finalise_all.sh
set -eu
cd "$(dirname "$0")/../.."
LOG=reports/phase4_finalise.log
: > "$LOG"

step () {
  echo "=== START $* $(date +%H:%M:%S) ===" | tee -a "$LOG"
  if "$@" >> "$LOG" 2>&1; then
    echo "=== DONE  $* $(date +%H:%M:%S) ===" | tee -a "$LOG"
  else
    echo "=== FAILED $* (exit $?) ===" | tee -a "$LOG"
    tail -25 "$LOG"
    exit 1
  fi
}

# Refuse to start on an incomplete sweep. A partial sweep would silently produce
# a report whose headline numbers are means over fewer seeds than the
# pre-registration fixed.
missing=0
for cfg in C1 C2 C3 C4; do
  for seed in 1 2 3; do
    [ -f "reports/phase4_run_${cfg}_seed${seed}.json" ] || { echo "MISSING ${cfg} seed${seed}"; missing=1; }
  done
done
[ "$missing" -eq 0 ] || { echo "incomplete sweep; not finalising"; exit 1; }
echo "all 12 training runs present" | tee -a "$LOG"

step python src/models/phase4_infer.py
step python src/models/phase4_eval.py
step python src/models/phase4_calibration.py
step python src/models/phase4_uncertainty.py
step python src/models/phase4_structure_eval.py
step python src/models/phase4_loao.py
step python src/report/figures_phase4.py
step python src/report/build_phase4_docx.py
step python src/report/finalise_phase4.py
step python src/report/update_blueprint_phase4.py

echo "=== PHASE 4 FINALISE COMPLETE $(date +%H:%M:%S) ===" | tee -a "$LOG"
