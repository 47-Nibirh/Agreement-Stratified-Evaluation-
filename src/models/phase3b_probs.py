"""
Phase 3B / Stage A -- persist the full 23-way softmax matrices.

phase3_eval.py wrote only argmax + max-probability to the prediction CSVs.
Calibration (ECE, MCE, Brier, reliability diagrams), predictive entropy and
top-k analyses all need the complete probability vector, so this script
re-runs the SAME three frozen Phase 2 checkpoints over the SAME cached
1,353-image test tensor and stores the full matrices.

This adds no new modelling decision: it is the identical inference path as
phase3_eval.py (same cache, same normalisation, same batch size, same
float16 autocast, same softmax). The re-run is gated twice --

  GATE 3B.1  argmax of the saved matrix must equal y_pred in
             reports/phase3_predictions_seed{k}.csv for all 1,353 rows
  GATE 3B.2  max of the saved matrix must equal the stored `confidence`
             column to 1e-5 for all 1,353 rows

-- so if inference were not bit-reproducible the script halts rather than
silently publishing a second, slightly different set of numbers.

Outputs
  reports/phase3_probs_seed{1,2,3}.npz   (probs float32 [1353,23], filenames)
  reports/phase3b_probs_gate.json
Run:  python src/models/phase3b_probs.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2_train import CohortDataset, build_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "phase3_cache_224.npy"
INDEX = ROOT / "data" / "phase3_cache_index.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
NORM = ROOT / "reports" / "phase2_norm_stats.json"
CKPT = ROOT / "checkpoints"
REPORTS = ROOT / "reports"


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    ns = json.load(open(NORM, encoding="utf-8"))

    idx = pd.read_csv(INDEX)
    n = len(idx)
    ds = CohortDataset(CACHE, np.arange(n), np.zeros(n, dtype=int), False,
                       ns["mean"], ns["std"])
    loader = DataLoader(ds, batch_size=24, shuffle=False, num_workers=0)

    gates = {}
    for cp in sorted(CKPT.glob("phase2_convnext_tiny_seed*.pt")):
        blob = torch.load(cp, map_location="cpu", weights_only=False)
        seed = int(blob["seed"])
        model = build_model(len(cls))
        model.load_state_dict(blob["state_dict"])
        model.to(device).eval()

        chunks = []
        with torch.no_grad():
            for x, _ in loader:
                x = x.to(device)
                with torch.autocast("cuda", dtype=torch.float16,
                                    enabled=device.type == "cuda"):
                    out = model(x)
                chunks.append(torch.softmax(out.float(), 1).cpu().numpy())
        prob = np.concatenate(chunks).astype(np.float32)

        ref = pd.read_csv(REPORTS / f"phase3_predictions_seed{seed}.csv")
        if list(ref.filename) != list(idx.filename):
            raise SystemExit(f"seed {seed}: row order differs from the Phase 3 prediction CSV")
        n_arg = int((prob.argmax(1) != ref.y_pred.to_numpy()).sum())
        max_dev = float(np.abs(prob.max(1) - ref.confidence.to_numpy()).max())
        if n_arg:
            raise SystemExit(f"GATE 3B.1 FAILED seed {seed}: {n_arg} argmax mismatches")
        if max_dev > 1e-5:
            raise SystemExit(f"GATE 3B.2 FAILED seed {seed}: max |dconf| = {max_dev:.2e}")
        gates[seed] = {"n_rows": n, "n_argmax_mismatch": n_arg,
                       "max_abs_confidence_deviation": max_dev}

        np.savez_compressed(REPORTS / f"phase3_probs_seed{seed}.npz",
                            probs=prob, filename=idx.filename.to_numpy().astype(str),
                            classes=np.array(sorted(cls, key=cls.get)))
        print(f"seed {seed}: probs saved, gates PASS (argmax 0 mismatch, "
              f"max |dconf| {max_dev:.2e})", flush=True)

    (REPORTS / "phase3b_probs_gate.json").write_text(json.dumps({
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_images": n, "gates": gates, "gate_pass": True,
        "runtime_sec": round(time.time() - t0, 1)}, indent=2), encoding="utf-8")
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
