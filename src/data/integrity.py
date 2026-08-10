"""
Phase 0 - Data Provenance & Integrity Gate
==========================================
Reproducible integrity battery for `Peptic Ulcer_Dataset.xlsx`.

Implements the six synthetic-data detection tests specified in
THESIS_RESEARCH_BLUEPRINT.md section 4.1.2, the leakage audit of section 4.1.3,
the label-construction audit of section 2.6, the ethics/de-identification
checks of section 4.1.5, and the sample-size/power facts of section 2.7.

All results are written to `reports/phase0_results.json`. No value reported in
the thesis is hard-coded; every number is recomputed from the source file.

Run:  python src/data/integrity.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.svm import LinearSVC

warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Peptic Ulcer_Dataset.xlsx"
OUT = ROOT / "reports" / "phase0_results.json"

# Column groupings used throughout the audit.
CATEGORICALS = ["Sex", "Indication", "Medication", "Oesophagus",
                "Stomach", "Duodenum", "Biopsy", "Comments", "Advice"]
FINDINGS = ["Oesophagus", "Stomach", "Duodenum"]
TARGET = "Comments"

R: dict = {}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def cramers_v(x: pd.Series, y: pd.Series) -> tuple[float, float, float, int]:
    """Bias-corrected Cramer's V (Bergsma 2013) plus the raw chi-square test."""
    ct = pd.crosstab(x, y)
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    n = ct.to_numpy().sum()
    r, k = ct.shape
    phi2 = chi2 / n
    phi2corr = max(0.0, phi2 - ((k - 1) * (r - 1)) / (n - 1))
    rcorr = r - ((r - 1) ** 2) / (n - 1)
    kcorr = k - ((k - 1) ** 2) / (n - 1)
    denom = min(kcorr - 1, rcorr - 1)
    v = float(np.sqrt(phi2corr / denom)) if denom > 0 else 0.0
    return v, float(chi2), float(p), int(dof)


def mutual_info_nats(x: pd.Series, y: pd.Series) -> float:
    """Empirical mutual information between two categoricals, in nats."""
    ct = pd.crosstab(x, y).to_numpy(dtype=float)
    pxy = ct / ct.sum()
    px = pxy.sum(axis=1, keepdims=True)
    py = pxy.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = pxy * np.log(pxy / (px * py))
    return float(np.nansum(term))


def cv_score(X, y, model, n_splits: int = 5) -> tuple[float, float]:
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    s = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)
    return float(s.mean()), float(s.std())


# --------------------------------------------------------------------------
# 1. Provenance fingerprint & structure
# --------------------------------------------------------------------------
def structure(df: pd.DataFrame) -> None:
    sha = hashlib.sha256(DATA.read_bytes()).hexdigest()
    dates = pd.to_datetime(df["Visit_Date"], format="%d-%m-%Y", errors="coerce")

    R["provenance"] = {
        "filename": DATA.name,
        "sha256": sha,
        "file_bytes": DATA.stat().st_size,
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "exact_duplicates": int(df.duplicated().sum()),
        "duplicates_excl_id": int(df.drop(columns=["Patient_ID"]).duplicated().sum()),
        "unique_ids": int(df["Patient_ID"].nunique()),
        "id_collisions": int(df.shape[0] - df["Patient_ID"].nunique()),
        "date_min": str(dates.min().date()),
        "date_max": str(dates.max().date()),
        "date_span_days": int((dates.max() - dates.min()).days),
        "dates_unparsed": int(dates.isna().sum()),
        "n_quarters": int(dates.dt.to_period("Q").nunique()),
        "quarterly_counts": {str(k): int(v) for k, v in
                             dates.dt.to_period("Q").value_counts().sort_index().items()},
    }

    cols = []
    for c in df.columns:
        cols.append({
            "column": c,
            "dtype": str(df[c].dtype),
            "unique": int(df[c].nunique()),
            "missing": int(df[c].isna().sum()),
            "missing_pct": round(100 * df[c].isna().mean(), 2),
            "cardinality_ratio": round(df[c].nunique() / len(df), 4),
        })
    R["column_audit"] = cols

    R["age_summary"] = {
        "min": int(df["Age"].min()), "max": int(df["Age"].max()),
        "mean": round(float(df["Age"].mean()), 2),
        "std": round(float(df["Age"].std()), 2),
        "median": float(df["Age"].median()),
    }

    R["phrase_banks"] = {
        c: {str(k): int(v) for k, v in df[c].value_counts().items()}
        for c in FINDINGS + [TARGET, "Biopsy", "Advice", "Medication", "Sex"]
    }


