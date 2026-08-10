"""
Phase 6 / P6.3 -- P6-B, confusion geometry with intervals on BOTH sides.

This settles the debt recorded as X3 in reports/phase3b_amendment.json. Phase 3
compared the model's wall-adjacent error share (89.68%) against a human value
(89.8%) and its station-neighbouring share (85.57%) against 93.1%, and called
the first a match and the second a 7.5-point shortfall. The rev-1 amendment
withdrew both: the model shares carried patient-clustered intervals, the human
values were corpus-wide POINT estimates with none, and the station interval
contained the human value. A comparison between an interval and a point is not
a comparison.

Here both sides are measured on the same images, with the same adjacency
definitions, under the same patient-clustered resample, and differenced inside
the bootstrap so the interval is on the difference.

  model side  an error is a prediction differing from an annotator's label;
              marginalized over the four annotators, which is the project's
              primary metric convention and is the ONLY construction that is
              defined on the no-majority stratum (where no modal label exists).
              On S-unanimous all four annotators carry the same label, so this
              collapses exactly to the Phase 3 construction -- which is what
              gate P6.3a checks.
  human side  a disagreement event is a pair of annotators (b, b') whose labels
              differ on that image; all 6 pairs per image are considered.

OTHERCLASS has no position on the (wall x station) grid -- blueprint sec.2.6
shows quality assessment is a different task -- so events involving it are
excluded from both sides, exactly as phase3_confusion.py did.

Gates
  P6.3a  C0's S-unanimous shares reproduce phase3_confusion_structure.json
  P6.3b  adjacency definitions identical to phase4_structure.py (asserted at
         import by phase6_common.selftest)

Output
  reports/phase6_geometry.json
Run:  python src/models/phase6_geometry.py
"""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase6_common as C  # noqa: E402

OUT = C.REPORTS / "phase6_geometry.json"
P3_CONF = C.REPORTS / "phase3_confusion_structure.json"


def geometry_counts(true_idx: np.ndarray, pred_idx: np.ndarray, inv: dict):
    """(n_wall_diff, n_wall_adjacent, n_station_diff, n_station_neighbouring).

    Identical logic to phase3_confusion.py, vectorised over a pair of label
    index arrays instead of iterating a dataframe.
    """
    nwd = nwa = nsd = nsn = 0
    for t, p in zip(true_idx, pred_idx):
        if t == p:
            continue
        wt, st = C.parse_label(inv[int(t)])
        wp, sp = C.parse_label(inv[int(p)])
        if wt is None or wp is None:
            continue
        if wt != wp:
            nwd += 1
            if f"{wt}-{wp}" in C.WALL_ADJACENT:
                nwa += 1
        if st != sp:
            nsd += 1
            if abs(st - sp) == 1:
                nsn += 1
    return nwd, nwa, nsd, nsn


def model_shares(votes: np.ndarray, pred: np.ndarray, inv: dict):
    """Marginalized over the four annotators: every (annotator, prediction)
    mismatch on the image is one error event."""
    nwd = nwa = nsd = nsn = 0
    for a in range(votes.shape[1]):
        d = geometry_counts(votes[:, a], pred, inv)
        nwd += d[0]; nwa += d[1]; nsd += d[2]; nsn += d[3]
    return _shares(nwd, nwa, nsd, nsn)


def human_shares(votes: np.ndarray, inv: dict):
    """Every disagreeing annotator pair on the image is one disagreement event
    -- the same event definition Phase 0 used to produce 89.8 / 93.1."""
    nwd = nwa = nsd = nsn = 0
    for b1, b2 in combinations(range(votes.shape[1]), 2):
        d = geometry_counts(votes[:, b1], votes[:, b2], inv)
        nwd += d[0]; nwa += d[1]; nsd += d[2]; nsn += d[3]
    return _shares(nwd, nwa, nsd, nsn)


def _shares(nwd, nwa, nsd, nsn):
    return {
        "wall_adjacent_pct": 100.0 * nwa / nwd if nwd else np.nan,
        "station_neighbouring_pct": 100.0 * nsn / nsd if nsd else np.nan,
        "n_wall_differing": nwd, "n_station_differing": nsd,
    }


