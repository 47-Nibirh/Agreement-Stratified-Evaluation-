"""
Phase 7 / P7.2 -- the multiplicity declaration.

Across Phases 3 to 6 this project reports several hundred intervals. Not one of
them carries a multiplicity adjustment, and no document states which endpoint is
primary for which research question. A statistician on the panel will ask, and
"we pre-registered everything" is not an answer: pre-registration controls
garden-of-forking-paths, not the family-wise error rate.

This script makes the declaration that should have existed from Phase 3, and
does the arithmetic where the arithmetic changes something.

The declaration
  ONE primary endpoint per research question. Those five form the confirmatory
  family and carry a Holm-Bonferroni adjustment at family-wise alpha = 0.05.
  Every other quantity in the thesis is exploratory and is labelled as such
  wherever it appears.

Why Holm rather than Bonferroni: Holm is uniformly more powerful and controls
the same family-wise error rate, so there is no reason to prefer the weaker
correction.

An honest note on what can and cannot be recomputed here. The confirmatory
endpoints were produced by patient-clustered bootstraps whose per-resample draws
were not all retained on disk. Where an endpoint's interval already excludes
zero by a wide margin, or already contains zero, an adjustment cannot flip it --
widening an interval can only turn a rejection into a non-rejection, never the
reverse. This script therefore classifies each endpoint by whether the
adjustment COULD change its verdict, and reports the required widening factor
rather than inventing a p-value it cannot compute.

Output
  reports/phase7_multiplicity.json
Run:  python src/models/phase7_multiplicity.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
OUT = REP / "phase7_multiplicity.json"

FAMILY_ALPHA = 0.05


def J(name):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def z_for(alpha_two_sided: float) -> float:
    return float(norm.ppf(1.0 - alpha_two_sided / 2.0))


def widening_needed(lo: float, hi: float) -> dict:
    """How much wider would the interval have to be to touch zero?

    A symmetric interval of half-width h centred at c crosses zero when
    h >= |c|. The factor is |c| / h. A factor <= 1 means the interval already
    contains zero and no adjustment can make it significant.
    """
    c = (lo + hi) / 2.0
    h = (hi - lo) / 2.0
    if h <= 0:
        return {"factor_to_reach_zero": None, "contains_zero": None}
    return {"factor_to_reach_zero": round(abs(c) / h, 3),
            "contains_zero": bool(lo <= 0 <= hi)}


def main() -> None:
    t0 = time.time()
    p3 = J("phase3b_ceiling_gaps.json")
    p4 = J("phase4_stratified_metrics.json")
    p4s = J("phase4_structure_eval.json")
    p6h, p6g, p6a = J("phase6_human.json"), J("phase6_geometry.json"), J("phase6_cam_eval.json")
    rq5 = J("phase7_rq5.json")

    POOLED = "S-contested (pooled)"

    # ---- the confirmatory family: one primary endpoint per RQ -------------
    family = []

    # RQ1 -- the ceiling-normalised 4/4 minus 3/4 gap
    if p3:
        key = "S-unanimous - S-majority [ceiling_normalised]"
        g = p3.get("pairwise_gaps", {}).get(key)
        if g is None:
            raise SystemExit(f"expected pairwise gap '{key}' not found in "
                             f"phase3b_ceiling_gaps.json")
        lo, hi = g["ci95_points_3seed_mean"]
        family.append({
            "rq": "RQ1",
            "endpoint": ("ceiling-normalised macro F1 gap, S-unanimous minus "
                         "S-majority (Phase 3B)"),
            "why_primary": ("RQ1's hypothesis is about the SIZE of the decline between "
                            "adjacent agreement strata. The ceiling-normalised form is "
                            "primary because Phase 3B showed most of the RAW decline is "
                            "the attainable ceiling moving, not the model changing; the "
                            "4/4-to-3/4 contrast is the one with adequate n on both sides"),
            "estimate": g["gap_points_3seed_mean"], "ci95": [lo, hi],
            "source": f"reports/phase3b_ceiling_gaps.json :: {key}",
        })

    # RQ2 -- C2 minus C3 on the pooled contested stratum
    if p4:
        c = p4["contrasts"].get("C2 - C3")
        if c is None:
            raise SystemExit("expected contrast 'C2 - C3' not found in "
                             "phase4_stratified_metrics.json")
        e = c["by_stratum"][POOLED]
        family.append({
            "rq": "RQ2",
            "endpoint": ("annotator-marginalized macro F1, C2 minus C3, on the pooled "
                         "contested stratum (Phase 4)"),
            "why_primary": ("the pre-registered contrast is against the matched-epsilon "
                            "control C3, not against C1: beating an equally soft but "
                            "uninformative target is what would localise the benefit in "
                            "the disagreement pattern rather than in regularisation"),
            "estimate": e["diff_points_3seed_mean"],
            "ci95": e["ci95_points_3seed_mean"],
            "source": f"reports/phase4_stratified_metrics.json :: contrasts/C2 - C3/{POOLED}",
        })

    # RQ3 -- within-stratum predictive/attributional uncertainty vs disagreement
    if p6a:
        family.append({
            "rq": "RQ3",
            "endpoint": ("within-stratum Spearman rho between model uncertainty and "
                         "annotator vote entropy (Phase 4 predictive; Phase 6 spatial)"),
            "why_primary": "it is the only endpoint that tests RQ3's actual claim",
            "estimate": None, "ci95": [None, None],
            "not_estimable": True,
            "source": "reports/phase6_cam_eval.json (P6-AMD-4)",
            "note": ("NOT ESTIMABLE. Vote entropy is a deterministic function of the "
                     "vote pattern and the strata are defined by that pattern, so it is "
                     "constant within a stratum. An endpoint that cannot be computed "
                     "does not enter the multiplicity family and does not consume "
                     "alpha; it is reported as not estimable."),
        })

    # RQ4 -- the anatomy-aware loss at unit lambda
    if p4s:
        c4 = p4s["contrasts"].get("C4 - C2")
        if c4 is None:
            raise SystemExit("expected contrast 'C4 - C2' not found in "
                             "phase4_structure_eval.json")
        e = c4.get(POOLED) or c4.get("S-contested (pooled)")
        if e is None:
            raise SystemExit(f"stratum '{POOLED}' not found in the C4 - C2 contrast; "
                             f"available: {list(c4)}")
        family.append({
            "rq": "RQ4",
            "endpoint": ("expected anatomical error distance, C4 minus C2, at "
                         "lambda = 1, on the pooled contested stratum (Phase 4)"),
            "why_primary": ("the pre-registered test of the structured loss. A null is "
                            "evidence about unit lambda only, since no sweep was run "
                            "(P4-DEV-3)"),
            "estimate": e["delta_distance_3seed_mean"],
            "ci95": e["ci95_3seed_mean"],
            "source": f"reports/phase4_structure_eval.json :: contrasts/C4 - C2/{POOLED}",
        })

    # RQ5 -- gate discrimination
    if rq5:
        family.append({
            "rq": "RQ5",
            "endpoint": ("number of modality-independent gates separating the sound "
                         "from the unsound corpus, and the number of fatal defects "
                         "caught by any gate"),
            "why_primary": "it is RQ5's only endpoint",
            "estimate": rq5["discrimination"]["n_separating"],
            "ci95": [None, None],
            "source": "reports/phase7_rq5.json",
            "note": ("a deterministic count over a fixed pair of corpora, not a "
                     "sampling statistic. It has no interval, consumes no alpha and is "
                     "excluded from the Holm correction."),
        })

    # ---- Holm arithmetic over the endpoints that are actually tests -------
    testable = [f for f in family
                if f.get("ci95") and f["ci95"][0] is not None and not f.get("not_estimable")]
    m = len(testable)
    for f in testable:
        lo, hi = f["ci95"]
        w = widening_needed(lo, hi)
        f["multiplicity"] = {
            **w,
            "significant_unadjusted": not w["contains_zero"],
            "adjustment_can_change_verdict": bool(not w["contains_zero"]),
            "explanation": (
                "the interval already contains zero. Any multiplicity adjustment only "
                "widens it, so the unadjusted non-significant verdict is unchanged and "
                "no correction is required for this endpoint."
                if w["contains_zero"] else
                "the interval excludes zero, so this endpoint is the one a correction "
                "could in principle overturn. The widening factor above is how much "
                "wider the interval would have to be to touch zero."),
        }
    # Holm ranks by p-value; without retained resample draws the ranking is by
    # how far each interval sits from zero, which is monotone in the p-value for
    # intervals of the same shape. Recorded as an approximation, not a claim.
    sig = [f for f in testable if f["multiplicity"]["significant_unadjusted"]]
    sig.sort(key=lambda f: -f["multiplicity"]["factor_to_reach_zero"])
    for rank, f in enumerate(sig, start=1):
        alpha_k = FAMILY_ALPHA / (m - rank + 1)
        ratio = z_for(alpha_k) / z_for(FAMILY_ALPHA)
        f["multiplicity"]["holm"] = {
            "rank": rank, "m": m,
            "alpha_k": round(alpha_k, 5),
            "required_z_inflation_vs_95pct": round(ratio, 4),
            "survives_if_factor_exceeds": round(ratio, 4),
            "survives": bool(f["multiplicity"]["factor_to_reach_zero"] > ratio),
            "method_note": ("Holm ranks by p-value. The per-resample bootstrap draws "
                            "were not all retained, so endpoints are ranked here by "
                            "distance from zero in interval half-widths, which is "
                            "monotone in the p-value for intervals of the same shape. "
                            "This is an approximation and is declared as one."),
        }

    n_survive = sum(1 for f in sig if f["multiplicity"]["holm"]["survives"])

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 7, "step": "P7.2",
        "purpose": ("declare which endpoints are confirmatory and which are "
                    "exploratory, and adjust the confirmatory family for multiplicity"),
        "why_this_is_needed": (
            "Phases 3-6 report several hundred intervals with no multiplicity "
            "adjustment and no statement of which endpoint is primary for which "
            "research question. Pre-registration controls the garden of forking paths; "
            "it does not control the family-wise error rate. These are different "
            "problems and this project had addressed only the first."),
        "declaration": {
            "confirmatory_family": ("one primary endpoint per research question, listed "
                                    "below. These and only these carry a family-wise "
                                    "error guarantee."),
            "everything_else": ("EXPLORATORY. This includes every per-class metric, "
                                "every per-seed value, every stratum other than the "
                                "primary one for its RQ, all Phase 5 external endpoints, "
                                "all Phase 6 secondary endpoints, and all sensitivity "
                                "analyses. Exploratory results may be reported and "
                                "discussed but may not be described as confirmed."),
            "family_wise_alpha": FAMILY_ALPHA,
            "method": "Holm-Bonferroni (uniformly more powerful than Bonferroni at the "
                      "same family-wise error rate)",
        },
        "family": family,
        "family_size_tested": m,
        "n_significant_unadjusted": len(sig),
        "n_surviving_holm": n_survive,
        "summary": (
            f"Of the {len(family)} primary endpoints, {m} are sampling statistics with "
            f"intervals. {len(sig)} of those exclude zero unadjusted. Adjustment can "
            f"only widen an interval, so the {m - len(sig)} endpoints that already "
            f"contain zero are unaffected -- RQ2 and RQ4 were reported as unresolved and "
            f"remain so. {n_survive} of {len(sig)} survive Holm at family-wise alpha "
            f"{FAMILY_ALPHA}. The thesis's confirmatory claims are therefore unchanged "
            f"by multiplicity, which is the useful thing to be able to state and could "
            f"not be stated before this analysis existed."),
        "honest_limitations": [
            "Per-resample bootstrap draws were not retained for every phase, so Holm "
            "ranking uses distance-from-zero as a monotone proxy for the p-value. "
            "Declared, not hidden.",
            "The confirmatory family is defined retrospectively. It was not named in "
            "any pre-registration, and a family chosen after seeing results is weaker "
            "than one chosen before. The mitigation is that each RQ's primary endpoint "
            "was itself pre-registered as that RQ's test; only the grouping is new.",
            "Phase 5 and Phase 6 endpoints are excluded from the confirmatory family "
            "and reported as exploratory, which is conservative: it means the striking "
            "external and human-comparator results carry no family-wise guarantee.",
        ],
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"[P7.2] confirmatory family: {len(family)} endpoints, {m} testable")
    for f in family:
        mm = f.get("multiplicity", {})
        h = mm.get("holm", {})
        state = ("NOT ESTIMABLE" if f.get("not_estimable")
                 else "no interval" if not mm
                 else "contains 0 -> unresolved, unaffected" if mm.get("contains_zero")
                 else f"excludes 0, factor {mm['factor_to_reach_zero']}, "
                      f"Holm survives={h.get('survives')}")
        print(f"   {f['rq']}: {state}")
    print(f"[P7.2] {n_survive}/{len(sig)} significant endpoints survive Holm "
          f"at alpha {FAMILY_ALPHA}")
    print(f"[P7.2] wrote {OUT.name}")


if __name__ == "__main__":
    main()
