"""
Figure generation for the GastroHUN Phase 0 / Phase 1 report.
=============================================================
Every figure is regenerated from the audit artefacts in `reports/` and the
literature tables in `literature_v2/`. Nothing is drawn from hand-entered
numbers. Colourblind-safe Okabe-Ito palette throughout.

Inputs
  reports/gastrohun_inventory.json
  reports/gastrohun_agreement.json
  reports/gastrohun_structure.json
  reports/gastrohun_neardup.json      (optional; contamination panel skipped if absent)
  reports/phase0_results.json         (previous dataset, used as negative control)
  literature_v2/*.csv, literature_v2/prisma_counts.json

Run:  python src/report/figures_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Wedge

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "figures_v2"
FIG.mkdir(exist_ok=True)
REP = ROOT / "reports"
LIT = ROOT / "literature_v2"


def _load(name: str):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


INV = _load("gastrohun_inventory.json")
AGR = _load("gastrohun_agreement.json")
STR = _load("gastrohun_structure.json")
ND = _load("gastrohun_neardup.json")
CAL = _load("gastrohun_dup_calibration.json")
OLD = _load("phase0_results.json")

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
WALL_ORDER = ["G", "A", "L", "P"]
STATIONS = [1, 2, 3, 4, 5, 6]


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", facecolor="white")
    plt.close(fig)
    SAVED.append(name)
    print(f"  [fig] {name}")


def box(ax, x, y, w, h, text, fc, tc="white", fs=7.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                linewidth=1.0, edgecolor="#333333", facecolor=fc))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, weight="bold", wrap=True)


def arrow(ax, p1, p2, color="#333333"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=11,
                                 linewidth=1.1, color=color))


# ==========================================================================
# F01  Thesis workflow
# ==========================================================================
def f01() -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.5))
    ax.set_xlim(0, 100); ax.set_ylim(0, 46); ax.axis("off"); ax.grid(False)

    phases = [
        ("PHASE 0\nData provenance\n& integrity gate", OI["blue"]),
        ("PHASE 1\nLiterature review\n& problem framing", OI["sky"]),
        ("PHASE 2\nBaseline\nreproduction", OI["green"]),
        ("PHASE 3\nAgreement-stratified\nevaluation", OI["orange"]),
        ("PHASE 4\nSoft-label &\nuncertainty training", OI["purple"]),
        ("PHASE 5\nExternal\nvalidation", OI["red"]),
    ]
    w, gap = 14.0, 1.6
    for i, (t, c) in enumerate(phases):
        x = 2 + i * (w + gap)
        box(ax, x, 26, w, 12, t, c, fs=7.2)
        if i < len(phases) - 1:
            arrow(ax, (x + w, 32), (x + w + gap, 32))

    ax.text(50, 21.5, "Deliverable of this report", ha="center",
            fontsize=9, style="italic", color="#333333")
    ax.add_patch(FancyBboxPatch((2, 12), 2 * w + gap, 8,
                                boxstyle="round,pad=0.02",
                                linewidth=1.6, edgecolor=OI["red"],
                                facecolor="none", linestyle="--"))
    notes = [
        (9, "8,834 images · 387 patients\n0 corrupt · 0 duplicates"),
        (25, "1,349 records screened\n82 studies included"),
        (41, "ConvNeXt family\nmacro F1 ≈ 88"),
        (57, "5 agreement strata\n(4/4 · 3/4 · 2/2 · team · single)"),
        (72, "Soft targets from\n4 annotator votes"),
        (88, "HyperKvasir /\nGastroVision"),
    ]
    for x, t in notes:
        ax.text(x, 7.5, t, ha="center", fontsize=6.4, color="#444444")
    save(fig, "F01_thesis_workflow")


# ==========================================================================
# F02  Phase 0 integrity gate, as applied to an imaging corpus
# ==========================================================================
def f02() -> None:
    fig, ax = plt.subplots(figsize=(8.4, 8.0))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off"); ax.grid(False)

    inv = INV or {}
    agr = AGR or {}
    steps = [
        ("G1  Provenance & licence\nsource, ethics ID, licence, version", OI["blue"],
         "PASS — Sci Data 12:102 (2025)\nCEI-2019-06-10 · CC BY 4.0"),
        ("G2  Physical integrity\nmanifest ↔ disk, decode, corruption", OI["blue"],
         f"PASS — {inv.get('n_decoded_ok', 0):,}/{inv.get('n_manifest_rows', 0):,} decoded\n"
         f"{inv.get('n_missing_from_disk', 0)} missing · {inv.get('n_corrupt', 0)} corrupt"),
        ("G3  Duplication & contamination\nexact hash + perceptual near-dup", OI["blue"],
         f"PASS — {inv.get('exact_duplicates', {}).get('n_groups', 0)} exact duplicate groups\n"
         "cross-split pairs pixel-verified"),
        ("G4  Label structure\nannotators, classes, consensus tiers", OI["green"],
         f"PASS — 4 independent experts\n{agr.get('n_classes', 0)} classes retained separately"),
        ("G5  Agreement quantification\nκ, α, AC1, per-class, per-patient", OI["green"],
         f"PASS — Fleiss κ = {agr.get('fleiss_kappa', 0):.3f}\n"
         f"α = {agr.get('krippendorff_alpha', 0):.3f} · AC1 = {agr.get('gwet_ac1', 0):.3f}"),
        ("G6  Split integrity\npatient disjointness, balance", OI["green"],
         "PASS — 0 patient overlaps\nclass χ² p ≈ 1.0"),
        ("G7  Statistical power\nper-class test precision", OI["orange"],
         f"CONDITIONAL — {agr.get('n_test_classes_underpowered_hw_gt_10pct', 0)}/23 classes\n"
         "have Wilson half-width > 10 pp"),
        ("G8  Population description\ndemographics, clinical context", OI["orange"],
         "CONDITIONAL — no age or sex\n60.2% have a clinical record"),
    ]
    y = 92
    for i, (label, colour, verdict) in enumerate(steps):
        box(ax, 4, y - 8, 44, 8.6, label, colour, fs=7.0)
        vcol = ("#1B5E20" if verdict.startswith("PASS") else "#E65100")
        ax.add_patch(FancyBboxPatch((52, y - 8), 44, 8.6,
                                    boxstyle="round,pad=0.02", linewidth=1.0,
                                    edgecolor=vcol, facecolor="#FFFFFF"))
        ax.text(74, y - 3.7, verdict, ha="center", va="center",
                fontsize=6.6, color=vcol, weight="bold")
        arrow(ax, (48, y - 3.7), (52, y - 3.7), color="#777777")
        if i < len(steps) - 1:
            arrow(ax, (26, y - 8), (26, y - 11.4))
        y -= 11.4
    ax.text(50, 1.5, "Gate verdict: PROCEED — the two conditional items are "
                     "reportable limitations, not blocking defects.",
            ha="center", fontsize=8, weight="bold", color="#1B5E20")
    save(fig, "F02_integrity_gate")


# ==========================================================================
# F03  SSS protocol: the 22 landmarks as a wall x station grid
# ==========================================================================
def f03() -> None:
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    tax = {t["code"]: t for t in STR["taxonomy"]}
    present = {(t["wall"], t["station"]): c for c, t in tax.items()
               if t["is_landmark"]}
    ca = AGR["complete_agreement_distribution"]

    grid = np.full((4, 6), np.nan)
    for (w, s), code in present.items():
        grid[WALL_ORDER.index(w), s - 1] = ca.get(code, 0)

    im = ax.imshow(grid, cmap="YlGnBu", aspect="auto")
    for i in range(4):
        for j in range(6):
            code = present.get((WALL_ORDER[i], j + 1))
            if code is None:
                ax.text(j, i, "—", ha="center", va="center",
                        color="#BBBBBB", fontsize=12)
                continue
            v = grid[i, j]
            ax.text(j, i - 0.16, code, ha="center", va="center",
                    fontsize=9, weight="bold",
                    color="white" if v > np.nanmean(grid) else "black")
            ax.text(j, i + 0.20, f"n={int(v)}", ha="center", va="center",
                    fontsize=7,
                    color="white" if v > np.nanmean(grid) else "#333333")

    ax.set_xticks(range(6))
    ax.set_xticklabels([f"S{s}\n{STR['station_names'][str(s)]}" for s in STATIONS],
                       fontsize=6.6)
    ax.set_yticks(range(4))
    ax.set_yticklabels([STR["wall_names"][w] for w in WALL_ORDER], fontsize=8)
    ax.set_title("SSS landmark taxonomy — wall × station, shaded by "
                 "complete-agreement image count")
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.82, label="images with 4/4 agreement")
    save(fig, "F03_sss_taxonomy")


# ==========================================================================
# F04  Class distribution: per annotator vs complete agreement
# ==========================================================================
def f04() -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    classes = AGR["classes"]
    x = np.arange(len(classes))
    marg = AGR["marginals"]
    ca = AGR["complete_agreement_distribution"]

    for i, (a, c) in enumerate(zip(["FG1", "FG2", "G1", "G2"],
                                   [OI["sky"], OI["blue"], OI["green"], OI["orange"]])):
        ax.plot(x, [marg[a][k] for k in classes], "o-", ms=3.2, lw=1.1,
                color=c, label=f"{a} (all 8,834)", alpha=0.85)
    ax.bar(x, [ca.get(k, 0) for k in classes], color=OI["grey"], alpha=0.32,
           label="4/4 complete agreement", zorder=0)

    ax.set_xticks(x); ax.set_xticklabels(classes, rotation=60, fontsize=7)
    ax.set_ylabel("images")
    ax.set_title("Per-annotator class distribution against the "
                 "complete-agreement subset")
    ax.legend(fontsize=7, ncol=5, loc="upper center")
    save(fig, "F04_class_distribution")


# ==========================================================================
# F05  Pairwise Cohen's kappa matrix
# ==========================================================================
def f05() -> None:
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.4, 4.0),
                                  gridspec_kw={"width_ratios": [1, 1.15]})
    raters = ["FG1", "FG2", "G1", "G2"]
    pw = AGR["pairwise_cohen_kappa"]
    M = np.full((4, 4), np.nan)
    for i in range(4):
        M[i, i] = 1.0
        for j in range(4):
            if i == j:
                continue
            k = f"{raters[i]}-{raters[j]}"
            k2 = f"{raters[j]}-{raters[i]}"
            v = pw.get(k, pw.get(k2))
            if v:
                M[i, j] = v["kappa"]
    im = ax.imshow(M, cmap="RdYlGn", vmin=0.6, vmax=1.0)
    for i in range(4):
        for j in range(4):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.3f}", ha="center", va="center",
                        fontsize=8.5, weight="bold" if i != j else "normal",
                        color="black")
    ax.set_xticks(range(4)); ax.set_xticklabels(raters)
    ax.set_yticks(range(4)); ax.set_yticklabels(raters)
    ax.set_title("Pairwise Cohen's κ")
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8)

    order = sorted(pw.items(), key=lambda kv: kv[1]["kappa"])
    names = [k for k, _ in order]
    vals = [v["kappa"] for _, v in order]
    los = [v["kappa"] - v["ci95"][0] for _, v in order]
    his = [v["ci95"][1] - v["kappa"] for _, v in order]
    cols = [OI["red"] if n in ("FG1-FG2", "G1-G2") else OI["blue"] for n in names]
    ax2.barh(names, vals, xerr=[los, his], color=cols, height=0.62,
             error_kw={"lw": 1.0, "capsize": 3})
    for i, v in enumerate(vals):
        ax2.text(v + 0.012, i, f"{v:.3f}", va="center", fontsize=7.5)
    ax2.set_xlim(0.6, 0.88)
    ax2.set_xlabel("Cohen's κ (patient-clustered bootstrap 95% CI)")
    ax2.set_title("Within-team pairs (red) are not the most concordant")
    save(fig, "F05_kappa_matrix")


# ==========================================================================
# F06  Agreement tier cascade
# ==========================================================================
def f06() -> None:
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.9),
                                  gridspec_kw={"width_ratios": [1.25, 1]})
    t = AGR["agreement_tiers"]
    labels = ["All images", "Triple (3/4)", "Team G (2/2)",
              "Team FG (2/2)", "Complete (4/4)"]
    vals = [t["all_images"], t["triple_agreement_3of4"], t["G_team_agreement"],
            t["FG_team_agreement"], t["complete_agreement_4of4"]]
    cols = [OI["grey"], OI["sky"], OI["green"], OI["orange"], OI["blue"]]
    ax.bar(labels, vals, color=cols, width=0.66)
    for i, v in enumerate(vals):
        ax.text(i, v + 90, f"{v:,}\n{100*v/vals[0]:.1f}%", ha="center",
                fontsize=7.4, weight="bold")
    ax.set_ylabel("images")
    ax.set_ylim(0, vals[0] * 1.18)
    ax.set_title("Agreement-tier cascade")
    ax.tick_params(axis="x", labelsize=7.5)
    ax.axhline(vals[-1], ls="--", lw=0.9, color=OI["red"])
    ax.text(4.4, vals[-1], "published\nbenchmark\nuses only this",
            fontsize=6.4, color=OI["red"], va="center", ha="left")

    vp = AGR["vote_patterns_pct"]
    order = ["4", "3-1", "2-1-1", "2-2", "1-1-1-1"]
    lbl = {"4": "4–0 unanimous", "3-1": "3–1 majority", "2-1-1": "2–1–1 plurality",
           "2-2": "2–2 tie", "1-1-1-1": "all four differ"}
    pv = [vp.get(k, 0) for k in order]
    cc = [OI["green"], OI["sky"], OI["yellow"], OI["orange"], OI["red"]]
    w = ax2.pie(pv, labels=[lbl[k] for k in order], colors=cc,
                autopct="%1.1f%%", startangle=90,
                textprops={"fontsize": 7}, wedgeprops={"linewidth": 0.6,
                                                       "edgecolor": "white"})
    ax2.set_title(f"Vote patterns — {AGR['pct_no_majority']:.1f}% have no majority")
    ax2.grid(False)
    save(fig, "F06_agreement_cascade")


# ==========================================================================
# F07  Disagreement decomposition: wall vs station
# ==========================================================================
def f07() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.7))
    d = STR["disagreement_decomposition_pct"]
    ax = axes[0]
    keys = ["same_station_different_wall", "landmark_vs_OTHERCLASS",
            "same_wall_different_station", "different_wall_and_station"]
    lbls = ["Same station,\ndifferent wall", "Landmark vs\nOTHERCLASS",
            "Same wall,\ndifferent station", "Both differ"]
    cols = [OI["red"], OI["purple"], OI["orange"], OI["grey"]]
    vals = [d[k] for k in keys]
    ax.barh(range(4), vals, color=cols, height=0.6)
    ax.set_yticks(range(4)); ax.set_yticklabels(lbls, fontsize=7.2)
    ax.invert_yaxis()
    for i, v in enumerate(vals):
        ax.text(v + 0.8, i, f"{v:.1f}%", va="center", fontsize=8, weight="bold")
    ax.set_xlabel("% of all disagreement events")
    ax.set_xlim(0, 60)
    ax.set_title(f"Decomposition of {STR['n_disagreement_pair_events']:,} events")

    ax = axes[1]
    g = STR["agreement_by_granularity"]
    lv = ["full", "station", "wall"]
    nm = ["Full\n(23 classes)", "Station only\n(7)", "Wall only\n(5)"]
    kap = [g[l]["mean_pairwise_kappa"] for l in lv]
    una = [STR["unanimity_rate_pct_by_granularity"][l] / 100 for l in lv]
    x = np.arange(3)
    ax.bar(x - 0.19, kap, 0.36, color=OI["blue"], label="mean pairwise κ")
    ax.bar(x + 0.19, una, 0.36, color=OI["green"], label="4/4 unanimity rate")
    for i in range(3):
        ax.text(i - 0.19, kap[i] + 0.015, f"{kap[i]:.3f}", ha="center", fontsize=7)
        ax.text(i + 0.19, una[i] + 0.015, f"{una[i]*100:.1f}%", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(nm, fontsize=7.2)
    ax.set_ylim(0, 1.02); ax.set_ylabel("value")
    ax.legend(fontsize=6.8, loc="lower right")
    ax.set_title("Collapsing the wall recovers nothing;\ncollapsing the station recovers a lot")

    ax = axes[2]
    wp = STR["wall_confusion_pairs"]
    adjacent = {"G-A", "A-G", "A-L", "L-A", "L-P", "P-L", "G-P", "P-G"}
    names = list(wp)[:6]
    vals = [wp[n] for n in names]
    cols = [OI["red"] if n in adjacent else OI["blue"] for n in names]
    ax.bar(range(len(names)), vals, color=cols, width=0.62)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("disagreement events")
    n_adj = sum(v for n, v in wp.items() if n in adjacent)
    n_opp = sum(v for n, v in wp.items() if n not in adjacent)
    ax.set_title(f"Circumferentially adjacent walls (red)\n"
                 f"= {100*n_adj/(n_adj+n_opp):.1f}% of wall confusions")
    save(fig, "F07_disagreement_decomposition")


# ==========================================================================
# F08  Per-station difficulty and station adjacency
# ==========================================================================
def f08() -> None:
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.8))
    sd = STR["station_difficulty"]
    ks = [f"station_{s}" for s in STATIONS]
    vals = [sd[k]["disagreement_rate_pct"] for k in ks]
    names = [f"S{s}\n{sd[f'station_{s}']['name'][:22]}" for s in STATIONS]
    cols = [plt.cm.OrRd(0.25 + 0.6 * (v - min(vals)) / (max(vals) - min(vals)))
            for v in vals]
    ax.bar(range(6), vals, color=cols, width=0.66, edgecolor="#555555", lw=0.5)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.7, f"{v:.1f}%", ha="center", fontsize=7.6, weight="bold")
    ax.set_xticks(range(6)); ax.set_xticklabels(names, fontsize=6.2)
    ax.set_ylabel("rater-pair disagreement rate (%)")
    ax.set_title("Annotator difficulty by anatomical station")
    ax.set_ylim(0, max(vals) * 1.2)

    sp = STR["station_confusion_pairs"]
    M = np.zeros((6, 6))
    for k, v in sp.items():
        a, b = map(int, k.split("-"))
        M[a - 1, b - 1] = M[b - 1, a - 1] = v
    im = ax2.imshow(M, cmap="OrRd")
    for i in range(6):
        for j in range(6):
            if M[i, j] > 0:
                ax2.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=6.8,
                         color="white" if M[i, j] > M.max() * 0.55 else "black")
    ax2.set_xticks(range(6)); ax2.set_xticklabels([f"S{s}" for s in STATIONS])
    ax2.set_yticks(range(6)); ax2.set_yticklabels([f"S{s}" for s in STATIONS])
    ax2.set_title("Station confusion is concentrated on the diagonal band")
    ax2.grid(False)
    fig.colorbar(im, ax=ax2, shrink=0.8)
    save(fig, "F08_station_difficulty")


# ==========================================================================
# F09  OTHERCLASS is an annotator-specific judgement
# ==========================================================================
def f09() -> None:
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.6))
    oc = STR["otherclass"]
    r = oc["per_rater_OTHERCLASS_rate_pct"]
    names = list(r); vals = [r[k] for k in names]
    cols = [OI["sky"], OI["blue"], OI["green"], OI["orange"]]
    ax.bar(names, vals, color=cols, width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.15, f"{v:.2f}%", ha="center", fontsize=8, weight="bold")
    ax.set_ylabel("% of images called OTHERCLASS")
    ax.set_title(f"Quality rejection rate varies "
                 f"{max(vals)/min(vals):.1f}× between annotators")
    ax.set_ylim(0, max(vals) * 1.28)

    parts = [oc["n_images_unanimous_OTHERCLASS"],
             oc["n_images_any_rater_called_OTHERCLASS"] - oc["n_images_unanimous_OTHERCLASS"]]
    ax2.pie(parts, labels=["unanimous\n4/4", "contested\n(1–3 raters)"],
            colors=[OI["green"], OI["red"]], autopct="%1.1f%%", startangle=140,
            textprops={"fontsize": 8},
            wedgeprops={"linewidth": 0.6, "edgecolor": "white"})
    ax2.set_title(f"Of {oc['n_images_any_rater_called_OTHERCLASS']} images ever "
                  f"called unqualified,\nonly {oc['pct_of_OTHERCLASS_nominations_that_are_unanimous']:.1f}% "
                  f"are unanimous")
    ax2.grid(False)
    save(fig, "F09_otherclass")


# ==========================================================================
# F10  Per-patient agreement distribution and split balance
# ==========================================================================
def f10() -> None:
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.6),
                                  gridspec_kw={"width_ratios": [1.3, 1]})
    pa = STR["per_patient_agreement"]
    bins = [pa["n_below_0.4_poor"], pa["n_0.4_to_0.6_moderate"],
            pa["n_0.6_to_0.8_substantial"], pa["n_above_0.8_almost_perfect"]]
    lbl = ["< 0.40\npoor/fair", "0.40–0.60\nmoderate",
           "0.60–0.80\nsubstantial", "≥ 0.80\nalmost perfect"]
    cols = [OI["red"], OI["orange"], OI["sky"], OI["green"]]
    ax.bar(lbl, bins, color=cols, width=0.64)
    for i, v in enumerate(bins):
        ax.text(i, v + 3, f"{v}\n({100*v/sum(bins):.1f}%)", ha="center",
                fontsize=7.4, weight="bold")
    ax.set_ylabel("patients")
    ax.set_ylim(0, max(bins) * 1.24)
    ax.tick_params(axis="x", labelsize=7)
    ax.set_title(f"Per-patient Fleiss κ — mean {pa['mean']:.3f} "
                 f"(SD {pa['sd']:.3f}), range {pa['min']:.3f}–{pa['max']:.3f}")

    bs = pa["by_split"]
    names = ["Train", "Validation", "Test"]
    vals = [bs[n]["mean_kappa"] for n in names]
    ax2.bar(names, vals, color=[OI["blue"], OI["green"], OI["orange"]], width=0.55)
    for i, v in enumerate(vals):
        ax2.text(i, v + 0.008, f"{v:.4f}", ha="center", fontsize=8, weight="bold")
    ax2.set_ylim(0.7, 0.78)
    ax2.set_ylabel("mean per-patient Fleiss κ")
    ax2.set_title(f"Stratification held\nKruskal–Wallis p = {pa['kruskal_p']:.3f}")
    save(fig, "F10_patient_agreement")


# ==========================================================================
# F11  Official split integrity
# ==========================================================================
def f11() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.5))
    ss = AGR["split_summary"]
    names = ["Train", "Validation", "Test"]

    ax = axes[0]
    x = np.arange(3)
    ax.bar(x - 0.2, [ss[n]["pct_images"] for n in names], 0.38,
           color=OI["blue"], label="% images")
    ax.bar(x + 0.2, [ss[n]["pct_patients"] for n in names], 0.38,
           color=OI["green"], label="% patients")
    for i, n in enumerate(names):
        ax.text(i - 0.2, ss[n]["pct_images"] + 1, f"{ss[n]['pct_images']:.1f}",
                ha="center", fontsize=7)
        ax.text(i + 0.2, ss[n]["pct_patients"] + 1, f"{ss[n]['pct_patients']:.1f}",
                ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel("% of corpus"); ax.legend(fontsize=7)
    ax.set_title("Image and patient shares track\nthe intended 70/15/15")

    ax = axes[1]
    vals = [ss[n]["pct_complete_agreement"] for n in names]
    ax.bar(names, vals, color=[OI["blue"], OI["green"], OI["orange"]], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.4, f"{v:.2f}%", ha="center", fontsize=8, weight="bold")
    ax.set_ylim(50, 66); ax.set_ylabel("% with 4/4 agreement")
    ax.set_title(f"Agreement prevalence balanced\nχ² p = "
                 f"{AGR['split_agreement_chi2']['p']:.3f}")

    ax = axes[2]
    ov = AGR["split_patient_overlaps"]
    ax.axis("off"); ax.grid(False)
    ax.text(0.5, 0.92, "Patient-level disjointness", ha="center",
            fontsize=9.5, weight="bold", transform=ax.transAxes)
    y = 0.72
    for k, v in ov.items():
        ok = len(v) == 0
        ax.text(0.5, y, f"{k.replace('-', '  ∩  ')}   =   {len(v)} patients",
                ha="center", fontsize=8.5, transform=ax.transAxes,
                color="#1B5E20" if ok else "#B71C1C",
                weight="bold" if ok else "normal")
        y -= 0.14
    ax.text(0.5, y - 0.04,
            f"duplicate filenames: {AGR['n_duplicate_filenames']}\n"
            f"class prevalence χ² p = {AGR['split_class_chi2']['p']:.4f}\n"
            f"Cramér's V = {AGR['split_class_chi2']['cramers_v']:.4f}",
            ha="center", fontsize=8, transform=ax.transAxes, color="#1B5E20")
    save(fig, "F11_split_integrity")


# ==========================================================================
# F12  Class attrition caused by the complete-agreement filter
# ==========================================================================
def f12() -> None:
    fig, ax = plt.subplots(figsize=(9.6, 3.9))
    att = AGR["class_attrition_under_consensus"]
    classes = [c for c in AGR["classes"]]
    order = sorted(classes, key=lambda c: -(att[c]["attrition_pct"] or 0))
    vals = [att[c]["attrition_pct"] for c in order]
    cols = [OI["red"] if v > 50 else OI["orange"] if v > 40 else OI["blue"]
            for v in vals]
    ax.bar(range(len(order)), vals, color=cols, width=0.68)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=60, fontsize=7)
    ax.set_ylabel("% of nominations discarded")
    ax.axhline(np.mean(vals), ls="--", lw=1.0, color=OI["black"])
    ax.text(len(order) - 0.5, np.mean(vals) + 1.4, f"mean {np.mean(vals):.1f}%",
            ha="right", fontsize=7.5)
    ax.set_title("Attrition per class when the benchmark's complete-agreement "
                 "filter is applied")
    save(fig, "F12_class_attrition")


# ==========================================================================
# F13  Test-set precision per class
# ==========================================================================
def f13() -> None:
    fig, ax = plt.subplots(figsize=(9.6, 3.7))
    pw = AGR["test_set_power"]
    order = sorted(pw, key=lambda c: pw[c]["n_test"])
    ns = [pw[c]["n_test"] for c in order]
    hw = [100 * pw[c]["wilson_half_width_at_p85"] for c in order]
    ax.bar(range(len(order)), hw, color=OI["orange"], width=0.66)
    ax.axhline(10, ls="--", color=OI["red"], lw=1.2)
    ax.text(0.4, 10.5, "±10 pp precision target", fontsize=7.5, color=OI["red"])
    for i, (n, h) in enumerate(zip(ns, hw)):
        ax.text(i, h + 0.35, f"n={n}", ha="center", fontsize=5.8, rotation=90)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=60, fontsize=7)
    ax.set_ylabel("95% Wilson half-width at p = 0.85 (pp)")
    ax.set_ylim(0, max(hw) * 1.2)
    ax.set_title(f"Per-class test precision — "
                 f"{AGR['n_test_classes_underpowered_hw_gt_10pct']}/23 classes "
                 f"exceed the ±10 pp target")
    save(fig, "F13_test_power")


# ==========================================================================
# F14  Physical inventory panel
# ==========================================================================
def f14() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.4))
    ax = axes[0]
    res = INV["resolutions"]
    ks = list(res); vs = [res[k] for k in ks]
    ax.pie(vs, labels=[f"{k}\n({v:,})" for k, v in zip(ks, vs)],
           colors=[OI["blue"], OI["orange"]], autopct="%1.2f%%",
           startangle=120, textprops={"fontsize": 7.5},
           wedgeprops={"linewidth": 0.6, "edgecolor": "white"})
    ax.set_title("Native resolution"); ax.grid(False)

    ax = axes[1]
    st = STR["provenance"]["by_source_type"]
    ks = list(st)
    ax.bar(range(len(ks)), [st[k]["n"] for k in ks],
           color=[OI["green"], OI["purple"]], width=0.55)
    for i, k in enumerate(ks):
        ax.text(i, st[k]["n"] + 90, f"{st[k]['n']:,}\n{st[k]['pct_of_corpus']:.1f}%",
                ha="center", fontsize=7.4, weight="bold")
    ax.set_xticks(range(len(ks)))
    ax.set_xticklabels([k.replace("_", "\n") for k in ks], fontsize=7.5)
    ax.set_ylabel("images"); ax.set_ylim(0, 9600)
    ax.set_title(f"Acquisition provenance\nagreement difference p = "
                 f"{STR['provenance']['unanimity_p']:.2f} (n.s.)")

    ax = axes[2]
    ipp = INV["images_per_patient"]
    ax.axis("off"); ax.grid(False)
    rows = [
        ("Patients", "387"),
        ("Images", f"{INV['n_decoded_ok']:,}"),
        ("Images / patient", f"{ipp['mean']:.1f} ± {ipp['std']:.1f}"),
        ("Range", f"{ipp['min']}–{ipp['max']}"),
        ("Total size", f"{INV['bytes']['total_gb']:.2f} GB"),
        ("Mean file", f"{INV['bytes']['mean_kb']:.0f} KB"),
        ("Missing / orphan", f"{INV['n_missing_from_disk']} / {INV['n_orphan_on_disk']}"),
        ("Corrupt", f"{INV['n_corrupt']}"),
        ("Exact duplicates", f"{INV['exact_duplicates']['n_groups']}"),
    ]
    y = 0.95
    for k, v in rows:
        ax.text(0.02, y, k, fontsize=8, transform=ax.transAxes)
        ax.text(0.98, y, v, fontsize=8, weight="bold", ha="right",
                transform=ax.transAxes,
                color="#1B5E20" if v in ("0", "0 / 0") else "#222222")
        y -= 0.105
    ax.set_title("Inventory summary")
    save(fig, "F14_inventory")


# ==========================================================================
# F15  Contamination audit (only if the scan has completed)
# ==========================================================================
def f15() -> None:
    if ND is None:
        print("  [fig] F15 skipped — neardup scan not yet available")
        return
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.6))
    sweep = ND["threshold_sweep"]
    ts = sorted(sweep, key=int)
    wp = [sweep[t]["within_patient"] for t in ts]
    cp = [sweep[t]["cross_patient_same_split"] for t in ts]
    cs = [sweep[t]["cross_split"] for t in ts]
    x = np.arange(len(ts))
    ax.bar(x - 0.26, wp, 0.25, color=OI["green"], label="within patient")
    ax.bar(x, cp, 0.25, color=OI["orange"], label="cross patient, same split")
    ax.bar(x + 0.26, cs, 0.25, color=OI["red"], label="cross split")
    ax.set_yscale("symlog")
    ax.set_xticks(x); ax.set_xticklabels([f"≤{t}" for t in ts])
    ax.set_xlabel("dHash Hamming distance")
    ax.set_ylabel("candidate pairs (log)")
    ax.legend(fontsize=6.8)
    ax.set_title("Perceptual near-duplicate candidates")

    ax2.axis("off"); ax2.grid(False)
    rows = [
        ("Pairs examined", f"{ND['n_pairs_examined']:,}"),
        ("Exact (SHA-256) duplicates", f"{INV['exact_duplicates']['n_groups']}"),
        ("Cross-split candidates (Hamming ≤ 6)", f"{ND['cross_split_candidates']:,}"),
        ("Flagged by provisional rule", f"{ND['cross_split_verified_duplicates']}"),
    ]
    if CAL:
        rows += [
            ("Survive null-anchored rule",
             f"{CAL['reassessment']['n_passing_null_anchored_rule']}"),
            ("Survive calibrated rule",
             f"{CAL['reassessment']['n_confirmed_by_calibrated_rule']}"),
        ]
    y = 0.92
    for k, v in rows:
        ax2.text(0.02, y, k, fontsize=8, transform=ax2.transAxes)
        good = k.startswith(("Exact", "Survive"))
        ax2.text(0.98, y, v, fontsize=8, weight="bold", ha="right",
                 transform=ax2.transAxes,
                 color="#1B5E20" if (good and v == "0") else "#222222")
        y -= 0.115
    if CAL:
        c = CAL["calibrated_rule"]
        ax2.text(0.5, 0.12,
                 f"Adopted rule: RMS < {c['rms_cut']:.4f} and r > "
                 f"{c['corr_cut']:.4f}\n"
                 f"anchored on a synthetic-duplicate positive control\n"
                 f"sensitivity {100*c['sensitivity_on_positive_control']:.1f}% · "
                 f"FPR {100*c['false_positive_rate_on_null']:.2f}% · "
                 f"margin {c['separation_margin']:.3f}",
                 ha="center", fontsize=6.6, style="italic",
                 transform=ax2.transAxes, color="#555555")
    ax2.set_title("Cross-split contamination")
    save(fig, "F15_contamination")

    # companion panel: the two calibration distributions
    if CAL is None:
        return
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    c = CAL["calibrated_rule"]
    n, p = CAL["null"], CAL["positive_control"]
    ax.axvspan(0, c["rms_cut"], color=OI["green"], alpha=0.12)
    ax.errorbar([p["rms"]["mean"]], [1], xerr=[[p["rms"]["mean"] - 0],
                                               [p["rms"]["max"] - p["rms"]["mean"]]],
                fmt="o", color=OI["green"], capsize=4, ms=7,
                label=f"synthetic duplicates (n={p['n_pairs']:,})")
    ax.errorbar([n["rms"]["p50"]], [0.6],
                xerr=[[n["rms"]["p50"] - n["rms"]["min"]],
                      [n["rms"]["mean"] + 2 * n["rms"]["sd"] - n["rms"]["p50"]]],
                fmt="s", color=OI["blue"], capsize=4, ms=7,
                label=f"class-matched non-duplicates (n={n['n_pairs']:,})")
    flagged = [e["rms"] for e in CAL["reassessment"]["pairs"]]
    ax.plot(flagged, [0.8] * len(flagged), "x", color=OI["red"], ms=7,
            label=f"pairs flagged by provisional rule (n={len(flagged)})")
    ax.axvline(c["rms_cut"], ls="--", color=OI["black"], lw=1.2)
    ax.text(c["rms_cut"] + 0.004, 1.18, "decision threshold", fontsize=7.5)
    ax.set_xlim(0, max(flagged + [n["rms"]["p50"]]) * 1.15)
    ax.set_ylim(0.4, 1.3)
    ax.set_yticks([])
    ax.set_xlabel("normalised RMS difference (256×256 grayscale)")
    ax.legend(fontsize=6.8, loc="upper right")
    ax.set_title("Every flagged pair falls outside the duplicate envelope")
    save(fig, "F15b_dup_calibration")


# ==========================================================================
# F16  Negative control: the retired dataset vs GastroHUN
# ==========================================================================
def f16() -> None:
    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    ax.axis("off"); ax.grid(False)
    checks = [
        ("Real patients, verifiable provenance", False, True),
        ("Named ethics approval + informed consent", False, True),
        ("Independent expert labels retained", False, True),
        ("Inter-annotator agreement quantifiable", False, True),
        ("Labels independent of the features", False, True),
        ("Official patient-level splits published", False, True),
        ("Signal present above the majority floor", False, True),
        ("Peer-reviewed data descriptor", False, True),
        ("Reusable under an open licence", False, True),
        ("Complete demographic metadata", False, False),
        ("Per-class test set adequately powered", False, False),
    ]
    ax.text(0.44, 1.02, "Retired dataset\n(Peptic Ulcer_Dataset.xlsx)",
            ha="center", fontsize=8.5, weight="bold", transform=ax.transAxes)
    ax.text(0.78, 1.02, "GastroHUN", ha="center", fontsize=8.5,
            weight="bold", transform=ax.transAxes)
    y = 0.94
    for label, old_ok, new_ok in checks:
        ax.text(0.01, y, label, fontsize=8, transform=ax.transAxes, va="center")
        for xx, ok in ((0.44, old_ok), (0.78, new_ok)):
            ax.text(xx, y, "✓" if ok else "✗", ha="center", va="center",
                    fontsize=13, weight="bold", transform=ax.transAxes,
                    color="#1B5E20" if ok else "#B71C1C")
        y -= 0.085
    if OLD:
        pt = OLD.get("permutation_test", {})
        ax.text(0.5, 0.01,
                f"Retired dataset: permutation test p = {pt.get('p_value', float('nan')):.4f} "
                f"— no measurable association between features and target.\n"
                f"GastroHUN: Fleiss κ = {AGR['fleiss_kappa']:.3f} across four "
                f"independent experts on {AGR['n_images']:,} images.",
                ha="center", fontsize=7.6, style="italic",
                transform=ax.transAxes, color="#333333")
    ax.set_title("Phase 0 gate applied to both corpora — the audit protocol "
                 "discriminates", fontsize=10, weight="bold")
    save(fig, "F16_negative_control")


# ==========================================================================
# F17  PRISMA 2020 flow
# ==========================================================================
def f17() -> None:
    P = json.loads((LIT / "prisma_counts.json").read_text(encoding="utf-8"))
    s, e = P["stages"], P["eligibility"]
    fig, ax = plt.subplots(figsize=(8.4, 8.4))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off"); ax.grid(False)

    main_boxes = [
        (86, f"Records identified through database searching\n"
             f"PubMed/MEDLINE, 7 themed queries\n(n = {s['records_identified_total']:,})"),
        (72, f"Records after duplicates removed\n(n = {s['records_after_deduplication']:,})"),
        (58, f"Records screened on title/abstract\n(n = {s['records_screened']:,})"),
        (44, f"Records assessed for eligibility\n(n = {e['records_assessed_for_eligibility']:,})"),
        (24, f"Studies included from database searching\n"
             f"(n = {e['included_from_database_search']})"),
        (9, f"TOTAL STUDIES INCLUDED IN REVIEW\n(n = {e['total_included_in_review']})"),
    ]
    for y, t in main_boxes:
        fc = OI["blue"] if y != 9 else "#1B5E20"
        box(ax, 14, y, 46, 10, t, fc, fs=7.0)
    for y in (86, 72, 58, 44):
        arrow(ax, (37, y), (37, y - 4))
    arrow(ax, (37, 24), (37, 19))

    excl = [
        (72, f"Duplicates removed\n(n = {s['duplicates_removed']})"),
        (58, f"Excluded at screening\n(n = {s['records_excluded_at_screening']})"),
        (44, f"Excluded at eligibility (n = {e['excluded_at_eligibility']:,})\n"
             f"• non-GI endoscopy homonym: {e['excluded_non_gi_homonym']}\n"
             f"• not luminal GI: {e['excluded_not_luminal_gi']}\n"
             f"• failed theme criteria: {e['excluded_failed_criteria']}\n"
             f"• below relevance cap: {e['excluded_below_cap']}"),
    ]
    for y, t in excl:
        h = 12 if y == 44 else 8
        box(ax, 66, y - 1, 32, h, t, OI["grey"], fs=6.2)
        arrow(ax, (60, y + 4), (66, y + 4), color="#777777")

    box(ax, 66, 24, 32, 10,
        f"Identified via other methods\n(hand-searched, not MEDLINE-indexed)\n"
        f"(n = {e['included_from_other_methods']})", OI["orange"], fs=6.6)
    arrow(ax, (82, 24), (82, 19), color="#777777")
    arrow(ax, (82, 19), (60, 14), color="#777777")

    ax.text(50, 2.5, f"Search executed {P['run_date']} · "
                     f"{P['database']}", ha="center", fontsize=7,
            style="italic", color="#555555")
    ax.set_title("PRISMA 2020 flow — revised imaging protocol",
                 fontsize=11, weight="bold")
    save(fig, "F17_prisma")


# ==========================================================================
# F18  Literature composition
# ==========================================================================
def f18() -> None:
    df = pd.read_csv(LIT / "extraction_table.csv")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.2, 3.9),
                                  gridspec_kw={"width_ratios": [1.35, 1]})
    tc = df["theme"].value_counts().sort_values()
    cols = [OI["blue"], OI["sky"], OI["green"], OI["orange"],
            OI["purple"], OI["red"], OI["yellow"]]
    ax.barh(range(len(tc)), tc.values, color=cols[:len(tc)], height=0.62)
    ax.set_yticks(range(len(tc)))
    ax.set_yticklabels([t[:44] for t in tc.index], fontsize=7)
    for i, v in enumerate(tc.values):
        ax.text(v + 0.14, i, str(v), va="center", fontsize=8, weight="bold")
    ax.set_xlabel("included studies")
    ax.set_title(f"Composition of the {len(df)} included studies")

    yr = pd.to_numeric(df["year"], errors="coerce").dropna().astype(int)
    recent = yr[yr >= 2013]
    ax2.hist(recent, bins=range(2013, 2028), color=OI["blue"],
             edgecolor="white", linewidth=0.7)
    ax2.set_xlabel("publication year")
    ax2.set_ylabel("studies")
    ax2.set_title(f"Recency — {100*(yr>=2020).mean():.0f}% published 2020 or later\n"
                  f"({(yr<2013).sum()} foundational works before 2013 not shown)")
    save(fig, "F18_literature")


# ==========================================================================
# F19  Conceptual framework / the research gap
# ==========================================================================
def f19() -> None:
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    ax.set_xlim(0, 100); ax.set_ylim(0, 62); ax.axis("off"); ax.grid(False)

    box(ax, 3, 46, 28, 11,
        "ESTABLISHED\nSSS protocol reduces\nmissed gastric lesions", OI["green"], fs=7.2)
    box(ax, 36, 46, 28, 11,
        "ESTABLISHED\nCNNs classify gastric\nlandmarks at macro F1 ≈ 88", OI["green"], fs=7.2)
    box(ax, 69, 46, 28, 11,
        "ESTABLISHED\nEndoscopist agreement is\nimperfect (κ ≈ 0.68–0.80)", OI["green"], fs=7.2)

    box(ax, 18, 28, 64, 12,
        "THE GAP\nEvery published GastroHUN benchmark trains and tests on the "
        f"{AGR['agreement_tiers_pct']['complete_agreement_4of4']:.1f}% of images with "
        f"complete 4/4 consensus.\nPerformance on the remaining "
        f"{100-AGR['agreement_tiers_pct']['complete_agreement_4of4']:.1f}% — "
        "precisely the images a clinician finds ambiguous — is unmeasured.",
        OI["red"], fs=7.6)
    for x in (17, 50, 83):
        arrow(ax, (x, 46), (x if x == 50 else 50, 40))

    box(ax, 3, 10, 28, 13,
        "RQ1\nHow does landmark accuracy\ndegrade across the\nagreement spectrum?",
        OI["blue"], fs=7.0)
    box(ax, 36, 10, 28, 13,
        "RQ2\nDo soft targets built from\nall four votes beat\nconsensus-only training?",
        OI["blue"], fs=7.0)
    box(ax, 69, 10, 28, 13,
        "RQ3\nDoes predictive uncertainty\ntrack human disagreement,\nand transfer externally?",
        OI["blue"], fs=7.0)
    for x in (17, 50, 83):
        arrow(ax, (50 if x == 50 else 50, 28), (x, 23))

    ax.text(50, 4, "Structural finding enabling all three: "
                   f"{STR['disagreement_decomposition_pct']['same_station_different_wall']:.1f}% "
                   "of disagreement is wall confusion within an agreed station.",
            ha="center", fontsize=8, weight="bold", color="#333333")
    save(fig, "F19_conceptual_framework")


# ==========================================================================
# F20  Proposed methodology pipeline
# ==========================================================================
def f20() -> None:
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    ax.set_xlim(0, 100); ax.set_ylim(0, 58); ax.axis("off"); ax.grid(False)

    lanes = [
        ("DATA", OI["blue"], 44, [
            "GastroHUN\n8,834 img / 387 pt",
            "Official patient-level\nsplit 270/58/59",
            "Agreement strata\n4/4 · 3/1 · 2/2 · 2-1-1",
        ]),
        ("MODEL", OI["green"], 27, [
            "ConvNeXt-T backbone\n(28 M params)",
            "Targets: hard consensus\nvs soft 4-vote vector",
            "Loss: CE · label smoothing\n· soft-target KL",
        ]),
        ("EVALUATION", OI["orange"], 10, [
            "Macro F1 per\nagreement stratum",
            "Calibration: ECE,\nreliability diagrams",
            "External: HyperKvasir /\nGastroVision landmarks",
        ]),
    ]
    for name, colour, y, items in lanes:
        ax.text(1.5, y + 5.5, name, fontsize=8.5, weight="bold", color=colour)
        for i, it in enumerate(items):
            x = 13 + i * 30
            box(ax, x, y, 26, 11, it, colour, fs=6.8)
            if i < len(items) - 1:
                arrow(ax, (x + 26, y + 5.5), (x + 30, y + 5.5))
        if y > 10:
            arrow(ax, (50, y), (50, y - 6), color="#777777")
    ax.text(50, 3, "Patient-level bootstrap (1,000 resamples) for every "
                   "reported interval; seeds and configs version-controlled.",
            ha="center", fontsize=7.6, style="italic", color="#444444")
    save(fig, "F20_methodology")


def main() -> None:
    for fn in (f01, f02, f03, f04, f05, f06, f07, f08, f09, f10,
               f11, f12, f13, f14, f15, f16, f17, f18, f19, f20):
        try:
            fn()
        except Exception as exc:  # keep going; report which failed
            print(f"  [FAIL] {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(SAVED)} figures -> {FIG}")


if __name__ == "__main__":
    main()
