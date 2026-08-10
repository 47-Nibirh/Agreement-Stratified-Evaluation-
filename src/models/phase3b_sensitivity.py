"""
Phase 3B / Stage E -- sensitivity analyses and interval estimates that the
delivered Phase 3 stated as point values.

(1) O3 CONFUSION-STRUCTURE INTERVALS.  Phase 3 reported the model's
    wall-adjacent error share as 89.68% and called it "within 0.12 points" of
    the human 89.8%, and the station-neighbouring share as 85.57% against a
    human 93.1%. Both were 3-seed means of a ratio computed on 65-72 wall
    errors and 64-69 station errors, and the per-seed spread is large
    (wall 85.07-92.31, station 81.16-88.06). A 0.12-point "near-exact match"
    is not a supportable claim at that resolution. This script attaches
    patient-clustered bootstrap intervals to both shares and tests each
    against the Phase 0 human value, so the comparison is stated with the
    precision the data actually carry.

(2) ACQUISITION-STREAM COMPOSITION PER STRATUM (blueprint sec.14 §3.9.2,
    link to limitation L4).  Phase 0 flagged the corpus's two acquisition
    streams (1350x1080 and 900x720) as imbalanced across splits
    (chi2 p = 1.9e-22 across splits; unanimity 60.45% vs 55.04% by stream).
    If the contested tiers over-represented the minority stream, the tier
    effect could be a stream effect. Composition is reported per tier, with a
    chi-square test and a within-dominant-stream re-run of the tier curve.

Outputs
  reports/phase3b_sensitivity.json
Run:  python src/models/phase3b_sensitivity.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3_confusion import (  # noqa: E402
    HUMAN_STATION_NEIGHBOUR_PCT, HUMAN_WALL_ADJACENT_PCT, WALL_ADJACENT, parse_label)
from phase3b_common import (  # noqa: E402
    BOOT_SEED, TIER_ORDER, ci95, marginalized_macro_f1, votes_to_idx)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
HASHES = REPORTS / "gastrohun_hashes.csv"
SEEDS = (1, 2, 3)
N_BOOT_SENS = 2000


def geometry_shares(df: pd.DataFrame) -> tuple:
    """(wall-adjacent share, station-neighbouring share) over this frame's errors."""
    e = df[df.pseudo_label != df.label_pred]
    wd = wa = sd = sn = 0
    for t, p in zip(e.pseudo_label, e.label_pred):
        wt, st = parse_label(t)
        wp, sp = parse_label(p)
        if wt is None or wp is None:
            continue
        if wt != wp:
            wd += 1
            wa += f"{wt}-{wp}" in WALL_ADJACENT
        if st != sp:
            sd += 1
            sn += abs(st - sp) == 1
    return (100 * wa / wd if wd else np.nan,
            100 * sn / sd if sd else np.nan, wd, sd)


