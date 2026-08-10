"""
Phase 0 / Step 4 - Structural decomposition of disagreement, and provenance
heterogeneity checks.

The 22 SSS landmark codes are not arbitrary. Following the Kenshi Yao protocol
as implemented in the GastroHUN acquisition, each code is a (WALL, STATION)
pair:

    WALL    G = greater curvature, A = anterior wall,
            L = lesser curvature,  P = posterior wall
    STATION 1 = antrum                    (G1 A1 L1 P1)
            2 = distal gastric body       (G2 A2 L2 P2)
            3 = upper-middle gastric body (G3 A3 L3 P3)
            4 = retroflexion, cardia/fundus (G4 A4 L4 P4)
            5 = retroflexion, lesser curvature exposed (A5 L5 P5)
            6 = final aligned view        (A6 L6 P6)

This lets every annotator disagreement be decomposed into an interpretable
axis: same station / different wall (rotational ambiguity about the gastric
axis) versus same wall / different station (depth ambiguity along it). That
decomposition is the empirical basis for an anatomy-aware loss, and is not
reported in the dataset descriptor.

Also tests whether the two image provenance streams (direct endoscope capture
vs frame grabbed from videoendoscopy) differ in annotator agreement, which
would make source_type a confounder.

Output: reports/gastrohun_structure.json

Run:  python src/data/gastrohun_structure.py
"""

from __future__ import annotations

import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ROOT / "official_splits" / "image_classification.csv"
META = ROOT / "metadata" / "gastrohun-image-metadata.json"
OUT = ROOT / "reports" / "gastrohun_structure.json"

ANN = ["FG1 (Team A)", "FG2 (Team A)", "G1 (Team B)", "G2 (Team B)"]
SHORT = {"FG1 (Team A)": "FG1", "FG2 (Team A)": "FG2",
         "G1 (Team B)": "G1", "G2 (Team B)": "G2"}

WALL_NAME = {
    "G": "Greater curvature",
    "A": "Anterior wall",
    "L": "Lesser curvature",
    "P": "Posterior wall",
}
STATION_NAME = {
    1: "Antrum",
    2: "Distal gastric body",
    3: "Upper-middle gastric body",
    4: "Retroflexion - cardia / fundus",
    5: "Retroflexion - lesser curvature exposed",
    6: "Final aligned view",
}


