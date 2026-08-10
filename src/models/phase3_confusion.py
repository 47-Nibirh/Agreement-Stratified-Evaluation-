"""
Phase 3 / Stage D -- model vs. human confusion-structure comparison (O3).

Phase 0 found that human disagreement is anatomically structured: 89.8% of
wall confusions involve circumferentially ADJACENT walls (cycle
Greater-curvature -> Anterior -> Lesser-curvature -> Posterior -> back to
Greater-curvature) and 93.1% of station confusions involve NEIGHBOURING
stations (|delta station| == 1 on the 6-station linear axis), using the same
adjacency definitions as src/report/figures_v2.py (F07/F08).

This script asks whether the model's errors on the S-unanimous stratum show
the same geometric structure, using the model's confusion matrix on the
single-ground-truth stratum (the only stratum with an uncontested reference
label, so this is the correct stratum for this comparison -- other strata mix
model error with annotator disagreement and would confound the two).

Output
  reports/phase3_confusion_structure.json
Run:  python src/models/phase3_confusion.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"

WALL_CYCLE = ["G", "A", "L", "P"]
WALL_ADJACENT = {"G-A", "A-G", "A-L", "L-A", "L-P", "P-L", "G-P", "P-G"}

HUMAN_WALL_ADJACENT_PCT = 89.8
HUMAN_STATION_NEIGHBOUR_PCT = 93.1


def parse_label(label: str):
    if label == "OTHERCLASS":
        return None, None
    wall = label[0]
    station = int(label[1:])
    return wall, station


def main() -> None:
    t0 = time.time()
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    inv = {v: k for k, v in cls.items()}

    seed_files = sorted(REPORTS.glob("phase3_predictions_seed*.csv"))
    if not seed_files:
        raise SystemExit("run phase3_eval.py first")

    per_seed = {}
    pooled_wall_pairs, pooled_station_pairs = {}, {}
    for f in seed_files:
        seed = int(f.stem.split("seed")[-1])
        df = pd.read_csv(f)
        df = df[df.tier == "S-unanimous"].copy()
        df["label_true"] = df["pseudo_label"]

        errs = df[df.label_true != df.label_pred]
        n_total, n_err = len(df), len(errs)

        n_wall_diff = n_wall_adj = 0
        n_station_diff = n_station_neighbour = 0
        wall_pairs, station_pairs = {}, {}
        for _, r in errs.iterrows():
            wt, st = parse_label(r.label_true)
            wp, sp = parse_label(r.label_pred)
            if wt is None or wp is None:
                continue  # OTHERCLASS confusions have no wall/station geometry
            if wt != wp:
                n_wall_diff += 1
                key = f"{wt}-{wp}"
                if key in WALL_ADJACENT:
                    n_wall_adj += 1
                wall_pairs[key] = wall_pairs.get(key, 0) + 1
            if st != sp:
                n_station_diff += 1
                if abs(st - sp) == 1:
                    n_station_neighbour += 1
                key = f"{min(st, sp)}-{max(st, sp)}"
                station_pairs[key] = station_pairs.get(key, 0) + 1

        wall_adj_pct = 100 * n_wall_adj / n_wall_diff if n_wall_diff else None
        station_neigh_pct = 100 * n_station_neighbour / n_station_diff if n_station_diff else None

        per_seed[seed] = {
            "n_test_images": n_total,
            "n_errors": n_err,
            "error_rate_pct": round(100 * n_err / n_total, 2),
            "n_wall_differing_errors": n_wall_diff,
            "wall_adjacent_pct": round(wall_adj_pct, 2) if wall_adj_pct is not None else None,
            "n_station_differing_errors": n_station_diff,
            "station_neighbouring_pct": round(station_neigh_pct, 2) if station_neigh_pct is not None else None,
        }
        for k, v in wall_pairs.items():
            pooled_wall_pairs[k] = pooled_wall_pairs.get(k, 0) + v
        for k, v in station_pairs.items():
            pooled_station_pairs[k] = pooled_station_pairs.get(k, 0) + v

    seeds = sorted(per_seed)
    mean_wall_adj = float(np.mean([per_seed[s]["wall_adjacent_pct"] for s in seeds
                                   if per_seed[s]["wall_adjacent_pct"] is not None]))
    mean_station_neigh = float(np.mean([per_seed[s]["station_neighbouring_pct"] for s in seeds
                                        if per_seed[s]["station_neighbouring_pct"] is not None]))

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stratum": "S-unanimous (the only stratum with an uncontested reference label)",
        "per_seed": per_seed,
        "mean_wall_adjacent_pct_3seed": round(mean_wall_adj, 2),
        "mean_station_neighbouring_pct_3seed": round(mean_station_neigh, 2),
        "human_wall_adjacent_pct": HUMAN_WALL_ADJACENT_PCT,
        "human_station_neighbouring_pct": HUMAN_STATION_NEIGHBOUR_PCT,
        "wall_gap_points": round(mean_wall_adj - HUMAN_WALL_ADJACENT_PCT, 2),
        "station_gap_points": round(mean_station_neigh - HUMAN_STATION_NEIGHBOUR_PCT, 2),
        "pooled_wall_confusion_pairs": dict(sorted(pooled_wall_pairs.items(),
                                                    key=lambda kv: -kv[1])),
        "pooled_station_confusion_pairs": dict(sorted(pooled_station_pairs.items(),
                                                       key=lambda kv: -kv[1])),
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase3_confusion_structure.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    print(f"model wall-adjacent error share:      {mean_wall_adj:.2f}%  "
          f"(human: {HUMAN_WALL_ADJACENT_PCT}%)")
    print(f"model station-neighbouring error share: {mean_station_neigh:.2f}%  "
          f"(human: {HUMAN_STATION_NEIGHBOUR_PCT}%)")


if __name__ == "__main__":
    main()
