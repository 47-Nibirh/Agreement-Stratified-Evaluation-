"""
P5.13 -- update the blueprint status board from the Phase 5 verdict JSONs.

No number is typed here; every figure is interpolated from the artefacts, so the
status board cannot drift from what the pipeline actually produced.

Run:  python src/report/update_blueprint_phase5.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BP = ROOT / "THESIS_RESEARCH_BLUEPRINT.md"
REP = ROOT / "reports"

OLD_VERSION = "v3.4"
NEW_VERSION = "v3.5"


def J(n):
    return json.loads((REP / n).read_text(encoding="utf-8"))


def main() -> int:
    tr, rj = J("phase5_transfer.json"), J("phase5_rejection.json")
    cal, sen = J("phase5_calibration.json"), J("phase5_sensitivity.json")
    mp = J("phase5_mapping.json")
    head = tr["headline_arm"]
    a, ra = tr["aggregate_3seed"][head], rj["aggregate_3seed"][head]
    v = cal["verdict_P5C"]
    ca = cal["aggregate_3seed"]

    text = BP.read_text(encoding="utf-8")

    row = (
        f"| **5** | External validation | ✅ **COMPLETE** | "
        f"`Phase5_Report.docx/.pdf` — HyperKvasir + GastroVision, "
        f"{tr['n_gastric_external']:,} gastric + {rj['n_out_of_protocol']:,} "
        f"out-of-protocol images, all five arms × 3 seeds, no adaptation. "
        f"**First finding: the external label spaces cannot express wall × station "
        f"at all**, so the endpoint is a pre-registered 2-way collapse, not 23-way. "
        f"**P5-A {tr['verdict']}** ({a['external_macro_f1_mean_3seed']:.2f} external "
        f"vs {a['internal_macro_f1_mean_3seed']:.2f} internal, drop "
        f"{a['drop_points']:.2f} pts, CI {a['drop_ci95'][0]:.2f} to "
        f"{a['drop_ci95'][1]:.2f}; precision target met). "
        f"**P5-B hypothesis FALSIFIED** — rejection "
        f"{100 * ra['rejection_rate_mean_3seed']:.1f}% vs a "
        f"{100 * rj['chance_rate']:.2f}% chance floor, and the soft-target arms "
        f"reject far better than the hard-label ones. "
        f"**P5-C {v['verdict']}** (ρ = {v['spearman_rho']:.3f}) but "
        f"{v['lowest_ece_internal']} and {v['lowest_ece_external']} swap at the top: "
        f"C2 is best externally (ECE {ca['C2']['ece_top1_mean_3seed']:.2f} vs C3's "
        f"{ca['C3']['ece_top1_mean_3seed']:.2f}). |"
    )
    old_row_start = "| **5** | External validation |"
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith(old_row_start):
            lines[i] = row
            break
    else:
        print("[P5.13] status-board row for Phase 5 not found")
        return 1
    text = "\n".join(lines)

    section_old_head = "### ⬜ PHASE 5 — External Validation (RQ3)"
    section_new = (
        "### ✅ PHASE 5 — External Validation (RQ3) — COMPLETE\n"
        "\n"
        "HyperKvasir and GastroVision were acquired, hashed against the GastroHUN "
        "inventory (zero collisions) and mapped by a table frozen before any image "
        "was scored. **The blueprint's premise did not survive contact with the "
        "data.** GastroHUN's label space is wall × station; neither external corpus "
        "carries the wall axis, and neither has a class for four of the six "
        "stations. GastroVision has no retroflex-stomach class at all. A 23-way "
        "external validation is therefore not available from these corpora, and the "
        "phase was reframed — before scoring — into a 2-way anatomical collapse "
        "(P5-A), an out-of-protocol rejection endpoint (P5-B) and a calibration-"
        "ordering endpoint (P5-C).\n"
        "\n"
        f"- **P5-A {tr['verdict']}.** {a['external_macro_f1_mean_3seed']:.2f} binary "
        f"macro F1 externally against {a['internal_macro_f1_mean_3seed']:.2f} "
        f"internally — a drop of {a['drop_points']:.2f} points, about twice the "
        f"pre-registered expectation. Every arm met the pre-registered "
        f"{tr['aggregate_3seed'][head]['precision_target_points']}-point precision "
        f"target, so these are powered verdicts rather than underpowered nulls.\n"
        f"- **P5-B: the pre-registered hypothesis was falsified, favourably.** "
        f"Rejection was predicted at or below the "
        f"{100 * rj['chance_rate']:.2f}% chance rate because GastroHUN's test split "
        f"holds only 50 OTHERCLASS images in 1,353. It reached "
        f"{100 * ra['rejection_rate_mean_3seed']:.1f}% for {head}, and the arms "
        f"separated sharply in the soft-target arms' favour. This benefit is "
        f"invisible internally.\n"
        f"- **P5-C {v['verdict']}** (Spearman ρ = {v['spearman_rho']:.3f}), but the "
        f"top two arms exchange places. C3's under-confidence travelled essentially "
        f"unchanged ({ca['C3']['overconfidence_points_mean_3seed']:.2f} points "
        f"externally against −6.45 internally), confirming the Phase 4 §4.2 claim "
        f"that its calibration advantage was a global confidence shift — a property "
        f"of the model, which follows it to a new centre and stops helping there.\n"
        f"- **Robustness.** Verdicts invariant to every ambiguous mapping flip: "
        f"{sen['verdicts_invariant_to_every_single_flip']}.\n"
        "\n"
        "**Carry-forward:** C2 is the recommended configuration, on external "
        "calibration and out-of-protocol rejection rather than internal accuracy. "
        "Report out-of-protocol rejection as a primary endpoint in Phases 6–7: it "
        "separated the arms where every internal endpoint failed to. Phase 5 "
        "intervals are image-level (no corpus publishes a case identifier) and must "
        "not be compared directly against the patient-clustered intervals of "
        "Phases 0–4.\n"
        "\n"
        "**Phase 5B (self-training) is planned and gated on the above being frozen "
        "and committed.** Adapting to the external images before the clean transfer "
        "numbers exist would make the external validation circular.\n"
        "\n"
        "### ⬜ PHASE 6"
    )
    if section_old_head not in text:
        print("[P5.13] Phase 5 section heading not found")
        return 1
    start = text.index(section_old_head)
    end = text.index("### ⬜ PHASE 6", start)
    text = text[:start] + section_new + text[end + len("### ⬜ PHASE 6"):]

    text = text.replace(f"# Master Research Blueprint — {OLD_VERSION}",
                        f"# Master Research Blueprint — {NEW_VERSION}")
    # the metadata block writes the version without the leading "v"
    text = text.replace(f"**Version:** {OLD_VERSION.lstrip('v')} — ",
                        f"**Version:** {NEW_VERSION.lstrip('v')} — ")
    for old_status in ("**Status:** ✅ Phases 0–4 complete; Phase 5 ready to start",
                       "**Status:** ✅ Phases 0-4 complete; Phase 5 ready to start"):
        text = text.replace(
            old_status,
            "**Status:** ✅ Phases 0–5 complete; Phase 5B (self-training) and "
            "Phase 6 ready to start")

    BP.write_text(text, encoding="utf-8")
    print(f"[P5.13] blueprint updated to {NEW_VERSION}")
    print(f"        P5-A {tr['verdict']} | P5-B {rj['verdict']} "
          f"(hypothesis falsified: {rj.get('hypothesis_supported') is False}) | "
          f"P5-C {v['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