def parse(code: str) -> tuple[str | None, int | None]:
    """'A5' -> ('A', 5); 'OTHERCLASS' -> (None, None)."""
    if code == "OTHERCLASS":
        return None, None
    return code[0], int(code[1:])


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(SPLITS, index_col=0)
    df["patient"] = df["num patient"].astype(int)
    meta = pd.DataFrame(json.load(open(META, encoding="utf-8")))
    df = df.merge(meta[["filename", "source_type", "width", "height", "kilobytes"]],
                  on="filename", how="left")

    classes = sorted(set(pd.unique(df[ANN].to_numpy().ravel()).tolist()))
    n = len(df)

    # ---- 1. taxonomy table ------------------------------------------------
    taxonomy = []
    for c in classes:
        w, s = parse(c)
        taxonomy.append(
            {
                "code": c,
                "wall": w, "wall_name": WALL_NAME.get(w) if w else None,
                "station": s, "station_name": STATION_NAME.get(s) if s else None,
                "is_landmark": c != "OTHERCLASS",
            }
        )

    # ---- 2. decomposition of every pairwise disagreement ------------------
    buckets = {
        "same_station_different_wall": 0,
        "same_wall_different_station": 0,
        "different_wall_and_station": 0,
        "landmark_vs_OTHERCLASS": 0,
    }
    station_gap: list[int] = []
    wall_pair_counts: dict[str, int] = {}
    station_pair_counts: dict[str, int] = {}
    per_station_disagree: dict[int, int] = {s: 0 for s in STATION_NAME}
    per_station_total: dict[int, int] = {s: 0 for s in STATION_NAME}

    lab = df[ANN].to_numpy()
    for row in lab:
        for a, b in combinations(range(4), 2):
            ca, cb = row[a], row[b]
            if ca == cb:
                w, s = parse(ca)
                if s is not None:
                    per_station_total[s] += 1
                continue
            wa, sa = parse(ca)
            wb, sb = parse(cb)
            if wa is None or wb is None:
                buckets["landmark_vs_OTHERCLASS"] += 1
                for s_ in (sa, sb):
                    if s_ is not None:
                        per_station_disagree[s_] += 1
                        per_station_total[s_] += 1
                continue
            if sa == sb:
                buckets["same_station_different_wall"] += 1
                key = "-".join(sorted([wa, wb]))
                wall_pair_counts[key] = wall_pair_counts.get(key, 0) + 1
            elif wa == wb:
                buckets["same_wall_different_station"] += 1
                key = "-".join(map(str, sorted([sa, sb])))
                station_pair_counts[key] = station_pair_counts.get(key, 0) + 1
                station_gap.append(abs(sa - sb))
            else:
                buckets["different_wall_and_station"] += 1
                station_gap.append(abs(sa - sb))
            for s_ in (sa, sb):
                per_station_disagree[s_] += 1
                per_station_total[s_] += 1

    total_disagree = sum(buckets.values())
    buckets_pct = {k: round(100 * v / total_disagree, 2) for k, v in buckets.items()}

    # ---- 3. agreement measured at coarser granularity ---------------------
    # If wall identity is the hard part, collapsing to STATION should raise
    # agreement sharply; collapsing to WALL should not.
    from sklearn.metrics import cohen_kappa_score

    def collapse(col: pd.Series, level: str) -> np.ndarray:
        out = []
        for c in col:
            w, s = parse(c)
            if level == "station":
                out.append("OTHER" if s is None else f"S{s}")
            elif level == "wall":
                out.append("OTHER" if w is None else w)
            else:
                out.append(c)
        return np.array(out)

    granularity = {}
    for level in ("full", "station", "wall"):
        ks = []
        for a, b in combinations(ANN, 2):
            ks.append(cohen_kappa_score(collapse(df[a], level), collapse(df[b], level)))
        raws = []
        for a, b in combinations(ANN, 2):
            raws.append(float((collapse(df[a], level) == collapse(df[b], level)).mean()))
        granularity[level] = {
            "mean_pairwise_kappa": round(float(np.mean(ks)), 4),
            "min_pairwise_kappa": round(float(np.min(ks)), 4),
            "max_pairwise_kappa": round(float(np.max(ks)), 4),
            "mean_raw_agreement": round(float(np.mean(raws)), 4),
            "n_categories": int(len(set(collapse(df[ANN[0]], level).tolist()))),
        }

    # unanimity rate at each granularity
    unan = {}
    for level in ("full", "station", "wall"):
        cols = np.array([collapse(df[a], level) for a in ANN]).T
        unan[level] = round(float(np.mean([len(set(r.tolist())) == 1 for r in cols])) * 100, 2)

    # ---- 4. per-station difficulty ---------------------------------------
    station_difficulty = {}
    for s in STATION_NAME:
        tot = per_station_total[s]
        station_difficulty[f"station_{s}"] = {
            "name": STATION_NAME[s],
            "n_rater_pair_observations": tot,
            "disagreement_rate_pct": round(100 * per_station_disagree[s] / tot, 2) if tot else None,
        }

    # ---- 5. OTHERCLASS behaviour -----------------------------------------
    oc_counts = (df[ANN] == "OTHERCLASS").sum(axis=1)
    otherclass = {
        "n_images_any_rater_called_OTHERCLASS": int((oc_counts > 0).sum()),
        "n_images_unanimous_OTHERCLASS": int((oc_counts == 4).sum()),
        "pct_of_OTHERCLASS_nominations_that_are_unanimous": round(
            100 * float((oc_counts == 4).sum()) / float((oc_counts > 0).sum()), 2
        ),
        "per_rater_OTHERCLASS_rate_pct": {
            SHORT[a]: round(100 * float((df[a] == "OTHERCLASS").mean()), 2) for a in ANN
        },
        "share_of_all_disagreement_pct": buckets_pct["landmark_vs_OTHERCLASS"],
    }

    # ---- 6. provenance heterogeneity: direct capture vs video frame ------
    df["_n_distinct"] = [len(set(r.tolist())) for r in lab]
    df["_unanimous"] = df["_n_distinct"] == 1
    ct = pd.crosstab(df["source_type"], df["_unanimous"])
    chi2, p, dof, _ = chi2_contingency(ct)
    a_ = df.loc[df["source_type"] == "direct_capture", "_n_distinct"]
    b_ = df.loc[df["source_type"] == "video_frame", "_n_distinct"]
    u, pu = mannwhitneyu(a_, b_, alternative="two-sided")

    src = {}
    for s, g in df.groupby("source_type"):
        src[s] = {
            "n": int(len(g)),
            "pct_of_corpus": round(100 * len(g) / n, 2),
            "pct_unanimous": round(100 * float(g["_unanimous"].mean()), 2),
            "mean_distinct_labels": round(float(g["_n_distinct"].mean()), 3),
            "n_patients": int(g["patient"].nunique()),
            "resolutions": {f"{w}x{h}": int(c) for (w, h), c in
                            g.groupby(["width", "height"]).size().items()},
        }

    # is source_type balanced across the official splits?
    ct_src = pd.crosstab(df["set_type"], df["source_type"])
    chi2s, ps, _, _ = chi2_contingency(ct_src)

    provenance = {
        "by_source_type": src,
        "unanimity_chi2": round(float(chi2), 2),
        "unanimity_p": float(p),
        "mannwhitney_u": float(u),
        "mannwhitney_p": float(pu),
        "source_type_by_split": {str(k): {str(kk): int(vv) for kk, vv in v.items()}
                                 for k, v in ct_src.to_dict("index").items()},
        "source_type_split_chi2": round(float(chi2s), 2),
        "source_type_split_p": float(ps),
    }

    # resolution vs agreement (the two resolutions track two acquisition rigs)
    ct_res = pd.crosstab(df["width"], df["_unanimous"])
    chi2r, pr, _, _ = chi2_contingency(ct_res)
    resolution = {
        "by_width": {
            str(w): {"n": int(len(g)),
                     "pct_unanimous": round(100 * float(g["_unanimous"].mean()), 2)}
            for w, g in df.groupby("width")
        },
        "chi2": round(float(chi2r), 2),
        "p": float(pr),
    }

    # ---- 7. per-patient agreement (the stratification variable) ----------
    def fleiss_for(sub: pd.DataFrame) -> float:
        cats = classes
        cidx = {c: i for i, c in enumerate(cats)}
        L = sub[ANN].to_numpy()
        cnt = np.zeros((len(sub), len(cats)), dtype=int)
        for j in range(4):
            for i, v in enumerate(L[:, j]):
                cnt[i, cidx[v]] += 1
        m = 4
        p_i = (np.square(cnt).sum(axis=1) - m) / (m * (m - 1))
        p_bar = p_i.mean()
        p_j = cnt.sum(axis=0) / (len(sub) * m)
        pe = np.square(p_j).sum()
        return float((p_bar - pe) / (1 - pe)) if pe < 1 else float("nan")

    per_pat = {}
    for pid, g in df.groupby("patient"):
        if len(g) < 5:
            continue
        per_pat[int(pid)] = round(fleiss_for(g), 4)
    vals = np.array([v for v in per_pat.values() if not np.isnan(v)])
    patient_agreement = {
        "n_patients_scored": int(len(vals)),
        "mean": round(float(vals.mean()), 4),
        "sd": round(float(vals.std(ddof=1)), 4),
        "min": round(float(vals.min()), 4),
        "max": round(float(vals.max()), 4),
        "quartiles": [round(float(q), 4) for q in np.percentile(vals, [25, 50, 75])],
        "n_below_0.4_poor": int((vals < 0.40).sum()),
        "n_0.4_to_0.6_moderate": int(((vals >= 0.40) & (vals < 0.60)).sum()),
        "n_0.6_to_0.8_substantial": int(((vals >= 0.60) & (vals < 0.80)).sum()),
        "n_above_0.8_almost_perfect": int((vals >= 0.80).sum()),
    }
    # does per-patient agreement differ across the official splits?
    pdf = pd.DataFrame({"patient": list(per_pat), "kappa": list(per_pat.values())})
    pmap = df.groupby("patient")["set_type"].first()
    pdf["set_type"] = pdf["patient"].map(pmap)
    from scipy.stats import kruskal
    groups = [g["kappa"].to_numpy() for _, g in pdf.groupby("set_type")]
    hstat, hp = kruskal(*groups)
    patient_agreement["by_split"] = {
        str(s): {"n": int(len(g)), "mean_kappa": round(float(g["kappa"].mean()), 4)}
        for s, g in pdf.groupby("set_type")
    }
    patient_agreement["kruskal_h"] = round(float(hstat), 3)
    patient_agreement["kruskal_p"] = float(hp)

    res = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "taxonomy": taxonomy,
        "wall_names": WALL_NAME,
        "station_names": {str(k): v for k, v in STATION_NAME.items()},
        "disagreement_decomposition": buckets,
        "disagreement_decomposition_pct": buckets_pct,
        "n_disagreement_pair_events": total_disagree,
        "wall_confusion_pairs": dict(sorted(wall_pair_counts.items(),
                                            key=lambda kv: -kv[1])),
        "station_confusion_pairs": dict(sorted(station_pair_counts.items(),
                                               key=lambda kv: -kv[1])),
        "station_gap_distribution": {str(k): int(v) for k, v in
                                     pd.Series(station_gap).value_counts().sort_index().items()},
        "agreement_by_granularity": granularity,
        "unanimity_rate_pct_by_granularity": unan,
        "station_difficulty": station_difficulty,
        "otherclass": otherclass,
        "provenance": provenance,
        "resolution": resolution,
        "per_patient_agreement": patient_agreement,
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    for k in ("disagreement_decomposition_pct", "agreement_by_granularity",
              "unanimity_rate_pct_by_granularity", "otherclass", "provenance",
              "resolution", "per_patient_agreement"):
        print("\n##", k, "\n", json.dumps(res[k], indent=1))


if __name__ == "__main__":
    main()