# --------------------------------------------------------------------------
# 2. Synthetic-data test battery (blueprint section 4.1.2)
# --------------------------------------------------------------------------
def battery(df: pd.DataFrame) -> None:
    b = {}

    # --- Test 1: numeric uniformity -------------------------------------
    age = df["Age"].to_numpy()
    lo, hi = 18, 90
    ks_d, ks_p = stats.kstest(age, "uniform", args=(lo, hi - lo))
    # chi-square goodness-of-fit against a uniform expectation, 12 equal bins
    nbins = 12
    obs, edges = np.histogram(age, bins=nbins, range=(lo, hi + 1))
    exp = np.full(nbins, obs.sum() / nbins)
    gof_chi2, gof_p = stats.chisquare(obs, exp)
    # ANOVA of age across diagnosis groups
    groups = [g["Age"].to_numpy() for _, g in df.groupby(TARGET)]
    f_stat, anova_p = stats.f_oneway(*groups)
    b["test1_numeric_uniformity"] = {
        "variable": "Age",
        "ks_statistic": round(float(ks_d), 4),
        "ks_p": round(float(ks_p), 4),
        "ks_reference": f"Uniform[{lo},{hi}]",
        "gof_chi2": round(float(gof_chi2), 3),
        "gof_dof": nbins - 1,
        "gof_p": round(float(gof_p), 4),
        "anova_F": round(float(f_stat), 3),
        "anova_p": round(float(anova_p), 4),
        "flag": bool(ks_p > 0.05),
    }

    # --- Test 2: categorical balance vs equiprobable ---------------------
    bal = []
    for c in CATEGORICALS:
        vc = df[c].dropna().value_counts()
        chi2, p = stats.chisquare(vc.to_numpy())
        bal.append({
            "column": c, "k": int(len(vc)),
            "min_count": int(vc.min()), "max_count": int(vc.max()),
            "imbalance_ratio": round(float(vc.max() / vc.min()), 3),
            "chi2": round(float(chi2), 3), "dof": int(len(vc) - 1),
            "p": round(float(p), 4),
            "equiprobable_not_rejected": bool(p > 0.05),
        })
    b["test2_categorical_balance"] = bal

    # --- Test 3: pairwise independence (full Cramer's V matrix) ----------
    n = len(CATEGORICALS)
    vmat = np.zeros((n, n))
    pmat = np.ones((n, n))
    pairs = []
    for i, j in combinations(range(n), 2):
        v, chi2, p, dof = cramers_v(df[CATEGORICALS[i]], df[CATEGORICALS[j]])
        vmat[i, j] = vmat[j, i] = v
        pmat[i, j] = pmat[j, i] = p
        pairs.append({"a": CATEGORICALS[i], "b": CATEGORICALS[j],
                      "cramers_v": round(v, 4), "chi2": round(chi2, 3),
                      "dof": dof, "p": round(p, 4)})
    np.fill_diagonal(vmat, 1.0)
    n_pairs = len(pairs)
    n_sig = sum(1 for x in pairs if x["p"] < 0.05)
    bonf = 0.05 / n_pairs
    b["test3_pairwise_independence"] = {
        "n_pairs": n_pairs,
        "n_significant_uncorrected": n_sig,
        "expected_by_chance": round(0.05 * n_pairs, 2),
        "bonferroni_alpha": round(bonf, 6),
        "n_significant_bonferroni": sum(1 for x in pairs if x["p"] < bonf),
        "max_offdiag_cramers_v": round(float(np.max(vmat[~np.eye(n, dtype=bool)])), 4),
        "mean_offdiag_cramers_v": round(float(np.mean(vmat[~np.eye(n, dtype=bool)])), 4),
        "all_below_0.10": bool(np.max(vmat[~np.eye(n, dtype=bool)]) < 0.10),
        "pairs": pairs,
    }
    R["_vmat"] = vmat.tolist()
    R["_pmat"] = pmat.tolist()
    R["_vlabels"] = CATEGORICALS

    # feature vs target association (the headline table)
    feat = []
    for c in [c for c in CATEGORICALS if c != TARGET]:
        v, chi2, p, dof = cramers_v(df[c], df[TARGET])
        feat.append({"feature": c, "chi2": round(chi2, 2), "dof": dof,
                     "p": round(p, 4), "cramers_v": round(v, 4),
                     "mi_nats": round(mutual_info_nats(df[c], df[TARGET]), 4)})
    b["feature_target_association"] = feat

    # --- Test 4: clinical plausibility (findings <-> diagnosis) ----------
    plaus = []
    for c in FINDINGS:
        v, chi2, p, dof = cramers_v(df[c], df[TARGET])
        ct = pd.crosstab(df[c], df[TARGET], normalize="index")
        # A real report set shows a dominant cell per row; measure the peak.
        peak = float(ct.to_numpy().max(axis=1).mean())
        uniform_expect = 1.0 / ct.shape[1]
        plaus.append({
            "finding_field": c, "chi2": round(chi2, 2), "dof": dof,
            "p": round(p, 4), "cramers_v": round(v, 4),
            "mean_row_peak_proportion": round(peak, 4),
            "uniform_expectation": round(uniform_expect, 4),
            "diagonal_structure_present": bool(peak > 2 * uniform_expect),
        })
    b["test4_clinical_plausibility"] = plaus
    b["test4_stomach_x_comments_counts"] = (
        pd.crosstab(df["Stomach"], df[TARGET]).to_dict()
    )

    # --- Test 5: cardinality --------------------------------------------
    card = [{"column": c, "unique": int(df[c].nunique()),
             "ratio": round(df[c].nunique() / len(df), 5),
             "text_field_flag": bool(c in FINDINGS + [TARGET, "Biopsy", "Advice", "Indication"]
                                     and df[c].nunique() / len(df) < 0.01)}
            for c in df.columns]
    b["test5_cardinality"] = card
    b["test5_summary"] = {
        "n_text_fields_below_0.01": sum(1 for x in card if x["text_field_flag"]),
        "corpus_vocabulary_size": int(len(set(
            " ".join(df[FINDINGS + [TARGET, "Biopsy", "Advice"]]
                     .fillna("").astype(str).agg(" ".join, axis=1))
            .lower().replace(".", " ").replace(",", " ").split()
        ))),
    }

    # --- Test 6: combinatorial coverage ---------------------------------
    tup_cols = FINDINGS + ["Biopsy"]
    possible = int(np.prod([df[c].nunique() for c in tup_cols]))
    observed = int(df[tup_cols].drop_duplicates().shape[0])
    full_cols = FINDINGS + ["Biopsy", "Indication", "Medication", "Advice"]

    # Under independent uniform sampling of n records from `possible` equally
    # likely tuples, the expected number of DISTINCT tuples observed is the
    # classical occupancy expectation  K*(1 - (1 - 1/K)^n).  Comparing the
    # observed count against this expectation is a far sharper test than raw
    # coverage: a real clinical corpus concentrates on a few plausible
    # combinations and falls far below it.
    n = len(df)
    exp_unique = possible * (1 - (1 - 1 / possible) ** n)
    # Monte-Carlo reference interval for the same statistic.
    rng_mc = np.random.default_rng(SEED)
    sim = [len(np.unique(rng_mc.integers(0, possible, n))) for _ in range(2000)]
    lo, hi = np.percentile(sim, [2.5, 97.5])

    b["test6_combinatorial_coverage"] = {
        "fields": tup_cols,
        "possible_combinations": possible,
        "observed_combinations": observed,
        "coverage_pct": round(100 * observed / possible, 2),
        "expected_unique_if_random": round(float(exp_unique), 1),
        "mc_95_interval_if_random": [int(lo), int(hi)],
        "observed_over_expected": round(observed / exp_unique, 4),
        "consistent_with_uniform_random_generation": bool(lo <= observed <= hi),
        "full_feature_tuples_unique": int(df[full_cols].drop_duplicates().shape[0]),
    }

    R["battery"] = b


