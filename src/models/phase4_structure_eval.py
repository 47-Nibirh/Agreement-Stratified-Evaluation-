"""
Phase 4 / Stage J -- does the anatomy-aware loss change the geometry of the
errors (RQ4)?

RQ4 asks whether exploiting the (wall x station) grid helps on contested
images. The pre-registered primary endpoint is the mean anatomical error
distance, measured with the same distance matrix C4 was trained against
(phase4_structure.py). Using the training distance as the evaluation distance
is deliberate and is declared: it is the quantity C4 optimises, so it is the
quantity on which the intervention must show an effect before any claim about
downstream benefit is entertained. The independent checks are the two
error-geometry shares taken from Phase 0, which C4 was NOT trained on:

  wall-adjacent share       of the errors whose predicted wall differs from
                            the reference wall, the fraction where the two
                            walls are circumferentially adjacent (human
                            benchmark 89.8%, Phase 0)
  station-neighbouring      of the errors whose predicted station differs, the
  share                     fraction where |delta station| = 1 (human
                            benchmark 93.1%, Phase 0)

Both use phase3_confusion.py's definitions verbatim, and both are computed on
S-unanimous, the only stratum with an uncontested reference label, so a model
confusion cannot be confounded with annotator disagreement.

The primary distance is annotator-marginalized -- averaged over the four
annotator labels rather than a single reference -- so it is defined on every
stratum including the two with no majority label, exactly like the Phase 3
primary metric.

Outputs
  reports/phase4_structure_eval.json
Run:  python src/models/phase4_structure_eval.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3_confusion import (  # noqa: E402
    HUMAN_STATION_NEIGHBOUR_PCT, HUMAN_WALL_ADJACENT_PCT, WALL_ADJACENT, parse_label)
from phase4_common import (  # noqa: E402
    BOOT_SEED, CONFIG_LABEL, POOLED_CONTESTED, REPORTS, ROOT, SEEDS, STRATA,
    available_configs, build_panel, ci95, classes, paired_bootstrap,
    patient_resamples, prereg, stratum_mask, verdict, votes_to_idx)

DIST = ROOT / "data" / "phase4_distance_matrix.npy"
N_BOOT_STRUCT = 1000  # pre-registered minimum; see phase4_common.N_BOOT_PAIR


def main() -> None:
    t0 = time.time()
    cls = classes()
    inv = {v: kk for kk, v in cls.items()}
    k = len(cls)
    pre = prereg()
    D = np.load(DIST).astype(np.float64)
    cfgs = available_configs()
    panel, _ = build_panel(cfgs)
    V = votes_to_idx(panel, cls)
    pat = panel.patient.to_numpy()

    # wall / station adjacency indicators over the class index, from the same
    # definitions phase3_confusion.py used for the Phase 0 comparison
    wall = [parse_label(inv[i])[0] for i in range(k)]
    stn = [parse_label(inv[i])[1] for i in range(k)]

    def dist_fn(cfg, seed):
        p = panel[f"pred_{cfg}_{seed}"].to_numpy()
        return lambda rows: float(D[V[rows], p[rows, None]].mean())

    # ---- per configuration --------------------------------------------------
    per_seed, aggregate = {}, {}
    for cfg in cfgs:
        per_seed[cfg] = {}
        for s in SEEDS:
            pred = panel[f"pred_{cfg}_{s}"].to_numpy()
            entry = {}
            for st in STRATA:
                rows = np.where(stratum_mask(panel, st))[0]
                dm = float(D[V[rows], pred[rows, None]].mean())
                # distance conditional on the prediction missing that annotator
                miss = V[rows] != pred[rows, None]
                dcond = float(D[V[rows], pred[rows, None]][miss].mean()) if miss.any() else None
                e = {"n_images": int(len(rows)),
                     "mean_anatomical_distance": round(dm, 5),
                     "mean_anatomical_distance_given_miss": (
                         round(dcond, 5) if dcond is not None else None),
                     "annotator_miss_rate": round(float(miss.mean()), 5)}
                entry[st] = e

            # ---- error geometry on S-unanimous, Phase 0 definitions ---------
            rows = np.where(stratum_mask(panel, "S-unanimous"))[0]
            sub = panel.iloc[rows]
            yt = sub.pseudo_label.map(cls).to_numpy()
            yp = pred[rows]
            err = yt != yp
            nwd = nwa = nsd = nsn = 0
            for a, b in zip(yt[err], yp[err]):
                wa, wb, sa, sb = wall[a], wall[b], stn[a], stn[b]
                if wa is None or wb is None:
                    continue
                if wa != wb:
                    nwd += 1
                    nwa += f"{wa}-{wb}" in WALL_ADJACENT
                if sa != sb:
                    nsd += 1
                    nsn += abs(sa - sb) == 1
            entry["_error_geometry_S_unanimous"] = {
                "n_images": int(len(rows)), "n_errors": int(err.sum()),
                "error_rate_pct": round(100 * float(err.mean()), 2),
                "n_wall_differing_errors": int(nwd),
                "wall_adjacent_pct": round(100 * nwa / nwd, 2) if nwd else None,
                "n_station_differing_errors": int(nsd),
                "station_neighbouring_pct": round(100 * nsn / nsd, 2) if nsd else None,
            }
            per_seed[cfg][s] = entry

        aggregate[cfg] = {}
        for st in STRATA:
            vals = [per_seed[cfg][s][st]["mean_anatomical_distance"] for s in SEEDS]
            rows = np.where(stratum_mask(panel, st))[0]
            bs = np.array([dist_fn(cfg, SEEDS[0])(rows[loc]) for loc in
                           patient_resamples(pat[rows], N_BOOT_STRUCT)])
            aggregate[cfg][st] = {
                "n_images": per_seed[cfg][SEEDS[0]][st]["n_images"],
                "mean_anatomical_distance_3seed": round(float(np.mean(vals)), 5),
                "sd_3seed": round(float(np.std(vals, ddof=1)), 5),
                "ci95_seed1": [round(x, 5) for x in ci95(bs)],
                "mean_anatomical_distance_given_miss_3seed": round(float(np.mean(
                    [per_seed[cfg][s][st]["mean_anatomical_distance_given_miss"]
                     for s in SEEDS])), 5),
            }
        geo = [per_seed[cfg][s]["_error_geometry_S_unanimous"] for s in SEEDS]
        aggregate[cfg]["_error_geometry_S_unanimous"] = {
            "error_rate_pct_3seed": round(float(np.mean([g["error_rate_pct"] for g in geo])), 2),
            "wall_adjacent_pct_3seed": round(float(np.mean(
                [g["wall_adjacent_pct"] for g in geo if g["wall_adjacent_pct"] is not None])), 2),
            "station_neighbouring_pct_3seed": round(float(np.mean(
                [g["station_neighbouring_pct"] for g in geo
                 if g["station_neighbouring_pct"] is not None])), 2),
            "n_wall_differing_errors_3seed_mean": round(float(np.mean(
                [g["n_wall_differing_errors"] for g in geo])), 1),
            "human_wall_adjacent_pct": HUMAN_WALL_ADJACENT_PCT,
            "human_station_neighbouring_pct": HUMAN_STATION_NEIGHBOUR_PCT,
        }
        print(f"  {cfg} structure metrics done", flush=True)

    # ---- paired contrasts on the anatomical distance ------------------------
    PAIRS = [("C4", "C2"), ("C4", "C1"), ("C2", "C3"), ("C2", "C1"), ("C1", "C0")]
    contrasts = {}
    for tre, con in PAIRS:
        if tre not in cfgs or con not in cfgs:
            continue
        contrasts[f"{tre} - {con}"] = {}
        for st in STRATA:
            m = stratum_mask(panel, st)
            per = []
            for s in SEEDS:
                d = paired_bootstrap(panel, m, dist_fn(tre, s), dist_fn(con, s),
                                     n_boot=N_BOOT_STRUCT)
                rows = np.where(m)[0]
                plug = dist_fn(tre, s)(rows) - dist_fn(con, s)(rows)
                per.append({"seed": s, "delta_distance_plugin": round(float(plug), 5),
                            "ci95": [round(float(x), 5) for x in ci95(d)]})
            lo = float(np.mean([p["ci95"][0] for p in per]))
            hi = float(np.mean([p["ci95"][1] for p in per]))
            pt = float(np.mean([p["delta_distance_plugin"] for p in per]))
            contrasts[f"{tre} - {con}"][st] = {
                "delta_distance_3seed_mean": round(pt, 5),
                "ci95_3seed_mean": [round(lo, 5), round(hi, 5)],
                "excludes_zero": bool(lo > 0 or hi < 0),
                "reduces_distance": bool(hi < 0),
                "sign_consistent_across_seeds": len(
                    {int(np.sign(p["delta_distance_plugin"])) for p in per}) == 1,
                "per_seed": per,
            }
        print(f"  distance contrast {tre} - {con} done", flush=True)

    # ---- pre-registered RQ4 verdict -----------------------------------------
    verdicts = {}
    if "C4 - C2" in contrasts:
        c = contrasts["C4 - C2"][POOLED_CONTESTED]
        met = json.loads((REPORTS / "phase4_stratified_metrics.json").read_text(
            encoding="utf-8")) if (REPORTS / "phase4_stratified_metrics.json").exists() else None
        f1c = (met["contrasts"].get("C4 - C2", {}).get("by_stratum", {})
               .get(POOLED_CONTESTED) if met else None)
        acc_ok = bool(f1c["ci95_points_3seed_mean"][1] >= 0) if f1c else None
        dist_down = bool(c["ci95_3seed_mean"][1] < 0)
        verdicts["RQ4"] = {
            "primary_endpoint": pre["research_questions"]["RQ4"]["primary_endpoint"],
            "stratum": POOLED_CONTESTED,
            "delta_distance": c["delta_distance_3seed_mean"],
            "ci95": c["ci95_3seed_mean"],
            "distance_reduced_significantly": dist_down,
            "macro_f1_side_condition_met": acc_ok,
            "macro_f1_delta_points": (f1c["diff_points_3seed_mean"] if f1c else None),
            "verdict": ("SUPPORTED" if dist_down and acc_ok else
                        "PARTIALLY SUPPORTED" if dist_down else
                        "NOT SUPPORTED" if c["ci95_3seed_mean"][0] > 0 else
                        "NOT RESOLVED"),
            "rule": pre["research_questions"]["RQ4"]["verdict_rule"],
        }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "RQ4 -- effect of the anatomical structured penalty on error geometry",
        "distance_matrix": "reports/phase4_distance_matrix.json",
        "primary_metric": ("annotator-marginalized mean anatomical distance: mean over "
                           "images and over the 4 annotator labels of d(vote, prediction); "
                           "0 for a prediction every annotator gave, 1 for a prediction "
                           "maximally far from all of them"),
        "independent_checks": ("wall-adjacent and station-neighbouring error shares on "
                               "S-unanimous, Phase 0 definitions, which C4 was not "
                               "trained against"),
        "configurations_evaluated": cfgs,
        "config_labels": {c: CONFIG_LABEL[c] for c in cfgs},
        "seeds": list(SEEDS),
        "partial_sweep": bool(tuple(SEEDS) != (1, 2, 3)),
        "n_boot": N_BOOT_STRUCT, "boot_unit": "patient", "boot_seed": BOOT_SEED,
        "per_seed": per_seed,
        "aggregate_3seed": aggregate,
        "contrasts": contrasts,
        "verdicts": verdicts,
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase4_structure_eval.json").write_text(json.dumps(out, indent=2),
                                                        encoding="utf-8")

    print("\n--- mean anatomical error distance, 3-seed mean -------------------")
    print(f"  {'config':6s}" + "".join(f"{st.replace('S-', '')[:11]:>13s}" for st in STRATA))
    for cfg in cfgs:
        print(f"  {cfg:6s}" + "".join(
            f"{aggregate[cfg][st]['mean_anatomical_distance_3seed']:13.4f}" for st in STRATA))
    print("\n--- error geometry on S-unanimous (human: "
          f"{HUMAN_WALL_ADJACENT_PCT}% wall / {HUMAN_STATION_NEIGHBOUR_PCT}% station) ---")
    for cfg in cfgs:
        g = aggregate[cfg]["_error_geometry_S_unanimous"]
        print(f"  {cfg:6s} err={g['error_rate_pct_3seed']:5.2f}%  "
              f"wall-adj={g['wall_adjacent_pct_3seed']:5.2f}%  "
              f"stn-neigh={g['station_neighbouring_pct_3seed']:5.2f}%")
    if verdicts:
        print(f"\n  RQ4 VERDICT: {verdicts['RQ4']['verdict']}")
    print(f"done in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
