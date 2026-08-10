"""
Phase 3 / Stage C -- agreement-stratified evaluation (RQ1).

Runs the 3 FROZEN Phase 2 checkpoints (no retraining, no reselection) on the
full 1,353-image official test split and reports performance separately for
each agreement stratum defined in phase3_data.py.

Metric definitions (pre-registered, blueprint v3.1 sec.4 Phase 3 / sec.14):

  Single-label strata (S-unanimous, S-majority; S-plurality as a secondary,
  clearly-flagged pseudo-label reading):
    macro F1 / precision / recall / accuracy against that stratum's ground
    truth or pseudo-label, exactly as in phase2_eval.py.

  Annotator-marginalized macro F1 (primary cross-stratum metric, defined for
  EVERY stratum including S-tied / S-dispersed, where no single ground truth
  exists):
    For each of the 4 annotator columns, treat that annotator's label as
    "ground truth" for every image in the stratum and compute macro F1 in
    the ordinary way; average the 4 resulting scores. At the S-unanimous
    limit all 4 annotator columns are identical, so this reduces exactly to
    plain macro F1 -- the metric is continuous across the tier boundary by
    construction, which is what makes the four strata comparable on one
    scale for the monotonicity test.

  Expected accuracy / any-annotator hit rate (descriptive, all strata):
    expected accuracy = mean over annotators of 1/4 x 1[pred == that label]
    any-hit rate       = 1[pred is in the set of labels actually given]

  S-tied and S-dispersed are pooled into S-no-majority for every primary
  statistic (n=8 for S-dispersed alone is not bootstrap-stable); both are
  still reported unpooled as an explicitly exploratory breakdown.

Consistency gate (P3.3): the S-unanimous-stratum predictions from this script
must reproduce reports/phase2_predictions_seed{k}.csv exactly (same images,
same frozen weights, same preprocessing) -- this is the check that the new
data path is wired correctly, not a new result.

Outputs
  reports/phase3_predictions_seed{1,2,3}.csv
  reports/phase3_stratified_metrics.json
Run:  python src/models/phase3_eval.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
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
PHASE2_PRED_PATTERN = "phase2_predictions_seed{}.csv"

N_BOOT = 1000
BOOT_SEED = 20260726
ANN_COLS = ["vote_0", "vote_1", "vote_2", "vote_3"]

TIER_ORDER = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]
ARCH_GAP_BENCHMARK = 3.25  # ConvNeXt-Large 88.25 - ConvNeXt-Tiny ~85.0, descriptor sec.2.7


def annotator_marginalized_f1(votes: np.ndarray, pred: np.ndarray, cls_to_idx: dict) -> tuple:
    """votes: (n,4) array of label strings. pred: (n,) int class indices."""
    scores = []
    for a in range(4):
        y = np.array([cls_to_idx[v] for v in votes[:, a]])
        labels = list(range(len(cls_to_idx)))
        scores.append(f1_score(y, pred, average="macro", labels=labels, zero_division=0))
    return float(np.mean(scores)), float(np.std(scores, ddof=1)), scores


def expected_accuracy_and_hit(votes: np.ndarray, pred_label: np.ndarray) -> tuple:
    pred_label = np.asarray(pred_label, dtype=object)
    match = (votes == pred_label[:, None])
    expected_acc = match.mean(axis=1)
    any_hit = match.any(axis=1)
    return float(expected_acc.mean()), float(any_hit.mean())


def bootstrap_metric(df: pd.DataFrame, metric_fn, n_boot: int = N_BOOT, seed: int = BOOT_SEED):
    rng = np.random.default_rng(seed)
    pats = df["patient"].unique()
    by_pat = {p: g for p, g in df.groupby("patient")}
    vals = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(pats, size=len(pats), replace=True)
        sub = pd.concat([by_pat[p] for p in pick], ignore_index=True)
        vals[b] = metric_fn(sub)
    return vals


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    inv = {v: k for k, v in cls.items()}
    n_classes = len(cls)
    ns = json.load(open(NORM, encoding="utf-8"))

    idx = pd.read_csv(INDEX)
    n = len(idx)
    rows = np.arange(n)
    dummy_y = np.zeros(n, dtype=int)
    ds = CohortDataset(CACHE, rows, dummy_y, False, ns["mean"], ns["std"])
    loader = DataLoader(ds, batch_size=24, shuffle=False, num_workers=0)

    ckpts = sorted(CKPT.glob("phase2_convnext_tiny_seed*.pt"))
    if not ckpts:
        raise SystemExit("no checkpoints found; Phase 2 must be run first")

    all_seed_dfs = {}
    for cp in ckpts:
        blob = torch.load(cp, map_location="cpu", weights_only=False)
        seed = int(blob["seed"])
        model = build_model(n_classes)
        model.load_state_dict(blob["state_dict"])
        model.to(device).eval()

        probs = []
        with torch.no_grad():
            for x, _ in loader:
                x = x.to(device)
                with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                    out = model(x)
                probs.append(torch.softmax(out.float(), 1).cpu().numpy())
        prob = np.concatenate(probs)
        pred = prob.argmax(1)

        pdf = idx.copy()
        pdf["y_pred"] = pred
        pdf["label_pred"] = [inv[i] for i in pred]
        pdf["confidence"] = prob.max(1)
        pdf.to_csv(REPORTS / f"phase3_predictions_seed{seed}.csv", index=False)
        all_seed_dfs[seed] = pdf
        print(f"seed {seed}: inference on {len(pdf)} images done", flush=True)

    # ---- P3.3 consistency gate: S-unanimous subset must match Phase 2 -----
    consistency = {}
    for seed, pdf in all_seed_dfs.items():
        p2 = pd.read_csv(REPORTS / PHASE2_PRED_PATTERN.format(seed))
        merged = pdf[pdf.tier == "S-unanimous"].merge(
            p2[["filename", "y_pred"]], on="filename", suffixes=("_p3", "_p2"))
        if len(merged) != 803:
            raise SystemExit(f"seed {seed}: S-unanimous join produced {len(merged)} rows, expected 803")
        mismatches = int((merged.y_pred_p3 != merged.y_pred_p2).sum())
        consistency[seed] = {"n_compared": len(merged), "n_mismatch": mismatches}
        if mismatches:
            raise SystemExit(f"CONSISTENCY GATE FAILED seed {seed}: {mismatches} predictions differ from Phase 2")
        print(f"seed {seed}: consistency gate PASS (803/803 match Phase 2)", flush=True)

    # ---- per-seed, per-stratum metrics -------------------------------------
    per_seed_stratum = {}
    for seed, pdf in all_seed_dfs.items():
        pdf = pdf.copy()
        votes = pdf[ANN_COLS].to_numpy(dtype=object)
        stratum_results = {}
        for tier_col in ["tier", "tier_pooled"]:
            for tier_name, g in pdf.groupby(tier_col):
                key = tier_name
                if key in stratum_results:
                    continue
                gi = g.index.to_numpy()
                v = votes[gi]
                pred = g["y_pred"].to_numpy()
                pred_label = g["label_pred"].to_numpy(dtype=object)

                marg_mean, marg_sd, marg_by_ann = annotator_marginalized_f1(v, pred, cls)
                exp_acc, hit = expected_accuracy_and_hit(v, pred_label)

                entry = {
                    "n_images": int(len(g)),
                    "n_patients": int(g["patient"].nunique()),
                    "annotator_marginalized_macro_f1": round(marg_mean, 5),
                    "annotator_marginalized_macro_f1_sd_across_annotators": round(marg_sd, 5),
                    "per_annotator_macro_f1": [round(s, 5) for s in marg_by_ann],
                    "expected_accuracy": round(exp_acc, 5),
                    "any_annotator_hit_rate": round(hit, 5),
                }
                if g["pseudo_label"].notna().all():
                    y_true = g["pseudo_label"].map(cls).to_numpy()
                    labels = list(range(n_classes))
                    entry["single_label_macro_f1"] = round(
                        float(f1_score(y_true, pred, average="macro", labels=labels, zero_division=0)), 5)
                    entry["single_label_accuracy"] = round(float(accuracy_score(y_true, pred)), 5)
                    entry["single_label_macro_precision"] = round(
                        float(precision_score(y_true, pred, average="macro", labels=labels, zero_division=0)), 5)
                    entry["single_label_macro_recall"] = round(
                        float(recall_score(y_true, pred, average="macro", labels=labels, zero_division=0)), 5)

                def marg_metric_fn(sub, cls=cls):
                    vv = sub[ANN_COLS].to_numpy(dtype=object)
                    pp = sub["y_pred"].to_numpy()
                    m, _, _ = annotator_marginalized_f1(vv, pp, cls)
                    return m

                boot = bootstrap_metric(g.reset_index(drop=True), marg_metric_fn)
                entry["annotator_marginalized_macro_f1_ci95"] = [
                    round(float(np.percentile(boot, 2.5)), 5),
                    round(float(np.percentile(boot, 97.5)), 5)]
                entry["annotator_marginalized_macro_f1_boot_sd"] = round(float(boot.std(ddof=1)), 5)
                stratum_results[key] = entry
        per_seed_stratum[seed] = stratum_results

    # ---- 3-seed aggregate per stratum (pooled tiers only, primary table) ---
    seeds = sorted(per_seed_stratum)
    aggregate = {}
    for tier in TIER_ORDER:
        vals = np.array([per_seed_stratum[s][tier]["annotator_marginalized_macro_f1"] for s in seeds])
        aggregate[tier] = {
            "n_images": per_seed_stratum[seeds[0]][tier]["n_images"],
            "n_patients": per_seed_stratum[seeds[0]][tier]["n_patients"],
            "annotator_marginalized_macro_f1_mean_3seed": round(float(vals.mean()), 5),
            "annotator_marginalized_macro_f1_sd_3seed": round(float(vals.std(ddof=1)), 5),
            "expected_accuracy_mean_3seed": round(float(np.mean(
                [per_seed_stratum[s][tier]["expected_accuracy"] for s in seeds])), 5),
            "any_annotator_hit_rate_mean_3seed": round(float(np.mean(
                [per_seed_stratum[s][tier]["any_annotator_hit_rate"] for s in seeds])), 5),
        }
        if "single_label_macro_f1" in per_seed_stratum[seeds[0]][tier]:
            aggregate[tier]["single_label_macro_f1_mean_3seed"] = round(float(np.mean(
                [per_seed_stratum[s][tier]["single_label_macro_f1"] for s in seeds])), 5)

    # ---- RQ1 monotonicity + gap test (on the 3-seed mean, primary metric) --
    ordered_vals = [aggregate[t]["annotator_marginalized_macro_f1_mean_3seed"] for t in TIER_ORDER]
    rho, pval = spearmanr(range(len(TIER_ORDER)), ordered_vals)
    gap_points = 100 * (ordered_vals[0] - ordered_vals[-1])
    monotonic = all(ordered_vals[i] >= ordered_vals[i + 1] for i in range(len(ordered_vals) - 1))

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "seeds": seeds,
        "n_test_images": int(n),
        "consistency_gate": consistency,
        "per_seed_stratum": per_seed_stratum,
        "aggregate_3seed": aggregate,
        "rq1": {
            "tier_order": TIER_ORDER,
            "annotator_marginalized_macro_f1_by_tier": {t: v for t, v in zip(TIER_ORDER, ordered_vals)},
            "spearman_rho": round(float(rho), 5),
            "spearman_p": round(float(pval), 5),
            "strictly_monotonic_non_increasing": bool(monotonic),
            "gap_S_unanimous_minus_S_no_majority_points": round(gap_points, 3),
            "architecture_gap_benchmark_points": ARCH_GAP_BENCHMARK,
            "gap_exceeds_architecture_benchmark": bool(gap_points > ARCH_GAP_BENCHMARK),
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase3_stratified_metrics.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    print("\n--- RQ1 summary (annotator-marginalized macro F1, 3-seed mean) ---")
    for t, v in zip(TIER_ORDER, ordered_vals):
        print(f"  {t:16s} n={aggregate[t]['n_images']:4d}  F1={100*v:.2f}")
    print(f"  Spearman rho={rho:.3f} (p={pval:.4f}), monotonic non-increasing={monotonic}")
    print(f"  gap S-unanimous - S-no-majority = {gap_points:.2f} pts "
          f"(architecture benchmark {ARCH_GAP_BENCHMARK} pts) "
          f"-> exceeds benchmark: {gap_points > ARCH_GAP_BENCHMARK}")


if __name__ == "__main__":
    main()