# --------------------------------------------------------------------------
# 3. Label-construction audit (exact replication of notebook cell 29)
# --------------------------------------------------------------------------
PRIORITY = ["Gastric Ulcer", "Duodenal Ulcer", "Gastritis", "Polyp",
            "Esophageal Varices", "Esophagitis", "Normal"]


def _rules(row) -> list[str]:
    o = str(row["Oesophagus"]).lower()
    s = str(row["Stomach"]).lower()
    d = str(row["Duodenum"]).lower()
    c = str(row["Comments"]).lower()
    m = []
    if "gastric ulcer" in c or ("ulcer" in s and "antrum" in s):
        m.append("Gastric Ulcer")
    if "duodenal ulcer" in c or ("ulcer" in d and ("bulb" in d or "duodenum" in d)):
        m.append("Duodenal Ulcer")
    if "gastritis" in c:
        m.append("Gastritis")
    if "polyp" in s or "polyp" in o:
        m.append("Polyp")
    if "varic" in o:
        m.append("Esophageal Varices")
    if "erosion" in o or "les lax" in o or "erythema" in o:
        m.append("Esophagitis")
    if all("normal" in x for x in (o, s, d)) or "normal upper gi" in c:
        m.append("Normal")
    return m


def label_audit(df: pd.DataFrame) -> pd.DataFrame:
    matches = df.apply(_rules, axis=1)
    counts = matches.apply(len)

    def collapse(m):
        if len(m) == 0:
            return "Normal"
        if len(m) == 1:
            return m[0]
        return next((c for c in PRIORITY if c in m), m[0])

    df = df.copy()
    df["_matches"] = matches
    df["_n_matches"] = counts
    df["disease_label"] = matches.apply(collapse)

    dist = counts.value_counts().sort_index()
    lab = df["disease_label"].value_counts()

    # co-occurrence matrix over the seven rule categories
    cats = PRIORITY
    co = pd.DataFrame(0, index=cats, columns=cats, dtype=int)
    for m in matches:
        for a in m:
            for bq in m:
                co.loc[a, bq] += 1

    R["label_audit"] = {
        "match_count_distribution": {int(k): int(v) for k, v in dist.items()},
        "match_count_pct": {int(k): round(100 * v / len(df), 2) for k, v in dist.items()},
        "n_multi_match": int((counts > 1).sum()),
        "pct_multi_match": round(100 * (counts > 1).mean(), 2),
        "n_zero_match_forced_normal": int((counts == 0).sum()),
        "pct_zero_match": round(100 * (counts == 0).mean(), 2),
        "n_unambiguous": int((counts == 1).sum()),
        "pct_unambiguous": round(100 * (counts == 1).mean(), 2),
        "max_simultaneous": int(counts.max()),
        "derived_label_distribution": {str(k): int(v) for k, v in lab.items()},
        "derived_imbalance_ratio": round(float(lab.max() / lab.min()), 2),
        "cooccurrence": co.to_dict(),
        "label_cardinality_mean": round(float(counts[counts > 0].mean()), 3),
    }
    return df


