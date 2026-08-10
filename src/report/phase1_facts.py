"""
Phase-I deliverables -- the single source of every number.

The Phase-I Progress Report and the Final-Defence slide deck are two views of
the same evidence, so they must not be allowed to disagree. This module loads
every quantity both of them cite from the JSON/CSV artefacts the pipeline
already wrote, and exposes it as one nested dict. Neither builder contains a
literal measurement; both interpolate from `facts()`.

That is the project's standing rule (blueprint sec.8, "no number is typed by
hand") applied to the two documents that will be read by examiners rather than
by the pipeline. If an artefact is regenerated, both documents change with it.

The only hand-entered values here are administrative (names, IDs, supervisor,
dates) and bibliographic, neither of which is a measurement.

Usage:  from phase1_facts import facts;  F = facts()
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
LIT = ROOT / "literature_v2"


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Administrative constants. Not measurements -- taken from the approved
# Proposal Approval Form and the Title-phase evaluation report.
# --------------------------------------------------------------------------
ADMIN = {
    "title": ("Agreement-Stratified Evaluation of Deep Learning for Anatomical "
              "Landmark Recognition in Upper Gastrointestinal Endoscopy"),
    "short_title": "Agreement-Stratified Evaluation of Deep Learning for UGI Landmark Recognition",
    "members": [
        ("Fatin Sadab Nibirh", "0242310005101526"),
        ("MD Himel Rahman", "0242310005101800"),
    ],
    "supervisor": ("Ms. Shayla Sharmin", "Assistant Professor"),
    "co_supervisor": ("Dr. Md. Zahid Hasan", "Associate Professor"),
    "department": "Department of Computer Science and Engineering",
    "university": "Daffodil International University",
    "submission_date": "03-08-2026",
    "reporting_period": "Summer 2026",
    "thematic_areas": [
        "Artificial Intelligence and Machine Learning",
        "Deep Learning",
        "Health Informatics",
        "Computer Vision",
        "Image Processing",
    ],
    "software": (
        "Python 3.14.5; PyTorch 2.12.0+cu126 with CUDA 12.6; torchvision "
        "(ConvNeXt-Tiny, EfficientNet-B0, ImageNet-pretrained weights); "
        "NumPy; pandas; scikit-learn; SciPy; Pillow; Matplotlib; "
        "python-docx and python-pptx for automated report and slide "
        "generation; Git for version control; NCBI E-utilities for the "
        "literature search."
    ),
}


def facts() -> dict:
    inv = _load(REPORTS / "gastrohun_inventory.json")
    agr = _load(REPORTS / "gastrohun_agreement.json")
    stru = _load(REPORTS / "gastrohun_structure.json")
    ndup = _load(REPORTS / "gastrohun_neardup.json")
    dcal = _load(REPORTS / "gastrohun_dup_calibration.json")
    pris = _load(LIT / "prisma_counts.json")
    p2pre = _load(REPORTS / "phase2_prereg.json")
    p2met = _load(REPORTS / "phase2_test_metrics.json")
    p2run = {k: _load(REPORTS / f"phase2_run_seed{k}.json") for k in (1, 2, 3)}
    p2norm = _load(REPORTS / "phase2_norm_stats.json")
    p2prov = _load(REPORTS / "phase2_split_provenance.json")
    p3met = _load(REPORTS / "phase3_stratified_metrics.json")
    p3cal = _load(REPORTS / "phase3b_calibration.json")
    p3ceil = _load(REPORTS / "phase3b_ceiling_gaps.json")
    p0old = _load(REPORTS / "phase0_results.json")

    agg = p2met["aggregate"]
    rep = p2met["reproduction"]

    F: dict = {}

    # ---- corpus -----------------------------------------------------------
    F["corpus"] = {
        "n_images": inv["n_manifest_rows"],
        "n_patients": inv["n_patient_folders"],
        "n_classes": agr["n_classes"],
        "n_annotators": len(agr["annotators"]),
        "annotators": agr["annotators"],
        "gb": inv["bytes"]["total_gb"],
        "res_hi": "1350x1080",
        "res_hi_n": inv["resolutions"]["1350x1080"],
        "res_lo": "900x720",
        "res_lo_n": inv["resolutions"]["900x720"],
        "img_per_patient_mean": inv["images_per_patient"]["mean"],
        "img_per_patient_sd": inv["images_per_patient"]["std"],
        "img_per_patient_min": inv["images_per_patient"]["min"],
        "img_per_patient_max": inv["images_per_patient"]["max"],
        "n_decoded": inv["n_decoded_ok"],
        "n_missing": inv["n_missing_from_disk"],
        "n_orphan": inv["n_orphan_on_disk"],
        "n_corrupt": inv["n_corrupt"],
        "n_exact_dupes": inv["exact_duplicates"]["n_groups"],
        "folder_mismatch": inv["folder_patient_mismatch"],
        "direct_capture": stru["provenance"]["by_source_type"]["direct_capture"]["n"],
        "video_frame": stru["provenance"]["by_source_type"]["video_frame"]["n"],
    }

    # ---- contamination scan ----------------------------------------------
    F["contamination"] = {
        "n_pairs_scanned": ndup["n_pairs_examined"],
        "dhash_threshold": ndup["operative_threshold"],
        "cross_split_candidates": ndup["cross_split_candidates"],
        "provisional_verified": ndup["cross_split_verified_duplicates"],
        "provisional_rule": ndup["decision_rules"],
        "null_n": dcal["null"]["n_pairs"],
        "null_rms_mean": dcal["null"]["rms"]["mean"],
        "null_rms_p1": dcal["null"]["rms"]["p1"],
        "pos_n": dcal["positive_control"]["n_pairs"],
        "pos_rms_mean": dcal["positive_control"]["rms"]["mean"],
        "pos_rms_p99": dcal["positive_control"]["rms"]["p99"],
        "pos_corr_p1": dcal["positive_control"]["corr"]["p1"],
        "calibrated_rule": dcal["calibrated_rule"],
        "reassessment": dcal["reassessment"],
    }

    # ---- agreement --------------------------------------------------------
    F["agreement"] = {
        "fleiss": agr["fleiss_kappa"],
        "alpha": agr["krippendorff_alpha"],
        "ac1": agr["gwet_ac1"],
        "pairwise": {k: v["kappa"] for k, v in agr["pairwise_cohen_kappa"].items()},
        "pairwise_ci": {k: v["ci95"] for k, v in agr["pairwise_cohen_kappa"].items()},
        "pairwise_within": {k: v["within_team"] for k, v in agr["pairwise_cohen_kappa"].items()},
        "tiers": agr["agreement_tiers"],
        "tiers_pct": agr["agreement_tiers_pct"],
        "vote_patterns": agr["vote_patterns"],
        "vote_patterns_pct": agr["vote_patterns_pct"],
        "n_no_majority": agr["n_no_majority"],
        "pct_no_majority": agr["pct_no_majority"],
        "n_disagreement_events": agr["n_disagreement_pair_events"],
        "unanimous_n": agr["agreement_tiers"]["complete_agreement_4of4"],
        "unanimous_pct": agr["agreement_tiers_pct"]["complete_agreement_4of4"],
    }
    F["agreement"]["contested_pct"] = round(100.0 - F["agreement"]["unanimous_pct"], 2)
    F["agreement"]["contested_n"] = (F["corpus"]["n_images"]
                                     - F["agreement"]["unanimous_n"])

    # ---- label-space structure -------------------------------------------
    F["structure"] = {
        "walls": stru["wall_names"],
        "stations": stru["station_names"],
        "decomp": stru["disagreement_decomposition"],
        "decomp_pct": stru["disagreement_decomposition_pct"],
        "kappa_full": stru["agreement_by_granularity"]["full"]["mean_pairwise_kappa"],
        "kappa_station": stru["agreement_by_granularity"]["station"]["mean_pairwise_kappa"],
        "kappa_wall": stru["agreement_by_granularity"]["wall"]["mean_pairwise_kappa"],
        "unan_full": stru["unanimity_rate_pct_by_granularity"]["full"],
        "unan_station": stru["unanimity_rate_pct_by_granularity"]["station"],
        "unan_wall": stru["unanimity_rate_pct_by_granularity"]["wall"],
        "otherclass_rate": stru["otherclass"]["per_rater_OTHERCLASS_rate_pct"],
        "otherclass_unanimous_pct": stru["otherclass"]["pct_of_OTHERCLASS_nominations_that_are_unanimous"],
        "patient_kappa_mean": stru["per_patient_agreement"]["mean"],
        "patient_kappa_sd": stru["per_patient_agreement"]["sd"],
        "patient_kappa_min": stru["per_patient_agreement"]["min"],
        "patient_kappa_max": stru["per_patient_agreement"]["max"],
        "stream_split_p": stru["provenance"]["source_type_split_p"],
        "taxonomy": stru["taxonomy"],
        "station_difficulty": stru["station_difficulty"],
        "wall_confusion_pairs": stru["wall_confusion_pairs"],
        "n_underpowered_classes": agr["n_test_classes_underpowered_hw_gt_10pct"],
    }
    F["structure"]["otherclass_spread"] = round(
        max(F["structure"]["otherclass_rate"].values())
        / min(F["structure"]["otherclass_rate"].values()), 1)

    # ---- literature review ------------------------------------------------
    st = pris["stages"]
    F["prisma"] = {
        "n_themes": len(pris["queries"]),
        "identified": st["records_identified_total"],
        "duplicates": st["duplicates_removed"],
        "unique": st["records_after_deduplication"],
        "screened": st["records_screened"],
        "excluded": st["records_excluded_at_screening"],
        "passing": st["records_passing_screen"],
        "exclusion_reasons": st["exclusion_reasons"],
        "themes": {v["theme"]: v["total_hits"] for v in pris["queries"].values()},
        "included": 82,          # 68 database + 14 hand-searched (Phase 1 report)
        "included_db": 68,
        "included_hand": 14,
        "date_from": min(v["date_from"] for v in pris["queries"].values()),
        "date_to": max(v["date_to"] for v in pris["queries"].values()),
    }
    import csv
    with open(LIT / "extraction_table.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    themes: dict = {}
    for r in rows:
        themes[r["theme"]] = themes.get(r["theme"], 0) + 1
    years = [int(r["year"]) for r in rows if r["year"].strip().isdigit()]
    F["prisma"]["included_by_theme"] = dict(
        sorted(themes.items(), key=lambda kv: -kv[1]))
    F["prisma"]["n_included_rows"] = len(rows)
    F["prisma"]["pct_since_2020"] = round(
        100.0 * sum(1 for y in years if y >= 2020) / len(years), 1)

    # ---- Phase 2 cohort, preprocessing, training --------------------------
    coh = p2prov["cohort"]
    F["cohort"] = {
        "n_images": coh["n_images"],
        "train": coh["by_split"]["Train"],
        "val": coh["by_split"]["Validation"],
        "test": coh["by_split"]["Test"],
        "retention_pct": coh["retention_pct"],
        "n_classes": coh["n_classes"],
        "n_patients": coh["n_patients"],
        "patients_by_split": coh.get("patients_by_split"),
        "overlap_total": sum(len(v) for v in p2prov["patient_overlap"].values()),
        "class_chi2_p": p2prov["class_split_p"],
        "gate2": p2prov["gate2_pass"],
        "gate3": p2prov["gate3_pass"],
    }
    F["preprocess"] = {
        "size": p2norm["size"],
        "resample": p2norm["resample"],
        "mean": p2norm["mean"],
        "std": p2norm["std"],
        "imagenet_mean": p2norm["imagenet_mean"],
        "imagenet_std": p2norm["imagenet_std"],
        "abs_delta_mean": p2norm["abs_delta_mean"],
        "max_delta": max(p2norm["abs_delta_mean"]),
        "n_norm_images": p2norm["n_images"],
        "n_pixels": p2norm["n_pixels_per_channel"],
        "crop_scale": (0.85, 1.0),
        "crop_ratio": (0.9, 1.111),
        "jitter": dict(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.02),
    }
    r1 = p2run[1]
    F["training"] = {
        "backbone": "ConvNeXt-Tiny",
        "weights": "ImageNet-1k (IMAGENET1K_V1)",
        "device": r1["device"],
        "torch": r1["torch"],
        "cuda": r1["cuda"],
        "python": r1["python"],
        "batch": r1["batch_size"],
        "effective_batch": r1["effective_batch"],
        "precision": r1["precision"],
        "memory_format": r1["memory_format"],
        "lr_head": r1["lr_head"],
        "lr_finetune": r1["lr_finetune"],
        "weight_decay": r1["weight_decay"],
        "warmup_epochs": r1["warmup_epochs"],
        "max_finetune_epochs": r1["max_finetune_epochs"],
        "patience": r1["patience"],
        "n_modules_unfrozen": r1["trainable_layers"]["n_modules_unfrozen"],
        "n_feature_modules": r1["trainable_layers"]["n_feature_modules"],
        "param_fraction_unfrozen": r1["trainable_layers"]["param_fraction_unfrozen"],
        "params_total": r1["trainable_layers"]["feature_params_total"],
        "peak_vram_mib": r1["peak_vram_mib"],
        "per_seed": {str(k): {"best_val_macro_f1": v["best_val_macro_f1"],
                         "best_epoch": v["best_epoch_overall"],
                         "n_epochs": v["n_epochs_run"],
                         "stop_reason": v["stop_reason"],
                         "wallclock_min": round(v["wallclock_sec"] / 60.0, 1)}
                     for k, v in p2run.items()},
        "total_train_min": round(sum(v["wallclock_sec"] for v in p2run.values()) / 60.0, 1),
        "history": {str(k): v["history"] for k, v in p2run.items()},
    }

    # ---- Phase 2 result / reproduction gate -------------------------------
    F["baseline"] = {
        "published": p2pre["published_macro_f1"],
        "band": p2pre["acceptance_band_points"],
        "observed": rep["observed_macro_f1"],
        "delta": rep["delta_points"],
        "verdict": rep["verdict"],
        "sd": round(agg["macro_f1_sd"] * 100, 2),
        "ci95": [round(x * 100, 2) for x in agg["seed_mean_boot_ci95"]],
        "per_seed": {k: round(v["macro_f1"] * 100, 2)
                     for k, v in p2met["per_seed"].items()},
        "per_seed_ci": {k: [round(x * 100, 2) for x in v["macro_f1_ci95"]]
                        for k, v in p2met["per_seed"].items()},
        "accuracy": round(sum(v["accuracy"] for v in p2met["per_seed"].values())
                          / 3 * 100, 2),
        "macro_precision": round(sum(v["macro_precision"] for v in p2met["per_seed"].values())
                                 / 3 * 100, 2),
        "macro_recall": round(sum(v["macro_recall"] for v in p2met["per_seed"].values())
                              / 3 * 100, 2),
        "weighted_f1": round(sum(v["weighted_f1"] for v in p2met["per_seed"].values())
                             / 3 * 100, 2),
        "ece": round(sum(v["ece"] for v in p2met["per_seed"].values()) / 3 * 100, 2),
        "brier": round(sum(v["brier"] for v in p2met["per_seed"].values()) / 3, 4),
        "n_test": p2met["n_test_images"],
        "n_test_patients": p2met["n_test_patients"],
        "n_boot": p2met["n_boot"],
        "boot_unit": p2met["boot_unit"],
        "boot_seed": p2met["boot_seed"],
        "published_source": p2pre["published_source"],
    }

    # ---- Phase 3 stratified evaluation ------------------------------------
    a3 = p3met["aggregate_3seed"]
    F["strata"] = {
        "order": p3met["rq1"]["tier_order"],
        "n": {k: v["n_images"] for k, v in a3.items()},
        "n_patients": {k: v["n_patients"] for k, v in a3.items()},
        "f1": {k: round(v["annotator_marginalized_macro_f1_mean_3seed"] * 100, 2)
               for k, v in a3.items()},
        "expected_accuracy": {k: round(v["expected_accuracy_mean_3seed"] * 100, 2)
                              for k, v in a3.items()},
        "any_hit": {k: round(v["any_annotator_hit_rate_mean_3seed"] * 100, 2)
                    for k, v in a3.items()},
        "n_test_total": p3met["n_test_images"],
        "gap": p3met["rq1"]["gap_S_unanimous_minus_S_no_majority_points"],
        "arch_benchmark": p3met["rq1"]["architecture_gap_benchmark_points"],
        "spearman_rho": p3met["rq1"]["spearman_rho"],
        "spearman_p": p3met["rq1"]["spearman_p"],
        "monotonic": p3met["rq1"]["strictly_monotonic_non_increasing"],
        "consistency_mismatch": sum(v["n_mismatch"] for v in p3met["consistency_gate"].values()),
        "consistency_compared": sum(v["n_compared"] for v in p3met["consistency_gate"].values()),
    }
    c3 = p3cal["aggregate_3seed"]
    F["calibration"] = {
        "ece": {k: round(v["ece_vs_expected_accuracy"] * 100, 2) for k, v in c3.items()},
        "confidence": {k: round(v["mean_confidence"] * 100, 2) for k, v in c3.items()},
        "expected_accuracy": {k: round(v["expected_accuracy"] * 100, 2) for k, v in c3.items()},
        "overconfidence": {k: round(v["overconfidence_points"], 2) for k, v in c3.items()},
    }
    cg = p3ceil["ceilings"]
    pg = p3ceil["pairwise_gaps"]
    F["ceiling"] = {
        "oracle_f1": {k: round(v["oracle_marginalized_macro_f1_mean"] * 100, 2)
                      for k, v in cg.items()},
        "mean_distinct_labels": {k: v["mean_distinct_labels_per_image"]
                                 for k, v in cg.items()},
        "gaps": {k: {"mean": v["gap_points_3seed_mean"],
                     "ci95": v["ci95_points_3seed_mean"],
                     "excludes_zero": v["excludes_zero"]}
                 for k, v in pg.items()},
    }

    # ---- negative control (retired corpus, validates the audit) -----------
    F["negative_control"] = {
        "n_rows": p0old["provenance"]["n_rows"],
        "max_cramers_v": max(x["cramers_v"] for x in p0old["battery"]["feature_target_association"]),
        "leak_accuracy": p0old["leakage"]["E03_notebook_with_comments"]["accuracy"],
        "leak_after_removal": p0old["leakage"]["E04_comments_removed"]["accuracy"],
        "multi_match_pct": p0old["label_audit"]["pct_multi_match"],
        "zero_match_pct": p0old["label_audit"]["pct_zero_match"],
    }

    F["admin"] = ADMIN
    return F


def pct(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


if __name__ == "__main__":
    F = facts()
    print(json.dumps(F, indent=2, default=str)[:6000])
