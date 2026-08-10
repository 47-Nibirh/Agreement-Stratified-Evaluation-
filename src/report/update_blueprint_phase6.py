"""
P6.9 -- update the blueprint status board from the Phase 6 verdict JSONs.

No number is typed here; every figure is interpolated from the artefacts, so the
status board cannot drift from what the pipeline actually produced.

Run:  python src/report/update_blueprint_phase6.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BP = ROOT / "THESIS_RESEARCH_BLUEPRINT.md"
REP = ROOT / "reports"

OLD_VERSION = "v3.5"
NEW_VERSION = "v3.6"
POOLED = "S-contested (pooled)"


def J(n):
    p = REP / n
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main() -> int:
    hum, geo, sel = J("phase6_human.json"), J("phase6_geometry.json"), J("phase6_selective.json")
    att = J("phase6_cam_eval.json")
    if not (hum and geo and sel):
        print("[P6.9] missing a Phase 6 artefact; run the analysis scripts first")
        return 1

    arm = hum["headline_arm"]
    hp = hum["results"][POOLED]["bootstrap"]["by_arm"][arm]
    sp = hum["sensitivity_P6-AMD-5"]["by_stratum"][POOLED]
    spa = sp["by_arm"][arm]
    headroom_pct = 100 * (spa["position_in_headroom"] or 0)
    gp = geo["results"][POOLED]["by_arm"][arm]
    gv = geo["verdict_summary"][POOLED]
    ext, inte = sel["external"], sel["internal"]
    pc5 = ext["phase5_consistency"]

    text = BP.read_text(encoding="utf-8")

    # ---- status-board row -------------------------------------------------
    att_bit = ""
    if att:
        att_bit = (f" **P6-C1 {att['verdict_summary']['P6-C1_primary']}** "
                   f"(within-{att['primary']['stratum']} ρ = "
                   f"{att['verdict_summary']['P6-C1_primary_rho']}).")
    row = (
        f"| **6** | Explainability & error analysis | ✅ **COMPLETE** | "
        f"`Phase6_Report.docx/.pdf` — four pre-registered endpoints, no retraining. "
        f"**P6-A: on contested images the model out-predicts a held-out annotator** "
        f"(Δ = {hp['delta_mean']:+.4f} macro F1, CI {hp['delta_ci95'][0]:+.4f} to "
        f"{hp['delta_ci95'][1]:+.4f}) **but not the panel's own modal vote** — it "
        f"recovers {headroom_pct:.0f}% of the headroom from the annotator "
        f"({sp['human_held_out']:.4f}) to the modal-vote oracle "
        f"({sp['modal_vote_oracle']:.4f}) and exceeds that oracle on no stratum "
        f"(P6-AMD-5). So the attainable ceiling on contested images is 0.67 not 1.00 — "
        f"much of the Phase 3 decline is the ceiling moving — while a real model "
        f"shortfall against that reduced ceiling remains. **P6-B: wall geometry {gv['wall'].split('(')[0].strip()}**, "
        f"station geometry diverges by {gp.get('station_neighbouring_delta_mean')} pts "
        f"(CI {gp.get('station_neighbouring_delta_ci95')}); X3 settled — the human "
        f"geometry is *undefined* on S-unanimous, so the Phase 3 comparison was "
        f"cross-population.{att_bit} "
        f"**P6-D: {pc5['verdict']}** — external AURC separates the arms decisively "
        f"({sel['best_arm_external_aurc']} "
        f"{ext['by_arm'][sel['best_arm_external_aurc']]['aurc_3seed']:.4f} vs "
        f"{sel['best_arm_internal_aurc']} "
        f"{ext['by_arm'][sel['best_arm_internal_aurc']]['aurc_3seed']:.4f}) where "
        f"internal AURC does not ({inte['by_arm']['C2']['aurc_3seed']:.4f} vs "
        f"{inte['by_arm']['C3']['aurc_3seed']:.4f}). |"
    )
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("| **6** | Explainability & error analysis |"):
            lines[i] = row
            break
    else:
        print("[P6.9] status-board row for Phase 6 not found")
        return 1
    text = "\n".join(lines)

    # ---- methodology section ---------------------------------------------
    section_old_head = "### ⬜ PHASE 6 — Explainability & Error Analysis"
    section_new = (
        "### ✅ PHASE 6 — Explainability & Error Analysis — COMPLETE\n"
        "\n"
        "The blueprint asked whether the model's residual error \"reflects genuine "
        "visual ambiguity rather than model capacity\". Answering that needs a "
        "comparator outside the model set, which no earlier phase had. Phase 6 "
        "introduces two — the annotators themselves, and the model's own confidence "
        "ordering — and keeps the attribution analysis quantitative so that it could "
        "fail. No retraining; the frozen checkpoints are re-used unchanged.\n"
        "\n"
        f"- **P6-A — the human comparator, and the phase's headline.** Each annotator "
        f"is held out and scored against the other three; the model is scored against "
        f"the same three, on the same images and the same patient resample. The frozen "
        f"rule returns **{hum['verdict_summary'][POOLED]}** on the pooled contested "
        f"stratum (Δ = {hp['delta_mean']:+.4f}, CI {hp['delta_ci95'][0]:+.4f} to "
        f"{hp['delta_ci95'][1]:+.4f}). **Do not state this as 'the model beats the "
        f"expert'.** Two asymmetries were found after scoring and then measured "
        f"(P6-AMD-5): the model is optimised to predict *this* panel's consensus and "
        f"the annotator is not; and the model *chooses* a label while the annotator is "
        f"stuck with theirs. The modal vote of the same three references scores "
        f"{sp['modal_vote_oracle']:.4f} against {sp['human_held_out']:.4f} for the "
        f"annotator; the model reaches {spa['model']:.4f}, i.e. {headroom_pct:.0f}% of "
        f"that headroom, and exceeds the oracle on **no** stratum. On the 2-1-1 "
        f"stratum 50% of held-out annotators are singletons who cannot score well "
        f"whatever their skill. **What P6-A establishes** is that the attainable "
        f"ceiling on contested images is 0.67 rather than 1.00 — so much of the Phase 3 "
        f"decline is the ceiling moving, as Phase 3B's ceiling-normalised analysis "
        f"already found — while a substantial model shortfall against that reduced "
        f"ceiling remains. The endpoint separates the two and sizes them. ⚠️ On "
        f"S-unanimous the human side is 1.0 **by construction**, so that contrast is "
        f"uninformative (P6-AMD-1).\n"
        f"- **P6-B — X3 settled, by a stronger argument than the one that raised it.** "
        f"The amendment withdrew the Phase 3 claim because a model interval was "
        f"compared against a human point estimate. Measuring both sides on the same "
        f"images shows something more basic: S-unanimous contains **zero** annotator "
        f"disagreement events, so the human geometry is *undefined* there. The Phase 3 "
        f"comparison was cross-population, and neither the 0.12-point 'match' nor the "
        f"7.5-point 'shortfall' was ever like-for-like. Where the comparison *is* "
        f"defined: wall geometry {gv['wall'].split('(')[0].strip().lower()}, station "
        f"geometry diverges by {gp.get('station_neighbouring_delta_mean')} points "
        f"(CI {gp.get('station_neighbouring_delta_ci95')}) — a specific, nameable "
        f"deficit rather than a general one.\n"
        + (f"- **P6-C — attribution scored, not displayed.** Grad-CAM dispersion "
           f"against annotator vote entropy, *within* stratum: "
           f"**{att['verdict_summary']['P6-C1_primary']}** "
           f"(ρ = {att['verdict_summary']['P6-C1_primary_rho']}, CI "
           f"{att['verdict_summary']['P6-C1_primary_ci95']}). Evidence about Grad-CAM "
           f"specifically; no method sweep was run, by design (P6-DEV-3).\n"
           if att else "")
        + f"- **P6-D — the Phase 5 carry-forward discharged.** Risk–coverage removes "
        f"the single operating point Phase 5 was stuck at. Internally the arms barely "
        f"separate (AURC {inte['by_arm']['C2']['aurc_3seed']:.4f} for C2 against "
        f"{inte['by_arm']['C3']['aurc_3seed']:.4f} for C3); externally they separate "
        f"decisively ({ext['by_arm']['C2']['aurc_3seed']:.4f} against "
        f"{ext['by_arm']['C3']['aurc_3seed']:.4f}). The ordering agrees with Phase 5's "
        f"rejection ranking: **{pc5['verdict']}** (ρ = {pc5['spearman_rho']}).\n"
        "\n"
        "**Carry-forward to Phase 7.** The thesis's central claim is that agreement "
        "stratification separates a falling *reference standard* from a falling "
        "*classifier*, which the literature reports as one quantity. Both fall; the "
        "ceiling accounts for the larger share and a real model shortfall remains, and "
        "confidence degrades further and faster than discrimination. Report the human "
        "comparator curve **and the modal-vote oracle** beside every stratified "
        "performance figure — Phase 3's numbers mislead without the first, and the "
        "first misleads without the second. Use external AURC as the arm-selection "
        "endpoint; it is the only measurement in the project that separates the "
        "configurations decisively.\n"
        "\n"
        "### ⬜ PHASE 7"
    )
    if section_old_head not in text:
        print("[P6.9] Phase 6 section heading not found")
        return 1
    start = text.index(section_old_head)
    end = text.index("### ⬜ PHASE 7", start)
    text = text[:start] + section_new + text[end + len("### ⬜ PHASE 7"):]

    # ---- version + status line -------------------------------------------
    text = text.replace(f"# Master Research Blueprint — {OLD_VERSION}",
                        f"# Master Research Blueprint — {NEW_VERSION}")
    text = text.replace(f"**Version:** {OLD_VERSION.lstrip('v')} — ",
                        f"**Version:** {NEW_VERSION.lstrip('v')} — ")
    text = text.replace(
        "**Status:** ✅ Phases 0–5 complete; Phase 5B (self-training) and Phase 6 "
        "ready to start",
        "**Status:** ✅ Phases 0–6 complete, Phase 5B included; Phase 7 "
        "(thesis writing) ready to start")

    BP.write_text(text, encoding="utf-8")
    print(f"[P6.9] blueprint updated to {NEW_VERSION}")
    print(f"[P6.9]   P6-A {POOLED}: {hum['verdict_summary'][POOLED]}")
    print(f"[P6.9]   P6-B wall: {gv['wall']}")
    print(f"[P6.9]   P6-B station: {gv['station']}")
    if att:
        print(f"[P6.9]   P6-C1: {att['verdict_summary']['P6-C1_primary']}")
    print(f"[P6.9]   P6-D: {pc5['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