# --------------------------------------------------------------------------
# 4. Leakage audit + honest baselines (E00-E07)
# --------------------------------------------------------------------------
def leakage(df: pd.DataFrame) -> None:
    exp = {}
    y_dl = df["disease_label"]

    def combined(cols):
        return df[cols].fillna("").astype(str).agg(" ".join, axis=1)

    tfidf = lambda: TfidfVectorizer(max_features=1000, min_df=5, max_df=0.8,
                                    ngram_range=(1, 2))

    # E03: notebook configuration - text INCLUDES the label-constituent Comments
    nb_cols = ["Indication", "Oesophagus", "Stomach", "Duodenum",
               "Biopsy", "Comments", "Medication"]
    X = combined(nb_cols)
    m, s = cv_score(X, y_dl, make_pipeline(tfidf(), LogisticRegression(max_iter=2000)))
    exp["E03_notebook_with_comments"] = {"accuracy": round(m, 4), "std": round(s, 4),
                                         "features": nb_cols, "target": "disease_label"}

    # E04: Comments removed
    c4 = [c for c in nb_cols if c != "Comments"]
    m, s = cv_score(combined(c4), y_dl, make_pipeline(tfidf(), LogisticRegression(max_iter=2000)))
    exp["E04_comments_removed"] = {"accuracy": round(m, 4), "std": round(s, 4), "features": c4}

    # E05: Comments and the label-constituent finding fields removed
    c5 = ["Indication", "Medication", "Biopsy"]
    m, s = cv_score(combined(c5), y_dl, make_pipeline(tfidf(), LogisticRegression(max_iter=2000)))
    exp["E05_all_label_constituents_removed"] = {"accuracy": round(m, 4),
                                                 "std": round(s, 4), "features": c5}

    maj_dl = float(y_dl.value_counts(normalize=True).max())
    exp["majority_baseline_disease_label"] = round(maj_dl, 4)

    # Determinism check: do unique finding-tuples map 1:1 onto labels?
    key = df[["Indication", "Oesophagus", "Stomach", "Duodenum",
              "Biopsy", "Comments", "Medication"]].fillna("__MISSING__").astype(str).agg("|".join, axis=1)
    g = pd.DataFrame({"k": key, "y": y_dl}).groupby("k")["y"].nunique()
    exp["determinism_check"] = {
        "unique_feature_combinations": int(len(g)),
        "combinations_mapping_to_exactly_one_label": int((g == 1).sum()),
        "pct_deterministic": round(100 * (g == 1).mean(), 2),
    }

    # ---- Honest target: Comments as the diagnosis label -----------------
    y = df[TARGET]
    feats = ["Age", "Sex", "Indication", "Medication", "Oesophagus",
             "Stomach", "Duodenum", "Biopsy"]
    Xd = df[feats].copy()
    Xd["Indication"] = Xd["Indication"].fillna("__MISSING__")
    enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    Xo = np.hstack([df[["Age"]].to_numpy(),
                    enc.fit_transform(Xd.drop(columns=["Age"]))])
    R["_n_onehot_predictors"] = int(Xo.shape[1])

    models = {
        "E00a_dummy_most_frequent": DummyClassifier(strategy="most_frequent"),
        "E00b_dummy_stratified": DummyClassifier(strategy="stratified", random_state=SEED),
        "E01_logistic_regression": LogisticRegression(max_iter=2000),
        "E01b_random_forest": RandomForestClassifier(n_estimators=300, random_state=SEED),
        "E01c_gradient_boosting": GradientBoostingClassifier(random_state=SEED),
    }
    honest = {}
    for name, mdl in models.items():
        mm, ss = cv_score(Xo, y, mdl)
        honest[name] = {"accuracy": round(mm, 4), "std": round(ss, 4)}

    # E02: TF-IDF + LinearSVC on the report text, target = Comments
    text_no_target = combined([c for c in nb_cols if c != "Comments"])
    mm, ss = cv_score(text_no_target, y, make_pipeline(tfidf(), LinearSVC()))
    honest["E02_tfidf_linearsvc"] = {"accuracy": round(mm, 4), "std": round(ss, 4)}

    honest["majority_baseline"] = {"accuracy": round(float(y.value_counts(normalize=True).max()), 4),
                                   "std": None}
    honest["random_baseline"] = {"accuracy": round(1 / y.nunique(), 4), "std": None}
    exp["honest_baselines_target_comments"] = honest

    # E07: random-noise features of identical shape (sanity control)
    rng = np.random.default_rng(SEED)
    Xn = rng.normal(size=Xo.shape)
    mm, ss = cv_score(Xn, y, LogisticRegression(max_iter=2000))
    exp["E07_random_noise_control"] = {"accuracy": round(mm, 4), "std": round(ss, 4)}

    R["leakage"] = exp


