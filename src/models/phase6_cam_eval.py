"""
Phase 6 / P6.5 -- P6-C, attribution scored as a measurement.

Phase 4 asked whether the model's PREDICTIVE uncertainty tracks human
disagreement and found that it does not: the within-stratum Spearman rho
between predictive entropy and annotator vote entropy sat at 0.02-0.08 for
every configuration, and the pooled value of 0.320 mostly measured which
stratum an image belonged to. RQ3 was supported for no configuration.

This script asks the same question of a different modality. If the model cannot
say IT is unsure, can it at least show WHERE it is unsure? Three quantities per
Grad-CAM map:

  dispersion       normalised Shannon entropy of the map read as a spatial
                   distribution over the 7x7 grid. 1.0 = evidence spread
                   uniformly over the frame; 0.0 = all evidence on one cell.
  inter-seed IoU   overlap of the top-q attribution masks across the three
                   seeds of one arm. Low = three models that agree on the label
                   are looking at different places to justify it.
  inter-arm IoU    the same across arms at fixed seed.

The primary endpoint is the WITHIN-stratum correlation on S-majority, fixed in
the pre-registration for the reason Phase 3B established: the pooled quantity is
confounded by stratum membership and is reported here only as the labelled
contrast that demonstrates the confound.

Gates
  P6.5a  within-stratum rho is primary; the pooled value is carried only as a
         contrast, and the artefact labels it as such
  P6.5b  IoU computed at the pre-registered top_q, with no post-hoc selection

Output
  reports/phase6_cam_eval.json
Run:  python src/models/phase6_cam_eval.py
"""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase6_common as C  # noqa: E402
from phase6_cam import cam_path  # noqa: E402

OUT = C.REPORTS / "phase6_cam_eval.json"


