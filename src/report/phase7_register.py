"""
Phase 7 / P7.3 -- the cross-phase results register.

The thesis quotes numbers produced across seven phases and thirty-odd JSON
artefacts. If each chapter reaches into those artefacts independently, the
document acquires exactly the failure mode this project has avoided everywhere
else: two chapters quoting the same quantity differently because one was written
later.

The register resolves every headline number ONCE, keyed by chapter, and fails
loudly if an artefact it expects is missing or has changed shape. The thesis
builder reads only the register. A number can therefore appear in the abstract,
a results table and the conclusion, and be the same number by construction.

It also carries the provenance of each value -- artefact file and JSON path --
so Appendix E (the reproducibility index) is generated rather than maintained.

Output
  reports/phase7_register.json
Run:  python src/report/phase7_register.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
OUT = REP / "phase7_register.json"

POOLED = "S-contested (pooled)"
TIERS = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]


class Missing(Exception):
    pass


def J(name, required=True):
    p = REP / name
    if not p.exists():
        if required:
            raise Missing(f"required artefact absent: {name}")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def dig(obj, path, artefact):
    """Fetch a nested value by '/'-separated path, failing loudly and usefully."""
    cur = obj
    for part in path.split("/"):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
                continue
            except (ValueError, IndexError):
                raise Missing(f"{artefact}: no index '{part}' in list at '{path}'")
        if not isinstance(cur, dict) or part not in cur:
            avail = list(cur)[:8] if isinstance(cur, dict) else type(cur).__name__
            raise Missing(f"{artefact}: no key '{part}' on the way to '{path}' "
                          f"(available: {avail})")
        cur = cur[part]
    return cur


def main() -> None:
    t0 = time.time()
    A = {
        "inventory": ("gastrohun_inventory.json", J("gastrohun_inventory.json")),
        "agreement": ("gastrohun_agreement.json", J("gastrohun_agreement.json")),
        "structure": ("gastrohun_structure.json", J("gastrohun_structure.json")),
        "neardup": ("gastrohun_neardup.json", J("gastrohun_neardup.json")),
        "dupcal": ("gastrohun_dup_calibration.json", J("gastrohun_dup_calibration.json")),
        "p2": ("phase2_test_metrics.json", J("phase2_test_metrics.json")),
        "p3": ("phase3_stratified_metrics.json", J("phase3_stratified_metrics.json")),
        "p3ceil": ("phase3b_ceiling_gaps.json", J("phase3b_ceiling_gaps.json")),
        "p3cal": ("phase3b_calibration.json", J("phase3b_calibration.json")),
        "p3amd": ("phase3b_amendment.json", J("phase3b_amendment.json")),
        "p4": ("phase4_stratified_metrics.json", J("phase4_stratified_metrics.json")),
        "p4cal": ("phase4_calibration.json", J("phase4_calibration.json")),
        "p4str": ("phase4_structure_eval.json", J("phase4_structure_eval.json")),
        "p4pre": ("phase4_prereg.json", J("phase4_prereg.json")),
        "p5tr": ("phase5_transfer.json", J("phase5_transfer.json")),
        "p5rj": ("phase5_rejection.json", J("phase5_rejection.json")),
        "p5cal": ("phase5_calibration.json", J("phase5_calibration.json")),
        "p5b": ("phase5b_eval.json", J("phase5b_eval.json")),
        "p6h": ("phase6_human.json", J("phase6_human.json")),
        "p6g": ("phase6_geometry.json", J("phase6_geometry.json")),
        "p6a": ("phase6_cam_eval.json", J("phase6_cam_eval.json")),
        "p6s": ("phase6_selective.json", J("phase6_selective.json")),
        "rq5": ("phase7_rq5.json", J("phase7_rq5.json")),
        "mult": ("phase7_multiplicity.json", J("phase7_multiplicity.json")),
        "b0": ("phase7_backbone.json", J("phase7_backbone.json", required=False)),
    }
    prov = []

    def V(key, path, label=None):
        """Resolve a value and record where it came from."""
        fname, obj = A[key]
        val = dig(obj, path, fname)
        prov.append({"label": label or path, "artefact": fname, "json_path": path})
        return val

    reg = {}

    # ---- Chapter 2: corpus audit -----------------------------------------
    agr = A["agreement"][1]
    reg["ch2_audit"] = {
        "n_images": V("inventory", "n_manifest_rows"),
        "n_decoded_ok": V("inventory", "n_decoded_ok"),
        "n_missing": V("inventory", "n_missing_from_disk"),
        "n_orphan": V("inventory", "n_orphan_on_disk"),
        "n_corrupt": V("inventory", "n_corrupt"),
        "n_patients": V("agreement", "n_patients"),
        "n_classes": V("agreement", "n_classes"),
        "annotators": V("agreement", "annotators"),
        "fleiss_kappa": V("agreement", "fleiss_kappa"),
        "krippendorff_alpha": V("agreement", "krippendorff_alpha"),
        "gwet_ac1": V("agreement", "gwet_ac1"),
        "pairwise_kappa": V("agreement", "pairwise_cohen_kappa"),
        "agreement_tiers": V("agreement", "agreement_tiers"),
        "agreement_tiers_pct": V("agreement", "agreement_tiers_pct"),
        "pct_no_majority": V("agreement", "pct_no_majority"),
        "split_class_chi2_p": V("agreement", "split_class_chi2/p"),
        "n_underpowered_classes": V("agreement", "n_test_classes_underpowered_hw_gt_10pct"),
        "pct_with_clinical_record": V("agreement", "clinical_metadata/pct_image_patients_with_clinical_record"),
        "disagreement_decomposition_pct": V("structure", "disagreement_decomposition_pct"),
        "n_disagreement_events": V("structure", "n_disagreement_pair_events"),
        "kappa_by_granularity": V("structure", "agreement_by_granularity"),
        "unanimity_by_granularity": V("structure", "unanimity_rate_pct_by_granularity"),
        "otherclass_per_rater": V("structure", "otherclass/per_rater_OTHERCLASS_rate_pct"),
        "neardup_pairs_examined": V("neardup", "n_pairs_examined"),
        "dup_flagged_uncalibrated": V("dupcal", "reassessment/n_flagged_by_provisional_rule"),
        "dup_confirmed_calibrated": V("dupcal", "reassessment/n_confirmed_by_calibrated_rule"),
    }

    # ---- Chapter 4: stratified evaluation --------------------------------
    p3 = A["p3"][1]
    reg["ch4_stratified"] = {
        "macro_f1_by_tier": {t: V("p3", f"aggregate_3seed/{t}/annotator_marginalized_macro_f1_mean_3seed")
                             for t in TIERS},
        "n_by_tier": {t: V("p3", f"aggregate_3seed/{t}/n_images") for t in TIERS},
        "ceilings": {t: V("p3ceil", f"ceilings/{t}/oracle_marginalized_macro_f1_mean")
                     for t in TIERS},
        "max_expected_accuracy": {t: V("p3ceil", f"ceilings/{t}/max_expected_accuracy_exact")
                                  for t in TIERS},
        "gap_4v3_ceiling_normalised": V(
            "p3ceil", "pairwise_gaps/S-unanimous - S-majority [ceiling_normalised]/gap_points_3seed_mean"),
        "gap_4v3_ci": V(
            "p3ceil", "pairwise_gaps/S-unanimous - S-majority [ceiling_normalised]/ci95_points_3seed_mean"),
        "ece_by_tier": {t: V("p3cal", f"aggregate_3seed/{t}/ece_vs_expected_accuracy")
                        for t in TIERS},
        "mean_confidence_by_tier": {t: V("p3cal", f"aggregate_3seed/{t}/mean_confidence")
                                    for t in TIERS},
        "expected_accuracy_by_tier": {t: V("p3cal", f"aggregate_3seed/{t}/expected_accuracy")
                                      for t in TIERS},
        "corrections": V("p3amd", "corrections") if "corrections" in A["p3amd"][1] else None,
    }

    # ---- Chapter 5: target construction ----------------------------------
    reg["ch5_targets"] = {
        "arms": V("p4", "configurations_evaluated"),
        "macro_f1_pooled_contested": {
            c: V("p4", f"aggregate_3seed/{c}/{POOLED}/annotator_marginalized_macro_f1_mean_3seed")
            for c in A["p4"][1]["configurations_evaluated"]},
        "ece_pooled_contested": {
            c: V("p4cal", f"aggregate_3seed/{c}/{POOLED}/ece_vs_expected_accuracy")
            for c in A["p4"][1]["configurations_evaluated"]},
        "ece_unanimous": {
            c: V("p4cal", f"aggregate_3seed/{c}/S-unanimous/ece_vs_expected_accuracy")
            for c in A["p4"][1]["configurations_evaluated"]},
        "contrast_C2_C3": V("p4", f"contrasts/C2 - C3/by_stratum/{POOLED}/diff_points_3seed_mean"),
        "contrast_C2_C3_ci": V("p4", f"contrasts/C2 - C3/by_stratum/{POOLED}/ci95_points_3seed_mean"),
        "epsilon_mass_matched": V("p4pre", "epsilon_derivation_detail/epsilon_mass_matched"),
        "epsilon_entropy_matched": V("p4pre", "epsilon_derivation_detail/epsilon_entropy_matched"),
        "rq4_C4_C2": V("p4str", f"contrasts/C4 - C2/{POOLED}/delta_distance_3seed_mean"),
        "rq4_C4_C2_ci": V("p4str", f"contrasts/C4 - C2/{POOLED}/ci95_3seed_mean"),
    }

    # ---- Chapter 6: external validation ----------------------------------
    reg["ch6_external"] = {
        "n_gastric": V("p5tr", "n_gastric_external"),
        "n_out_of_protocol": V("p5rj", "n_out_of_protocol"),
        "headline_arm": V("p5tr", "headline_arm"),
        "transfer_verdict": V("p5tr", "verdict"),
        "external_f1": V("p5tr", "aggregate_3seed/C2/external_macro_f1_mean_3seed"),
        "internal_f1": V("p5tr", "aggregate_3seed/C2/internal_macro_f1_mean_3seed"),
        "drop_points": V("p5tr", "aggregate_3seed/C2/drop_points"),
        "drop_ci": V("p5tr", "aggregate_3seed/C2/drop_ci95"),
        "chance_rate": V("p5rj", "chance_rate"),
        "rejection_by_arm": {c: V("p5rj", f"aggregate_3seed/{c}/rejection_rate_mean_3seed")
                             for c in A["p5rj"][1]["aggregate_3seed"]},
        "p5b_verdicts": {k: V("p5b", f"results/{k}/verdict")
                         for k in A["p5b"][1]["results"]},
        "p5b_split_weakness": V("p5b", "split_weakness"),
    }

    # ---- Chapter 7: explainability and error analysis --------------------
    p6h = A["p6h"][1]
    reg["ch7_error"] = {
        "human_by_stratum": {s: V("p6h", f"sensitivity_P6-AMD-5/by_stratum/{s}/human_held_out")
                             for s in TIERS + [POOLED]},
        "oracle_by_stratum": {s: V("p6h", f"sensitivity_P6-AMD-5/by_stratum/{s}/modal_vote_oracle")
                              for s in TIERS + [POOLED]},
        "model_by_stratum": {s: V("p6h", f"sensitivity_P6-AMD-5/by_stratum/{s}/by_arm/C2/model")
                             for s in TIERS + [POOLED]},
        "headroom_recovered": {s: V("p6h", f"sensitivity_P6-AMD-5/by_stratum/{s}/by_arm/C2/position_in_headroom")
                               for s in TIERS + [POOLED]},
        "singleton_rate": {s: V("p6h", f"sensitivity_P6-AMD-5/by_stratum/{s}/mean_singleton_rate")
                           for s in TIERS + [POOLED]},
        "qualified_verdict": V("p6h", f"qualified_verdict/{POOLED}"),
        "geometry_wall_delta": V("p6g", f"results/{POOLED}/by_arm/C2/wall_adjacent_delta_mean"),
        "geometry_wall_ci": V("p6g", f"results/{POOLED}/by_arm/C2/wall_adjacent_delta_ci95"),
        "geometry_station_delta": V("p6g", f"results/{POOLED}/by_arm/C2/station_neighbouring_delta_mean"),
        "geometry_station_ci": V("p6g", f"results/{POOLED}/by_arm/C2/station_neighbouring_delta_ci95"),
        "x3_finding": V("p6g", "x3_settlement/finding"),
        "attribution_primary_verdict": V("p6a", "verdict_summary/P6-C1_primary"),
        "attribution_secondary": {c: V("p6a", f"secondary/{c}/verdict") for c in A["p6a"][1]["arms"]},
        "iou_unanimous": {c: V("p6a", f"secondary/{c}/inter_seed_iou_unanimous") for c in A["p6a"][1]["arms"]},
        "aurc_internal": {c: V("p6s", f"internal/by_arm/{c}/aurc_3seed") for c in A["p6s"][1]["arms"]},
        "aurc_external": {c: V("p6s", f"external/by_arm/{c}/aurc_3seed")
                          for c in A["p6s"][1]["external"]["by_arm"]},
        "phase5_consistency": V("p6s", "external/phase5_consistency/verdict"),
    }

    # ---- Chapter 8: RQ5 ---------------------------------------------------
    reg["ch8_rq5"] = {
        "verdict": V("rq5", "verdict"),
        "n_separating": V("rq5", "discrimination/n_separating"),
        "n_independent": V("rq5", "discrimination/n_modality_independent"),
        "outright_fail": V("rq5", "discrimination/outright_fail_gates"),
        "agreeing": V("rq5", "discrimination/agreeing_gates"),
        "reversed": V("rq5", "discrimination/gates_where_the_UNSOUND_corpus_scores_HIGHER"),
        "n_fatal": V("rq5", "what_the_protocol_missed/n_fatal"),
        "n_fatal_caught": V("rq5", "what_the_protocol_missed/n_fatal_caught_by_any_gate"),
        "verdict_statement": V("rq5", "verdict_statement"),
    }

    # ---- Chapter 9: multiplicity and synthesis ---------------------------
    reg["ch9_synthesis"] = {
        "family_size": V("mult", "family_size_tested"),
        "n_significant": V("mult", "n_significant_unadjusted"),
        "n_surviving": V("mult", "n_surviving_holm"),
        "summary": V("mult", "summary"),
    }
    if A["b0"][1] is not None:
        reg["ch9_synthesis"].update({
            "backbone": V("b0", "backbone"),
            "n_replicating": V("b0", "n_replicating"),
            "n_tested": V("b0", "n_tested"),
            "R1": V("b0", "replication/R1_rq2_accuracy_null"),
            "R2": V("b0", "replication/R2_calibration_reversal"),
            "R3": V("b0", "replication/R3_human_comparator_position"),
            "b0_ece_contested": {
                "C2": V("b0", f"levels_by_stratum/{POOLED}/by_arm/C2/ece_3seed"),
                "C3": V("b0", f"levels_by_stratum/{POOLED}/by_arm/C3/ece_3seed")},
            "b0_ece_unanimous": {
                "C2": V("b0", "levels_by_stratum/S-unanimous/by_arm/C2/ece_3seed"),
                "C3": V("b0", "levels_by_stratum/S-unanimous/by_arm/C3/ece_3seed")},
            "b0_headroom": V("b0", f"human_comparator/{POOLED}/by_arm/C2/position_in_headroom"),
            "b0_stop_reasons": V("b0", "stop_reasons"),
            "endpoints_WITHOUT_a_second_backbone": [
                "confusion geometry (Chapter 7 §7.3)",
                "attribution stability (Chapter 7 §7.4)",
                "external transfer, rejection and selective prediction (Chapters 6, 7 §7.5)",
            ],
        })

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 7, "step": "P7.3",
        "purpose": ("resolve every headline number the thesis quotes exactly once, "
                    "keyed by chapter, so that no two chapters can quote the same "
                    "quantity differently"),
        "n_artefacts_read": len(A),
        "n_values_resolved": len(prov),
        "register": reg,
        "provenance": prov,
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P7.3] {len(prov)} values resolved from {len(A)} artefacts")
    for ch in reg:
        print(f"   {ch}: {len(reg[ch])} entries")
    print(f"[P7.3] wrote {OUT.name}")


if __name__ == "__main__":
    main()