def permutation_test(df: pd.DataFrame, n_perm: int = 1000) -> None:
    """E06 - label-permutation null distribution (Ojala & Garriga, 2010)."""
    cache = ROOT / "reports" / f"_perm_cache_{n_perm}.json"
    if cache.exists():
        R["permutation_test"] = json.loads(cache.read_text(encoding="utf-8"))
        print(f"    (loaded cached null distribution from {cache.name})")
        return

    y = df[TARGET].to_numpy()
    feats = ["Sex", "Indication", "Medication", "Oesophagus",
             "Stomach", "Duodenum", "Biopsy"]
    Xd = df[feats].fillna("__MISSING__")
    enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    Xo = np.hstack([df[["Age"]].to_numpy(), enc.fit_transform(Xd)])

    mdl = LogisticRegression(max_iter=2000)
    real, _ = cv_score(Xo, y, mdl)

    rng = np.random.default_rng(SEED)
    null = []
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    for i in range(n_perm):
        yp = rng.permutation(y)
        s = cross_val_score(mdl, Xo, yp, cv=cv, scoring="accuracy", n_jobs=-1)
        null.append(float(s.mean()))
        if (i + 1) % 100 == 0:
            print(f"    permutation {i + 1}/{n_perm}", flush=True)

    null = np.array(null)
    p = float((np.sum(null >= real) + 1) / (n_perm + 1))
    R["permutation_test"] = {
        "n_permutations": n_perm,
        "real_score": round(real, 4),
        "null_mean": round(float(null.mean()), 4),
        "null_std": round(float(null.std()), 4),
        "null_p05": round(float(np.percentile(null, 5)), 4),
        "null_p95": round(float(np.percentile(null, 95)), 4),
        "null_max": round(float(null.max()), 4),
        "p_value": round(p, 4),
        "percentile_of_real": round(float(stats.percentileofscore(null, real)), 2),
        "null_distribution": [round(x, 5) for x in null.tolist()],
    }
    cache.write_text(json.dumps(R["permutation_test"]), encoding="utf-8")


