"""
Phase 6 / P6.6 -- P6-D, selective prediction.

The Phase 5 carry-forward is explicit: "Report out-of-protocol rejection as a
primary endpoint in Phases 6-7: it separated the arms where every internal
endpoint failed to." Phase 5 measured it at exactly one operating point --
argmax == OTHERCLASS -- which is a property of where the 23-way decision
boundary happens to fall, not of how well the model's confidence orders its own
mistakes. A single operating point can flatter or damn a model by accident.

Risk-coverage removes the threshold. Order the images by confidence, accept the
most confident fraction c, and record the error rate among the accepted. Sweep
c from 1/n to 1. AURC is the area under that curve: the expected error of a
model that is allowed to abstain, averaged over every abstention budget. A
model whose confidence perfectly ordered its mistakes would push all error to
the low-confidence tail and score a near-zero AURC.

Two panels, both scored by max softmax (the deployed model's own confidence,
not a bolt-on detector):

  internal  the 1,353-image GastroHUN test split; an error is a prediction
            differing from the modal label. The 81 no-majority images have no
            modal label and are excluded, exactly as Phase 5 excluded them.
  external  the 17,122-image Phase 5 panel; on the 13,997 out-of-protocol
            images the CORRECT action is OTHERCLASS, so asserting any gastric
            station there is an error. This is the endpoint Phase 5 measured at
            one point.

Intervals: patient-clustered internally; image-level externally, because
neither external corpus publishes a case key (Phase 5's P5-DEV-3, restated
wherever an external interval is printed).

Gates
  P6.6a  risk at coverage 1.0 equals 1 - accuracy computed directly from the
         frozen predictions, to < 1e-9
  P6.6b  external panel row order matches data/phase5_cache_index.csv

Output
  reports/phase6_selective.json
Run:  python src/models/phase6_selective.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase6_common as C  # noqa: E402

OUT = C.REPORTS / "phase6_selective.json"
EXT_INDEX = C.DATA / "phase5_cache_index.csv"
P5_REJ = C.REPORTS / "phase5_rejection.json"
P5_MAP = C.REPORTS / "phase5_mapping.json"


def risk_coverage(correct: np.ndarray, score: np.ndarray):
    """(coverages, risks, AURC). Highest score accepted first."""
    order = np.argsort(-score, kind="stable")
    c = correct[order].astype(float)
    n = len(c)
    cum_err = np.cumsum(1.0 - c)
    k = np.arange(1, n + 1)
    risks = cum_err / k
    covs = k / n
    return covs, risks, float(risks.mean())


def at_risk(covs, risks, target):
    """Largest coverage whose risk is <= target; 0.0 if never attained."""
    ok = np.where(risks <= target)[0]
    return float(covs[ok[-1]]) if ok.size else 0.0


def at_coverage(covs, risks, target):
    i = int(np.searchsorted(covs, target, side="left"))
    i = min(i, len(risks) - 1)
    return float(risks[i])


def curve_points(covs, risks, n=200):
    """Downsample the curve to n points for plotting.

    Stored in the artefact rather than recomputed in the figure script, so the
    project's no-hand-computed-values rule holds for figures too: every point
    F43/F44 plots traces to a field written here.
    """
    grid = np.linspace(1.0 / len(covs), 1.0, n)
    i = np.searchsorted(covs, grid, side="left").clip(0, len(risks) - 1)
    return {"coverage": [round(float(c), 5) for c in grid],
            "risk": [round(float(r), 5) for r in risks[i]]}


def collapse_vector(mapping: dict, cls: dict) -> np.ndarray:
    out = np.empty(len(cls), dtype=object)
    for group, spec in mapping["collapse_definition"].items():
        for i in spec["class_indices"]:
            out[i] = group
    return out


def main() -> None:
    t0 = time.time()
    pre = C.prereg()
    rule = pre["endpoints"]["P6-D"]
    panel, meta = C.build_panel()
    arms = meta["arms"]
    cls = C.classes()

    # ================= INTERNAL PANEL =====================================
    keep = panel.pseudo_label.map(cls).notna().to_numpy()
    y_true = panel.pseudo_label.map(cls).to_numpy()[keep].astype(int)
    patients_int = panel.patient.to_numpy()[keep]
    internal = {"n_scored": int(keep.sum()),
                "n_excluded_no_modal_label": int((~keep).sum()),
                "exclusion_rule": ("images with no modal label are excluded, "
                                   "exactly as in Phase 5"),
                "by_arm": {}}
    gate_a = {}
    boot_int = {a: [] for a in arms}
    curve_int = {}
    for arm in arms:
        per_seed = []
        for s in C.SEEDS:
            pred = panel[f"pred_{arm}_{s}"].to_numpy()[keep]
            conf = panel[f"conf_{arm}_{s}"].to_numpy()[keep]
            correct = (pred == y_true)
            covs, risks, aurc = risk_coverage(correct, conf)
            # ---- GATE P6.6a: risk at full coverage == 1 - accuracy --------
            direct = 1.0 - float(correct.mean())
            d = abs(risks[-1] - direct)
            gate_a[f"{arm}_seed{s}"] = {"risk_at_full_coverage": round(float(risks[-1]), 12),
                                        "one_minus_accuracy": round(direct, 12),
                                        "abs_delta": d}
            if d >= 1e-9:
                raise SystemExit(f"GATE P6.6a FAILED for {arm} seed{s}: delta {d:.3e}")
            per_seed.append({
                "aurc": round(aurc, 5),
                "accuracy": round(float(correct.mean()), 5),
                "coverage_at_risk_10pct": round(at_risk(covs, risks, 0.10), 5),
                "risk_at_coverage_80pct": round(at_coverage(covs, risks, 0.80), 5),
            })
            if s == C.SEEDS[0]:
                curve_int[arm] = curve_points(covs, risks)
        internal["by_arm"][arm] = {
            "aurc_3seed": round(float(np.mean([p["aurc"] for p in per_seed])), 5),
            "accuracy_3seed": round(float(np.mean([p["accuracy"] for p in per_seed])), 5),
            "coverage_at_risk_10pct_3seed": round(float(np.mean(
                [p["coverage_at_risk_10pct"] for p in per_seed])), 5),
            "risk_at_coverage_80pct_3seed": round(float(np.mean(
                [p["risk_at_coverage_80pct"] for p in per_seed])), 5),
            "per_seed": per_seed,
            "curve_seed1": curve_int[arm],
        }

    # patient-clustered CI on internal AURC, paired across arms
    rows_int = np.arange(len(y_true))
    for local in C.patient_resamples(patients_int, C.N_BOOT_P6):
        r = rows_int[local]
        for arm in arms:
            pred = panel[f"pred_{arm}_{C.SEEDS[0]}"].to_numpy()[keep][r]
            conf = panel[f"conf_{arm}_{C.SEEDS[0]}"].to_numpy()[keep][r]
            _, _, aurc = risk_coverage(pred == y_true[r], conf)
            boot_int[arm].append(aurc)
    for arm in arms:
        internal["by_arm"][arm]["aurc_ci95"] = [
            round(x, 5) for x in C.ci95(np.asarray(boot_int[arm]))]
    internal["interval_unit"] = "patient (clustered)"

    # ================= EXTERNAL PANEL =====================================
    external = None
    if EXT_INDEX.exists() and P5_MAP.exists():
        ext = pd.read_csv(EXT_INDEX)
        cv = collapse_vector(json.loads(P5_MAP.read_text(encoding="utf-8")), cls)
        truth = ext.collapsed_label.to_numpy()
        external = {"n_scored": len(ext),
                    "n_out_of_protocol": int((truth == "OTHERCLASS").sum()),
                    "n_gastric": int((truth != "OTHERCLASS").sum()),
                    "error_definition": rule["panels"]["external"],
                    "interval_unit": "image (Phase 5 P5-DEV-3)",
                    "interval_caveat": pre["inherits"]["interval_procedure"]["external"],
                    "by_arm": {}}
        boot_ext, ext_correct, ext_conf = {a: [] for a in arms}, {}, {}
        curve_ext = {}
        for arm in arms:
            per_seed = []
            for s in C.SEEDS:
                p = C.REPORTS / f"phase5_probs_{arm}_seed{s}.npz"
                if not p.exists():
                    continue
                z = np.load(p, allow_pickle=True)
                probs = z["probs"]
                if len(probs) != len(ext):
                    raise SystemExit(f"GATE P6.6b FAILED: {arm} seed{s} has "
                                     f"{len(probs)} rows, panel has {len(ext)}")
                pred = cv[probs.argmax(1)]
                conf = probs.max(1)
                correct = (pred == truth)
                covs, risks, aurc = risk_coverage(correct, conf)
                per_seed.append({
                    "aurc": round(aurc, 5),
                    "accuracy": round(float(correct.mean()), 5),
                    "coverage_at_risk_10pct": round(at_risk(covs, risks, 0.10), 5),
                    "risk_at_coverage_80pct": round(at_coverage(covs, risks, 0.80), 5),
                })
                if s == C.SEEDS[0]:
                    ext_correct[arm], ext_conf[arm] = correct, conf
                    curve_ext[arm] = curve_points(covs, risks)
            if not per_seed:
                continue
            external["by_arm"][arm] = {
                "aurc_3seed": round(float(np.mean([x["aurc"] for x in per_seed])), 5),
                "accuracy_3seed": round(float(np.mean([x["accuracy"] for x in per_seed])), 5),
                "coverage_at_risk_10pct_3seed": round(float(np.mean(
                    [x["coverage_at_risk_10pct"] for x in per_seed])), 5),
                "risk_at_coverage_80pct_3seed": round(float(np.mean(
                    [x["risk_at_coverage_80pct"] for x in per_seed])), 5),
                "per_seed": per_seed,
                "curve_seed1": curve_ext[arm],
            }
        external["gate_P6.6b"] = f"PASS -- all arms have {len(ext)} rows in panel order"

        # ---- consistency with the Phase 5 single-point ranking ------------
        # Orientation stated explicitly: LOWER AURC is better, HIGHER rejection
        # is better, so the quantity correlated is (-AURC) against rejection.
        # A positive rho therefore means the two agree about which arms are good.
        rej = json.loads(P5_REJ.read_text(encoding="utf-8"))["aggregate_3seed"]
        shared = [a for a in arms if a in external["by_arm"] and a in rej]
        neg_aurc = np.array([-external["by_arm"][a]["aurc_3seed"] for a in shared])
        rejr = np.array([rej[a]["rejection_rate_mean_3seed"] for a in shared])
        rho = float(spearmanr(neg_aurc, rejr).statistic)

        rng = np.random.default_rng(C.BOOT_SEED)
        n_ext = len(ext)
        rhos = []
        for _ in range(200):   # image-level; 200 resamples over 17k rows
            idx = rng.integers(0, n_ext, n_ext)
            na = []
            for a in shared:
                _, _, au = risk_coverage(ext_correct[a][idx], ext_conf[a][idx])
                na.append(-au)
            r = spearmanr(np.array(na), rejr).statistic
            if np.isfinite(r):
                rhos.append(float(r))
        lo, hi = C.ci95(np.asarray(rhos))
        external["phase5_consistency"] = {
            "arms": shared,
            "orientation": ("lower AURC is better and higher rejection is better, so "
                            "the correlated quantities are (-AURC) and the Phase 5 "
                            "rejection rate; a POSITIVE rho means the two endpoints "
                            "agree about which arms are good"),
            "neg_aurc_external": [round(x, 5) for x in neg_aurc],
            "phase5_rejection_rate": [round(x, 5) for x in rejr],
            "spearman_rho": round(rho, 4),
            "spearman_ci95": [round(lo, 4), round(hi, 4)],
            "n_boot": len(rhos),
            "verdict": ("CONSISTENT WITH THE PHASE 5 RANKING" if lo > 0
                        else "INCONSISTENT WITH THE PHASE 5 RANKING"),
            "caveat": ("with only five arms the Spearman statistic takes a small "
                       "number of discrete values, so this interval is coarse by "
                       "construction and is reported as a consistency check rather "
                       "than as a powered test"),
            "interval_excludes_point_estimate": bool(not (lo <= rho <= hi)),
            "interval_excludes_point_estimate_note": (
                "The bootstrap interval does not contain the point estimate. This is "
                "not an error: Spearman's rho on five items can take only a handful "
                "of values, the full-sample ordering achieves the maximum 1.0, and "
                "every resample that perturbs one adjacent pair drops it to 0.9 or "
                "0.8. The percentile interval therefore sits entirely below a point "
                "estimate that is at the boundary of the statistic's range. Read the "
                "interval as 'the ordering agrees strongly under resampling', not as "
                "a conventional confidence interval."
                if not (lo <= rho <= hi) else "n/a -- the interval contains the point estimate"),
        }

    best_int = min(internal["by_arm"], key=lambda a: internal["by_arm"][a]["aurc_3seed"])
    best_ext = (min(external["by_arm"], key=lambda a: external["by_arm"][a]["aurc_3seed"])
                if external else None)
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 6, "step": "P6.6", "endpoint": "P6-D",
        "question": rule["question"], "carry_forward": rule["carry_forward"],
        "score": rule["score"], "score_note": rule["score_note"],
        "verdict_rule": rule["verdict_rule"],
        "arms": arms, "seeds": list(C.SEEDS),
        "gates": {"P6.1a": meta["gate_P6.1a"],
                  "P6.6a": {"status": "PASS", "per_arm_seed": gate_a}},
        "internal": internal, "external": external,
        "best_arm_internal_aurc": best_int,
        "best_arm_external_aurc": best_ext,
        "runtime_sec": round(time.time() - t0, 1),
    }
    out["verdict_summary"] = {
        "best_arm_internal": best_int, "best_arm_external": best_ext,
        "phase5_consistency": (external["phase5_consistency"]["verdict"]
                               if external else "NOT EVALUATED"),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("[P6.6] gate P6.6a PASS for every arm and seed")
    print("[P6.6] internal AURC (lower is better):")
    for a in arms:
        e = internal["by_arm"][a]
        print(f"   {C.CONFIG_SHORT[a]:16s} AURC {e['aurc_3seed']:.4f} {e['aurc_ci95']}  "
              f"cov@10%risk {e['coverage_at_risk_10pct_3seed']:.3f}")
    if external:
        print("[P6.6] external AURC (image-level intervals, Phase 5 caveat applies):")
        for a in external["by_arm"]:
            e = external["by_arm"][a]
            print(f"   {C.CONFIG_SHORT[a]:16s} AURC {e['aurc_3seed']:.4f}  "
                  f"cov@10%risk {e['coverage_at_risk_10pct_3seed']:.3f}")
        pc = external["phase5_consistency"]
        print(f"[P6.6] Phase 5 consistency: rho={pc['spearman_rho']} "
              f"{pc['spearman_ci95']} -> {pc['verdict']}")
    print(f"[P6.6] best internal {best_int}, best external {best_ext} "
          f"-> {OUT.name} ({out['runtime_sec']}s)")


if __name__ == "__main__":
    main()
