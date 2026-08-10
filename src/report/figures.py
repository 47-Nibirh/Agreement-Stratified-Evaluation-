"""
Figure generation for the Phase 0 / Phase 1 report.
===================================================
Every figure is regenerated from `reports/phase0_results.json` and
`literature/*.csv` with a fixed seed and a colourblind-safe palette
(Okabe-Ito), in line with the universal figure standards of
THESIS_RESEARCH_BLUEPRINT.md section 6.6.

Run:  python src/report/figures.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
R = json.loads((ROOT / "reports" / "phase0_results.json").read_text(encoding="utf-8"))
DF = pd.read_excel(ROOT / "Peptic Ulcer_Dataset.xlsx")

# Okabe-Ito colourblind-safe palette
OI = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
      "red": "#D55E00", "purple": "#CC79A7", "yellow": "#F0E442",
      "sky": "#56B4E9", "black": "#000000", "grey": "#7F7F7F"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
})

SAVED: list[str] = []


def save(fig, name: str) -> None:
    p = FIG / f"{name}.png"
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    SAVED.append(name)
    print(f"  [fig] {name}")


def box(ax, x, y, w, h, text, fc, tc="white", fs=7.5, style="round,pad=0.02"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style,
                                linewidth=1.0, edgecolor="#333333", facecolor=fc))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, weight="bold", linespacing=1.35, zorder=5)


def arrow(ax, p1, p2, color="#333333", style="-|>", lw=1.1, ls="-"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=11,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=1, shrinkB=1, zorder=1))


# ==========================================================================
# F1 - Research workflow (Phase 0 -> Phase 1)
# ==========================================================================
def f01_workflow():
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7.2); ax.axis("off"); ax.grid(False)

    ax.text(5, 6.95, "Phase 0 - Data Provenance & Integrity Gate",
            ha="center", fontsize=9.5, weight="bold", color=OI["red"])
    p0 = [("Provenance\nverification", 0.25), ("Synthetic-data\ntest battery", 2.2),
          ("Leakage audit\nof prior code", 4.15), ("Label-construction\naudit", 6.1),
          ("Ethics & de-\nidentification", 8.05)]
    for t, x in p0:
        box(ax, x, 5.5, 1.75, 0.95, t, "#8b1a1a")
    for i in range(4):
        arrow(ax, (p0[i][1] + 1.75, 5.97), (p0[i + 1][1], 5.97))

    box(ax, 3.5, 4.15, 3.0, 0.85, "GATE\nRoute decision", "#d00000")
    arrow(ax, (5, 5.5), (5, 5.0))

    ax.text(5, 3.75, "Phase 1 - Literature Review & Problem Framing",
            ha="center", fontsize=9.5, weight="bold", color=OI["blue"])
    p1 = [("Reproducible\nsearch protocol", 0.55), ("Screening &\neligibility", 3.0),
          ("Extraction &\ngap analysis", 5.45), ("Research questions\nfrozen", 7.9)]
    for t, x in p1:
        box(ax, x, 2.3, 2.0, 0.95, t, "#1d3557")
    for i in range(3):
        arrow(ax, (p1[i][1] + 2.0, 2.77), (p1[i + 1][1], 2.77))
    arrow(ax, (5, 4.15), (5, 3.25))

    box(ax, 1.2, 0.75, 3.1, 0.85, "Phase 2\nData understanding & EDA", "#495057", fs=7)
    box(ax, 5.7, 0.75, 3.1, 0.85, "Phase 3\nTarget definition (leakage firewall)",
        "#495057", fs=7)
    arrow(ax, (4.2, 2.3), (2.75, 1.6)); arrow(ax, (5.8, 2.3), (7.25, 1.6))
    ax.text(5, 0.25, "Downstream phases 2-10 are gated on the Phase 0 route decision",
            ha="center", fontsize=7.5, style="italic", color="#555555")
    save(fig, "F01_research_workflow")


# ==========================================================================
# F2 - Integrity gate flowchart
# ==========================================================================
def f02_integrity_gate():
    fig, ax = plt.subplots(figsize=(6.8, 6.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10.9); ax.axis("off"); ax.grid(False)
    b = R["battery"]
    t6 = b["test6_combinatorial_coverage"]

    CX = 3.85          # centre-line of the test column
    box(ax, 2.35, 9.95, 3.0, 0.7, "Raw dataset\n1,269 x 12", OI["grey"], fs=7.5)

    tests = [
        f"T1  Numeric uniformity\nAge indistinguishable from Uniform[18,90]:  "
        f"KS D={b['test1_numeric_uniformity']['ks_statistic']}, p={b['test1_numeric_uniformity']['ks_p']}",
        "T2  Categorical balance\nEquiprobability not rejected in 8 of 9 fields",
        f"T3  Pairwise independence\nmax Cramér's V = {b['test3_pairwise_independence']['max_offdiag_cramers_v']} "
        f"over 36 pairs; 0 survive Bonferroni",
        "T4  Clinical plausibility\nNo findings-to-diagnosis diagonal "
        "($\\chi^2$=32.45, df=30, p=0.347)",
        f"T5  Cardinality\n7 'text' fields hold 2-7 phrases; vocabulary = "
        f"{b['test5_summary']['corpus_vocabulary_size']} tokens",
        f"T6  Combinatorial coverage\n{t6['observed_combinations']} distinct tuples vs "
        f"{t6['expected_unique_if_random']} expected at random (MC 95% "
        f"{t6['mc_95_interval_if_random'][0]}-{t6['mc_95_interval_if_random'][1]})",
    ]
    y = 9.05
    H, STEP = 0.82, 1.18
    for t in tests:
        arrow(ax, (CX, y + H + (0.28 if y > 8.9 else STEP - H)), (CX, y + H),
              color="#666666")
        box(ax, 0.7, y, 6.3, H, t, "#8b1a1a", fs=6.1)
        box(ax, 7.25, y + 0.12, 1.35, 0.58, "FAIL", OI["red"], fs=8)
        y -= STEP

    box(ax, 0.7, 1.35, 7.9, 0.78,
        "6 / 6 integrity tests FAILED\n"
        "The corpus behaves as independent uniform draws; Route C is inadmissible.",
        "#d00000", fs=7.0)
    arrow(ax, (CX, y + STEP), (CX, 2.13), color="#666666")

    box(ax, 0.7, 0.2, 7.9, 0.78,
        "ROUTE A - Reframe: honest system + documented negative result",
        "#bc6c25", fs=7.4)
    arrow(ax, (4.65, 1.35), (4.65, 0.98), lw=1.5)
    save(fig, "F02_integrity_gate_flowchart")


# ==========================================================================
# F3 - Cardinality bar chart
# ==========================================================================
def f03_cardinality():
    ca = pd.DataFrame(R["column_audit"])
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    colors = [OI["red"] if u > 100 else (OI["orange"] if u <= 10 else OI["blue"])
              for u in ca.unique]
    ax.bar(ca.column, ca.unique, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_yscale("log")
    ax.axhline(10, color=OI["green"], ls="--", lw=1.2,
               label="10 unique values")
    for i, u in enumerate(ca.unique):
        ax.text(i, u * 1.15, str(u), ha="center", fontsize=7, weight="bold")
    ax.set_ylabel("Unique values (log scale)")
    ax.set_title("Column cardinality: the 'text' fields are closed categorical sets")
    ax.set_xticks(range(len(ca)))
    ax.set_xticklabels(ca.column, rotation=45, ha="right", fontsize=7.5)
    ax.legend(fontsize=7, frameon=False)
    ax.set_ylim(1, 3000)
    save(fig, "F03_cardinality")


# ==========================================================================
# F4 - Age histogram + uniform overlay ; F5 - Q-Q plot
# ==========================================================================
def f04_age():
    t1 = R["battery"]["test1_numeric_uniformity"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.9))
    age = DF["Age"].to_numpy()
    a1.hist(age, bins=24, range=(18, 90), color=OI["sky"],
            edgecolor="black", linewidth=0.5, alpha=0.9)
    a1.axhline(len(age) / 24, color=OI["red"], ls="--", lw=1.6,
               label="Uniform[18, 90] expectation")
    a1.set_xlabel("Age (years)"); a1.set_ylabel("Frequency")
    a1.set_title(f"Age distribution\nKS D={t1['ks_statistic']}, p={t1['ks_p']}")
    a1.legend(fontsize=7, frameon=False)

    n = len(age)
    theo = stats.uniform.ppf((np.arange(1, n + 1) - 0.5) / n, loc=18, scale=72)
    a2.scatter(theo, np.sort(age), s=4, color=OI["blue"], alpha=0.6)
    a2.plot([18, 90], [18, 90], color=OI["red"], ls="--", lw=1.6,
            label="45$^\\circ$ reference")
    a2.set_xlabel("Theoretical quantiles (Uniform)")
    a2.set_ylabel("Observed quantiles")
    a2.set_title("Q-Q plot of Age against Uniform[18, 90]")
    a2.legend(fontsize=7, frameon=False)
    save(fig, "F04_age_uniformity")


# ==========================================================================
# F5 - Cramer's V heatmap ; F6 - p-value heatmap
# ==========================================================================
def f05_association_heatmaps():
    v = np.array(R["_vmat"]); p = np.array(R["_pmat"]); lab = R["_vlabels"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.6))

    m = v.copy(); np.fill_diagonal(m, np.nan)
    im1 = a1.imshow(m, cmap="viridis", vmin=0, vmax=0.30)
    a1.set_title("Bias-corrected Cramér's V\n(all pairs < 0.10 = negligible)")
    fig.colorbar(im1, ax=a1, fraction=0.046, label="Cramér's V")
    for i in range(len(lab)):
        for j in range(len(lab)):
            if i != j:
                a1.text(j, i, f"{v[i,j]:.02f}".lstrip("0"), ha="center",
                        va="center", fontsize=5.4,
                        color="white" if v[i, j] < 0.18 else "black")

    pm = p.copy(); np.fill_diagonal(pm, np.nan)
    im2 = a2.imshow(pm, cmap="RdYlGn", vmin=0, vmax=1)
    a2.set_title("Pairwise $\\chi^2$ p-values\n(0 of 36 survive Bonferroni)")
    fig.colorbar(im2, ax=a2, fraction=0.046, label="p-value")
    for i in range(len(lab)):
        for j in range(len(lab)):
            if i != j and p[i, j] < 0.05:
                a2.text(j, i, "*", ha="center", va="center",
                        fontsize=9, color="black", weight="bold")

    for a in (a1, a2):
        a.set_xticks(range(len(lab))); a.set_yticks(range(len(lab)))
        a.set_xticklabels(lab, rotation=45, ha="right", fontsize=6.5)
        a.set_yticklabels(lab, fontsize=6.5)
        a.grid(False)
    save(fig, "F05_association_heatmaps")


# ==========================================================================
# F6 - Stomach x Comments mosaic
# ==========================================================================
def f06_mosaic():
    ct = pd.crosstab(DF["Stomach"], DF["Comments"], normalize="index")
    t4 = [x for x in R["battery"]["test4_clinical_plausibility"]
          if x["finding_field"] == "Stomach"][0]
    fig, ax = plt.subplots(figsize=(7.0, 3.3))
    im = ax.imshow(ct.to_numpy(), cmap="viridis", vmin=0, vmax=0.35, aspect="auto")
    ax.set_xticks(range(ct.shape[1]))
    ax.set_xticklabels([c.replace(" ", "\n", 1)[:30] for c in ct.columns],
                       rotation=30, ha="right", fontsize=6)
    ax.set_yticks(range(ct.shape[0]))
    ax.set_yticklabels([c[:34] for c in ct.index], fontsize=6)
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            ax.text(j, i, f"{ct.iat[i,j]*100:.0f}", ha="center", va="center",
                    fontsize=6, color="white" if ct.iat[i, j] < 0.22 else "black")
    ax.set_title(f"Stomach finding × Diagnosis, row-normalised (%)\n"
                 f"$\\chi^2$={t4['chi2']}, df={t4['dof']}, p={t4['p']} - "
                 f"no diagonal structure")
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.03, label="Row proportion")
    save(fig, "F06_mosaic_stomach_diagnosis")


# ==========================================================================
# F7 - Target class distribution
# ==========================================================================
def f07_target_distribution():
    vc = DF["Comments"].value_counts()
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ax.bar(range(len(vc)), vc.to_numpy(), color=OI["blue"],
           edgecolor="black", linewidth=0.5)
    ax.axhline(len(DF) / len(vc), color=OI["red"], ls="--", lw=1.4,
               label=f"Equiprobable expectation ({len(DF)/len(vc):.1f})")
    for i, val in enumerate(vc.to_numpy()):
        ax.text(i, val + 4, str(val), ha="center", fontsize=7.5, weight="bold")
    ax.set_xticks(range(len(vc)))
    ax.set_xticklabels([t.replace(" ", "\n", 2)[:34] for t in vc.index], fontsize=6.5)
    ax.set_ylabel("Records")
    ratio = vc.max() / vc.min()
    ax.set_title(f"Diagnosis (Comments) class distribution - imbalance ratio "
                 f"{ratio:.2f}:1, so no resampling is warranted")
    ax.legend(fontsize=7, frameon=False)
    ax.set_ylim(0, vc.max() * 1.18)
    save(fig, "F07_target_distribution")


# ==========================================================================
# F8 - Leakage cascade
# ==========================================================================
def f08_leakage_cascade():
    L = R["leakage"]
    names = ["E03\nNotebook\n(incl. Comments)", "E04\nComments\nremoved",
             "E05\nAll label-constituent\nfields removed"]
    vals = [L["E03_notebook_with_comments"]["accuracy"],
            L["E04_comments_removed"]["accuracy"],
            L["E05_all_label_constituents_removed"]["accuracy"]]
    errs = [L["E03_notebook_with_comments"]["std"],
            L["E04_comments_removed"]["std"],
            L["E05_all_label_constituents_removed"]["std"]]
    base = L["majority_baseline_disease_label"]

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    cols = [OI["red"], OI["orange"], OI["green"]]
    bars = ax.bar(names, vals, yerr=errs, capsize=4, color=cols,
                  edgecolor="black", linewidth=0.6)
    ax.axhline(base, color=OI["black"], ls="--", lw=1.5,
               label=f"Majority baseline = {base:.3f}")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.025, f"{v:.4f}",
                ha="center", fontsize=8.5, weight="bold")
    ax.set_ylabel("5-fold CV accuracy")
    ax.set_ylim(0, 1.13)
    ax.set_title("Leakage cascade: performance collapses only when every\n"
                 "label-constituent field is removed")
    ax.legend(fontsize=7.5, frameon=False, loc="center right")
    ax.tick_params(axis="x", labelsize=7)
    save(fig, "F08_leakage_cascade")


# ==========================================================================
# F9 - Permutation null distribution (E06)
# ==========================================================================
def f09_permutation():
    pt = R["permutation_test"]
    null = np.array(pt["null_distribution"])
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.hist(null, bins=38, color=OI["sky"], edgecolor="black",
            linewidth=0.4, alpha=0.9, label=f"Null distribution ({pt['n_permutations']} permutations)")
    ax.axvline(pt["real_score"], color=OI["red"], lw=2.0,
               label=f"Observed score = {pt['real_score']:.4f}")
    ax.axvline(pt["null_p95"], color=OI["black"], ls="--", lw=1.2,
               label=f"95th percentile of null = {pt['null_p95']:.4f}")
    ax.set_xlabel("5-fold CV accuracy under permuted labels")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Label-permutation test (E06): observed score falls at the "
                 f"{pt['percentile_of_real']:.0f}th\npercentile of the null, p = {pt['p_value']:.3f}")
    ax.legend(fontsize=7, frameon=False)
    save(fig, "F09_permutation_test")


# ==========================================================================
# F10 - Rule-match histogram ; F11 - co-occurrence
# ==========================================================================
def f10_label_ambiguity():
    la = R["label_audit"]
    d = {int(k): v for k, v in la["match_count_distribution"].items()}
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    ks = sorted(d)
    cols = [OI["red"], OI["green"]] + [OI["orange"]] * (len(ks) - 2)
    bars = ax.bar([str(k) for k in ks], [d[k] for k in ks], color=cols,
                  edgecolor="black", linewidth=0.6)
    for b, k in zip(bars, ks):
        ax.text(b.get_x() + b.get_width() / 2, d[k] + 8,
                f"{d[k]}\n({100*d[k]/sum(d.values()):.1f}%)", ha="center",
                fontsize=7, weight="bold")
    ax.set_xlabel("Number of disease rules simultaneously satisfied")
    ax.set_ylabel("Records")
    ax.set_ylim(0, max(d.values()) * 1.28)
    ax.set_title(f"Label ambiguity: only {la['pct_unambiguous']}% of records match exactly one rule;\n"
                 f"{la['pct_zero_match']}% match none and are silently forced to 'Normal'")
    save(fig, "F10_rule_match_histogram")


def f11_cooccurrence():
    co = pd.DataFrame(R["label_audit"]["cooccurrence"])
    order = ["Gastric Ulcer", "Duodenal Ulcer", "Gastritis", "Polyp",
             "Esophageal Varices", "Esophagitis", "Normal"]
    co = co.reindex(index=order, columns=order).fillna(0).astype(int)
    m = co.to_numpy().astype(float)
    np.fill_diagonal(m, np.nan)
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    im = ax.imshow(m, cmap="magma")
    for i in range(len(order)):
        for j in range(len(order)):
            if i != j:
                ax.text(j, i, int(m[i, j]), ha="center", va="center",
                        fontsize=6.5,
                        color="white" if m[i, j] < np.nanmax(m) * 0.55 else "black")
            else:
                ax.text(j, i, f"[{co.iat[i,j]}]", ha="center", va="center",
                        fontsize=6, color=OI["grey"], style="italic")
    ax.set_xticks(range(len(order))); ax.set_yticks(range(len(order)))
    ax.set_xticklabels(order, rotation=45, ha="right", fontsize=6.5)
    ax.set_yticklabels(order, fontsize=6.5)
    ax.set_title("Rule co-occurrence matrix\n(diagonal in brackets = total rule matches)")
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046, label="Co-occurring records")
    save(fig, "F11_label_cooccurrence")


# ==========================================================================
# F12 - Route decision diagram
# ==========================================================================
def f12_route_decision():
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9); ax.axis("off"); ax.grid(False)

    box(ax, 3.3, 8.05, 3.4, 0.75, "Phase 0 audit complete", OI["grey"])
    box(ax, 2.9, 6.6, 4.2, 0.85, "Provider confirms\nREAL clinical data?", "#1d3557")
    arrow(ax, (5.0, 8.05), (5.0, 7.45))

    box(ax, 0.15, 5.0, 3.4, 0.85, "Independence tests\nstill show zero signal?", "#1d3557")
    arrow(ax, (3.6, 7.02), (1.85, 5.85)); ax.text(2.4, 6.55, "Yes", fontsize=7, weight="bold")
    ax.text(7.3, 6.55, "No / synthetic /\nno response", fontsize=7, weight="bold",
            ha="center", color=OI["red"])
    arrow(ax, (7.1, 7.02), (8.2, 4.2), color=OI["red"])

    box(ax, 0.15, 3.4, 3.4, 0.8, "ROUTE B-real\nStandard supervised pipeline", "#2d6a4f")
    arrow(ax, (1.0, 5.0), (1.0, 4.2)); ax.text(1.2, 4.55, "Signal", fontsize=6.5)

    box(ax, 6.5, 3.35, 3.3, 0.85, "Real free-text reports\nobtainable in 3 weeks?", "#1d3557")
    arrow(ax, (2.9, 5.42), (6.5, 3.9)); ax.text(4.6, 4.75, "Still zero", fontsize=6.5)

    box(ax, 6.5, 1.9, 3.3, 0.8, "ROUTE B - Re-collect\nPublication viable", "#2d6a4f")
    arrow(ax, (8.15, 3.35), (8.15, 2.7)); ax.text(8.3, 3.0, "Yes", fontsize=6.5)

    box(ax, 2.4, 1.9, 3.5, 0.8, "ROUTE A - Reframe\nHonest system + negative result", "#bc6c25")
    arrow(ax, (6.5, 3.6), (4.15, 2.7)); ax.text(5.0, 3.15, "No", fontsize=6.5)

    box(ax, 2.4, 0.5, 3.5, 0.8,
        "SELECTED: ROUTE A\n(6/6 integrity tests failed; no provenance statement)",
        "#d00000", fs=7)
    arrow(ax, (4.15, 1.9), (4.15, 1.3), color=OI["red"], lw=1.6)
    save(fig, "F12_route_decision")


# ==========================================================================
# F13 - PRISMA flow diagram
# ==========================================================================
def f13_prisma():
    P = json.loads((ROOT / "literature" / "prisma_counts.json").read_text(encoding="utf-8"))
    s, e = P["stages"], P["eligibility"]
    fig, ax = plt.subplots(figsize=(7.0, 6.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 12.4); ax.axis("off"); ax.grid(False)

    for y0, y1, lbl, c in [(10.2, 12.3, "Identification", "#0072B2"),
                           (6.6, 10.1, "Screening", "#E69F00"),
                           (3.0, 6.5, "Eligibility", "#009E73"),
                           (0.3, 2.9, "Included", "#D55E00")]:
        ax.add_patch(FancyBboxPatch((0.02, y0), 0.92, y1 - y0,
                                    boxstyle="round,pad=0.01",
                                    facecolor=c, edgecolor="none", alpha=0.9))
        ax.text(0.48, (y0 + y1) / 2, lbl, rotation=90, ha="center", va="center",
                fontsize=8, weight="bold", color="white")

    W, X = 4.9, 1.15          # main column
    EX, EW = 6.35, 3.45       # side exclusion column
    q = P["queries"]
    tot_hits = sum(v["total_hits"] for v in q.values())

    box(ax, X, 11.25, W, 0.95,
        f"Records identified in PubMed/MEDLINE\n{len(q)} search strings, {tot_hits:,} total hits\n"
        f"{s['records_identified_total']} retrieved (cap {q['S1_endoscopy_nlp']['retmax']} per query)",
        "#0072B2", fs=6.6)
    box(ax, X, 10.2, W, 0.72,
        f"Records after de-duplication: {s['records_after_deduplication']}\n"
        f"({s['duplicates_removed']} cross-query duplicates removed)", "#0072B2", fs=6.6)
    arrow(ax, (X + W / 2, 11.25), (X + W / 2, 10.92))

    box(ax, X, 8.9, W, 0.72,
        f"Records screened on title/abstract\nn = {s['records_screened']}",
        "#E69F00", fs=7.2, tc="black")
    arrow(ax, (X + W / 2, 10.2), (X + W / 2, 9.62))

    reasons = list(s["exclusion_reasons"].items())[:5]
    txt = "\n".join(f"• {k[:40]}: {v}" for k, v in reasons)
    box(ax, EX, 8.35, EW, 1.75,
        f"Excluded at screening, n = {s['records_excluded_at_screening']}\n{txt}",
        "#adb5bd", tc="black", fs=5.1)
    arrow(ax, (X + W, 9.26), (EX, 9.26), color="#888888")

    box(ax, X, 6.75, W, 0.72,
        f"Records assessed for eligibility\nn = {s['records_passing_screen']}",
        "#E69F00", fs=7.2, tc="black")
    arrow(ax, (X + W / 2, 8.9), (X + W / 2, 7.47))

    box(ax, X, 4.65, W, 1.15,
        "Theme-specific eligibility criteria\nand per-theme relevance ranking applied",
        "#009E73", fs=7.0)
    arrow(ax, (X + W / 2, 6.75), (X + W / 2, 5.8))

    box(ax, EX, 3.65, EW, 2.4,
        f"Excluded at eligibility, n = "
        f"{e['records_failing_theme_criteria'] + e['records_excluded_preprint'] + e['records_excluded_homonym_false_positive'] + e['records_excluded_duplicate_copublication'] + e['records_excluded_primary_not_methodological'] + e['records_eligible_but_capped']}\n"
        f"• Failed theme criteria: {e['records_failing_theme_criteria']}\n"
        f"• Preprint, not peer reviewed: {e['records_excluded_preprint']}\n"
        f"• Homonym false positive: {e['records_excluded_homonym_false_positive']}\n"
        f"• Duplicate / co-publication: {e['records_excluded_duplicate_copublication']}\n"
        f"• Primary study, not a\n   methodological appraisal: "
        f"{e['records_excluded_primary_not_methodological']}\n"
        f"• Eligible but outside per-theme\n   relevance cap: {e['records_eligible_but_capped']}",
        "#adb5bd", tc="black", fs=5.4)
    arrow(ax, (X + W, 5.22), (EX, 5.22), color="#888888")

    box(ax, 0.95, 2.05, 3.5, 0.85,
        f"Included from PubMed/MEDLINE\nn = {e['records_included_from_pubmed']}",
        "#D55E00", fs=6.8)
    box(ax, 5.05, 2.05, 3.9, 0.85,
        f"Included via other methods\n(hand-searched CS venues)\nn = {e['records_included_other_methods']}",
        "#D55E00", fs=6.4)
    arrow(ax, (X + W / 2, 4.65), (2.7, 2.9))

    box(ax, 2.3, 0.5, 5.2, 0.85,
        f"Studies included in the extraction table\nn = {e['records_included_total']}",
        "#8b1a1a", fs=7.8)
    arrow(ax, (2.7, 2.05), (4.2, 1.35)); arrow(ax, (7.0, 2.05), (5.7, 1.35))
    save(fig, "F13_prisma_flow")


# ==========================================================================
# F14 - literature distribution ; F15 - timeline ; F16 - keywords
# ==========================================================================
def f14_lit_distribution():
    d = pd.read_csv(ROOT / "literature" / "extraction_table.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.0))
    tc = d.theme.value_counts()
    cols = [OI["blue"], OI["orange"], OI["green"], OI["red"], OI["purple"]]
    a1.barh(range(len(tc)), tc.to_numpy(), color=cols[:len(tc)],
            edgecolor="black", linewidth=0.5)
    a1.set_yticks(range(len(tc)))
    a1.set_yticklabels([t.replace(" ", "\n", 1) for t in tc.index], fontsize=6.5)
    for i, v in enumerate(tc.to_numpy()):
        a1.text(v + 0.15, i, str(v), va="center", fontsize=7.5, weight="bold")
    a1.set_xlabel("Included studies"); a1.set_title("Distribution by sub-review theme")
    a1.invert_yaxis(); a1.set_xlim(0, tc.max() * 1.2)

    src = d.source.fillna("PubMed/MEDLINE").value_counts()
    a2.pie(src.to_numpy(), labels=[f"{i}\n(n={v})" for i, v in src.items()],
           autopct="%1.0f%%", colors=[OI["sky"], OI["yellow"]],
           textprops={"fontsize": 7}, wedgeprops={"edgecolor": "black", "linewidth": 0.6})
    a2.set_title("Identification route")
    a2.grid(False)
    save(fig, "F14_literature_distribution")


def f15_timeline():
    d = pd.read_csv(ROOT / "literature" / "extraction_table.csv")
    yc = d.year.astype(int).value_counts().sort_index()
    allyr = range(yc.index.min(), yc.index.max() + 1)
    yc = yc.reindex(allyr, fill_value=0)
    fig, ax = plt.subplots(figsize=(6.8, 2.9))
    ax.bar(yc.index, yc.to_numpy(), color=OI["blue"], edgecolor="black", linewidth=0.5)
    ax.plot(yc.index, yc.to_numpy(), color=OI["red"], marker="o", ms=3, lw=1.2,
            label="Trend")
    for x, v in zip(yc.index, yc.to_numpy()):
        if v:
            ax.text(x, v + 0.25, str(v), ha="center", fontsize=6.5, weight="bold")
    ax.set_xlabel("Publication year"); ax.set_ylabel("Included studies")
    ax.set_title("Publication timeline of the included literature")
    ax.set_xticks(list(allyr)); ax.tick_params(axis="x", labelsize=6.5, rotation=90)
    ax.set_ylim(0, yc.max() * 1.25)
    ax.legend(fontsize=7, frameon=False)
    save(fig, "F15_publication_timeline")


STOP = set("""a an and are as at be by for from has have in into is it its of on or that the to
with we our this these those which was were been study studies using used use results
method methods can may also such between both within their there than then when while
have not no all any more most other some new our can based approach paper article
present presented show shown found high low large small significant significantly
data model models performance clinical patients patient""".split())


def f16_keywords():
    d = pd.read_csv(ROOT / "literature" / "extraction_table.csv")
    txt = " ".join(d.title.fillna("").astype(str)).lower()
    toks = re.findall(r"[a-z][a-z\-]{2,}", txt)
    cnt = Counter(t for t in toks if t not in STOP and len(t) > 3)
    top = cnt.most_common(20)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    words = [w for w, _ in top][::-1]; vals = [v for _, v in top][::-1]
    ax.barh(range(len(words)), vals, color=OI["green"], edgecolor="black", linewidth=0.5)
    ax.set_yticks(range(len(words))); ax.set_yticklabels(words, fontsize=7)
    for i, v in enumerate(vals):
        ax.text(v + 0.1, i, str(v), va="center", fontsize=6.5)
    ax.set_xlabel("Frequency in included titles")
    ax.set_title("Top 20 content terms across the 50 included studies")
    ax.set_xlim(0, max(vals) * 1.15)
    save(fig, "F16_keyword_frequency")


# ==========================================================================
# F17 - conceptual framework ; F18 - methodology pipeline
# ==========================================================================
def f17_conceptual_framework():
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.axis("off"); ax.grid(False)

    box(ax, 0.2, 5.5, 2.6, 1.1, "DATA LAYER\nTemplated UGI\nendoscopy records", OI["grey"])
    box(ax, 3.7, 5.5, 2.6, 1.1, "LABEL LAYER\nRule-derived\nsilver labels", "#bc6c25")
    box(ax, 7.2, 5.5, 2.6, 1.1, "MODEL LAYER\nClassical ML +\nrule-based arm", "#1d3557")
    arrow(ax, (2.8, 6.05), (3.7, 6.05)); arrow(ax, (6.3, 6.05), (7.2, 6.05))

    box(ax, 0.2, 3.7, 2.6, 1.1, "Threat: synthetic\ngeneration\n(Phase 0 battery)", "#8b1a1a", fs=7)
    box(ax, 3.7, 3.7, 2.6, 1.1, "Threat: circularity\n& ambiguity\n(Phase 0 audit)", "#8b1a1a", fs=7)
    box(ax, 7.2, 3.7, 2.6, 1.1, "Threat: inflated\nperformance\n(E03-E06)", "#8b1a1a", fs=7)
    for x in (1.5, 5.0, 8.5):
        arrow(ax, (x, 5.5), (x, 4.8), color=OI["red"], ls="--")

    box(ax, 1.4, 2.0, 7.2, 0.95,
        "VALIDITY LAYER - permutation testing, feature provenance, grouped splitting,\n"
        "temporal validation, TRIPOD+AI reporting", "#2d6a4f", fs=7.5)
    for x in (1.5, 5.0, 8.5):
        arrow(ax, (x, 3.7), (x, 2.95), color="#2d6a4f")

    box(ax, 1.4, 0.4, 7.2, 0.95,
        "CONTRIBUTION - an auditable negative result plus a quantified account of how\n"
        "label construction and leakage generate apparent performance", "#d00000", fs=7.5)
    arrow(ax, (5.0, 2.0), (5.0, 1.35), lw=1.6)
    save(fig, "F17_conceptual_framework")


def f18_methodology_pipeline():
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3.2); ax.axis("off"); ax.grid(False)
    steps = [("Acquire\n& fingerprint", OI["grey"]), ("Integrity\nbattery", "#8b1a1a"),
             ("Leakage &\nlabel audit", "#8b1a1a"), ("Route\ndecision", "#d00000"),
             ("Systematic\nsearch", "#1d3557"), ("Screen &\nextract", "#1d3557"),
             ("Gap analysis\n& RQs", "#2d6a4f")]
    w, gap = 1.24, 0.145
    x = 0.15
    for t, c in steps:
        box(ax, x, 1.5, w, 1.0, t, c, fs=6.6)
        x += w + gap
    for i in range(len(steps) - 1):
        xs = 0.15 + (i + 1) * (w + gap)
        arrow(ax, (xs - gap, 2.0), (xs, 2.0))
    ax.text(5.0, 0.85, "Deliverables: phase0_results.json  |  feature_provenance.csv  |  "
                       "extraction_table.csv  |  prisma_counts.json",
            ha="center", fontsize=6.8, style="italic", color="#444444")
    ax.text(5.0, 0.35, "Every stage is executed by a committed script and re-runnable end to end",
            ha="center", fontsize=6.8, weight="bold", color="#8b1a1a")
    save(fig, "F18_methodology_pipeline")


# ==========================================================================
# F19 - honest baselines
# ==========================================================================
def f19_baselines():
    h = R["leakage"]["honest_baselines_target_comments"]
    order = ["E00a_dummy_most_frequent", "E00b_dummy_stratified",
             "E01_logistic_regression", "E01b_random_forest",
             "E01c_gradient_boosting", "E02_tfidf_linearsvc"]
    lbl = ["Dummy\n(most frequent)", "Dummy\n(stratified)", "Logistic\nregression",
           "Random\nforest", "Gradient\nboosting", "TF-IDF +\nLinearSVC"]
    vals = [h[k]["accuracy"] for k in order]
    errs = [h[k]["std"] or 0 for k in order]
    maj = h["majority_baseline"]["accuracy"]
    rnd = h["random_baseline"]["accuracy"]

    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    ax.bar(lbl, vals, yerr=errs, capsize=4, color=OI["sky"],
           edgecolor="black", linewidth=0.6)
    ax.axhline(maj, color=OI["red"], ls="--", lw=1.5, label=f"Majority baseline = {maj:.4f}")
    ax.axhline(rnd, color=OI["grey"], ls=":", lw=1.5, label=f"Random (1/6) = {rnd:.4f}")
    for i, (v, e) in enumerate(zip(vals, errs)):
        ax.text(i, v + e + 0.006, f"{v:.4f}", ha="center", fontsize=7, weight="bold")
    ax.set_ylabel("5-fold CV accuracy")
    ax.set_ylim(0, 0.26)
    ax.set_title("Honest baselines with the diagnosis field as target:\n"
                 "no model exceeds the majority baseline")
    ax.legend(fontsize=7, frameon=False)
    ax.tick_params(axis="x", labelsize=6.8)
    save(fig, "F19_honest_baselines")


# ==========================================================================
def main():
    print("[figures] generating ...")
    for fn in [f01_workflow, f02_integrity_gate, f03_cardinality, f04_age,
               f05_association_heatmaps, f06_mosaic, f07_target_distribution,
               f08_leakage_cascade, f09_permutation, f10_label_ambiguity,
               f11_cooccurrence, f12_route_decision, f13_prisma,
               f14_lit_distribution, f15_timeline, f16_keywords,
               f17_conceptual_framework, f18_methodology_pipeline, f19_baselines]:
        fn()
    print(f"[figures] {len(SAVED)} figures -> {FIG}")


if __name__ == "__main__":
    main()