# --------------------------------------------------------------------------
# 5. Ethics / de-identification & power
# --------------------------------------------------------------------------
def ethics_and_power(df: pd.DataFrame) -> None:
    dates = pd.to_datetime(df["Visit_Date"], format="%d-%m-%Y", errors="coerce")
    qi = pd.DataFrame({
        "age_band": pd.cut(df["Age"], bins=range(15, 96, 5), right=False).astype(str),
        "sex": df["Sex"],
        "visit_month": dates.dt.to_period("M").astype(str),
    })
    grp = qi.groupby(list(qi.columns), observed=True).size()
    qi_coarse = qi.copy()
    qi_coarse["visit_month"] = dates.dt.to_period("Y").astype(str)
    grp_c = qi_coarse.groupby(list(qi_coarse.columns), observed=True).size()

    R["ethics"] = {
        "patient_id_format": str(df["Patient_ID"].iloc[0]),
        "patient_id_is_sequential_surrogate": bool(
            df["Patient_ID"].str.extract(r"(\d+)")[0].astype(int).is_monotonic_increasing),
        "k_anonymity_age5_sex_month": int(grp.min()),
        "n_equivalence_classes_month": int(len(grp)),
        "pct_classes_below_k5_month": round(100 * float((grp < 5).mean()), 2),
        "k_anonymity_age5_sex_year": int(grp_c.min()),
        "n_equivalence_classes_year": int(len(grp_c)),
        "pct_classes_below_k5_year": round(100 * float((grp_c < 5).mean()), 2),
        "direct_identifiers_present": ["Patient_ID (surrogate key)"],
        "quasi_identifier_triple": ["Age", "Sex", "Visit_Date"],
    }

    y = df[TARGET]
    smallest = int(y.value_counts().min())
    p = R["_n_onehot_predictors"]
    n_test = int(round(0.15 * len(df)))
    R["power"] = {
        "n_total": int(len(df)),
        "n_classes": int(y.nunique()),
        "smallest_class": smallest,
        "n_onehot_predictors": p,
        "events_per_variable": round(smallest / p, 2),
        "riley_minimum_epv": "10-20",
        "epv_adequate": bool(smallest / p >= 10),
        "test_set_15pct": n_test,
        "ci_halfwidth_at_acc_018": round(
            float(1.96 * np.sqrt(0.18 * 0.82 / n_test) * 100), 2),
        "ci_halfwidth_at_acc_050": round(
            float(1.96 * np.sqrt(0.50 * 0.50 / n_test) * 100), 2),
    }

    # split-integrity: text-identical rows
    fcols = ["Indication", "Oesophagus", "Stomach", "Duodenum",
             "Biopsy", "Medication", "Advice"]
    key = df[fcols].fillna("").astype(str).agg("|".join, axis=1)
    vc = key.value_counts()
    dup_keys = vc[vc > 1]
    R["split_integrity"] = {
        "unique_feature_tuples": int(key.nunique()),
        "n_repeating_tuples": int(len(dup_keys)),
        "n_rows_in_repeating_tuples": int(dup_keys.sum()),
        "pct_rows_affected": round(100 * dup_keys.sum() / len(df), 2),
        "grouped_splitting_required": bool(len(dup_keys) > 0),
    }


