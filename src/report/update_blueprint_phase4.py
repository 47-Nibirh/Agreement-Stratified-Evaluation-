"""
Rewrite the blueprint's STATUS BOARD and completed-task register for Phase 4.

The blueprint is the one document in this project a reader treats as the
authoritative summary, so it is the last place a hand-typed number should
appear. This script regenerates the Phase 4 row and register entries from the
verdict fields in reports/phase4_*.json, exactly as the report does, and
bumps the version header.

It is idempotent: running it twice produces the same file, because it replaces
a delimited block rather than appending.

Run:  python src/report/update_blueprint_phase4.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BP = ROOT / "THESIS_RESEARCH_BLUEPRINT.md"
REP = ROOT / "reports"
VERSION = "3.4"

BEGIN = "<!-- PHASE4-REGISTER:BEGIN -->"
END = "<!-- PHASE4-REGISTER:END -->"


def J(name):
    p = REP / name
    if not p.exists():
        raise SystemExit(f"missing {name}; run the Phase 4 pipeline first")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    MET, CAL = J("phase4_stratified_metrics.json"), J("phase4_calibration.json")
    UNC, STR = J("phase4_uncertainty.json"), J("phase4_structure_eval.json")
    LOAO, COH = J("phase4_loao.json"), J("phase4_cohort.json")
    PRE = J("phase4_prereg.json")

    if MET.get("partial_sweep"):
        raise SystemExit("refusing to update the blueprint from a partial seed sweep; "
                         f"phase4_stratified_metrics.json was built on seeds "
                         f"{MET['seeds']}")

    P = "S-contested (pooled)"
    agg = MET["aggregate_3seed"]
    cagg = CAL["aggregate_3seed"]
    cfgs = MET["configurations_evaluated"]
    v2 = MET["verdicts"]["RQ2_primary"]
    vc = CAL["verdicts"]["RQ2_calibration"]
    v4 = STR["verdicts"]["RQ4"]
    g = MET["contrasts"]["C2 - C3"]["by_stratum"][P]
    gc = CAL["contrasts"]["C2 - C3"][P]
    gd = STR["contrasts"]["C4 - C2"][P]
    g10 = MET["contrasts"]["C1 - C0"]["by_stratum"][P]
    rq3_sup = [c for c, v in UNC["verdicts"].items() if v.get("verdict") == "SUPPORTED"]

    def f1(c, st=P):
        return 100 * agg[c][st]["annotator_marginalized_macro_f1_mean_3seed"]

    def ece(c, st=P):
        return 100 * cagg[c][st]["ece_vs_expected_accuracy"]

    row = (f"| **4** | Soft-label & uncertainty training | ✅ **COMPLETE** | "
           f"`Phase4_Report.docx/.pdf` — C0–C4 on a cohort held constant. "
           f"**RQ2 accuracy {v2['verdict']}** (C2−C3 on the pooled contested "
           f"stratum {g['diff_points_3seed_mean']:+.2f} pts, CI "
           f"{g['ci95_points_3seed_mean'][0]:+.2f} to "
           f"{g['ci95_points_3seed_mean'][1]:+.2f}). "
           f"**RQ2 calibration {vc['verdict']}** (ΔECE "
           f"{gc['delta_ece_points_3seed_mean']:+.2f} pts, CI "
           f"{gc['ci95_points_3seed_mean'][0]:+.2f} to "
           f"{gc['ci95_points_3seed_mean'][1]:+.2f} — the *control* is the better "
           f"calibrated arm on contested images). "
           f"**RQ3** supported for {', '.join(rq3_sup) if rq3_sup else 'no configuration'}. "
           f"**RQ4 {v4['verdict']}** at λ=1. |")

    reg = [
        f"- [x] **Phase 4 cohort and cache gated** — extended cohort E = "
        f"{COH['by_split']['Train']:,} train / {COH['by_split']['Validation']:,} "
        f"validation (majority-or-better), "
        f"{100 * COH['fraction_contested_by_split']['Train']:.1f}% contested; gates "
        f"P4.1a–e pass, and all "
        f"{J('phase4_cache_gate.json')['gate_p4_2_byte_identity']['n_shared_with_phase2_cache']:,} "
        f"images shared with the Phase 2 cache decode **bit-identically** (P4.2)",

        f"- [x] **Phase 4 pre-registered before training** — frozen "
        f"{PRE['frozen_at']}; ε for the C3 control **derived** by matching the "
        f"probability mass C2 displaces from the modal label "
        f"({PRE['epsilon_derivation_detail']['c2_mean_mass_displaced']:.6f} → ε = "
        f"{PRE['configurations']['C3']['label_smoothing_epsilon']:.6f}; entropy "
        f"matching would have given "
        f"{PRE['epsilon_derivation_detail']['epsilon_entropy_matched']:.6f}), λ fixed "
        f"a priori at unit weight, verdict rules fixed for RQ2/RQ3/RQ4",

        f"- [x] **Phase 4 executed — 12 runs, C1–C4 × 3 seeds** — every arm shares the "
        f"backbone, schedule, augmentation, normalisation and selection criterion of "
        f"Phase 2, so only the target differs. Annotator-marginalized macro F1 on the "
        f"pooled contested stratum: " +
        " · ".join(f"{c} {f1(c):.2f}" for c in cfgs),

        f"- [x] **RQ2 accuracy — {v2['verdict']}** — the pre-registered contrast is "
        f"C2−C3, not C2−C1: beating an *equally soft but uninformative* target is what "
        f"would localise the benefit in the disagreement pattern rather than in "
        f"regularisation. Measured "
        f"{g['diff_points_3seed_mean']:+.2f} pts (CI "
        f"{g['ci95_points_3seed_mean'][0]:+.2f} to "
        f"{g['ci95_points_3seed_mean'][1]:+.2f}). Adding the contested images at a "
        f"hard target (C1−C0) gives {g10['diff_points_3seed_mean']:+.2f} pts (CI "
        f"{g10['ci95_points_3seed_mean'][0]:+.2f} to "
        f"{g10['ci95_points_3seed_mean'][1]:+.2f}), but is confounded by C0's "
        f"different validation set and longer training, so it is descriptive only",

        f"- [x] **RQ2 calibration — {vc['verdict']}, and the reversal is the finding** "
        f"— ECE on the pooled contested stratum: " +
        " · ".join(f"{c} {ece(c):.2f}%" for c in cfgs) +
        f". The generic control C3 is far better calibrated there than the "
        f"vote-proportion arm C2 (Δ {gc['delta_ece_points_3seed_mean']:+.2f} pts, CI "
        f"{gc['ci95_points_3seed_mean'][0]:+.2f} to "
        f"{gc['ci95_points_3seed_mean'][1]:+.2f}). But on the unanimous stratum the "
        f"order reverses (" +
        " · ".join(f"{c} {ece(c, 'S-unanimous'):.2f}%" for c in cfgs) +
        f"): uniform smoothing suppresses confidence globally, so it is "
        f"*under*confident where annotators agree, whereas C2 is trained one-hot "
        f"there and is nearly exact. **No configuration achieves acceptable "
        f"calibration on contested images**, which relocates the Phase 3 finding from "
        f"'an artefact of consensus-only training' to a property of the problem",

        f"- [x] **RQ3 — the Phase 3 artefact reproduces in every configuration** — the "
        f"pooled predictive-vs-vote entropy correlation stays several times the "
        f"within-stratum value for every arm, confirming that the pooled quantity the "
        f"literature would report mostly measures which stratum an image is in. "
        f"Supported for {', '.join(rq3_sup) if rq3_sup else 'no configuration'} on "
        f"S-majority",

        f"- [x] **RQ4 — {v4['verdict']} at λ=1** — anatomical error distance C4−C2 = "
        f"{gd['delta_distance_3seed_mean']:+.5f} (CI {gd['ci95_3seed_mean'][0]:+.5f} "
        f"to {gd['ci95_3seed_mean'][1]:+.5f}). No λ sweep was run (P4-DEV-3), so this "
        f"is evidence about unit weight, not about anatomy-aware losses in general",

        f"- [x] **Leave-one-annotator-out** — the RQ2 verdict is "
        f"{'invariant' if LOAO['rq2_verdict_invariant_to_dropping_any_single_annotator'] else 'NOT invariant'} "
        f"to dropping any single annotator, FG2 included. Training-side LOAO declared "
        f"unexecuted for budget rather than omitted",

        f"- ⚠️ **The pre-registered epoch cap bound** — "
        f"{sum(1 for c in ('C1', 'C2', 'C3', 'C4') for s in (1, 2, 3) if (REP / f'phase4_run_{c}_seed{s}.json').exists() and json.loads((REP / f'phase4_run_{c}_seed{s}.json').read_text(encoding='utf-8'))['stop_reason'] == 'epoch_cap')} "
        f"of 12 runs stopped at the cap rather than by early stopping. It applies "
        f"identically to C1–C4 so the target contrasts are unaffected, but the "
        f"absolute scores are lower bounds and C1−C0 is not a controlled comparison",
    ]

    text = BP.read_text(encoding="utf-8")

    text = re.sub(r"# Master Research Blueprint — v[\d.]+",
                  f"# Master Research Blueprint — v{VERSION}", text, count=1)
    text = re.sub(r"\*\*Version:\*\* [\d.]+ — [\d-]+",
                  f"**Version:** {VERSION} — {time.strftime('%Y-%m-%d')}", text, count=1)
    text = re.sub(r"\*\*Status:\*\* .*",
                  "**Status:** ✅ Phases 0–4 complete; Phase 5 ready to start", text,
                  count=1)
    text = re.sub(r"^\| \*\*4\*\* \|.*$", row, text, count=1, flags=re.M)
    text = re.sub(r"^(\| \*\*5\*\* \| External validation \| )⬜ Not started",
                  r"\1⬜ Not started — **pre-condition:** carry the best-*calibrated* "
                  r"arm, not the most accurate (Phase 4 §4.7)", text, count=1, flags=re.M)

    block = BEGIN + "\n\n" + "\n".join(reg) + "\n\n" + END
    if BEGIN in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block, text,
                      flags=re.S)
    else:
        anchor = "\n---\n\n## 1. What changed from v2.0"
        text = text.replace(anchor, "\n" + block + anchor, 1)

    BP.write_text(text, encoding="utf-8")
    print(f"blueprint updated to v{VERSION}")
    print(f"  Phase 4 row: RQ2 accuracy {v2['verdict']}, calibration {vc['verdict']}, "
          f"RQ4 {v4['verdict']}")
    print(f"  {len(reg)} register entries written between the delimiters")


if __name__ == "__main__":
    main()
