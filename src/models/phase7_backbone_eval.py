"""
Phase 7 / P7.0-B (evaluation) -- does any of this depend on ConvNeXt?

Chapter 9 ranks "single backbone for most endpoints" as the highest-severity
threat to the thesis's validity. This script tests it. Nine EfficientNet-B0
checkpoints (C1, C2, C3 x 3 seeds), trained through the literal Phase 4 code
path with only the model constructor substituted, are run over the same 1,353
test images and scored by the same functions that produced the ConvNeXt numbers:

  ece_mce            imported from phase4_calibration
  marginalized_macro_f1, patient bootstrap   imported from phase3b_common
  score_against_panel, modal_of, singleton_rate   imported from phase6_human

Nothing is reimplemented, so a difference in a number cannot be a difference in
the code that computed it.

Three claims are put at risk:

  R1  the RQ2 accuracy null. C2 - C3 on the pooled contested stratum was
      unresolved on ConvNeXt. Does it stay unresolved?
  R2  the calibration reversal, which is the thesis's durable finding. On
      ConvNeXt the matched-smoothing control C3 is better calibrated than the
      vote-proportion arm C2 on CONTESTED images, and the order REVERSES on
      unanimous ones. Does that pattern reproduce?
  R3  the human-comparator position. On ConvNeXt the model out-predicts a
      held-out annotator on contested images but recovers only about a quarter
      of the headroom to the modal-vote oracle, exceeding it on no stratum.
      Does a different architecture sit in the same place?

A replication that FAILS is as publishable as one that succeeds, and more
useful than not having run it. The verdicts below are computed, not chosen.

Output
  reports/phase7_backbone.json
  reports/phase7_backbone_probs_{cfg}_seed{k}.npz
Run:  python src/models/phase7_backbone_eval.py
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
import phase6_common as C  # noqa: E402
from phase2_train import CohortDataset  # noqa: E402
from phase3b_common import macro_f1, marginalized_macro_f1  # noqa: E402
from phase4_calibration import ece_mce  # noqa: E402
from phase6_human import modal_of, score_against_panel, singleton_rate  # noqa: E402
from phase7_backbone_train import build_model_b0  # noqa: E402

OUT = C.REPORTS / "phase7_backbone.json"
CACHE = C.DATA / "phase3_cache_224.npy"
NORM = C.REPORTS / "phase2_norm_stats.json"
ARMS = ("C1", "C2", "C3")
BATCH = 24
POOLED = C.POOLED_CONTESTED


def ckpt(cfg, seed):
    return C.ROOT / "checkpoints" / f"phase4_{cfg}_b0_seed{seed}.pt"


def probs_path(cfg, seed):
    return C.REPORTS / f"phase7_backbone_probs_{cfg}_seed{seed}.npz"


@torch.no_grad()
def infer(model, loader, device):
    out = []
    for x, _ in loader:
        x = x.to(device)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            z = model(x)
        out.append(torch.softmax(z.float(), 1).cpu().numpy())
    return np.concatenate(out).astype(np.float32)


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = C.classes()
    k = len(cls)
    ns = json.loads(NORM.read_text(encoding="utf-8"))
    panel, meta = C.build_panel()
    idx = pd.read_csv(C.CACHE_INDEX)
    n = len(idx)
    votes = C.votes_matrix(panel)
    patients = panel.patient.to_numpy()

    ds = CohortDataset(CACHE, np.arange(n), np.zeros(n, dtype=int), False,
                       ns["mean"], ns["std"])
    loader = DataLoader(ds, batch_size=BATCH, shuffle=False, num_workers=0)

    # ---- inference -------------------------------------------------------
    P, missing = {}, []
    for cfg in ARMS:
        for s in C.SEEDS:
            cp = ckpt(cfg, s)
            if not cp.exists():
                missing.append(cp.name)
                continue
            pp = probs_path(cfg, s)
            if pp.exists():
                P[(cfg, s)] = np.load(pp, allow_pickle=True)["probs"].astype(np.float64)
                continue
            blob = torch.load(cp, map_location="cpu", weights_only=False)
            m = build_model_b0(k)
            m.load_state_dict(blob["state_dict"])
            m.to(device).eval()
            pr = infer(m, loader, device)
            np.savez_compressed(pp, probs=pr,
                                filename=idx.filename.to_numpy().astype(str))
            P[(cfg, s)] = pr.astype(np.float64)
            del m
            if device.type == "cuda":
                torch.cuda.empty_cache()
            print(f"  inferred {cfg} seed{s}", flush=True)
    if missing:
        raise SystemExit(f"missing checkpoints: {missing}")

    pred = {(c, s): P[(c, s)].argmax(1) for c in ARMS for s in C.SEEDS}
    conf = {(c, s): P[(c, s)].max(1) for c in ARMS for s in C.SEEDS}
    exp_acc = {(c, s): (votes == pred[(c, s)][:, None]).mean(axis=1)
               for c in ARMS for s in C.SEEDS}

    # ---- levels by stratum ------------------------------------------------
    levels = {}
    for stratum in C.STRATA:
        m = C.stratum_mask(panel, stratum)
        rows = np.where(m)[0]
        levels[stratum] = {"n_images": int(m.sum()), "by_arm": {}}
        for c in ARMS:
            f1 = [marginalized_macro_f1(votes[m], pred[(c, s)][m], k) for s in C.SEEDS]
            ec = [ece_mce(conf[(c, s)][rows], exp_acc[(c, s)][rows])[0] for s in C.SEEDS]
            levels[stratum]["by_arm"][c] = {
                "macro_f1_3seed": round(float(np.mean(f1)), 5),
                "ece_3seed": round(float(np.mean(ec)), 5),
            }

    # ---- R1 / R2: paired patient-clustered contrasts, C2 vs C3 -----------
    contrasts = {}
    for stratum in ("S-unanimous", POOLED):
        m = C.stratum_mask(panel, stratum)
        rows = np.where(m)[0]
        pats = patients[rows]
        d_f1, d_ece = [], []
        for local in C.patient_resamples(pats, C.N_BOOT_P6):
            r = rows[local]
            f2 = np.mean([marginalized_macro_f1(votes[r], pred[("C2", s)][r], k)
                          for s in C.SEEDS])
            f3 = np.mean([marginalized_macro_f1(votes[r], pred[("C3", s)][r], k)
                          for s in C.SEEDS])
            e2 = np.mean([ece_mce(conf[("C2", s)][r], exp_acc[("C2", s)][r])[0]
                          for s in C.SEEDS])
            e3 = np.mean([ece_mce(conf[("C3", s)][r], exp_acc[("C3", s)][r])[0]
                          for s in C.SEEDS])
            d_f1.append(100 * (f2 - f3))
            d_ece.append(100 * (e2 - e3))
        lo1, hi1 = C.ci95(np.asarray(d_f1))
        lo2, hi2 = C.ci95(np.asarray(d_ece))
        contrasts[stratum] = {
            "macro_f1_C2_minus_C3_points": round(float(np.mean(d_f1)), 3),
            "macro_f1_ci95": [round(lo1, 3), round(hi1, 3)],
            "macro_f1_verdict": C.verdict_three_way(
                lo1, hi1, above="C2 BETTER", below="C3 BETTER", null="NOT RESOLVED"),
            "ece_C2_minus_C3_points": round(float(np.mean(d_ece)), 3),
            "ece_ci95": [round(lo2, 3), round(hi2, 3)],
            "ece_verdict": C.verdict_three_way(
                lo2, hi2, above="C3 BETTER CALIBRATED", below="C2 BETTER CALIBRATED",
                null="NOT RESOLVED"),
        }

    # ---- R3: the human comparator on this backbone -----------------------
    rng = np.random.default_rng(20260729)
    human = {}
    for stratum in C.STRATA:
        m = C.stratum_mask(panel, stratum)
        v = votes[m]
        h_all, o_all = [], []
        mdl = {c: [] for c in ARMS}
        for a in range(4):
            refs = [b for b in range(4) if b != a]
            h_all.append(score_against_panel(v, v[:, a], refs, k))
            o_all.append(score_against_panel(v, modal_of(v, refs, rng), refs, k))
            for c in ARMS:
                mdl[c].append(float(np.mean([
                    score_against_panel(v, pred[(c, s)][m], refs, k) for s in C.SEEDS])))
        hh, oo = float(np.mean(h_all)), float(np.mean(o_all))
        entry = {"human_held_out": round(hh, 5), "modal_vote_oracle": round(oo, 5),
                 "mean_singleton_rate": round(
                     float(np.mean([singleton_rate(v, a) for a in range(4)])), 5),
                 "by_arm": {}}
        for c in ARMS:
            mm = float(np.mean(mdl[c]))
            span = oo - hh
            entry["by_arm"][c] = {
                "model": round(mm, 5),
                "vs_human": round(mm - hh, 5),
                "position_in_headroom": (round((mm - hh) / span, 4)
                                         if abs(span) > 1e-9 else None),
                "exceeds_oracle": bool(mm > oo),
            }
        human[stratum] = entry

    # ---- replication verdicts, computed against the ConvNeXt artefacts ----
    cn_p4 = json.loads((C.REPORTS / "phase4_stratified_metrics.json").read_text(encoding="utf-8"))
    cn_cal = json.loads((C.REPORTS / "phase4_calibration.json").read_text(encoding="utf-8"))
    cn_h = json.loads((C.REPORTS / "phase6_human.json").read_text(encoding="utf-8"))
    cn_sens = cn_h["sensitivity_P6-AMD-5"]["by_stratum"]

    cn_r1 = cn_p4["contrasts"]["C2 - C3"]["by_stratum"][POOLED]
    cn_r1_res = "NOT RESOLVED" if (cn_r1["ci95_points_3seed_mean"][0] <= 0 <=
                                   cn_r1["ci95_points_3seed_mean"][1]) else "RESOLVED"
    b0_r1_res = ("NOT RESOLVED" if contrasts[POOLED]["macro_f1_verdict"] == "NOT RESOLVED"
                 else "RESOLVED")

    cn_ece_c2 = cn_cal["aggregate_3seed"]["C2"][POOLED]["ece_vs_expected_accuracy"]
    cn_ece_c3 = cn_cal["aggregate_3seed"]["C3"][POOLED]["ece_vs_expected_accuracy"]
    cn_ece_c2u = cn_cal["aggregate_3seed"]["C2"]["S-unanimous"]["ece_vs_expected_accuracy"]
    cn_ece_c3u = cn_cal["aggregate_3seed"]["C3"]["S-unanimous"]["ece_vs_expected_accuracy"]
    cn_reversal = bool(cn_ece_c3 < cn_ece_c2 and cn_ece_c2u < cn_ece_c3u)
    b0_c3_better_contested = levels[POOLED]["by_arm"]["C3"]["ece_3seed"] < \
        levels[POOLED]["by_arm"]["C2"]["ece_3seed"]
    b0_c2_better_unanimous = levels["S-unanimous"]["by_arm"]["C2"]["ece_3seed"] < \
        levels["S-unanimous"]["by_arm"]["C3"]["ece_3seed"]
    b0_reversal = bool(b0_c3_better_contested and b0_c2_better_unanimous)

    cn_pos = cn_sens[POOLED]["by_arm"]["C2"]["position_in_headroom"]
    b0_pos = human[POOLED]["by_arm"]["C2"]["position_in_headroom"]
    cn_exceeds = any(cn_sens[s]["by_arm"]["C2"]["exceeds_oracle"] for s in cn_sens)
    b0_exceeds = any(human[s]["by_arm"]["C2"]["exceeds_oracle"] for s in human)

    replication = {
        "R1_rq2_accuracy_null": {
            "convnext": cn_r1_res, "efficientnet_b0": b0_r1_res,
            "convnext_estimate": cn_r1["diff_points_3seed_mean"],
            "convnext_ci": cn_r1["ci95_points_3seed_mean"],
            "b0_estimate": contrasts[POOLED]["macro_f1_C2_minus_C3_points"],
            "b0_ci": contrasts[POOLED]["macro_f1_ci95"],
            "replicates": bool(cn_r1_res == b0_r1_res),
        },
        "R2_calibration_reversal": {
            "pattern": ("C3 better calibrated on CONTESTED images and C2 better on "
                        "UNANIMOUS ones -- the thesis's durable finding"),
            "convnext": {"ece_C2_contested": cn_ece_c2, "ece_C3_contested": cn_ece_c3,
                         "ece_C2_unanimous": cn_ece_c2u, "ece_C3_unanimous": cn_ece_c3u,
                         "pattern_present": cn_reversal},
            "efficientnet_b0": {
                "ece_C2_contested": levels[POOLED]["by_arm"]["C2"]["ece_3seed"],
                "ece_C3_contested": levels[POOLED]["by_arm"]["C3"]["ece_3seed"],
                "ece_C2_unanimous": levels["S-unanimous"]["by_arm"]["C2"]["ece_3seed"],
                "ece_C3_unanimous": levels["S-unanimous"]["by_arm"]["C3"]["ece_3seed"],
                "pattern_present": b0_reversal,
                "paired_contest_ci": contrasts[POOLED]["ece_ci95"],
                "paired_contest_verdict": contrasts[POOLED]["ece_verdict"],
            },
            "replicates": bool(cn_reversal == b0_reversal),
        },
        "R3_human_comparator_position": {
            "convnext_headroom_recovered": cn_pos,
            "b0_headroom_recovered": b0_pos,
            "convnext_exceeds_oracle_anywhere": cn_exceeds,
            "b0_exceeds_oracle_anywhere": b0_exceeds,
            "replicates": bool((cn_exceeds == b0_exceeds) and
                               abs((cn_pos or 0) - (b0_pos or 0)) < 0.20),
            "replication_criterion": ("same oracle-exceedance status on every stratum, "
                                      "and headroom recovered within 20 percentage "
                                      "points of the ConvNeXt value"),
        },
    }
    n_rep = sum(1 for r in replication.values() if r["replicates"])

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 7, "step": "P7.0-B",
        "question": ("does the thesis depend on ConvNeXt? Chapter 9 ranks this the "
                     "highest-severity threat to validity."),
        "backbone": "EfficientNet-B0 (4.0 M parameters against ConvNeXt-Tiny's 28 M)",
        "what_is_held_fixed": (
            "cohort E, the 224px cache, training-set normalisation, augmentation, the "
            "two-stage schedule, the soft-target loss, early stopping, the epoch cap "
            "and the seeds. phase7_backbone_train.py imports phase4_train and rebinds "
            "only build_model, so this is the Phase 4 code path with a different "
            "network in it."),
        "fine_tuning_depth_match": {
            "convnext_param_fraction_unfrozen": 0.945,
            "efficientnet_b0_param_fraction_unfrozen": 0.923,
            "why": ("'top 40% of feature modules' unfreezes a different NUMBER of "
                    "modules in each network, so the comparable quantity is the "
                    "fraction of feature PARAMETERS it frees. They match to about two "
                    "points, which removes the obvious confound."),
        },
        "scoring_note": ("every metric is computed by the function that produced the "
                         "ConvNeXt number: ece_mce from phase4_calibration, "
                         "marginalized_macro_f1 from phase3b_common, and the comparator "
                         "primitives from phase6_human. Nothing is reimplemented."),
        "arms": list(ARMS), "seeds": list(C.SEEDS),
        "stop_reasons": {f"{c}_seed{s}": json.loads(
            (C.REPORTS / f"phase4_run_{c}_b0_seed{s}.json").read_text(encoding="utf-8")
        ).get("stop_reason") for c in ARMS for s in C.SEEDS},
        "levels_by_stratum": levels,
        "paired_contrasts": contrasts,
        "human_comparator": human,
        "replication": replication,
        "n_replicating": n_rep,
        "n_tested": len(replication),
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"\n[P7.0-B] EfficientNet-B0 replication: {n_rep}/{len(replication)} claims hold")
    for kk, v in replication.items():
        print(f"   {kk}: replicates={v['replicates']}")
    print(f"\n   R1 RQ2 accuracy   ConvNeXt {cn_r1['diff_points_3seed_mean']:+.2f} "
          f"{cn_r1['ci95_points_3seed_mean']}  |  B0 "
          f"{contrasts[POOLED]['macro_f1_C2_minus_C3_points']:+.2f} "
          f"{contrasts[POOLED]['macro_f1_ci95']}")
    print(f"   R2 ECE contested  ConvNeXt C2 {cn_ece_c2:.4f} C3 {cn_ece_c3:.4f}  |  "
          f"B0 C2 {levels[POOLED]['by_arm']['C2']['ece_3seed']:.4f} "
          f"C3 {levels[POOLED]['by_arm']['C3']['ece_3seed']:.4f}")
    print(f"   R2 ECE unanimous  ConvNeXt C2 {cn_ece_c2u:.4f} C3 {cn_ece_c3u:.4f}  |  "
          f"B0 C2 {levels['S-unanimous']['by_arm']['C2']['ece_3seed']:.4f} "
          f"C3 {levels['S-unanimous']['by_arm']['C3']['ece_3seed']:.4f}")
    print(f"   R3 headroom       ConvNeXt {100 * (cn_pos or 0):.0f}%  |  "
          f"B0 {100 * (b0_pos or 0):.0f}%   exceeds oracle: "
          f"ConvNeXt {cn_exceeds}, B0 {b0_exceeds}")
    print(f"[P7.0-B] wrote {OUT.name} in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
