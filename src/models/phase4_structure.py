"""
Phase 4 / Stage C -- the anatomical distance matrix used by configuration C4.

Blueprint sec.2.2 records that the 23-class label space is a (wall x station)
grid, and sec.2.5 records that human disagreement respects that grid: 89.8% of
wall confusions are between circumferentially ADJACENT walls and 93.1% of
station confusions are between NEIGHBOURING stations. The blueprint calls this
structure "the thesis's main analytical lever". Ordinary cross-entropy is blind
to it: confusing A3 with L3 (one quarter-turn of the scope) and confusing A3
with P6 (wrong wall AND the far end of the stomach) cost exactly the same.

C4 adds a penalty proportional to the anatomical distance between the target
and the predicted distribution. This script builds that distance matrix, once,
from the label strings alone -- no model, no data, no tuning.

Definition (pre-registered)
  wall axis     circumferential cycle G -> A -> L -> P -> G, so the cyclic
                distance between two walls is 0, 1 or 2; normalised by 2.
                This is exactly the adjacency relation of Phase 0 F07 and of
                phase3_confusion.WALL_ADJACENT.
  station axis  the six SSS stations on a linear insertion-depth axis, so the
                distance is |delta station|; normalised by 5. This is exactly
                the relation of Phase 0 F08 (|delta| == 1 is "neighbouring").
  landmark pair d = 0.5 * wall_norm + 0.5 * station_norm  in [0, 1]
  OTHERCLASS    "unsuitable for assessment" is a quality judgement, not a
                position on the grid (blueprint sec.2.6 shows it is a
                different task), so it has no geometry: d(OTHERCLASS, any
                landmark) = 1.0, the maximum, and d(OTHERCLASS, OTHERCLASS) = 0.
                Assigning it anything smaller would silently assert that some
                landmarks are "closer to unusable" than others.

Equal weighting of the two axes is a pre-registered choice, not a fitted one.
It is the neutral option; no weighted variant was trained (see the limitation
recorded in reports/phase4_prereg.json).

Gates
  P4.3a  symmetric, zero diagonal, range [0, 1]
  P4.3b  every pair Phase 0 calls wall-adjacent has wall_norm = 0.5 and every
         pair it calls wall-opposite has 1.0
  P4.3c  every pair Phase 0 calls station-neighbouring has station_norm = 0.2

Outputs
  reports/phase4_distance_matrix.json
  data/phase4_distance_matrix.npy   (23, 23) float32
Run:  python src/models/phase4_structure.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
OUT_JSON = ROOT / "reports" / "phase4_distance_matrix.json"
OUT_NPY = ROOT / "data" / "phase4_distance_matrix.npy"

WALL_CYCLE = ["G", "A", "L", "P"]
WALL_ADJACENT = {"G-A", "A-G", "A-L", "L-A", "L-P", "P-L", "G-P", "P-G"}  # phase3_confusion.py
N_STATIONS = 6
W_WALL = 0.5
W_STATION = 0.5
OTHER = "OTHERCLASS"


def parse_label(label: str):
    if label == OTHER:
        return None, None
    return label[0], int(label[1:])


def wall_norm(a: str, b: str) -> float:
    ia, ib = WALL_CYCLE.index(a), WALL_CYCLE.index(b)
    d = abs(ia - ib)
    return min(d, len(WALL_CYCLE) - d) / 2.0


def station_norm(a: int, b: int) -> float:
    return abs(a - b) / (N_STATIONS - 1)


def main() -> None:
    t0 = time.time()
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    names = [k for k, _ in sorted(cls.items(), key=lambda kv: kv[1])]
    k = len(names)

    D = np.zeros((k, k), dtype=np.float64)
    Wn = np.full((k, k), np.nan)
    Sn = np.full((k, k), np.nan)
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i == j:
                continue
            wa, sa = parse_label(a)
            wb, sb = parse_label(b)
            if wa is None or wb is None:
                D[i, j] = 1.0
                continue
            w = wall_norm(wa, wb)
            s = station_norm(sa, sb)
            Wn[i, j], Sn[i, j] = w, s
            D[i, j] = W_WALL * w + W_STATION * s

    # ---- gates -------------------------------------------------------------
    if not np.allclose(D, D.T):
        raise SystemExit("GATE P4.3a FAILED: distance matrix is not symmetric")
    if np.any(np.diag(D) != 0):
        raise SystemExit("GATE P4.3a FAILED: non-zero diagonal")
    if D.min() < 0 or D.max() > 1:
        raise SystemExit(f"GATE P4.3a FAILED: range [{D.min()}, {D.max()}] outside [0,1]")

    n_adj_checked = n_opp_checked = n_stn_checked = 0
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            wa, sa = parse_label(a)
            wb, sb = parse_label(b)
            if wa is None or wb is None or wa == wb:
                continue
            key = f"{wa}-{wb}"
            if key in WALL_ADJACENT:
                if abs(Wn[i, j] - 0.5) > 1e-12:
                    raise SystemExit(f"GATE P4.3b FAILED: {a}/{b} adjacent but wall_norm={Wn[i, j]}")
                n_adj_checked += 1
            else:
                if abs(Wn[i, j] - 1.0) > 1e-12:
                    raise SystemExit(f"GATE P4.3b FAILED: {a}/{b} opposite but wall_norm={Wn[i, j]}")
                n_opp_checked += 1
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            wa, sa = parse_label(a)
            wb, sb = parse_label(b)
            if wa is None or wb is None or sa == sb:
                continue
            if abs(sa - sb) == 1:
                if abs(Sn[i, j] - 0.2) > 1e-12:
                    raise SystemExit(f"GATE P4.3c FAILED: {a}/{b} neighbouring but station_norm={Sn[i, j]}")
                n_stn_checked += 1

    np.save(OUT_NPY, D.astype(np.float32))

    off = D[~np.eye(k, dtype=bool)]
    landmark_idx = [i for i, nme in enumerate(names) if nme != OTHER]
    Dl = D[np.ix_(landmark_idx, landmark_idx)]
    offl = Dl[~np.eye(len(landmark_idx), dtype=bool)]

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "anatomical distance matrix for the C4 structured penalty",
        "classes": names,
        "n_classes": k,
        "definition": {
            "wall_cycle": WALL_CYCLE,
            "wall_norm": "cyclic wall distance / 2, so adjacent = 0.5, opposite = 1.0",
            "station_norm": "|delta station| / 5, so neighbouring = 0.2",
            "combination": f"{W_WALL} * wall_norm + {W_STATION} * station_norm",
            "otherclass_rule": "distance 1.0 to every landmark; OTHERCLASS has no grid position",
            "weights_are_preregistered_not_fitted": True,
        },
        "gates": {
            "P4.3a_symmetric_zero_diagonal_unit_range": True,
            "P4.3b_wall_adjacency_matches_phase0": True,
            "P4.3b_n_adjacent_pairs_checked": n_adj_checked,
            "P4.3b_n_opposite_pairs_checked": n_opp_checked,
            "P4.3c_station_adjacency_matches_phase0": True,
            "P4.3c_n_neighbouring_pairs_checked": n_stn_checked,
        },
        "mean_offdiagonal_distance_all_classes": round(float(off.mean()), 5),
        "mean_offdiagonal_distance_landmarks_only": round(float(offl.mean()), 5),
        "min_offdiagonal_distance": round(float(off.min()), 5),
        "distance_value_histogram": {str(round(float(v), 4)): int(c) for v, c in
                                     zip(*np.unique(np.round(off, 4), return_counts=True))},
        "examples": {
            f"{a} vs {b}": round(float(D[cls[a], cls[b]]), 4) for a, b in
            [("A3", "L3"), ("A3", "P3"), ("A3", "A4"), ("A3", "P6"),
             ("G1", "A1"), ("A1", OTHER)]
        },
        "matrix": [[round(float(v), 6) for v in row] for row in D],
        "runtime_sec": round(time.time() - t0, 2),
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"GATE P4.3a-c PASS ({n_adj_checked} adjacent, {n_opp_checked} opposite, "
          f"{n_stn_checked} neighbouring-station pairs verified)")
    print(f"  mean off-diagonal distance: {off.mean():.4f} "
          f"(landmarks only {offl.mean():.4f})")
    for kk, v in out["examples"].items():
        print(f"  d({kk}) = {v}")
    print(f"wrote {OUT_JSON.name}, {OUT_NPY.name}")


if __name__ == "__main__":
    main()
