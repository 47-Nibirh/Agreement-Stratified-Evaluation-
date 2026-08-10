"""
Phase 4 / Stage I -- predictive uncertainty and its relation to human
disagreement (RQ3).

The pre-registered primary quantity is the WITHIN-stratum Spearman correlation
between the model's predictive entropy and the per-image annotator vote
entropy. That specific form was fixed by the Phase 3 carry-forward decision for
a measured reason: Phase 3 found the POOLED correlation to be 0.320 while the
within-tier values were 0.02-0.08, i.e. the pooled figure was almost entirely a
between-tier effect. Reported pooled, RQ3 would read as a success while
measuring nothing but tier membership. Both are computed here so the artefact
is visible rather than merely asserted.

Vote entropy is identically zero on S-unanimous, so the correlation is
undefined there. It is reported as null, never as zero.

Three uncertainty estimators, in increasing cost:

  softmax     entropy of the single deterministic forward pass
  MC-SD       mean predictive distribution over 20 stochastic forward passes
              with the StochasticDepth modules returned to training mode
              (pre-registration P4-DEV-1); this also yields the standard
              total / aleatoric / epistemic decomposition, where
                  total      = H(mean_t p_t)
                  aleatoric  = mean_t H(p_t)
                  epistemic  = total - aleatoric  (the mutual information)
  ensemble    the same decomposition over the 3 seeds of a configuration, i.e.
              a 3-member deep ensemble (P4-DEV-2 records that the blueprint's
              5-member ensemble did not fit the budget, so the ensemble result
              is a lower bound on what ensembling buys)

Outputs
  reports/phase4_uncertainty.json
Run:  python src/models/phase4_uncertainty.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_common import (  # noqa: E402
    BOOT_SEED, CONFIG_LABEL, CONTESTED, POOLED_CONTESTED, REPORTS, SEEDS,
    STRATA, available_configs, build_panel, ci95, classes, macro_f1,
    marginalized_macro_f1, mc_path, patient_resamples, prereg, probs_path,
    stratum_mask, votes_to_idx)

N_BOOT_RHO = 1000  # pre-registered minimum; see phase4_common.N_BOOT_PAIR
DEFINED_STRATA = list(CONTESTED) + [POOLED_CONTESTED]


def entropy(p, axis=-1):
    q = np.clip(p, 1e-12, 1.0)
    return -(q * np.log(q)).sum(axis=axis)


def rho_replicates(pred_ent, vote_ent, pat, rows, n_boot=N_BOOT_RHO):
    """Per-resample Spearman rho, NaN where the resample is degenerate.

    The replicate vector is returned rather than a summary so that the three
    seeds can be combined on the SAME patient resamples. patient_resamples is
    driven by a fixed seed, so replicate i is the same patient draw for every
    seed, which is what makes the across-seed average below a paired quantity.
    """
    out = np.full(n_boot, np.nan)
    for i, loc in enumerate(patient_resamples(pat[rows], n_boot)):
        r = rows[loc]
        if np.unique(vote_ent[r]).size < 2 or np.unique(pred_ent[r]).size < 2:
            continue
        out[i] = spearmanr(pred_ent[r], vote_ent[r])[0]
    return out


def rho_ci(pred_ent, vote_ent, pat, rows, n_boot=N_BOOT_RHO):
    v = rho_replicates(pred_ent, vote_ent, pat, rows, n_boot)
    v = v[np.isfinite(v)]
    return ci95(v) if v.size > 10 else [None, None]


def main() -> None:
    t0 = time.time()
    cls = classes()
    k = len(cls)
    pre = prereg()
    cfgs = available_configs()
    panel, _ = build_panel(cfgs)
    V = votes_to_idx(panel, cls)
    pat = panel.patient.to_numpy()
    n = len(panel)

    vote_ent = np.array([entropy(np.bincount(r, minlength=k) / 4.0) for r in V])

    # ---- gather estimators ---------------------------------------------------
    est = {}
    for cfg in cfgs:
        P = {}
        for s in SEEDS:
            blob = np.load(probs_path(cfg, s), allow_pickle=True)
            P[s] = blob["probs"].astype(np.float64)
        est[(cfg, "softmax")] = {s: {"mean": P[s], "samples": None} for s in SEEDS}

        mc = {}
        for s in SEEDS:
            f = mc_path(cfg, s)
            if f.exists():
                mc[s] = np.load(f)["samples"].astype(np.float64)
        if len(mc) == len(SEEDS):
            est[(cfg, "mc_stochastic_depth")] = {
                s: {"mean": mc[s].mean(0), "samples": mc[s]} for s in SEEDS}

        ens = np.stack([P[s] for s in SEEDS])
        est[(cfg, "deep_ensemble_3seed")] = {"ens": {"mean": ens.mean(0), "samples": ens}}

    # ---- correlations --------------------------------------------------------
    results = {}
    for (cfg, estimator), members in est.items():
        per_member = {}
        for mkey, d in members.items():
            pe = entropy(d["mean"])
            rec = {}
            for st in ["S-unanimous"] + DEFINED_STRATA:
                rows = np.where(stratum_mask(panel, st))[0]
                if np.unique(vote_ent[rows]).size < 2:
                    rec[st] = {"n_images": int(len(rows)), "spearman_rho": None,
                               "spearman_p": None, "ci95": [None, None],
                               "undefined_reason": "vote entropy is identically 0 on "
                                                   "this stratum"}
                    continue
                r, p = spearmanr(pe[rows], vote_ent[rows])
                rec[st] = {"n_images": int(len(rows)),
                           "spearman_rho": round(float(r), 5),
                           "spearman_p": float(p),
                           "ci95": [None if x is None else round(float(x), 5)
                                    for x in rho_ci(pe, vote_ent, pat, rows)]}
            r_all, p_all = spearmanr(pe, vote_ent)
            rec["_pooled_all_1353_images"] = {
                "n_images": int(n), "spearman_rho": round(float(r_all), 5),
                "spearman_p": float(p_all),
                "note": ("reported only to expose the between-tier artefact Phase 3 "
                         "identified; NOT the RQ3 endpoint")}
            rec["_mean_predictive_entropy_by_stratum"] = {
                st: round(float(pe[stratum_mask(panel, st)].mean()), 5) for st in STRATA}

            if d["samples"] is not None:
                tot = entropy(d["mean"])
                alea = entropy(d["samples"]).mean(0)
                epi = tot - alea
                rec["_uncertainty_decomposition"] = {
                    st: {"total": round(float(tot[stratum_mask(panel, st)].mean()), 5),
                         "aleatoric": round(float(alea[stratum_mask(panel, st)].mean()), 5),
                         "epistemic_mutual_information": round(
                             float(epi[stratum_mask(panel, st)].mean()), 5)}
                    for st in STRATA}
                for st in DEFINED_STRATA:
                    rows = np.where(stratum_mask(panel, st))[0]
                    if np.unique(epi[rows]).size >= 2:
                        rr, pp = spearmanr(epi[rows], vote_ent[rows])
                        rec["_uncertainty_decomposition"][st][
                            "epistemic_vs_vote_entropy_rho"] = round(float(rr), 5)
            per_member[str(mkey)] = rec

        agg = {}
        member_keys = [mk for mk in per_member]
        for st in ["S-unanimous"] + DEFINED_STRATA:
            rr = [per_member[mk][st]["spearman_rho"] for mk in member_keys
                  if per_member[mk][st]["spearman_rho"] is not None]
            agg[st] = {"mean_rho": round(float(np.mean(rr)), 5) if rr else None,
                       "n_members": len(rr)}
        results[f"{cfg}|{estimator}"] = {"per_member": per_member, "aggregate": agg}
        print(f"  {cfg} {estimator} done", flush=True)

    # ---- what the estimators buy in accuracy / sharpness ---------------------
    utility = {}
    for cfg in cfgs:
        row = {}
        for st in STRATA:
            rows = np.where(stratum_mask(panel, st))[0]
            single = float(np.mean([
                marginalized_macro_f1(V[rows],
                                      panel[f"pred_{cfg}_{s}"].to_numpy()[rows], k)
                for s in SEEDS]))
            ens_pred = est[(cfg, "deep_ensemble_3seed")]["ens"]["mean"].argmax(1)
            ens = marginalized_macro_f1(V[rows], ens_pred[rows], k)
            e = {"single_model_mean_macro_f1": round(single, 5),
                 "deep_ensemble_3seed_macro_f1": round(ens, 5),
                 "ensemble_gain_points": round(100 * (ens - single), 3)}
            key = (cfg, "mc_stochastic_depth")
            if key in est:
                mcp = np.mean([est[key][s]["mean"] for s in SEEDS], axis=0).argmax(1)
                mc_f1 = marginalized_macro_f1(V[rows], mcp[rows], k)
                e["mc_stochastic_depth_macro_f1"] = round(mc_f1, 5)
                e["mc_gain_points"] = round(100 * (mc_f1 - single), 3)
            row[st] = e
        utility[cfg] = row

    # ---- pre-registered verdict ---------------------------------------------
    # The interval that decides the verdict is a POOLED patient-clustered
    # bootstrap on the 3-seed mean rho: for each of the N_BOOT_RHO patient
    # resamples the rho is computed for all three seeds and averaged, and the
    # percentiles are taken over that distribution of averages. An earlier run
    # instead averaged the three per-seed interval bounds, which propagates no
    # between-seed variation and has no coverage guarantee; that quantity is
    # retained below as a descriptive field but no longer drives the verdict.
    verdicts = {}
    st = "S-majority"
    v_rows = np.where(stratum_mask(panel, st))[0]
    for cfg in cfgs:
        key = f"{cfg}|softmax"
        rec = results[key]["per_member"]
        rhos = [rec[str(s)][st]["spearman_rho"] for s in SEEDS]
        los = [rec[str(s)][st]["ci95"][0] for s in SEEDS]
        his = [rec[str(s)][st]["ci95"][1] for s in SEEDS]
        if any(x is None for x in los + his):
            verdicts[cfg] = {"stratum": st, "verdict": "NOT COMPUTABLE"}
            continue

        reps = np.vstack([
            rho_replicates(entropy(est[(cfg, "softmax")][s]["mean"]),
                           vote_ent, pat, v_rows)
            for s in SEEDS])
        ok = np.isfinite(reps).all(axis=0)
        pooled = reps[:, ok].mean(axis=0)
        p_lo, p_hi = ci95(pooled) if pooled.size > 10 else (None, None)
        a_lo, a_hi = float(np.mean(los)), float(np.mean(his))

        verdicts[cfg] = {
            "stratum": st, "estimator": "softmax entropy",
            "mean_rho_3seed": round(float(np.mean(rhos)), 5),
            "ci95_pooled_paired": [round(float(p_lo), 5), round(float(p_hi), 5)],
            "n_valid_replicates": int(pooled.size),
            "ci95_mean_of_per_seed_bounds": [round(a_lo, 5), round(a_hi, 5)],
            "interval_note": (
                "the verdict is read off ci95_pooled_paired, a patient-clustered "
                "bootstrap on the 3-seed mean rho over shared resamples. "
                "ci95_mean_of_per_seed_bounds is the arithmetic mean of the three "
                "per-seed intervals, reported only for continuity with the first "
                "run of this analysis; it is not a calibrated 95% interval and "
                "must not be quoted as one."),
            "verdict": ("SUPPORTED" if p_lo > 0 else
                        "NOT SUPPORTED" if p_hi < 0 else "NOT RESOLVED"),
        }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "RQ3 -- does predictive uncertainty track human disagreement",
        "primary_quantity": pre["research_questions"]["RQ3"]["primary_quantity"],
        "strata_where_defined": DEFINED_STRATA,
        "configurations_evaluated": cfgs,
        "config_labels": {c: CONFIG_LABEL[c] for c in cfgs},
        "n_mc_samples": pre["research_questions"]["RQ3"]["n_mc_samples"],
        "seeds": list(SEEDS),
        "partial_sweep": bool(tuple(SEEDS) != (1, 2, 3)),
        "n_boot": N_BOOT_RHO, "boot_unit": "patient", "boot_seed": BOOT_SEED,
        "mean_vote_entropy_by_stratum": {
            st: round(float(vote_ent[stratum_mask(panel, st)].mean()), 5) for st in STRATA},
        "results": results,
        "estimator_utility": utility,
        "verdicts": verdicts,
        "phase3_reference": {
            "pooled_all_images_rho": 0.320,
            "within_tier_rho_range": [0.02, 0.08],
            "source": "reports/phase3b_calibration.json",
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase4_uncertainty.json").write_text(json.dumps(out, indent=2),
                                                     encoding="utf-8")

    print("\n--- within-stratum Spearman rho (softmax entropy vs vote entropy) --")
    print(f"  {'config':6s}" + "".join(f"{s.replace('S-', '')[:11]:>14s}"
                                        for s in DEFINED_STRATA) + f"{'pooled-all':>14s}")
    for cfg in cfgs:
        a = results[f"{cfg}|softmax"]["aggregate"]
        pooled = np.mean([results[f"{cfg}|softmax"]["per_member"][str(s)]
                          ["_pooled_all_1353_images"]["spearman_rho"] for s in SEEDS])
        print(f"  {cfg:6s}" + "".join(
            f"{(a[s]['mean_rho'] if a[s]['mean_rho'] is not None else float('nan')):14.3f}"
            for s in DEFINED_STRATA) + f"{pooled:14.3f}")
    print(f"done in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