def dispersion(cams: np.ndarray) -> np.ndarray:
    """Normalised spatial Shannon entropy per map, in [0, 1]; NaN if the map is
    identically zero (ReLU removed all positive evidence)."""
    flat = cams.reshape(len(cams), -1).astype(np.float64)
    s = flat.sum(1)
    out = np.full(len(cams), np.nan)
    ok = s > 0
    p = flat[ok] / s[ok][:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -np.nansum(np.where(p > 0, p * np.log(p), 0.0), axis=1)
    out[ok] = h / np.log(flat.shape[1])
    return out


def top_mask(cams: np.ndarray, q: float) -> np.ndarray:
    """Boolean (n, cells) mask of the top-q fraction of cells per map."""
    flat = cams.reshape(len(cams), -1).astype(np.float64)
    k = max(1, int(round(q * flat.shape[1])))
    idx = np.argsort(-flat, axis=1)[:, :k]
    m = np.zeros_like(flat, dtype=bool)
    np.put_along_axis(m, idx, True, axis=1)
    return m


def pairwise_iou(masks: list) -> np.ndarray:
    """Mean pairwise IoU per image across a list of (n, cells) boolean masks."""
    vals = []
    for a, b in combinations(range(len(masks)), 2):
        inter = (masks[a] & masks[b]).sum(1)
        union = (masks[a] | masks[b]).sum(1)
        vals.append(np.where(union > 0, inter / np.maximum(union, 1), np.nan))
    return np.nanmean(np.stack(vals), axis=0)


def boot_spearman(x, y, patients, n_boot=C.N_BOOT_P6):
    rows = np.arange(len(x))
    vals = []
    for local in C.patient_resamples(patients, n_boot):
        r = rows[local]
        xa, ya = x[r], y[r]
        ok = np.isfinite(xa) & np.isfinite(ya)
        if ok.sum() < 8 or np.unique(ya[ok]).size < 2 or np.unique(xa[ok]).size < 2:
            continue
        rho = spearmanr(xa[ok], ya[ok]).statistic
        if np.isfinite(rho):
            vals.append(float(rho))
    return np.asarray(vals)


def main() -> None:
    t0 = time.time()
    pre = C.prereg()
    rule = pre["endpoints"]["P6-C"]
    q = rule["top_q"]
    primary_stratum = rule["primary"]["stratum"]

    panel, meta = C.build_panel()
    arms = [a for a in meta["arms"] if all(cam_path(a, s).exists() for s in C.SEEDS)]
    if not arms:
        raise SystemExit("no arm has a complete set of CAM files; run phase6_cam.py")
    patients = panel.patient.to_numpy()
    ventropy = panel.vote_entropy.to_numpy()

    # ---- the disagreement signal the pre-registration should have used ----
    # Vote ENTROPY is a deterministic function of the vote PATTERN: a 3-1 split
    # is always 0.5623 nats, a 2-1-1 always 1.0397. The strata are DEFINED by
    # that same pattern, so entropy is constant within S-unanimous, S-majority
    # and S-plurality alike and a within-stratum correlation against it does not
    # exist. Vote SPREAD -- the mean pairwise anatomical distance between the
    # four annotators' labels under the frozen Phase 4 distance matrix -- carries
    # the same disagreement information but distinguishes a dissenter one wall
    # away from a dissenter at the far end of the stomach, so it varies within a
    # tier. It is used below as a DECLARED EXPLORATORY substitute, never as the
    # pre-registered primary.
    D = np.load(C.DATA / "phase4_distance_matrix.npy")
    votes = C.votes_matrix(panel)
    vspread = np.mean([D[votes[:, a], votes[:, b]]
                       for a, b in combinations(range(4), 2)], axis=0)

    # ---- load, and derive the per-image quantities ------------------------
    disp, masks = {}, {}
    n_zero_maps = {}
    for a in arms:
        for s in C.SEEDS:
            z = np.load(cam_path(a, s), allow_pickle=True)
            cams = z["cams"].astype(np.float32)
            if list(z["filename"].astype(str)) != list(panel.filename):
                raise SystemExit(f"row order mismatch in CAMs for {a} seed{s}")
            d = dispersion(cams)
            disp[(a, s)] = d
            masks[(a, s)] = top_mask(cams, q)
            n_zero_maps[f"{a}_seed{s}"] = int(np.isnan(d).sum())

    disp_mean = {a: np.nanmean(np.stack([disp[(a, s)] for s in C.SEEDS]), axis=0)
                 for a in arms}
    inter_seed = {a: pairwise_iou([masks[(a, s)] for s in C.SEEDS]) for a in arms}
    inter_arm = {s: pairwise_iou([masks[(a, s)] for a in arms]) for s in C.SEEDS} \
        if len(arms) > 1 else {}
    inter_arm_mean = (np.nanmean(np.stack([inter_arm[s] for s in C.SEEDS]), axis=0)
                      if inter_arm else None)

    # ---- P6-C1 primary: within-stratum dispersion vs vote entropy ---------
    primary, by_stratum = {}, {}
    for stratum in C.STRATA:
        m = C.stratum_mask(panel, stratum)
        ve, vs = ventropy[m], vspread[m]
        entry = {"n_images": int(m.sum()),
                 "vote_entropy_distinct_values": int(np.unique(ve).size),
                 "vote_spread_distinct_values": int(np.unique(np.round(vs, 6)).size),
                 "by_arm": {}}
        if np.unique(ve).size < 2:
            entry["note"] = (
                "vote entropy is CONSTANT on this stratum, so a correlation against "
                "it does not exist -- it is undefined, not weak. Entropy is a "
                "deterministic function of the vote pattern (3-1 is always 0.5623 "
                "nats, 2-1-1 always 1.0397) and the strata are defined by that same "
                "pattern. See the P6-AMD-4 amendment.")
        for a in arms:
            d = disp_mean[a][m]
            rec = {"dispersion_mean": round(float(np.nanmean(d)), 5),
                   "dispersion_sd": round(float(np.nanstd(d)), 5),
                   "inter_seed_iou_mean": round(float(np.nanmean(inter_seed[a][m])), 5)}
            # pre-registered signal: vote entropy
            if np.unique(ve).size >= 2:
                ok = np.isfinite(d) & np.isfinite(ve)
                rho = float(spearmanr(d[ok], ve[ok]).statistic)
                b = boot_spearman(d, ve, patients[m])
                lo, hi = (C.ci95(b) if b.size >= 10 else (None, None))
                rec.update({
                    "spearman_rho": round(rho, 4),
                    "spearman_ci95": ([round(lo, 4), round(hi, 4)]
                                      if lo is not None else [None, None]),
                    "verdict": C.verdict_three_way(
                        lo, hi, above="SUPPORTED", below="NOT SUPPORTED",
                        null="NOT RESOLVED") if lo is not None else "NOT ESTIMABLE",
                })
            else:
                rec["spearman_rho"] = None
                rec["spearman_ci95"] = [None, None]
                rec["verdict"] = ("NOT ESTIMABLE (vote entropy is constant on this "
                                  "stratum by construction)")
            # declared-exploratory substitute signal: anatomical vote spread
            if np.unique(np.round(vs, 6)).size >= 2:
                ok = np.isfinite(d) & np.isfinite(vs)
                rho2 = float(spearmanr(d[ok], vs[ok]).statistic)
                b2 = boot_spearman(d, vs, patients[m])
                lo2, hi2 = (C.ci95(b2) if b2.size >= 10 else (None, None))
                rec.update({
                    "spread_spearman_rho": round(rho2, 4),
                    "spread_spearman_ci95": ([round(lo2, 4), round(hi2, 4)]
                                             if lo2 is not None else [None, None]),
                    "spread_verdict": C.verdict_three_way(
                        lo2, hi2, above="POSITIVE ASSOCIATION",
                        below="NEGATIVE ASSOCIATION", null="NO ASSOCIATION")
                    if lo2 is not None else "NOT ESTIMABLE",
                })
            else:
                rec["spread_verdict"] = "NOT ESTIMABLE (spread constant on this stratum)"
            entry["by_arm"][a] = rec
        by_stratum[stratum] = entry
    primary["stratum"] = primary_stratum
    primary["by_arm"] = by_stratum[primary_stratum]["by_arm"]
    primary["estimable"] = bool(
        by_stratum[primary_stratum]["vote_entropy_distinct_values"] >= 2)

    # ---- the pooled contrast, reported ONLY as a confound demonstration ---
    pooled = {}
    for a in arms:
        d = disp_mean[a]
        ok = np.isfinite(d) & np.isfinite(ventropy)
        pooled[a] = round(float(spearmanr(d[ok], ventropy[ok]).statistic), 4)

    # ---- P6-C2 secondary: does attribution destabilise on contested images?
    m_un = C.stratum_mask(panel, "S-unanimous")
    m_ct = C.stratum_mask(panel, C.POOLED_CONTESTED)
    secondary = {}
    for a in arms:
        iou = inter_seed[a]
        d_point = float(np.nanmean(iou[m_un]) - np.nanmean(iou[m_ct]))
        rows_un, rows_ct = np.where(m_un)[0], np.where(m_ct)[0]
        diffs = []
        gen_un = C.patient_resamples(patients[rows_un], C.N_BOOT_P6)
        gen_ct = C.patient_resamples(patients[rows_ct], C.N_BOOT_P6)
        for lu, lc in zip(gen_un, gen_ct):
            diffs.append(np.nanmean(iou[rows_un[lu]]) - np.nanmean(iou[rows_ct[lc]]))
        dv = np.asarray([x for x in diffs if np.isfinite(x)])
        lo, hi = C.ci95(dv)
        secondary[a] = {
            "inter_seed_iou_unanimous": round(float(np.nanmean(iou[m_un])), 5),
            "inter_seed_iou_contested": round(float(np.nanmean(iou[m_ct])), 5),
            "delta": round(d_point, 5),
            "delta_ci95": [round(lo, 5), round(hi, 5)],
            "verdict": C.verdict_three_way(
                lo, hi,
                above="ATTRIBUTION DESTABILISES ON CONTESTED IMAGES",
                below="ATTRIBUTION IS MORE STABLE ON CONTESTED IMAGES",
                null="STABLE (no resolvable difference)"),
        }

    headline = "C2"
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 6, "step": "P6.5", "endpoint": "P6-C",
        "question": rule["question"],
        "method": rule["method"], "method_note": rule["method_note"],
        "layer": rule["layer"], "target_class": rule["target_class"],
        "top_q": q, "top_q_note": rule["top_q_note"],
        "quantities": rule["quantities"],
        "arms": arms, "seeds": list(C.SEEDS), "headline_arm": headline,
        "n_zero_maps": n_zero_maps,
        "gates": {
            "P6.1a": meta["gate_P6.1a"],
            "P6.5a": ("PASS -- the primary quantity is the within-stratum rho on "
                      f"{primary_stratum}; the pooled value is carried below "
                      "explicitly labelled as a confound demonstration, never as "
                      "the result"),
            "P6.5b": f"PASS -- IoU computed at the pre-registered top_q = {q}",
        },
        "primary_rule": rule["primary"],
        "primary": primary,
        "by_stratum": by_stratum,
        "pooled_contrast": {
            "spearman_rho_pooled": pooled,
            "why_not_the_result": (
                "Phase 3B established that a correlation pooled across strata mostly "
                "measures which stratum an image is in, because vote entropy is "
                "identically zero on S-unanimous and positive elsewhere. The pooled "
                "value is reported to demonstrate the size of that confound against "
                "the within-stratum value, not as evidence for or against P6-C."),
        },
        "amendment_P6-AMD-4": {
            "what": ("the pre-registered primary endpoint is NOT ESTIMABLE on its "
                     "pre-registered stratum, for a structural reason the "
                     "pre-registration did not anticipate."),
            "why": ("annotator vote entropy is a deterministic function of the vote "
                    "PATTERN -- a 3-1 split is always 0.5623 nats, a 2-1-1 split "
                    "always 1.0397 -- and the agreement strata are DEFINED by that "
                    "same pattern. Vote entropy is therefore constant within "
                    "S-unanimous, S-majority and S-plurality alike (1 distinct value "
                    "each), and takes only 2 values on S-no-majority. A within-stratum "
                    "correlation against a constant does not exist."),
            "consequence": ("P6-C1 is reported as NOT ESTIMABLE rather than as a null. "
                            "Reporting it as 'no association' would assert a "
                            "measurement that was never possible."),
            "carry_back": ("this also bears on Phase 4's RQ3, which reported "
                           "'within-stratum' entropy correlations of 0.02-0.08. On "
                           "this corpus that quantity can only be non-degenerate where "
                           "a stratum mixes vote patterns. Phase 7 should restate the "
                           "RQ3 finding with this structural limit made explicit."),
            "substitute": ("a declared EXPLORATORY substitute is reported alongside: "
                           "the mean pairwise ANATOMICAL distance between the four "
                           "annotators' labels under the frozen Phase 4 distance "
                           "matrix. It carries the same disagreement information but "
                           "distinguishes a dissenter one wall away from a dissenter "
                           "at the far end of the stomach, so it varies within a tier "
                           "(8, 23 and 10 distinct values on S-majority, S-plurality "
                           "and S-no-majority). It is post-hoc and is labelled "
                           "exploratory everywhere it appears; it is NOT a "
                           "substitute pre-registered endpoint."),
        },
        "secondary_rule": rule["secondary"],
        "secondary": secondary,
        "inter_arm_iou_mean": (round(float(np.nanmean(inter_arm_mean)), 5)
                               if inter_arm_mean is not None else None),
        "runtime_sec": round(time.time() - t0, 1),
    }
    out["verdict_summary"] = {
        "P6-C1_primary": primary["by_arm"][headline].get("verdict"),
        "P6-C1_primary_rho": primary["by_arm"][headline].get("spearman_rho"),
        "P6-C1_primary_ci95": primary["by_arm"][headline].get("spearman_ci95"),
        "P6-C1b_exploratory_spread": primary["by_arm"][headline].get("spread_verdict"),
        "P6-C1b_exploratory_rho": primary["by_arm"][headline].get("spread_spearman_rho"),
        "P6-C1b_exploratory_ci95": primary["by_arm"][headline].get("spread_spearman_ci95"),
        "P6-C2_secondary": secondary[headline]["verdict"],
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"[P6.5] P6-C1 primary (vote entropy), within {primary_stratum}: "
          f"estimable={primary['estimable']}")
    for a in arms:
        r = primary["by_arm"][a]
        print(f"   {C.CONFIG_SHORT[a]:16s} rho {r.get('spearman_rho')} "
              f"{r.get('spearman_ci95')} -> {r.get('verdict')}")
    print(f"[P6.5] P6-C1b EXPLORATORY (anatomical vote spread), within {primary_stratum}:")
    for a in arms:
        r = primary["by_arm"][a]
        print(f"   {C.CONFIG_SHORT[a]:16s} rho {r.get('spread_spearman_rho')} "
              f"{r.get('spread_spearman_ci95')} -> {r.get('spread_verdict')}")
    print(f"[P6.5] pooled entropy (confound demo, NOT the result): {pooled}")
    print("[P6.5] P6-C2 secondary, inter-seed attribution stability:")
    for a in arms:
        s = secondary[a]
        print(f"   {C.CONFIG_SHORT[a]:16s} unanimous {s['inter_seed_iou_unanimous']:.3f} "
              f"contested {s['inter_seed_iou_contested']:.3f} "
              f"d={s['delta']:+.4f} {s['delta_ci95']} -> {s['verdict']}")
    print(f"[P6.5] wrote {OUT.name} in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
