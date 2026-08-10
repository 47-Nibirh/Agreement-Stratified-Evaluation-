"""
Phase 0 / Step 2 - Label structure, inter-annotator agreement, split integrity.

GastroHUN ships FOUR independent expert labels per image (two fellows, Team A;
two gastroenterologists, Team B). This script quantifies:

  * per-annotator marginal class distributions and prevalence drift
  * all six pairwise Cohen's kappa values (+ bootstrap 95% CI)
  * Fleiss' kappa and Krippendorff's alpha (nominal) over all four raters
  * Gwet's AC1 (paradox-robust chance correction)
  * per-class agreement and the structure of disagreement (which SSS sites
    are confused with which)
  * the agreement-tier cascade: how many images survive each consensus rule
  * official split integrity: patient-level disjointness, class balance,
    agreement-tier balance across Train / Validation / Test
  * class imbalance and per-class statistical power

Output: reports/gastrohun_agreement.json

Run:  python src/data/gastrohun_agreement.py
"""

from __future__ import annotations

import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ROOT / "official_splits" / "image_classification.csv"
META = ROOT / "metadata" / "gastrohun-image-metadata.json"
VMETA = ROOT / "metadata" / "gastrohun-videoendoscopy-metadata.json"
OUT = ROOT / "reports" / "gastrohun_agreement.json"

ANN = ["FG1 (Team A)", "FG2 (Team A)", "G1 (Team B)", "G2 (Team B)"]
SHORT = {"FG1 (Team A)": "FG1", "FG2 (Team A)": "FG2",
         "G1 (Team B)": "G1", "G2 (Team B)": "G2"}

RNG = np.random.default_rng(20260726)


# --------------------------------------------------------------------------
# chance-corrected agreement statistics
# --------------------------------------------------------------------------
def fleiss_kappa(counts: np.ndarray) -> float:
    """counts: (n_items, n_categories) tally of raters per category."""
    n_items, _ = counts.shape
    n_raters = counts.sum(axis=1)
    assert len(set(n_raters.tolist())) == 1, "Fleiss requires a fixed rater count"
    m = int(n_raters[0])
    p_i = (np.square(counts).sum(axis=1) - m) / (m * (m - 1))
    p_bar = p_i.mean()
    p_j = counts.sum(axis=0) / (n_items * m)
    pe = np.square(p_j).sum()
    return float((p_bar - pe) / (1 - pe))


def krippendorff_alpha_nominal(labels: np.ndarray) -> float:
    """labels: (n_items, n_raters) of category indices, no missing values."""
    n_items, m = labels.shape
    cats = np.unique(labels)
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)

    coincidence = np.zeros((k, k))
    for row in labels:
        for a in range(m):
            for b in range(m):
                if a == b:
                    continue
                coincidence[idx[row[a]], idx[row[b]]] += 1.0 / (m - 1)

    n_c = coincidence.sum(axis=1)
    n_tot = n_c.sum()
    do = coincidence.sum() - np.trace(coincidence)
    de = (n_tot**2 - np.square(n_c).sum()) / (n_tot - 1)
    return float(1 - do / de)


def gwet_ac1(counts: np.ndarray) -> float:
    """Gwet's AC1 - chance correction that is stable under high prevalence."""
    n_items, k = counts.shape
    m = int(counts.sum(axis=1)[0])
    p_a = ((np.square(counts).sum(axis=1) - m) / (m * (m - 1))).mean()
    pi = counts.sum(axis=0) / (n_items * m)
    p_e = (pi * (1 - pi)).sum() / (k - 1)
    return float((p_a - p_e) / (1 - p_e))


