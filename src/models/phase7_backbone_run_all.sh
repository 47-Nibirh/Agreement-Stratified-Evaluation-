#!/usr/bin/env bash
# Phase 7 / P7.0-B -- EfficientNet-B0 replication of the Phase 4 target contrast.
#
# Seed-major order deliberately: a complete 1-seed replication of all three arms
# is more useful than three seeds of one arm if the run is interrupted, because
# the endpoint is a CONTRAST between arms.
#
# C2 first within each seed: it is the headline arm and the one every Phase 5/6
# carry-forward recommends.
set -u
cd "$(dirname "$0")/../.."
for seed in 1 2 3; do
  for cfg in C2 C3 C1; do
    ck="checkpoints/phase4_${cfg}_b0_seed${seed}.pt"
    if [ -f "$ck" ]; then
      echo "[skip] $cfg seed$seed already trained"
      continue
    fi
    echo "=== $(date +%H:%M:%S) training $cfg seed$seed (EfficientNet-B0) ==="
    python src/models/phase7_backbone_train.py --config "$cfg" --seed "$seed" --workers 2
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "[FAIL] $cfg seed$seed exited $rc -- stopping so the failure is visible"
      exit $rc
    fi
  done
done
echo "=== $(date +%H:%M:%S) all EfficientNet-B0 runs complete ==="