# --------------------------------------------------------------------------
# 6. Feature provenance table
# --------------------------------------------------------------------------
def feature_provenance(df: pd.DataFrame) -> None:
    rows = [
        ("Patient_ID", "identifier", "none", "Drop before modelling", "Surrogate key; no clinical content"),
        ("Age", "independent", "pre-procedure", "Admissible", "Demographic, recorded before endoscopy"),
        ("Sex", "independent", "pre-procedure", "Admissible", "Demographic, recorded before endoscopy"),
        ("Visit_Date", "independent", "pre-procedure", "Admissible (temporal split only)", "Procedural metadata"),
        ("Indication", "independent", "pre-procedure", "Admissible", "Referral reason, precedes findings"),
        ("Medication", "independent", "intra-procedure", "Admissible", "Sedation agent; procedural not diagnostic"),
        ("Oesophagus", "label-constituent", "intra-procedure", "BLOCKED for label T-A", "Used by _is_varices / _is_esophagitis / _is_polyp"),
        ("Stomach", "label-constituent", "intra-procedure", "BLOCKED for label T-A", "Used by _is_gastric_ulcer / _is_polyp"),
        ("Duodenum", "label-constituent", "intra-procedure", "BLOCKED for label T-A", "Used by _is_duodenal_ulcer"),
        ("Biopsy", "independent", "intra-procedure", "Admissible", "Not referenced by any labelling rule"),
        ("Comments", "label-constituent / target", "post-procedure", "TARGET - never a feature", "Diagnosis field; used by 4 of 7 rules"),
        ("Advice", "post-hoc", "post-procedure", "BLOCKED", "Management decision taken after diagnosis is known"),
    ]
    R["feature_provenance"] = [
        {"column": a, "class": b, "temporality": c, "admissibility": d, "justification": e}
        for a, b, c, d, e in rows
    ]
    n_block = sum(1 for r in R["feature_provenance"] if "BLOCKED" in r["admissibility"])
    R["feature_provenance_summary"] = {
        "n_columns": len(rows),
        "n_classified": len(rows),
        "n_blocked": n_block,
        "n_admissible": sum(1 for r in R["feature_provenance"] if r["admissibility"].startswith("Admissible")),
    }


# --------------------------------------------------------------------------
def main() -> None:
    print(f"[Phase 0] Loading {DATA.name}")
    df = pd.read_excel(DATA)
    print(f"          shape = {df.shape}")

    print("[Phase 0] 1/7 structure & provenance fingerprint")
    structure(df)
    print("[Phase 0] 2/7 synthetic-data test battery (6 tests)")
    battery(df)
    print("[Phase 0] 3/7 label-construction audit")
    df = label_audit(df)
    print("[Phase 0] 4/7 leakage audit and honest baselines")
    leakage(df)
    print("[Phase 0] 5/7 permutation test (E06, 1000 permutations)")
    permutation_test(df, n_perm=1000)
    print("[Phase 0] 6/7 ethics, de-identification and power")
    ethics_and_power(df)
    print("[Phase 0] 7/7 feature provenance")
    feature_provenance(df)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")
    print(f"[Phase 0] results -> {OUT}")

    # provenance CSV deliverable
    pd.DataFrame(R["feature_provenance"]).to_csv(
        ROOT / "docs" / "feature_provenance.csv", index=False)
    print(f"[Phase 0] provenance table -> docs/feature_provenance.csv")


if __name__ == "__main__":
    sys.exit(main())