def main() -> None:
    t0 = time.time()
    pre = C.prereg()
    rule = pre["endpoints"]["P6-B"]
    panel, meta = C.build_panel()
    inv = C.inv_classes()
    votes = C.votes_matrix(panel)
    patients = panel.patient.to_numpy()
    arms = meta["arms"]

    # ---- GATE P6.3a -------------------------------------------------------
    # On S-unanimous the four annotator labels are identical, so the
    # marginalized model construction collapses to Phase 3's single-label one.
    # It must therefore reproduce the published shares exactly.
    ref = json.loads(P3_CONF.read_text(encoding="utf-8"))
    m_un = C.stratum_mask(panel, "S-unanimous")
    per_seed_un = [model_shares(votes[m_un], panel[f"pred_C0_{s}"].to_numpy()[m_un], inv)
                   for s in C.SEEDS]
    got_w = round(float(np.mean([x["wall_adjacent_pct"] for x in per_seed_un])), 2)
    got_s = round(float(np.mean([x["station_neighbouring_pct"] for x in per_seed_un])), 2)
    gate = {
        "recomputed_wall_adjacent_pct": got_w,
        "phase3_published_wall_adjacent_pct": ref["mean_wall_adjacent_pct_3seed"],
        "recomputed_station_neighbouring_pct": got_s,
        "phase3_published_station_neighbouring_pct": ref["mean_station_neighbouring_pct_3seed"],
    }
    ok = (got_w == ref["mean_wall_adjacent_pct_3seed"] and
          got_s == ref["mean_station_neighbouring_pct_3seed"])
    gate["status"] = "PASS" if ok else "FAIL"
    if not ok:
        raise SystemExit(f"GATE P6.3a FAILED: {gate}")

    # ---- point estimates and the paired bootstrap --------------------------
    results = {}
    for stratum in C.STRATA:
        m = C.stratum_mask(panel, stratum)
        rows = np.where(m)[0]
        v = votes[m]
        hs = human_shares(v, inv)
        entry = {"n_images": int(m.sum()),
                 "human": {k: (round(x, 2) if isinstance(x, float) and np.isfinite(x)
                               else (None if isinstance(x, float) else x))
                           for k, x in hs.items()},
                 "by_arm": {}}
        for arm in arms:
            per_seed = [model_shares(v, panel[f"pred_{arm}_{s}"].to_numpy()[m], inv)
                        for s in C.SEEDS]
            entry["by_arm"][arm] = {
                "wall_adjacent_pct_3seed": round(float(np.nanmean(
                    [x["wall_adjacent_pct"] for x in per_seed])), 2),
                "station_neighbouring_pct_3seed": round(float(np.nanmean(
                    [x["station_neighbouring_pct"] for x in per_seed])), 2),
                "per_seed": [{k: (round(x, 2) if isinstance(x, float) and np.isfinite(x)
                                  else (None if isinstance(x, float) else x))
                              for k, x in ps.items()} for ps in per_seed],
            }

        # paired: one patient resample, both sides scored on it, then differenced
        pats = patients[rows]
        boot = {arm: {"wall": [], "station": []} for arm in arms}
        boot_h = {"wall": [], "station": []}
        for local in C.patient_resamples(pats, C.N_BOOT_P6):
            r = rows[local]
            vr = votes[r]
            h = human_shares(vr, inv)
            boot_h["wall"].append(h["wall_adjacent_pct"])
            boot_h["station"].append(h["station_neighbouring_pct"])
            for arm in arms:
                mo = model_shares(vr, panel[f"pred_{arm}_{C.SEEDS[0]}"].to_numpy()[r], inv)
                boot[arm]["wall"].append(mo["wall_adjacent_pct"] - h["wall_adjacent_pct"])
                boot[arm]["station"].append(
                    mo["station_neighbouring_pct"] - h["station_neighbouring_pct"])

        # On a unanimity-defined stratum there are NO annotator disagreement
        # events at all, so the human geometry is undefined there -- not merely
        # imprecise. Detected numerically and declared; see comparable_note.
        entry["human_geometry_defined"] = bool(hs["n_wall_differing"] > 0
                                               or hs["n_station_differing"] > 0)
        for axis, key in (("wall", "wall_adjacent"),
                          ("station", "station_neighbouring")):
            v = np.asarray(boot_h[axis], dtype=float)
            v = v[np.isfinite(v)]
            entry["human"][f"{key}_ci95"] = (
                [round(x, 2) for x in C.ci95(v)] if v.size >= 10 else [None, None])
        for arm in arms:
            for axis, key in (("wall", "wall_adjacent"), ("station", "station_neighbouring")):
                d = np.asarray(boot[arm][axis])
                d = d[np.isfinite(d)]
                if d.size < 10:
                    entry["by_arm"][arm][f"{key}_delta_ci95"] = [None, None]
                    entry["by_arm"][arm][f"{key}_verdict"] = "NOT ESTIMABLE"
                    continue
                lo, hi = C.ci95(d)
                entry["by_arm"][arm][f"{key}_delta_mean"] = round(float(d.mean()), 2)
                entry["by_arm"][arm][f"{key}_delta_ci95"] = [round(lo, 2), round(hi, 2)]
                entry["by_arm"][arm][f"{key}_verdict"] = C.verdict_three_way(
                    lo, hi,
                    above="DIVERGES FROM HUMAN GEOMETRY (model more adjacent)",
                    below="DIVERGES FROM HUMAN GEOMETRY (model less adjacent)",
                    null="MIRRORS HUMAN GEOMETRY")
        results[stratum] = entry

    headline = "C2"
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 6, "step": "P6.3", "endpoint": "P6-B",
        "question": rule["question"], "debt": rule["debt"],
        "definitions": rule["definitions"],
        "verdict_rule": rule["verdict_rule"],
        "event_definitions": {
            "model": ("prediction differing from an annotator's label, marginalized "
                      "over all four annotators"),
            "human": "a disagreeing annotator pair; all 6 pairs per image considered",
            "excluded": ("events involving OTHERCLASS, which has no position on the "
                         "(wall x station) grid"),
        },
        "arms": arms, "seeds": list(C.SEEDS), "headline_arm": headline,
        "gates": {"P6.1a": meta["gate_P6.1a"], "P6.3a": gate,
                  "P6.3b": "PASS -- asserted at import by phase6_common.selftest()"},
        "x3_settlement": None,
        "results": results,
        "runtime_sec": None,
    }
    un = results["S-unanimous"]
    pooled = results[C.POOLED_CONTESTED]["by_arm"][headline]
    out["x3_settlement"] = {
        "arm": headline,
        "s_unanimous_human_geometry_defined": un["human_geometry_defined"],
        "finding": (
            "X3 is settled, and by a stronger argument than the one that raised it. "
            "The amendment withdrew the Phase 3 claim because a model INTERVAL was "
            "compared against a human POINT estimate. Measuring both sides on the "
            "same images shows something more basic: S-unanimous is defined by all "
            "four annotators agreeing, so it contains ZERO annotator disagreement "
            "events and the human error geometry is UNDEFINED there -- not imprecise, "
            "undefined. The Phase 3 comparison therefore set the model's geometry on "
            "the unanimous stratum against a human benchmark computed over the whole "
            "corpus, which is dominated by contested images. It was a cross-population "
            "comparison, and neither the 0.12-point 'match' nor the 7.5-point "
            "'shortfall' was ever a like-for-like quantity."
            if not un["human_geometry_defined"] else
            "Both sides are defined on S-unanimous and are compared directly."),
        "where_the_comparison_is_defined": (
            "the contested strata, where annotators genuinely disagree and both "
            "geometries exist on the same images"),
        "pooled_contested": {
            "wall": {"delta": pooled.get("wall_adjacent_delta_mean"),
                     "ci95": pooled.get("wall_adjacent_delta_ci95"),
                     "verdict": pooled.get("wall_adjacent_verdict")},
            "station": {"delta": pooled.get("station_neighbouring_delta_mean"),
                        "ci95": pooled.get("station_neighbouring_delta_ci95"),
                        "verdict": pooled.get("station_neighbouring_verdict")},
        },
        "amendment": ("P6-AMD-2: the pre-registration assumed the human geometry "
                      "would be estimable on every stratum. It is not estimable on "
                      "S-unanimous, for a structural reason. The S-unanimous row is "
                      "reported as NOT DEFINED rather than as a verdict, and the "
                      "endpoint is carried by the contested strata."),
    }
    out["verdict_summary"] = {}
    for s in C.STRATA:
        if not results[s]["human_geometry_defined"]:
            v = {"wall": "NOT DEFINED (no human disagreement events on this stratum)",
                 "station": "NOT DEFINED (no human disagreement events on this stratum)"}
            for arm in arms:
                results[s]["by_arm"][arm]["wall_adjacent_verdict"] = v["wall"]
                results[s]["by_arm"][arm]["station_neighbouring_verdict"] = v["station"]
        else:
            v = {"wall": results[s]["by_arm"][headline].get("wall_adjacent_verdict"),
                 "station": results[s]["by_arm"][headline].get("station_neighbouring_verdict")}
        out["verdict_summary"][s] = v
    out["runtime_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"[P6.3] gate P6.3a {gate['status']} "
          f"(wall {got_w} station {got_s} vs published "
          f"{ref['mean_wall_adjacent_pct_3seed']}/{ref['mean_station_neighbouring_pct_3seed']})")
    print(f"[P6.3] P6-B, headline arm {headline}:")
    def f2(x):
        return "  n/a " if x is None else f"{x:6.2f}"

    for s in C.STRATA:
        e = results[s]; a = e["by_arm"][headline]
        print(f"   {s:24s} wall model {f2(a['wall_adjacent_pct_3seed'])} vs human "
              f"{f2(e['human']['wall_adjacent_pct'])}  d={a.get('wall_adjacent_delta_mean')} "
              f"{a.get('wall_adjacent_delta_ci95')} -> {a.get('wall_adjacent_verdict')}")
        print(f"   {'':24s} stn  model {f2(a['station_neighbouring_pct_3seed'])} vs human "
              f"{f2(e['human']['station_neighbouring_pct'])}  d={a.get('station_neighbouring_delta_mean')} "
              f"{a.get('station_neighbouring_delta_ci95')} -> {a.get('station_neighbouring_verdict')}")
    print(f"[P6.3] wrote {OUT.name} in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
