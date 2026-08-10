"""
Phase 4 / Stage D -- pre-registration.

Freezes every decision that could otherwise be made after seeing a result:
the five configurations and their exact target constructions, the two
hyper-parameters those constructions need (epsilon for C3, lambda for C4), the
model-selection criterion, the seeds, the epoch cap, the primary and secondary
endpoints for RQ2/RQ3/RQ4, the comparison and interval procedure, and the
verdict rule for each research question. Written before the first Phase 4
training run and not edited afterwards; the evaluation scripts read their
verdict rules from this file, so no criterion can be adjusted once the numbers
are known.

The two hyper-parameters are DERIVED, not chosen:

  epsilon (C3).  The C3 control exists so that a C2 gain cannot be attributed
    to ordinary regularisation. That only works if the two arms soften the
    target by the same amount. C2 moves probability mass off the modal label
    only on 3/4 images, and moves 0.25 when it does; averaged over the
    training cohort that is a fixed, measurable quantity. epsilon is set so
    that uniform label smoothing displaces exactly the same expected mass:
        E[1 - t_modal] under C2  =  epsilon * (1 - 1/K)
    Mass, not entropy, is the matched quantity because mass displacement is
    what scales the gradient contributed by the softening term; the
    entropy-matched value is computed and reported alongside so the reader can
    see how much the choice of matching criterion matters.

  lambda (C4).  Fixed a priori at unit weight -- the structured penalty and
    the cross-entropy enter the objective with equal coefficient. No sweep was
    run and no alternative value was trained, so lambda is not a researcher
    degree of freedom that could have been exercised after seeing results. The
    consequence (an unswept lambda is a weak test of RQ4's *best* achievable
    effect, though a valid test of the effect at unit weight) is recorded as a
    declared limitation, not glossed over.

Output: reports/phase4_prereg.json
Run:    python src/models/phase4_prereg.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "data" / "phase4_cache_index.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
COHORT = ROOT / "reports" / "phase4_cohort.json"
PROBE = ROOT / "reports" / "phase4_probe.json"
PROBE2 = ROOT / "reports" / "phase2_vram_probe.json"
DISTJ = ROOT / "reports" / "phase4_distance_matrix.json"
OUT = ROOT / "reports" / "phase4_prereg.json"

SEEDS = [1, 2, 3]
TIME_BUDGET_HOURS = 18.0        # total training budget across all Phase 4 runs
N_RUNS = 12                     # 4 configurations x 3 seeds
WARMUP_EPOCHS = 10
LAMBDA = 1.0
ANN_Y = ["vote_0_y", "vote_1_y", "vote_2_y", "vote_3_y"]


def smoothing_entropy(eps: float, k: int) -> float:
    p = np.full(k, eps / k)
    p[0] += 1.0 - eps
    return float(-(p * np.log(np.clip(p, 1e-300, 1))).sum())


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT.name} already exists -- the pre-registration is "
                         f"frozen and must not be rewritten")

    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    k = len(cls)
    idx = pd.read_csv(INDEX)
    tr = idx[idx.set_type == "Train"]
    coh = json.load(open(COHORT, encoding="utf-8"))
    probe = json.load(open(PROBE, encoding="utf-8"))
    probe2 = json.load(open(PROBE2, encoding="utf-8"))
    distj = json.load(open(DISTJ, encoding="utf-8"))

    # ---- C2 target statistics, measured on the training cohort -------------
    n = len(tr)
    V = tr[ANN_Y].to_numpy()
    T = np.zeros((n, k))
    for a in range(V.shape[1]):
        T[np.arange(n), V[:, a]] += 0.25
    modal_mass = T[np.arange(n), tr["y"].to_numpy()]
    mass_displaced = float((1.0 - modal_mass).mean())
    c2_entropy = float(-(T * np.log(np.clip(T, 1e-300, 1))).sum(1).mean())

    # ---- epsilon: mass-matched (primary) and entropy-matched (reference) ---
    eps_mass = mass_displaced / (1.0 - 1.0 / k)
    eps_entropy = brentq(lambda e: smoothing_entropy(e, k) - c2_entropy,
                         1e-9, 0.99, xtol=1e-12)

    # ---- epoch cap from the measured cost and the declared budget ----------
    ep_ft = probe["measured_finetune_epoch_sec"]
    ep_wu = probe["measured_warmup_epoch_sec"]
    budget_per_run = TIME_BUDGET_HOURS * 3600 / N_RUNS
    max_ft = int((budget_per_run - WARMUP_EPOCHS * ep_wu) // ep_ft)
    max_ft = max(20, min(100, max_ft))

    pre = {
        "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 4,
        "title": "Soft-label and uncertainty training (RQ2, RQ3, RQ4)",
        "statement": (
            "This document fixes every decision that could otherwise be made "
            "after seeing the result. It is written after the cohort, the cache, "
            "the distance matrix and the timing probe exist, and before the first "
            "Phase 4 training run. It is not edited afterwards."),
        "governing_blueprint": "THESIS_RESEARCH_BLUEPRINT.md v3.3, sec.4 PHASE 4",

        # ---- 1. cohort ---------------------------------------------------
        "cohort": {
            "definition": coh["cohort_definition"],
            "n_train": coh["by_split"]["Train"],
            "n_validation": coh["by_split"]["Validation"],
            "fraction_contested_train": coh["fraction_contested_by_split"]["Train"],
            "held_constant_across": ["C1", "C2", "C3", "C4"],
            "rationale": (
                "A hard label is undefined on the 2-2 and 1-1-1-1 tiers, so the C3 "
                "control cannot be scored on them. Holding the cohort at the "
                "majority-or-better set makes C1 vs C2 vs C3 vs C4 a pure "
                "target-construction contrast; C0 vs C1 is the separate, and "
                "separately reported, cohort contrast."),
            "excluded": coh["excluded_trainval_images"],
        },

        # ---- 2. configurations -------------------------------------------
        "configurations": {
            "C0": {
                "target": "hard unanimous label, 4/4 cohort only",
                "cohort": "Phase 2 consensus cohort (3,722 / 793)",
                "role": "reference arm",
                "retrained_in_phase_4": False,
                "source": "checkpoints/phase2_convnext_tiny_seed{1,2,3}.pt",
                "note": ("reused unchanged. Its model-selection criterion was macro "
                         "F1 on the 793-image unanimous validation subset, not the "
                         "1,103-image extended one used by C1-C4; this asymmetry is "
                         "unavoidable because C0's cohort does not contain the "
                         "contested validation images, and it is the reason C1, not "
                         "C0, is the control for the target-construction contrasts."),
            },
            "C1": {"target": "one-hot at the majority label", "cohort": "E",
                   "role": "isolates the effect of adding the 3/4 contested images"},
            "C2": {"target": "vote proportions across the 4 annotators", "cohort": "E",
                   "role": "RQ2 treatment arm"},
            "C3": {"target": "one-hot at the majority label + uniform label smoothing",
                   "cohort": "E",
                   "role": "control: the soft-target gain must exceed generic regularisation",
                   "label_smoothing_epsilon": round(float(eps_mass), 6),
                   "epsilon_derivation": "mass-matched to C2 (see below)",
                   "epsilon_entropy_matched_reference": round(float(eps_entropy), 6),
                   "epsilon_conventional_reference": 0.1},
            "C4": {"target": "vote proportions + anatomical structured penalty",
                   "cohort": "E", "role": "RQ4 treatment arm",
                   "structure_penalty_lambda": LAMBDA,
                   "penalty": "lambda * sum_i sum_j t_i q_j d(i,j), q = softmax(z)",
                   "distance_matrix": "reports/phase4_distance_matrix.json",
                   "lambda_derivation": (
                       "fixed a priori at unit weight; no sweep was run. At "
                       f"initialisation the cross-entropy is ln(23) = "
                       f"{np.log(k):.3f} nats and the mean off-diagonal distance is "
                       f"{distj['mean_offdiagonal_distance_all_classes']}, so the "
                       f"penalty contributes roughly "
                       f"{100 * distj['mean_offdiagonal_distance_all_classes'] / (np.log(k) + distj['mean_offdiagonal_distance_all_classes']):.0f}% "
                       f"of the initial objective.")},
        },
        "epsilon_derivation_detail": {
            "criterion": "equal expected probability mass displaced from the modal label",
            "c2_mean_mass_displaced": round(mass_displaced, 6),
            "c2_mean_target_entropy_nats": round(c2_entropy, 6),
            "formula": "epsilon = E[1 - t_modal] / (1 - 1/K)",
            "K": k,
            "epsilon_mass_matched": round(float(eps_mass), 6),
            "epsilon_entropy_matched": round(float(eps_entropy), 6),
            "why_mass_not_entropy": (
                "the gradient of the soft-target cross-entropy with respect to the "
                "logits is (q - t), so the perturbation C2 introduces relative to a "
                "one-hot target is exactly the displaced mass; matching that makes "
                "the two arms comparable in the quantity that actually drives "
                "learning. Entropy matching gives a markedly smaller epsilon "
                f"({eps_entropy:.4f} vs {eps_mass:.4f}) and is reported so the "
                "sensitivity of the control to this choice is visible."),
            "note": ("both derived values are computed from the training cohort's "
                     "vote matrix, not chosen; the conventional epsilon = 0.1 is "
                     "recorded only as an external reference point and was not run."),
        },

        # ---- 3. training protocol (inherited, not re-decided) -------------
        "training_protocol": {
            "inherited_from": "src/models/phase2_train.py, unchanged",
            "backbone": "ConvNeXt-Tiny, ImageNet-1k pretrained, 23-way head",
            "input": "224x224, Lanczos, Phase 2 TRAINING-SET normalisation statistics",
            "normalisation_reused_deliberately": (
                "the Phase 2 channel statistics are reused rather than recomputed on "
                "the extended cohort, so that C0 and C1-C4 see identical pixels; "
                "recomputing them would make every C-vs-C0 difference partly a "
                "preprocessing difference"),
            "augmentation": "RandomResizedCrop(0.85-1.0) + ColorJitter, no flips "
                            "(a flip changes the anatomical wall and would corrupt the label)",
            "schedule": "10-epoch head warm-up at constant LR 1e-3, then fine-tune the "
                        "top 40% of feature modules at 1e-4 with cosine annealing",
            "patience": 10,
            "effective_batch": 32,
            "precision": "float32, channels_last (Phase 2 DEV-1, measured)",
            "loss": ("soft-target cross-entropy -sum_j t_j log softmax(z)_j for every "
                     "arm; asserted bit-equal to nn.CrossEntropyLoss on one-hot "
                     "targets at import time, so the hard-label arms are not "
                     "disadvantaged by a different code path"),
        },
        "seeds": SEEDS,
        "batch_size": probe2["chosen_batch"],
        "epoch_cap_finetune": max_ft,
        "epoch_cap_derivation": {
            "measured_warmup_epoch_sec": ep_wu,
            "measured_finetune_epoch_sec": ep_ft,
            "measured_on": "the extended cohort with the C4 penalty active (the most "
                           "expensive arm)",
            "declared_budget_hours": TIME_BUDGET_HOURS,
            "n_runs": N_RUNS,
            "formula": "max_ft = floor((budget/n_runs - 10 * warmup_epoch) / finetune_epoch)",
            "binds_only_if_early_stopping_has_not_fired": True,
            "phase2_realised_finetune_epochs": [21, 28, 32],
        },
        "model_selection": {
            "criterion": "macro F1 on the extended validation cohort (n=1,103) "
                         "against the hard majority label",
            "identical_across": ["C1", "C2", "C3", "C4"],
            "rationale": (
                "a single criterion for every arm; scored against a hard label so "
                "that the soft-target arms are not selected on a metric that "
                "mechanically favours them, and computed on the same images for "
                "every arm so selection cannot differ by cohort."),
        },

        # ---- 4. evaluation -------------------------------------------------
        "evaluation": {
            "test_set": "the full 1,353-image official test split, unchanged from Phase 3",
            "strata": ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"],
            "primary_metric": "annotator-marginalized macro F1 (Phase 3 definition)",
            "ceiling_normalisation": (
                "reported alongside the raw scale for every stratum, per the Phase 3 "
                "carry-forward decision, using the modal-vote oracle of "
                "phase3b_common.modal_oracle"),
            "secondary_metrics": ["expected accuracy", "any-annotator hit rate",
                                  "single-label macro F1 where a majority label exists"],
            "calibration": "ECE, MCE, Brier on the top-1 probability, reliability "
                           "curves, all against expected accuracy (Phase 3B definition)",
            "interval_procedure": (
                "patient-clustered bootstrap, 1,000 resamples, seed 20260726, applied "
                "independently within each stratum -- identical to Phases 2 and 3"),
            "paired_comparison_procedure": (
                "config-vs-config differences use a PAIRED patient-clustered "
                "bootstrap: one patient resample is drawn and both configurations are "
                "scored on that same resample before differencing, so the interval "
                "reflects the difference and not the sum of two independent sampling "
                "errors. Differences are computed per seed and averaged across the 3 "
                "seeds."),
            "never_resample_images": True,
        },

        # ---- 5. endpoints and verdict rules --------------------------------
        "research_questions": {
            "RQ2": {
                "question": "Does training on soft targets from all four votes beat "
                            "hard consensus labels?",
                "hypothesis": "matches on the unanimous stratum, exceeds on contested "
                              "strata, better calibrated throughout",
                "primary_contrast": "C2 - C3",
                "why_C3_not_C1": (
                    "C3 is the pre-registered control (blueprint: 'C3 is not "
                    "optional'). Beating C1 only shows that softening helps; beating "
                    "C3 shows that softening WHERE THE ANNOTATORS ACTUALLY DISAGREED "
                    "helps beyond softening everywhere by the same total amount."),
                "primary_endpoint": (
                    "annotator-marginalized macro F1 on the pooled contested test set "
                    "(S-majority + S-plurality + S-no-majority, n = 550)"),
                "verdict_rule": (
                    "SUPPORTED if the paired patient-clustered 95% CI of "
                    "(C2 - C3) on the pooled contested set excludes 0 in C2's "
                    "favour; NOT SUPPORTED if it excludes 0 in C3's favour; "
                    "NOT RESOLVED if it contains 0."),
                "secondary_endpoints": [
                    "the same contrast per stratum",
                    "parity on S-unanimous: (C2 - C1) CI containing 0",
                    "delta ECE (C2 - C3) per stratum, negative = better calibrated",
                    "C1 - C0 on every stratum, the cohort effect",
                ],
                "calibration_verdict_rule": (
                    "BETTER CALIBRATED if the paired CI of ECE(C2) - ECE(C3) on the "
                    "pooled contested set excludes 0 below zero."),
            },
            "RQ3": {
                "question": "Does predictive uncertainty track human disagreement?",
                "primary_quantity": (
                    "WITHIN-stratum Spearman rho between predictive entropy and "
                    "per-image annotator vote entropy -- fixed by the Phase 3 "
                    "carry-forward decision, because the pooled correlation (0.320) "
                    "was shown to be almost entirely a between-tier effect that "
                    "collapses to 0.02-0.08 within tiers"),
                "strata_where_defined": (
                    "S-majority, S-plurality, S-no-majority. Vote entropy is "
                    "identically 0 on S-unanimous, so the correlation is undefined "
                    "there and is reported as null, never as 0."),
                "uncertainty_estimators": [
                    "single-model softmax entropy",
                    "MC stochastic depth: the ConvNeXt StochasticDepth modules are the "
                    "only stochastic component of this architecture and are active "
                    "during training, so re-enabling them at inference is the "
                    "architecture-appropriate form of the MC-dropout argument. "
                    "LayerNorm (not BatchNorm) means no other module changes "
                    "behaviour between train and eval mode.",
                    "3-member deep ensemble over the 3 seeds of each configuration",
                ],
                "n_mc_samples": 20,
                "verdict_rule": (
                    "SUPPORTED for a configuration if its within-stratum rho is "
                    "positive with a patient-clustered 95% CI excluding 0 on "
                    "S-majority, the largest contested stratum. Cross-configuration "
                    "ranking is reported descriptively."),
                "out_of_scope_here": (
                    "the external-transfer half of RQ3 ('ranking preserved "
                    "externally') requires HyperKvasir / GastroVision and is Phase 5"),
            },
            "RQ4": {
                "question": "Does an anatomy-aware loss exploiting the wall/station "
                            "structure help on contested images?",
                "primary_contrast": "C4 - C2 (both use vote-proportion targets, so the "
                                    "contrast isolates the structured penalty)",
                "primary_endpoint": "mean anatomical error distance on the test split, "
                                    "using the pre-registered distance matrix",
                "secondary_endpoints": [
                    "annotator-marginalized macro F1 on the pooled contested set",
                    "share of wall confusions that are circumferentially adjacent "
                    "(S-unanimous, Phase 0 / phase3_confusion definition)",
                    "share of station confusions that are neighbouring",
                ],
                "verdict_rule": (
                    "SUPPORTED if the paired CI of mean anatomical error distance "
                    "(C4 - C2) excludes 0 below zero AND the paired CI of macro F1 "
                    "(C4 - C2) does not exclude 0 below zero, i.e. the penalty "
                    "reshapes the errors without costing accuracy. PARTIALLY "
                    "SUPPORTED if the distance falls but macro F1 also falls "
                    "significantly."),
            },
        },

        # ---- 6. sensitivity ------------------------------------------------
        "sensitivity_analyses": {
            "leave_one_annotator_out": {
                "motivation": "blueprint sec.2.3: FG2 is the outlier annotator on "
                              "every measure, and its pairwise kappa with the other "
                              "resident (0.6799) is the lowest in the panel",
                "executed": "evaluation-side, for every configuration: the "
                            "annotator-marginalized macro F1 and the expected accuracy "
                            "are recomputed dropping each annotator in turn",
                "not_executed": ("training-side LOAO, i.e. rebuilding the C2 targets "
                                 "from 3 annotators and retraining. That is 4 further "
                                 "runs (~5 h) and does not fit the declared budget. "
                                 "The command to run it is implemented "
                                 "(phase4_train.py --drop-annotator) so the analysis "
                                 "is reproducible, and its absence is declared rather "
                                 "than concealed."),
            },
            "per_seed_stability": "every headline number is reported per seed as well "
                                  "as at the 3-seed mean",
        },

        # ---- 7. deviations from the blueprint ------------------------------
        "deviations": [
            {"id": "P4-DEV-1",
             "item": "MC dropout",
             "blueprint": "sec.4 PHASE 4: 'MC dropout as the cheap route'",
             "adopted": "MC stochastic depth",
             "evidence": "torchvision's ConvNeXt-Tiny contains no nn.Dropout module; "
                         "its only stochastic component is StochasticDepth "
                         "(p up to 0.1 per block). Inserting a dropout layer that was "
                         "absent during training would change the function being "
                         "sampled, which is exactly what the MC-dropout argument "
                         "forbids. Sampling the stochastic mechanism the network was "
                         "actually trained with is the faithful translation.",
             "impact": "none on the scientific claim; the estimator is still a "
                       "Monte-Carlo average over the training-time stochastic "
                       "mechanism"},
            {"id": "P4-DEV-2",
             "item": "Deep ensemble size",
             "blueprint": "sec.4 PHASE 4: 'a 5-member deep ensemble ... if the budget allows'",
             "adopted": "3 members (the 3 seeds already trained per configuration)",
             "evidence": f"the budget does not allow. 4 configurations x 3 seeds is "
                         f"{N_RUNS} runs at a measured {ep_ft:.0f} s per fine-tuning "
                         f"epoch on the extended cohort; 5 members would be 20 runs. "
                         f"The blueprint made the 5-member ensemble explicitly "
                         f"conditional on budget.",
             "impact": "a 3-member ensemble is a weaker uncertainty estimator than a "
                       "5-member one; the ensemble result is therefore reported as a "
                       "lower bound on what ensembling buys"},
            {"id": "P4-DEV-3",
             "item": "lambda for the C4 penalty",
             "blueprint": "not specified",
             "adopted": f"lambda = {LAMBDA}, fixed a priori, no sweep",
             "evidence": "a sweep over 3 values would cost 9 further runs. Unit "
                         "weight is the neutral choice and, being fixed before any "
                         "C4 result was seen, cannot be a post-hoc selection.",
             "impact": "RQ4 is tested at one point in lambda-space. A null result is "
                       "therefore evidence about unit weight, not about the family of "
                       "structured penalties."},
            {"id": "P4-DEV-4",
             "item": "Dataloader worker count",
             "blueprint": "not specified",
             "adopted": "2 (Phase 2 used 3)",
             "evidence": "3 workers over the 953 MB extended cache reproducibly "
                         "raised CUDNN_STATUS_INTERNAL_ERROR_HOST_ALLOCATION_FAILED "
                         "on this 16 GB machine with ~4.4 GB free.",
             "impact": "throughput only; the sampled data and the RNG stream are "
                       "unaffected because shuffling is driven by a seeded generator "
                       "on the main process."},
        ],

        # ---- 8. falsification and scope ------------------------------------
        "falsification": (
            "RQ2 is falsified if the paired interval on (C2 - C3) over the pooled "
            "contested set excludes 0 in C3's favour: that would mean vote-proportion "
            "targets are worse than an equally-soft uninformative target, i.e. the "
            "annotator disagreement pattern carries no usable signal beyond its "
            "magnitude. RQ4 is falsified if the anatomical error distance does not "
            "fall. A finding of 'no difference' is reported as such and is a "
            "publishable negative result, not a failure of the phase."),
        "scope_exclusions": [
            "no architecture change (ConvNeXt-Tiny throughout)",
            "no external dataset (Phase 5)",
            "no Grad-CAM (Phase 6)",
            "no retraining of C0; the Phase 2 checkpoints are reused unchanged",
            "no threshold tuning, no post-hoc temperature scaling (a separate "
            "intervention that would confound the calibration comparison)",
        ],
        "artefacts_to_be_produced": [
            "checkpoints/phase4_{C1,C2,C3,C4}_seed{1,2,3}.pt",
            "reports/phase4_run_*.json",
            "reports/phase4_predictions_{config}_seed{k}.csv",
            "reports/phase4_probs_{config}_seed{k}.npz",
            "reports/phase4_stratified_metrics.json",
            "reports/phase4_calibration.json",
            "reports/phase4_uncertainty.json",
            "reports/phase4_structure_eval.json",
            "reports/phase4_loao.json",
            "figures_phase4/P4_F25..F32_*.png",
            "Phase4_Report.docx / .pdf",
        ],
    }
    OUT.write_text(json.dumps(pre, indent=2), encoding="utf-8")
    print(f"pre-registration frozen -> {OUT.name}")
    print(f"  C2 mean mass displaced from the modal label: {mass_displaced:.6f}")
    print(f"  C3 epsilon (mass-matched)    = {eps_mass:.6f}")
    print(f"  C3 epsilon (entropy-matched) = {eps_entropy:.6f}  [reference only]")
    print(f"  C4 lambda = {LAMBDA}")
    print(f"  seeds {SEEDS}, fine-tune epoch cap {max_ft} "
          f"(budget {TIME_BUDGET_HOURS} h over {N_RUNS} runs)")


if __name__ == "__main__":
    main()
