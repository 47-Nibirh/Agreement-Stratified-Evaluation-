"""
P5.0 -- freeze the Phase 5 carry-forward decision.

Which Phase 4 arms go forward into external validation, decided from the Phase 4
artefacts ALONE and frozen before any external image exists on disk. Run before
reports/phase5_prereg.json, and before src/models/phase5_data.py.

The blueprint status board records the Phase 4 sec.4.7 guidance as "carry the
best-CALIBRATED arm, not the most accurate". This script does not simply apply
that rule; it evaluates it, records why it is insufficient, and writes the
decision that supersedes it. Two reasons, both computed below rather than
asserted:

  1. RQ3's external half asks whether the uncertainty RANKING is preserved
     outside the training distribution. A ranking is not testable with one arm.
  2. "Best calibrated" on the pooled contested stratum selects C3, whose low ECE
     is bought by suppressing confidence globally -- it is materially
     UNDER-confident on unanimous images, where the other soft-target arms are
     near-exact. Selecting it alone would carry forward an artefact.

Phase 5 is inference-only, so carrying every arm costs 5 x 3 forward passes.
The constraint that motivated selecting a single arm does not exist here.

Run:  python src/models/phase5_carry_forward.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
OUT = REPORTS / "phase5_carry_forward.json"

CONFIGS = ("C0", "C1", "C2", "C3", "C4")
POOLED = "S-contested (pooled)"
UNANIMOUS = "S-unanimous"

# an arm whose |overconfidence| on the UNANIMOUS stratum exceeds this is treated
# as achieving its ECE by a global confidence shift rather than by being right
# about which images are hard. Fixed here, before the external data exists.
GLOBAL_SHIFT_TOL_POINTS = 5.0


def J(name: str) -> dict:
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def main() -> int:
    if OUT.exists():
        print(f"[P5.0] {OUT.name} already exists; refusing to overwrite.")
        print("       The carry-forward decision is frozen. Delete it deliberately "
              "if it genuinely must be revised, and say so in the report.")
        return 1

    cal = J("phase4_calibration.json")["aggregate_3seed"]
    met = J("phase4_stratified_metrics.json")["aggregate_3seed"]
    amd = J("phase4_amendment.json")

    ev = {}
    for c in CONFIGS:
        u, p = cal[c][UNANIMOUS], cal[c][POOLED]
        ev[c] = {
            "ece_unanimous_points": round(100 * u["ece_vs_expected_accuracy"], 3),
            "ece_contested_points": round(100 * p["ece_vs_expected_accuracy"], 3),
            "overconfidence_unanimous_points": round(u["overconfidence_points"], 3),
            "overconfidence_contested_points": round(p["overconfidence_points"], 3),
            "macro_f1_unanimous_points": round(
                100 * met[c][UNANIMOUS]["annotator_marginalized_macro_f1_mean_3seed"], 3),
            "macro_f1_contested_points": round(
                100 * met[c][POOLED]["annotator_marginalized_macro_f1_mean_3seed"], 3),
        }

    # --- what the literal "best calibrated" rule would have selected -----------
    best_cal = min(CONFIGS, key=lambda c: ev[c]["ece_contested_points"])
    shift = abs(ev[best_cal]["overconfidence_unanimous_points"])
    disqualified = shift > GLOBAL_SHIFT_TOL_POINTS

    # arms whose calibration is NOT a global shift, ranked by contested ECE
    honest = [c for c in CONFIGS
              if abs(ev[c]["overconfidence_unanimous_points"]) <= GLOBAL_SHIFT_TOL_POINTS]
    best_honest = min(honest, key=lambda c: ev[c]["ece_contested_points"]) if honest else None

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5,
        "step": "P5.0",
        "title": "Carry-forward decision for external validation",
        "frozen_before": ("any external image was acquired, cached or scored. The "
                          "decision is a function of Phase 4 artefacts only."),
        "governing_clauses": {
            "blueprint_status_board": ("pre-condition: carry the best-calibrated arm, "
                                       "not the most accurate (Phase 4 sec.4.7)"),
            "phase4_s47": ("Phase 5 should carry the best-calibrated configuration, "
                           "not the most accurate one, into external validation"),
            "rq3_external_half": ("whether the uncertainty ranking is preserved "
                                  "outside the training distribution"),
        },
        "evidence_from_phase4": ev,
        "global_shift_tolerance_points": GLOBAL_SHIFT_TOL_POINTS,
        "literal_rule_evaluation": {
            "rule": "select argmin ECE on the pooled contested stratum",
            "selects": best_cal,
            "its_ece_contested_points": ev[best_cal]["ece_contested_points"],
            "its_overconfidence_unanimous_points":
                ev[best_cal]["overconfidence_unanimous_points"],
            "disqualified_as_global_shift": bool(disqualified),
            "why": (
                f"{best_cal} attains the lowest contested ECE "
                f"({ev[best_cal]['ece_contested_points']} points) but is "
                f"{abs(ev[best_cal]['overconfidence_unanimous_points'])} points "
                f"{'UNDER' if ev[best_cal]['overconfidence_unanimous_points'] < 0 else 'OVER'}"
                f"-confident on unanimous images, beyond the "
                f"{GLOBAL_SHIFT_TOL_POINTS}-point tolerance. Its calibration is "
                f"therefore substantially a global confidence shift, not evidence "
                f"that it knows which images are hard. Carrying it alone would "
                f"carry an artefact into the external test."
            ) if disqualified else (
                f"{best_cal} attains the lowest contested ECE and stays within the "
                f"global-shift tolerance on unanimous images."),
            "best_arm_excluding_global_shift": best_honest,
        },
        "decision": {
            "carry": list(CONFIGS),
            "n_arms": len(CONFIGS),
            "seeds": [1, 2, 3],
            "n_inference_passes": len(CONFIGS) * 3,
            "supersedes": ("the single-arm reading of Phase 4 sec.4.7 recorded on the "
                           "blueprint status board"),
            "rationale": [
                ("RQ3's external half is a question about RANKING preservation. A "
                 "ranking cannot be measured with one arm, so a single-arm "
                 "carry-forward would make the phase's own research question "
                 "untestable."),
                (f"The literal best-calibrated rule selects {best_cal}, which is "
                 f"disqualified above as a global confidence shift. Carrying every "
                 f"arm exposes that pattern externally instead of concealing it "
                 f"behind a single selected model."),
                ("Phase 5 is inference-only. The compute argument that justifies "
                 "selecting one arm during training does not apply: the whole "
                 "carry-forward is 15 forward passes."),
                ("Carrying C0 preserves the Phase 2/3 reference arm, so the external "
                 "drop can be quoted against the internal baseline the rest of the "
                 "thesis uses."),
            ],
            "primary_arm_for_headline_numbers": "C2",
            "primary_arm_rationale": (
                "C2 is the RQ2 treatment arm and the soft-target construction the "
                "thesis is about. Headline external numbers are quoted for C2 with "
                "every other arm tabulated alongside; C3 is retained explicitly as "
                "the calibration control, not as a candidate model."),
        },
        "inherited_outstanding_from_phase4": amd.get("outstanding", []),
        "binding_on_phase5": [
            "no fine-tuning, adaptation or self-training on external data before the "
            "clean transfer numbers are recorded and frozen; any adaptation arm is a "
            "SEPARATE, later, declared comparison against these numbers",
            "Phase 2 training-set normalisation statistics reused unchanged",
            "all intervals >=1,000 resamples (blueprint sec.6; see phase4_amendment "
            "P4-AMD-1)",
        ],
    }

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.0] wrote {OUT}")
    print(f"       literal 'best calibrated' rule selects : {best_cal}")
    print(f"       disqualified as a global shift          : {disqualified}")
    print(f"       best arm excluding global shift         : {best_honest}")
    print(f"       DECISION: carry {', '.join(CONFIGS)} "
          f"({out['decision']['n_inference_passes']} inference passes), "
          f"headline arm {out['decision']['primary_arm_for_headline_numbers']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
