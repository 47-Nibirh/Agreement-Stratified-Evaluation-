"""
Phase 2 / Stage D -- pre-registration.

Freezes the reproduction target, the acceptance rule, the number of seeds, the
interval procedure and the non-reproduction diagnostic order BEFORE any full
training run. Written once; never edited afterwards. The evaluation script
reads its verdict rule from this file, so the criterion cannot be adjusted
after the result is known.

The published reference is taken from the GastroHUN data descriptor
(Sci Data 12:102, 2025; doi:10.1038/s41597-025-04401-5), Scenario A, the
configuration in which ConvNeXt_Tiny is trained AND tested on
complete-agreement labels -- the same condition reproduced here.

Output: reports/phase2_prereg.json
Run:    python src/models/phase2_prereg.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "reports" / "phase2_vram_probe.json"
OUT = ROOT / "reports" / "phase2_prereg.json"

SEEDS = [1, 2, 3]
TIME_BUDGET_HOURS = 6.0     # total training budget across all seeds


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT.name} already exists -- pre-registration is "
                         f"frozen and must not be rewritten")
    probe = json.load(open(PROBE, encoding="utf-8"))

    ep_ft = probe["projected_epoch_sec_finetune"]
    ep_wu = probe["projected_epoch_sec_warmup"]
    budget_per_seed = TIME_BUDGET_HOURS * 3600 / len(SEEDS)
    max_ft = int((budget_per_seed - 10 * ep_wu) // ep_ft)
    max_ft = max(20, min(100, max_ft))

    pre = {
        "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 2,
        "statement": (
            "This document fixes every decision that could otherwise be made "
            "after seeing the result. It is written before the first full "
            "training run and is not edited afterwards."),

        # ---- 1. reproduction target -------------------------------------
        "published_macro_f1": 85.0,
        "published_sd": None,
        "published_source": (
            "Panesso-Ortiz et al., GastroHUN: an Endoscopy Dataset of "
            "Complete Systematic Screening Protocol for the Stomach, "
            "Scientific Data 12:102 (2025), doi:10.1038/s41597-025-04401-5, "
            "Scenario A / Baseline results"),
        "published_quote": (
            "'lighter models like ResNet18 and ConvNeXt_Tiny reach ~85% "
            "F1-score with only ~11M and ~28M parameters respectively'"),
        "published_condition": (
            "ConvNeXt_Tiny trained on the complete-agreement ('All') labels "
            "and tested on the 803-image complete-agreement test set; "
            "3,722 train / 793 validation / 803 test"),
        "published_reference_note": (
            "The descriptor states the ConvNeXt_Tiny figure to two "
            "significant figures in the narrative ('~85%'); the exact "
            "tabular cell is not machine-extractable from the PMC record. "
            "The target is therefore treated as 85.0 with the blueprint's "
            "+/-1.5 point band, which is wider than the rounding uncertainty. "
            "Anchor values reported exactly in the same table are "
            "ConvNeXt_Large 88.25 +/- 0.22 and ResNet152 85.28 +/- 0.27."),

        # ---- 2. acceptance rule -----------------------------------------
        "acceptance_band_points": 1.5,
        "decision_statistic": "mean macro F1 over seeds, test set, percent",
        "verdict_rule": (
            "PASS if |observed seed-mean macro F1 - 85.0| <= 1.5 points; "
            "otherwise FAIL and the diagnostic order below is executed."),

        # ---- 3. estimation procedure ------------------------------------
        "seeds": SEEDS,
        "n_bootstrap": 1000,
        "bootstrap_unit": "patient",
        "bootstrap_rule": (
            "Resample the 58 test patients with replacement, 1000 times, "
            "recomputing macro F1 on each resample; report the 2.5th and "
            "97.5th percentiles. Images are never resampled: Phase 0 "
            "measured per-patient Fleiss kappa 0.7459 +/- 0.1448, so images "
            "within a patient are not independent (blueprint sec.6)."),
        "secondary_interval": (
            "The descriptor's own procedure is also reproduced for "
            "comparability: 100 iterations, each drawing 50% of the "
            "complete-agreement samples within each patient, with the "
            "interval formed as mean +/- t(0.975, B-1) * s/sqrt(B). That "
            "quantity is the standard error of the bootstrap MEAN, not a "
            "95% interval on model performance, which is why the published "
            "margins are near +/-0.2. Both are reported."),

        # ---- 4. declared deviations from blueprint v3.0 ------------------
        "deviations": [
            {
                "id": "DEV-1",
                "item": "Numerical precision",
                "blueprint": "AMP float16 + GradScaler (sec.7)",
                "adopted": ("float32" if not probe["amp_adopted"] else
                            "AMP float16"),
                "evidence": (
                    f"Measured on this device: AMP float16 runs at "
                    f"{probe['amp_vs_fp32_speedup']:.2f}x the throughput of "
                    f"float32 at batch 24. The GTX 1650 is the TU117 Turing "
                    f"die, which ships without tensor cores, so FP16 yields "
                    f"no matrix-multiply acceleration while autocast casting "
                    f"and gradient scaling add overhead."),
                "impact": ("None on the scientific result; precision is a "
                           "throughput decision. FP32 is also the numerically "
                           "safer of the two."),
            },
            {
                "id": "DEV-2",
                "item": "Fine-tuning epoch cap",
                "blueprint": "up to 100 epochs (sec.4)",
                "adopted": f"{max_ft} epochs",
                "evidence": (
                    f"Measured throughput gives a projected {ep_ft:.0f} s per "
                    f"fine-tuning epoch. A {TIME_BUDGET_HOURS:g} h total "
                    f"budget across {len(SEEDS)} seeds admits {max_ft} "
                    f"epochs per seed."),
                "impact": (
                    "Binds only if early stopping has not already fired. The "
                    "stopping criterion (patience 10 on validation macro F1) "
                    "is unchanged, and the realised stop reason is reported "
                    "per seed so the reader can see whether the cap bound."),
            },
            {
                "id": "DEV-3",
                "item": "Number of training runs",
                "blueprint": "not specified",
                "adopted": f"{len(SEEDS)} seeds ({SEEDS})",
                "evidence": (
                    "The published baselines are reported as mean +/- margin "
                    "over repeated evaluation. A single run cannot separate "
                    "reproduction error from run-to-run variance."),
                "impact": "Verdict is taken on the seed mean.",
            },
        ],

        # ---- 5. non-reproduction diagnostic order -----------------------
        "diagnostic_order_if_fail": [
            "1. Normalisation statistics: confirm training-set mean/std were "
            "applied and not ImageNet defaults.",
            "2. Cohort membership: re-verify the 3,722/793/803 complete-"
            "agreement split and the 23-class index.",
            "3. Schedule: confirm the head warm-up ran for 10 epochs at "
            "constant LR and that exactly the top 40% of feature modules "
            "were unfrozen.",
            "4. Augmentation: ablate the augmentation policy to the identity "
            "transform.",
            "5. Optimiser: sweep fine-tuning learning rate over "
            "{3e-5, 1e-4, 3e-4}.",
        ],
        "vram_fallback_ladder": [
            "reduce batch size along the measured ladder",
            "gradient accumulation to hold the effective batch at 32",
            "192x192 input",
            "EfficientNet-B0 backbone",
        ],

        # ---- 6. what would falsify the phase ----------------------------
        "falsification": (
            "If the seed-mean macro F1 falls outside 83.5-86.5 after the "
            "diagnostic order is exhausted, the pipeline is declared not to "
            "reproduce the published baseline and Phases 3-6 do not proceed "
            "on it."),
        "scope_exclusions": [
            "No non-consensus image is trained on or evaluated (Phase 3-4)",
            "No soft targets, label smoothing, MC dropout or ensembles (Phase 4)",
            "No external dataset (Phase 5)",
            "No Grad-CAM or model-vs-human confusion comparison (Phase 6)",
        ],
    }
    OUT.write_text(json.dumps(pre, indent=2), encoding="utf-8")
    print(f"pre-registration frozen -> {OUT.name}")
    print(f"  target {pre['published_macro_f1']} +/- "
          f"{pre['acceptance_band_points']} points")
    print(f"  seeds {SEEDS}, max fine-tune epochs {max_ft}, "
          f"AMP adopted = {probe['amp_adopted']}")


if __name__ == "__main__":
    main()