def main() -> None:
    t0 = time.time()
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    k = len(cls)
    dfs = {s: pd.read_csv(REPORTS / f"phase3_predictions_seed{s}.csv") for s in SEEDS}

    # ---- 1. O3 with intervals ----------------------------------------------
    o3 = {}
    for s in SEEDS:
        g = dfs[s][dfs[s].tier == "S-unanimous"].reset_index(drop=True)
        w, st, nwd, nsd = geometry_shares(g)
        rng = np.random.default_rng(BOOT_SEED)
        groups = {p: gg for p, gg in g.groupby("patient")}
        pats = g.patient.unique()
        bw, bs = np.empty(N_BOOT_SENS), np.empty(N_BOOT_SENS)
        for b in range(N_BOOT_SENS):
            sub = pd.concat([groups[p] for p in rng.choice(pats, len(pats), True)],
                            ignore_index=True)
            bw[b], bs[b], _, _ = geometry_shares(sub)
        bw, bs = bw[~np.isnan(bw)], bs[~np.isnan(bs)]
        o3[s] = {
            "n_wall_differing_errors": nwd, "n_station_differing_errors": nsd,
            "wall_adjacent_pct": round(w, 2), "wall_adjacent_ci95": [round(x, 2) for x in ci95(bw)],
            "station_neighbouring_pct": round(st, 2),
            "station_neighbouring_ci95": [round(x, 2) for x in ci95(bs)],
            "wall_ci_contains_human_value": bool(ci95(bw)[0] <= HUMAN_WALL_ADJACENT_PCT <= ci95(bw)[1]),
            "station_ci_contains_human_value": bool(ci95(bs)[0] <= HUMAN_STATION_NEIGHBOUR_PCT <= ci95(bs)[1]),
        }
    wmean = float(np.mean([o3[s]["wall_adjacent_pct"] for s in SEEDS]))
    smean = float(np.mean([o3[s]["station_neighbouring_pct"] for s in SEEDS]))
    wlo = float(np.mean([o3[s]["wall_adjacent_ci95"][0] for s in SEEDS]))
    whi = float(np.mean([o3[s]["wall_adjacent_ci95"][1] for s in SEEDS]))
    slo = float(np.mean([o3[s]["station_neighbouring_ci95"][0] for s in SEEDS]))
    shi = float(np.mean([o3[s]["station_neighbouring_ci95"][1] for s in SEEDS]))

    o3_summary = {
        "wall_adjacent_pct_3seed": round(wmean, 2),
        "wall_adjacent_ci95_3seed": [round(wlo, 2), round(whi, 2)],
        "wall_ci_width_points": round(whi - wlo, 2),
        "human_wall_adjacent_pct": HUMAN_WALL_ADJACENT_PCT,
        "wall_consistent_with_human": bool(wlo <= HUMAN_WALL_ADJACENT_PCT <= whi),
        "station_neighbouring_pct_3seed": round(smean, 2),
        "station_neighbouring_ci95_3seed": [round(slo, 2), round(shi, 2)],
        "station_ci_width_points": round(shi - slo, 2),
        "human_station_neighbouring_pct": HUMAN_STATION_NEIGHBOUR_PCT,
        "station_consistent_with_human": bool(slo <= HUMAN_STATION_NEIGHBOUR_PCT <= shi),
        "interpretation": (
            "The wall-geometry match is consistent with the human value, but the "
            "interval is far too wide to support the originally reported "
            "'within 0.12 points' near-exact match. The station comparison is "
            "reported the same way rather than as a point difference."),
    }

    # ---- 2. acquisition-stream composition ----------------------------------
    hsh = pd.read_csv(HASHES, usecols=["filename", "width"])
    wmap = hsh.set_index("filename")["width"].to_dict()
    base = dfs[SEEDS[0]].copy()
    base["stream"] = base.filename.map(wmap)
    if base.stream.isna().any():
        raise SystemExit("some test filenames have no width in the Phase 0 hash inventory")

    tab = pd.crosstab(base.tier_pooled, base.stream).reindex(TIER_ORDER)
    chi2, pval, dof, _ = chi2_contingency(tab.values)
    composition = {
        t: {"n_total": int(tab.loc[t].sum()),
            **{f"stream_{int(c)}px": int(tab.loc[t, c]) for c in tab.columns},
            "minority_stream_pct": round(100 * float(tab.loc[t].min()) / float(tab.loc[t].sum()), 2)}
        for t in TIER_ORDER}

    dominant = int(tab.sum(axis=0).idxmax())
    within = {}
    for t in TIER_ORDER:
        vals = []
        for s in SEEDS:
            d = dfs[s].copy()
            d["stream"] = d.filename.map(wmap)
            g = d[(d.tier_pooled == t) & (d.stream == dominant)]
            vals.append(marginalized_macro_f1(votes_to_idx(g, cls), g.y_pred.to_numpy(), k))
        within[t] = {"n_images": int(((base.tier_pooled == t) & (base.stream == dominant)).sum()),
                     "marginalized_macro_f1_3seed": round(float(np.mean(vals)), 5)}
    full = {t: None for t in TIER_ORDER}
    for t in TIER_ORDER:
        vals = [marginalized_macro_f1(votes_to_idx(dfs[s][dfs[s].tier_pooled == t], cls),
                                      dfs[s][dfs[s].tier_pooled == t].y_pred.to_numpy(), k)
                for s in SEEDS]
        full[t] = round(float(np.mean(vals)), 5)

    stream = {
        "streams_px_width": [int(c) for c in tab.columns],
        "dominant_stream_px": dominant,
        "composition_by_tier": composition,
        "chi2": round(float(chi2), 4), "dof": int(dof), "p_value": float(pval),
        "composition_differs_across_tiers": bool(pval < 0.05),
        "tier_curve_all_streams": {t: round(100 * full[t], 2) for t in TIER_ORDER},
        "tier_curve_dominant_stream_only": {
            t: round(100 * within[t]["marginalized_macro_f1_3seed"], 2) for t in TIER_ORDER},
        "max_abs_shift_points": round(max(
            abs(100 * within[t]["marginalized_macro_f1_3seed"] - 100 * full[t])
            for t in TIER_ORDER), 2),
    }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_boot": N_BOOT_SENS, "boot_unit": "patient", "boot_seed": BOOT_SEED,
        "o3_confusion_structure_with_intervals": {"per_seed": o3, "summary": o3_summary},
        "acquisition_stream_sensitivity": stream,
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase3b_sensitivity.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("--- O3 with patient-clustered intervals ---------------------------")
    print(f"  wall-adjacent      {wmean:6.2f}%  95% CI [{wlo:.2f}, {whi:.2f}]  "
          f"human {HUMAN_WALL_ADJACENT_PCT}  consistent: {o3_summary['wall_consistent_with_human']}")
    print(f"  station-neighbour  {smean:6.2f}%  95% CI [{slo:.2f}, {shi:.2f}]  "
          f"human {HUMAN_STATION_NEIGHBOUR_PCT}  consistent: {o3_summary['station_consistent_with_human']}")
    print("\n--- acquisition-stream composition per tier -----------------------")
    for t in TIER_ORDER:
        c = composition[t]
        print(f"  {t:16s} " + "  ".join(f"{kk}={vv}" for kk, vv in c.items() if kk.startswith("stream_"))
              + f"  minority={c['minority_stream_pct']:5.2f}%")
    print(f"  chi2={chi2:.3f} dof={dof} p={pval:.4g} -> composition differs: {pval < 0.05}")
    print(f"  tier curve, all streams        : {stream['tier_curve_all_streams']}")
    print(f"  tier curve, {dominant}px stream only: {stream['tier_curve_dominant_stream_only']}")
    print(f"  max shift = {stream['max_abs_shift_points']} pts")
    print(f"done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
