"""
P5.17 -- score the adapted arm against the frozen Phase 5 baseline.

Runs the 5B checkpoints over the external eval split and the GastroHUN test
split, then computes every pre-registered contrast with a PAIRED image-level
bootstrap: one resample of eval rows, both arms scored on those same rows, then
differenced.

The baseline is not re-inferred. It is the committed Phase 5 prediction file for
the same arm and seed, restricted to the eval rows, so both sides of every
contrast are scored on identical images.

Outputs
  reports/phase5b_probs_C2_seed{s}.npz, phase5b_probs_int_C2_seed{s}.npz
  reports/phase5b_eval.json
Run:  python src/models/phase5b_eval.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase5_common import (  # noqa: E402
    DATA, GASTRIC, OTHER, REPORTS, ci95, classes, collapse_vector,
    collapsed_pred, binary_macro_f1, external_panel, ext_probs_path,
    int_probs_path, internal_panel)
from phase5_infer import forward_probs, make_loader  # noqa: E402
from phase2_train import build_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CKPT = ROOT / "checkpoints"
PREREG = REPORTS / "phase5b_prereg.json"
SPLIT = DATA / "phase5b_split.csv"
EXT_CACHE = DATA / "phase5_cache_224.npy"
INT_CACHE = DATA / "phase3_cache_224.npy"
NORM = REPORTS / "phase2_norm_stats.json"
OUT = REPORTS / "phase5b_eval.json"

N_BOOT, BOOT_SEED, N_BINS = 1000, 20260726, 10


def ece(conf, correct, n_bins=N_BINS):
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1]), 0, n_bins - 1)
    return float(sum((idx == b).mean() * abs(conf[idx == b].mean() -
                                             correct[idx == b].mean())
                     for b in range(n_bins) if (idx == b).any()))


def paired(fn_a, fn_b, n, n_boot=N_BOOT, seed=BOOT_SEED):
    rng = np.random.default_rng(seed)
    return np.array([fn_a(r) - fn_b(r)
                     for r in (rng.integers(0, n, n) for _ in range(n_boot))])


def verdict(ci, favour_negative=False):
    if ci[0] is None:
        return "NOT COMPUTABLE"
    if ci[0] > 0:
        return "HURTS" if favour_negative else "ADAPTATION HELPS"
    if ci[1] < 0:
        return "ADAPTATION HELPS" if favour_negative else "HURTS"
    return "NOT RESOLVED"


def main() -> int:
    t0 = time.time()
    pre = json.loads(PREREG.read_text(encoding="utf-8"))
    arm, seeds = pre["arm"], pre["seeds"]
    missing = [s for s in seeds if not (CKPT / f"phase5b_{arm}_seed{s}.pt").exists()]
    if missing:
        print(f"[P5.17] missing 5B checkpoints for seeds {missing}")
        return 1

    cls = classes()
    ns = json.loads(NORM.read_text(encoding="utf-8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cv = collapse_vector()

    ext = external_panel()
    split = pd.read_csv(SPLIT)
    assert list(split["path"]) == list(ext["path"])
    eval_rows = np.where(split["role"].to_numpy() == "eval")[0]
    truth = ext["collapsed_label"].to_numpy()[eval_rows]
    gm = np.isin(truth, list(GASTRIC))
    om = truth == OTHER

    inte = internal_panel()
    int_truth_idx = inte["y_true_idx"].to_numpy()
    int_defined = ~pd.isna(inte["y_true_idx"]).to_numpy()

    n_ext_all = len(ext)
    ext_loader = make_loader(EXT_CACHE, n_ext_all, ns)
    int_loader = make_loader(INT_CACHE, len(inte), ns)

    ad_ext, ad_int = {}, {}
    for s in seeds:
        pe = REPORTS / f"phase5b_probs_{arm}_seed{s}.npz"
        pi = REPORTS / f"phase5b_probs_int_{arm}_seed{s}.npz"
        if pe.exists() and pi.exists():
            ad_ext[s], ad_int[s] = np.load(pe)["probs"], np.load(pi)["probs"]
            continue
        blob = torch.load(CKPT / f"phase5b_{arm}_seed{s}.pt", map_location="cpu",
                          weights_only=False)
        model = build_model(len(cls))
        model.load_state_dict(blob["state_dict"])
        model.to(device).eval()
        ad_ext[s] = forward_probs(model, ext_loader, device)
        ad_int[s] = forward_probs(model, int_loader, device)
        np.savez_compressed(pe, probs=ad_ext[s])
        np.savez_compressed(pi, probs=ad_int[s])
        print(f"  seed{s}: adapted inference done", flush=True)
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    # baseline: the committed Phase 5 / Phase 4 files, subset -- never re-inferred
    ba_ext = {s: np.load(ext_probs_path(arm, s))["probs"] for s in seeds}
    ba_int = {s: np.load(int_probs_path(arm, s))["probs"] for s in seeds}

    A = {s: collapsed_pred(ad_ext[s][eval_rows], cv) for s in seeds}
    B = {s: collapsed_pred(ba_ext[s][eval_rows], cv) for s in seeds}

    def f1_of(P):
        return lambda r: 100 * binary_macro_f1(truth[r][np.isin(truth[r], list(GASTRIC))],
                                               P[r][np.isin(truth[r], list(GASTRIC))])

    def rej_of(P):
        return lambda r: float((P[r] == OTHER).mean())

    def mean_over_seeds(f):
        return lambda r: float(np.mean([f(s)(r) for s in seeds]))

    res = {}
    # ---- P5-A ---------------------------------------------------------------
    g_idx = np.where(gm)[0]
    a_pt = float(np.mean([100 * binary_macro_f1(truth[g_idx], A[s][g_idx]) for s in seeds]))
    b_pt = float(np.mean([100 * binary_macro_f1(truth[g_idx], B[s][g_idx]) for s in seeds]))
    d = paired(mean_over_seeds(lambda s: lambda r: 100 * binary_macro_f1(
                   truth[g_idx][r], A[s][g_idx][r])),
               mean_over_seeds(lambda s: lambda r: 100 * binary_macro_f1(
                   truth[g_idx][r], B[s][g_idx][r])), len(g_idx))
    ci = ci95(d)
    res["P5-A"] = {"n": int(len(g_idx)), "adapted": round(a_pt, 3),
                   "baseline": round(b_pt, 3), "delta_points": round(a_pt - b_pt, 3),
                   "ci95": [round(x, 3) for x in ci], "verdict": verdict(ci)}

    # ---- P5-B ---------------------------------------------------------------
    o_idx = np.where(om)[0]
    a_r = float(np.mean([(A[s][o_idx] == OTHER).mean() for s in seeds]))
    b_r = float(np.mean([(B[s][o_idx] == OTHER).mean() for s in seeds]))
    d = paired(mean_over_seeds(lambda s: lambda r: float((A[s][o_idx][r] == OTHER).mean())),
               mean_over_seeds(lambda s: lambda r: float((B[s][o_idx][r] == OTHER).mean())),
               len(o_idx))
    ci = ci95(d)
    res["P5-B"] = {"n": int(len(o_idx)), "adapted": round(a_r, 5),
                   "baseline": round(b_r, 5), "delta": round(a_r - b_r, 5),
                   "ci95": [round(x, 5) for x in ci], "verdict": verdict(ci)}

    # ---- P5-C ---------------------------------------------------------------
    def ece_arm(P, probs):
        c = np.mean([probs[s][eval_rows].max(1) for s in seeds], axis=0)
        corr = np.mean([(P[s] == truth).astype(float) for s in seeds], axis=0)
        return c, corr
    ca, cra = ece_arm(A, ad_ext)
    cb, crb = ece_arm(B, ba_ext)
    a_e, b_e = 100 * ece(ca, cra), 100 * ece(cb, crb)
    n_all = len(eval_rows)
    d = paired(lambda r: 100 * ece(ca[r], cra[r]), lambda r: 100 * ece(cb[r], crb[r]),
               n_all)
    ci = ci95(d)
    res["P5-C"] = {"n": int(n_all), "adapted_ece": round(a_e, 3),
                   "baseline_ece": round(b_e, 3), "delta_ece": round(a_e - b_e, 3),
                   "ci95": [round(x, 3) for x in ci],
                   "verdict": ("BETTER CALIBRATED" if ci[1] is not None and ci[1] < 0
                               else "WORSE CALIBRATED" if ci[0] is not None and ci[0] > 0
                               else "NOT RESOLVED")}

    # ---- forgetting on the source domain ------------------------------------
    di = np.where(int_defined)[0]
    ty = int_truth_idx[di].astype(int)
    from sklearn.metrics import f1_score

    def imf1(P, r):
        return 100 * f1_score(ty[r], P[r], average="macro",
                              labels=list(range(len(cls))), zero_division=0)
    Ai = {s: ad_int[s][di].argmax(1) for s in seeds}
    Bi = {s: ba_int[s][di].argmax(1) for s in seeds}
    a_i = float(np.mean([imf1(Ai[s], np.arange(len(di))) for s in seeds]))
    b_i = float(np.mean([imf1(Bi[s], np.arange(len(di))) for s in seeds]))
    d = paired(mean_over_seeds(lambda s: lambda r: imf1(Ai[s], r)),
               mean_over_seeds(lambda s: lambda r: imf1(Bi[s], r)), len(di))
    ci = ci95(d)
    res["internal_retention"] = {
        "n": int(len(di)), "adapted_macro_f1": round(a_i, 3),
        "baseline_macro_f1": round(b_i, 3), "delta_points": round(a_i - b_i, 3),
        "ci95": [round(x, 3) for x in ci],
        "verdict": ("REGRESSION ON THE SOURCE DOMAIN" if ci[1] is not None and ci[1] < 0
                    else "NO SIGNIFICANT REGRESSION"),
        "note": ("23-way macro F1 on the GastroHUN test split, the metric Phase 4 "
                 "used. The 81 no-majority images have no modal label and are "
                 "excluded, as in Phase 5.")}

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": "5B", "step": "P5.17", "arm": arm, "seeds": seeds,
        "n_eval_split": int(len(eval_rows)),
        "baseline_source": pre["comparator"]["restriction_declared"],
        "interval_procedure": pre["interval_procedure"],
        "split_weakness": pre["split"]["declared_weakness"],
        "results": res,
        "verdict_rules": pre["verdict_rules"],
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.17] wrote {OUT}")
    for k, v in res.items():
        key = ("delta_points" if "delta_points" in v else
               "delta" if "delta" in v else "delta_ece")
        print(f"  {k:20} {v[key]:+.4f} CI {v['ci95']} -> {v['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