def boot_kappa_ci(a: np.ndarray, b: np.ndarray, groups: np.ndarray,
                  n_boot: int = 1000) -> tuple[float, float]:
    """Patient-clustered bootstrap CI for Cohen's kappa (images are not iid)."""
    uniq = np.unique(groups)
    index = {g: np.where(groups == g)[0] for g in uniq}
    vals = []
    for _ in range(n_boot):
        pick = RNG.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([index[g] for g in pick])
        try:
            vals.append(cohen_kappa_score(a[sel], b[sel]))
        except Exception:  # noqa: BLE001
            continue
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(SPLITS, index_col=0)
    df["patient"] = df["num patient"].astype(int)

    meta = pd.DataFrame(json.load(open(META, encoding="utf-8")))
    meta["patient"] = meta["num patient"].astype(int)

    classes = sorted(set(pd.unique(df[ANN].to_numpy().ravel()).tolist()))
    cidx = {c: i for i, c in enumerate(classes)}
    K = len(classes)

    lab = np.array([[cidx[v] for v in df[a]] for a in ANN]).T   # (n_items, 4)
    n_items = lab.shape[0]
    groups = df["patient"].to_numpy()

    # ---- tally matrix for Fleiss / AC1 -----------------------------------
    counts = np.zeros((n_items, K), dtype=int)
    for j in range(4):
        counts[np.arange(n_items), lab[:, j]] += 1

    # ---- 1. marginal distributions per annotator -------------------------
    marginals = {}
    for a in ANN:
        vc = df[a].value_counts()
        marginals[SHORT[a]] = {c: int(vc.get(c, 0)) for c in classes}

    # how far apart are the annotators' overall prevalence vectors?
    prev = np.array([[marginals[SHORT[a]][c] / n_items for c in classes] for a in ANN])
    tvd = {}
    for i, j in combinations(range(4), 2):
        key = f"{SHORT[ANN[i]]}-{SHORT[ANN[j]]}"
        tvd[key] = round(float(0.5 * np.abs(prev[i] - prev[j]).sum()), 4)

    # ---- 2. pairwise Cohen's kappa ---------------------------------------
    pairwise = {}
    for i, j in combinations(range(4), 2):
        key = f"{SHORT[ANN[i]]}-{SHORT[ANN[j]]}"
        k_ = cohen_kappa_score(lab[:, i], lab[:, j])
        raw = float((lab[:, i] == lab[:, j]).mean())
        lo, hi = boot_kappa_ci(lab[:, i], lab[:, j], groups, n_boot=400)
        pairwise[key] = {
            "kappa": round(float(k_), 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "raw_agreement": round(raw, 4),
            "within_team": SHORT[ANN[i]][0] == SHORT[ANN[j]][0]
            and (i, j) in ((0, 1), (2, 3)),
        }
    within = [v["kappa"] for k, v in pairwise.items() if k in ("FG1-FG2", "G1-G2")]
    between = [v["kappa"] for k, v in pairwise.items() if k not in ("FG1-FG2", "G1-G2")]

    # ---- 3. multi-rater statistics ---------------------------------------
    fk = fleiss_kappa(counts)
    ka = krippendorff_alpha_nominal(lab)
    ac1 = gwet_ac1(counts)

    # ---- 4. agreement tier cascade ---------------------------------------
    tiers = {
        "all_images": n_items,
        "complete_agreement_4of4": int(df["Complete agreement"].notna().sum()),
        "triple_agreement_3of4": int(df["Triple agreement"].notna().sum()),
        "FG_team_agreement": int(df["FG agreement"].notna().sum()),
        "G_team_agreement": int(df["G agreement"].notna().sum()),
    }
    tiers_pct = {k: round(100 * v / n_items, 2) for k, v in tiers.items()}

    n_distinct = np.array([len(set(row.tolist())) for row in lab])
    consensus_profile = {
        f"{int(d)}_distinct_labels": int((n_distinct == d).sum()) for d in range(1, 5)
    }
    consensus_profile_pct = {
        k: round(100 * v / n_items, 2) for k, v in consensus_profile.items()
    }

    # majority structure: 4-0, 3-1, 2-2, 2-1-1, 1-1-1-1
    def pattern(row: np.ndarray) -> str:
        c = sorted(np.bincount(row, minlength=K)[np.unique(row)].tolist(), reverse=True)
        return "-".join(map(str, c))

    pat = pd.Series([pattern(r) for r in lab]).value_counts()
    vote_patterns = {k: int(v) for k, v in pat.items()}
    vote_patterns_pct = {k: round(100 * v / n_items, 2) for k, v in pat.items()}

    # images with NO majority (2-2 or 1-1-1-1) -> undecidable by voting
    no_majority = int(sum(v for k, v in vote_patterns.items() if k in ("2-2", "1-1-1-1")))

    # ---- 5. per-class agreement ------------------------------------------
    # class-specific Fleiss kappa (one-vs-rest) and mean rater support
    per_class = {}
    for c in classes:
        ci = cidx[c]
        bi = np.zeros((n_items, 2), dtype=int)
        bi[:, 0] = counts[:, ci]
        bi[:, 1] = 4 - counts[:, ci]
        kc = fleiss_kappa(bi)
        nominated = int((counts[:, ci] > 0).sum())
        unanimous = int((counts[:, ci] == 4).sum())
        per_class[c] = {
            "n_unanimous": unanimous,
            "n_any_rater": nominated,
            "unanimity_rate": round(unanimous / nominated, 4) if nominated else None,
            "fleiss_kappa_ovr": round(kc, 4),
            "mean_raters_when_nominated": round(
                float(counts[counts[:, ci] > 0, ci].mean()), 3
            ) if nominated else None,
        }

    # ---- 6. disagreement structure ---------------------------------------
    # aggregate confusion over all 6 unordered rater pairs, off-diagonal only
    conf = np.zeros((K, K))
    for i, j in combinations(range(4), 2):
        conf += confusion_matrix(lab[:, i], lab[:, j], labels=range(K))
    sym = conf + conf.T
    np.fill_diagonal(sym, 0)
    pairs = []
    for i in range(K):
        for j in range(i + 1, K):
            if sym[i, j] > 0:
                pairs.append(
                    {"class_a": classes[i], "class_b": classes[j],
                     "n_disagreements": int(sym[i, j])}
                )
    pairs.sort(key=lambda d: -d["n_disagreements"])
    total_disagree = float(sym.sum() / 2)
    for p in pairs:
        p["share_of_all_disagreement_pct"] = round(
            100 * p["n_disagreements"] / total_disagree, 2
        )
    top_conf = pairs[:20]
    top10_share = round(sum(p["n_disagreements"] for p in pairs[:10]) / total_disagree * 100, 2)

    # ---- 7. consensus label distribution (majority of 4, ties dropped) ----
    maj_lab, maj_ok = [], []
    for row in lab:
        bc = np.bincount(row, minlength=K)
        top = bc.max()
        if (bc == top).sum() == 1 and top >= 3:
            maj_lab.append(classes[int(bc.argmax())])
            maj_ok.append(True)
        else:
            maj_lab.append(None)
            maj_ok.append(False)
    df["_majority"] = maj_lab
    consensus_dist = df["_majority"].value_counts().to_dict()

    # complete-agreement class distribution (what the published benchmark uses)
    ca = df[df["Complete agreement"].notna()]
    ca_dist = ca["Complete agreement"].value_counts().to_dict()
    ca_imbalance = {
        "n": int(len(ca)),
        "n_classes_present": int(ca["Complete agreement"].nunique()),
        "max_class": int(max(ca_dist.values())),
        "min_class": int(min(ca_dist.values())),
        "imbalance_ratio": round(max(ca_dist.values()) / min(ca_dist.values()), 2),
        "gini": round(float(
            1 - np.square(np.array(list(ca_dist.values())) / len(ca)).sum()
        ), 4),
    }

    # which classes LOSE the most images when the consensus filter is applied
    attrition = {}
    for c in classes:
        any_r = int((counts[:, cidx[c]] > 0).sum())
        kept = int(ca_dist.get(c, 0))
        attrition[c] = {
            "nominated_by_any_rater": any_r,
            "kept_under_complete_agreement": kept,
            "attrition_pct": round(100 * (1 - kept / any_r), 2) if any_r else None,
        }

    # ---- 8. official split integrity -------------------------------------
    split_patients = {s: set(g["patient"]) for s, g in df.groupby("set_type")}
    overlaps = {}
    for a, b in combinations(sorted(split_patients), 2):
        overlaps[f"{a}-{b}"] = sorted(split_patients[a] & split_patients[b])
    fn_dupe = int(df["filename"].duplicated().sum())

    split_summary = {}
    for s, g in df.groupby("set_type"):
        gca = g[g["Complete agreement"].notna()]
        split_summary[s] = {
            "n_images": int(len(g)),
            "n_patients": int(g["patient"].nunique()),
            "pct_images": round(100 * len(g) / n_items, 2),
            "pct_patients": round(100 * g["patient"].nunique() / df["patient"].nunique(), 2),
            "n_complete_agreement": int(len(gca)),
            "pct_complete_agreement": round(100 * len(gca) / len(g), 2),
            "images_per_patient_mean": round(float(len(g) / g["patient"].nunique()), 2),
            "n_classes_complete_agreement": int(gca["Complete agreement"].nunique()),
        }

    # is class prevalence stable across splits? (chi-square on consensus labels)
    from scipy.stats import chi2_contingency
    ct = pd.crosstab(df["set_type"], df["Complete agreement"])
    chi2, p_chi, dof, _ = chi2_contingency(ct)
    cramers_v = float(np.sqrt(chi2 / (ct.to_numpy().sum() * (min(ct.shape) - 1))))

    # agreement-tier prevalence stable across splits?
    df["_has_ca"] = df["Complete agreement"].notna()
    ct2 = pd.crosstab(df["set_type"], df["_has_ca"])
    chi2b, p_chi_b, _, _ = chi2_contingency(ct2)

    # ---- 9. per-class power ----------------------------------------------
    test_ca = df[(df["set_type"] == "Test") & df["Complete agreement"].notna()]
    test_counts = test_ca["Complete agreement"].value_counts()
    # half-width of a 95% Wilson interval at p=0.85 for each class's test n
    power = {}
    for c, n in test_counts.items():
        p_ = 0.85
        z = 1.96
        denom = 1 + z**2 / n
        centre = (p_ + z**2 / (2 * n)) / denom
        half = z * np.sqrt(p_ * (1 - p_) / n + z**2 / (4 * n**2)) / denom
        power[c] = {"n_test": int(n), "wilson_half_width_at_p85": round(float(half), 4)}
    n_classes_underpowered = sum(
        1 for v in power.values() if v["wilson_half_width_at_p85"] > 0.10
    )

    # ---- 10. patient-level clinical metadata coverage --------------------
    vm = pd.DataFrame(json.load(open(VMETA, encoding="utf-8")))
    vm["patient"] = vm["num patient"].astype(int)
    img_pats = set(df["patient"])
    vm_pats = set(vm["patient"])
    clinical = {
        "n_patients_with_images": len(img_pats),
        "n_patients_with_videoendoscopy_record": len(vm_pats),
        "n_overlap": len(img_pats & vm_pats),
        "pct_image_patients_with_clinical_record": round(
            100 * len(img_pats & vm_pats) / len(img_pats), 2
        ),
        "h_pylori_reported": int(vm["H. PYLORI"].notna().sum()),
        "h_pylori_missing": int(vm["H. PYLORI"].isna().sum()),
        "h_pylori_positive": int((vm["H. PYLORI"] == "Positive").sum()),
        "olga_reported": int(vm["OLGA"].notna().sum()),
        "olga_missing": int(vm["OLGA"].isna().sum()),
        "olga_distribution": {str(k): int(v) for k, v in
                              vm["OLGA"].value_counts(dropna=False).items()},
        "n_unique_free_text_findings": int(vm["Findings"].nunique()),
        "n_unique_diagnoses_strings": int(vm["Diagnoses"].nunique()),
        "has_age": bool("age" in [c.lower() for c in vm.columns]),
        "has_sex": bool("sex" in [c.lower() for c in vm.columns]),
        "columns": list(vm.columns),
    }

    # ---- 11. image metadata cross-check ----------------------------------
    meta_check = {
        "n_rows_metadata": int(len(meta)),
        "n_rows_splits": int(len(df)),
        "filenames_identical": bool(
            set(meta["filename"]) == set(df["filename"])
        ),
        "labels_identical": None,
    }
    m = meta.set_index("filename")
    d = df.set_index("filename")
    common = m.index.intersection(d.index)
    meta_check["labels_identical"] = bool(
        all((m.loc[common, a].to_numpy() == d.loc[common, a].to_numpy()).all() for a in ANN)
    )

    res = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_images": n_items,
        "n_patients": int(df["patient"].nunique()),
        "n_classes": K,
        "classes": classes,
        "annotators": [SHORT[a] for a in ANN],
        "marginals": marginals,
        "prevalence_total_variation_distance": tvd,
        "pairwise_cohen_kappa": pairwise,
        "kappa_within_team_mean": round(float(np.mean(within)), 4),
        "kappa_between_team_mean": round(float(np.mean(between)), 4),
        "fleiss_kappa": round(fk, 4),
        "krippendorff_alpha": round(ka, 4),
        "gwet_ac1": round(ac1, 4),
        "agreement_tiers": tiers,
        "agreement_tiers_pct": tiers_pct,
        "consensus_profile": consensus_profile,
        "consensus_profile_pct": consensus_profile_pct,
        "vote_patterns": vote_patterns,
        "vote_patterns_pct": vote_patterns_pct,
        "n_no_majority": no_majority,
        "pct_no_majority": round(100 * no_majority / n_items, 2),
        "per_class_agreement": per_class,
        "top_confusion_pairs": top_conf,
        "n_disagreement_pair_events": int(total_disagree),
        "top10_confusion_share_pct": top10_share,
        "consensus_majority_distribution": {str(k): int(v) for k, v in consensus_dist.items()},
        "complete_agreement_distribution": {str(k): int(v) for k, v in ca_dist.items()},
        "complete_agreement_imbalance": ca_imbalance,
        "class_attrition_under_consensus": attrition,
        "split_summary": split_summary,
        "split_patient_overlaps": {k: v for k, v in overlaps.items()},
        "n_duplicate_filenames": fn_dupe,
        "split_class_chi2": {"chi2": round(float(chi2), 2), "dof": int(dof),
                             "p": float(p_chi), "cramers_v": round(cramers_v, 4)},
        "split_agreement_chi2": {"chi2": round(float(chi2b), 2), "p": float(p_chi_b)},
        "test_set_power": power,
        "n_test_classes_underpowered_hw_gt_10pct": n_classes_underpowered,
        "clinical_metadata": clinical,
        "metadata_crosscheck": meta_check,
        "runtime_sec": round(time.time() - t0, 1),
    }

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"wrote {OUT}  ({res['runtime_sec']}s)")
    for k in ("fleiss_kappa", "krippendorff_alpha", "gwet_ac1",
              "kappa_within_team_mean", "kappa_between_team_mean",
              "agreement_tiers_pct", "vote_patterns_pct", "pct_no_majority",
              "split_patient_overlaps", "n_duplicate_filenames"):
        print(k, "=", json.dumps(res[k]))


if __name__ == "__main__":
    main()
