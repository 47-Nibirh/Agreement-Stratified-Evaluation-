"""
Phase 3B figure suite -- the corrections and the restored pre-registered
sections (F25-F30).

Every value is read from reports/phase3b_*.json. No number is typed into this
file, per the project's no-hand-typed-numbers rule (blueprint sec.8).

Run:  python src/report/figures_phase3b.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase2_style as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
FIGDIR = ROOT / "figures_phase3"
FIGDIR.mkdir(exist_ok=True)

TIER_ORDER = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]
TIER_LABELS = {"S-unanimous": "4/4\nunanimous", "S-majority": "3/4\nmajority",
               "S-plurality": "2-1-1\nplurality", "S-no-majority": "2-2 / 1-1-1-1\npooled"}


def save(fig, name):
    fig.savefig(FIGDIR / name, dpi=S.DPI)
    plt.close(fig)
    print(f"  wrote {name}")
    return FIGDIR / name


def load(name):
    p = REP / name
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


# ==========================================================================
# F25  Raw vs ceiling-normalised tier curve -- the headline correction
# ==========================================================================
def fig_ceiling_curve():
    d = load("phase3b_ceiling_gaps.json")
    if not d:
        return None
    r = d["rq1_restated"]
    ceil = [100 * d["ceilings"][t]["oracle_marginalized_macro_f1_mean"] for t in TIER_ORDER]
    raw = r["raw_marginalized_macro_f1"]
    nrm = r["ceiling_normalised_macro_f1_pct_of_attainable"]
    x = np.arange(len(TIER_ORDER))

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))

    ax = axes[0]
    ax.fill_between(x, ceil, 100, color=S.GRID, alpha=0.55, zorder=1,
                    label="unattainable by any single-label predictor")
    ax.plot(x, ceil, "^--", color=S.MUTED, lw=1.8, ms=9, zorder=3,
            label="attainable ceiling (modal-vote oracle)")
    ax.plot(x, raw, "o-", color=S.BLUE, lw=2.4, ms=10, mec="white", mew=1.3, zorder=4,
            label="frozen model (as reported in Phase 3)")
    for i, (c, v) in enumerate(zip(ceil, raw)):
        ax.annotate(f"{v:.1f}", (i, v), textcoords="offset points", xytext=(0, -18),
                    ha="center", fontsize=9.5, fontweight="bold", color=S.BLUE)
        ax.annotate(f"{c:.1f}", (i, c), textcoords="offset points", xytext=(0, 11),
                    ha="center", fontsize=8.8, color=S.MUTED)
        ax.vlines(i, v, c, color=S.ORANGE, lw=3.4, alpha=0.55, zorder=2)
    ax.set_ylim(0, 112)          # headroom so the 100.0 ceiling label clears the title
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("annotator-marginalized macro F1 (%)")
    ax.set_title("The ceiling moves with the tier\n"
                 "orange bar = headroom actually available to the model", pad=10)
    ax.legend(loc="upper right", fontsize=8.0)

    ax = axes[1]
    ax.plot(x, nrm, "o-", color=S.GREEN, lw=2.4, ms=10, mec="white", mew=1.3, zorder=4,
            label="ceiling-normalised (% of attainable)")
    for i, v in enumerate(nrm):
        ax.annotate(f"{v:.1f}", (i, v), textcoords="offset points", xytext=(0, -18),
                    ha="center", fontsize=9.5, fontweight="bold", color=S.GREEN)
    ax.plot(x, raw, "o--", color=S.BLUE, lw=1.5, ms=7, alpha=0.55, zorder=3,
            label="raw scale (for comparison)")
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of attainable score")
    lo, hi = r["ceiling_normalised_gap_ci95_points"]
    ax.set_title("Same model, ceiling held constant\n"
                 f"4/4 - no-majority gap = {r['ceiling_normalised_gap_points']:.2f} pts "
                 f"(95% CI {lo:.2f} to {hi:.2f}), not {r['raw_gap_points']:.1f}", pad=10)
    ax.legend(loc="lower left", fontsize=8.4)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([f"{TIER_LABELS[t]}\nn={d['ceilings'][t]['n_images']}"
                            for t in TIER_ORDER])
        ax.grid(axis="x", visible=False)
        S.despine(ax)
    fig.tight_layout()
    return save(fig, "P3_F25_ceiling_normalised_curve.png")


# ==========================================================================
# F26  Forest plot of all pairwise tier gaps, raw and ceiling-normalised
# ==========================================================================
def fig_gap_forest():
    d = load("phase3b_ceiling_gaps.json")
    if not d:
        return None
    g = d["pairwise_gaps"]
    bench = d["rq1_restated"]["architecture_benchmark_points"]
    pairs = [k for k in g if k.endswith("[raw]")]
    labels = [p.replace(" [raw]", "").replace("S-", "") for p in pairs]

    fig, ax = plt.subplots(figsize=(10.4, 5.6))
    y = np.arange(len(pairs))[::-1]
    for off, scale, col, mk in ((0.17, "raw", S.BLUE, "o"),
                                (-0.17, "ceiling_normalised", S.GREEN, "s")):
        pts, los, his = [], [], []
        for p in pairs:
            e = g[p.replace("[raw]", f"[{scale}]")]
            pts.append(e["gap_points_3seed_mean"])
            los.append(e["ci95_points_3seed_mean"][0])
            his.append(e["ci95_points_3seed_mean"][1])
        pts, los, his = np.array(pts), np.array(los), np.array(his)
        ax.errorbar(pts, y + off, xerr=[pts - los, his - pts], fmt=mk, color=col,
                    ms=7, capsize=4, lw=1.8, mec="white", mew=1.0,
                    label={"raw": "raw scale (as reported)",
                           "ceiling_normalised": "ceiling-normalised"}[scale])
    ax.axvline(0, color=S.INK, lw=1.1, zorder=1)
    ax.axvline(bench, color=S.ORANGE, lw=1.6, ls="--", zorder=1,
               label=f"architecture benchmark ({bench} pts)")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("gap in annotator-marginalized macro F1 (points), "
                  "patient-clustered bootstrap 95% CI")
    ax.set_title("Pairwise tier gaps -- the pre-registered intervals the delivered\n"
                 "Phase 3 did not compute (blueprint sec.4 Phase 3, decision 4)", pad=10)
    ax.grid(axis="y", visible=False)
    S.despine(ax)
    ax.legend(loc="lower right", fontsize=8.4)
    fig.tight_layout()
    return save(fig, "P3_F26_pairwise_gap_forest.png")


# ==========================================================================
# F27  Calibration by stratum (blueprint §3.8)
# ==========================================================================
def fig_calibration():
    d = load("phase3b_calibration.json")
    if not d:
        return None
    agg = d["aggregate_3seed"]
    fig = plt.figure(figsize=(12.6, 8.2))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 0.85], hspace=0.42, wspace=0.32)

    for i, t in enumerate(TIER_ORDER):
        ax = fig.add_subplot(gs[0, i])
        bins = d["per_seed"]["1"][t]["reliability_bins_vs_expected_accuracy"]
        xs = [b["mean_confidence"] for b in bins if b["n"]]
        ys = [b["mean_target"] for b in bins if b["n"]]
        ns = [b["n"] for b in bins if b["n"]]
        ax.plot([0, 1], [0, 1], ls="--", color=S.MUTED, lw=1.2, zorder=1)
        ax.scatter(xs, ys, s=[18 + 120 * n / max(ns) for n in ns], color=S.BLUE,
                   alpha=0.85, zorder=3, ec="white", lw=0.8)
        ax.plot(xs, ys, color=S.BLUE, lw=1.5, zorder=2)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(f"{t}\nECE {100*agg[t]['ece_vs_expected_accuracy']:.1f}%", fontsize=9.4)
        ax.set_xlabel("confidence", fontsize=8.6)
        if i == 0:
            ax.set_ylabel("expected accuracy", fontsize=8.6)
        S.despine(ax)

    ax = fig.add_subplot(gs[1, :2])
    x = np.arange(len(TIER_ORDER))
    conf = [100 * agg[t]["mean_confidence"] for t in TIER_ORDER]
    acc = [100 * agg[t]["expected_accuracy"] for t in TIER_ORDER]
    ax.plot(x, conf, "o-", color=S.RED, lw=2.2, ms=9, mec="white", mew=1.2,
            label="mean confidence")
    ax.plot(x, acc, "s-", color=S.BLUE, lw=2.2, ms=8, mec="white", mew=1.2,
            label="expected accuracy")
    ax.fill_between(x, acc, conf, color=S.RED, alpha=0.13)
    for i in x:
        ax.annotate(f"+{conf[i]-acc[i]:.0f}", (i, (conf[i] + acc[i]) / 2),
                    ha="center", fontsize=9, fontweight="bold", color=S.RED)
    ax.set_xticks(x); ax.set_xticklabels([TIER_LABELS[t] for t in TIER_ORDER], fontsize=8.4)
    ax.set_ylabel("%"); ax.set_ylim(0, 100); ax.grid(axis="x", visible=False)
    ax.set_title("Confidence barely moves while accuracy collapses", fontsize=9.8, pad=8)
    ax.legend(fontsize=8.4, loc="lower left"); S.despine(ax)

    ax = fig.add_subplot(gs[1, 2:])
    ece = [100 * agg[t]["ece_vs_expected_accuracy"] for t in TIER_ORDER]
    lo = [100 * agg[t]["ece_ci95_seed1"][0] for t in TIER_ORDER]
    hi = [100 * agg[t]["ece_ci95_seed1"][1] for t in TIER_ORDER]
    ax.bar(x, ece, color=S.ORANGE, alpha=0.85, width=0.62,
           yerr=[np.array(ece) - np.array(lo), np.array(hi) - np.array(ece)],
           capsize=5, ecolor=S.INK, error_kw={"lw": 1.3})
    for i, v in enumerate(ece):
        ax.annotate(f"{v:.1f}%", (i, hi[i]), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=9, fontweight="bold", color=S.INK)
    ax.set_ylim(0, max(hi) * 1.18)
    ax.set_xticks(x); ax.set_xticklabels([TIER_LABELS[t] for t in TIER_ORDER], fontsize=8.4)
    ax.set_ylabel("expected calibration error (%)")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"ECE rises {d['headline']['ece_ratio_worst_over_unanimous']:.1f}x "
                 "from the unanimous to the worst tier", fontsize=9.8, pad=8)
    S.despine(ax)

    fig.suptitle("Calibration by agreement stratum -- pre-registered as blueprint §3.8 "
                 "and absent from the delivered Phase 3", fontsize=11.5, y=0.985)
    return save(fig, "P3_F27_calibration_by_stratum.png")


# ==========================================================================
# F28  Per-class F1 across strata (blueprint §3.6)
# ==========================================================================
def fig_perclass():
    d = load("phase3b_perclass.json")
    if not d:
        return None
    pc = d["per_class_by_tier"]
    names = pc["S-unanimous"]["classes"]
    M = np.array([[pc[t]["marginalized_per_class_f1_3seed"][i] for t in TIER_ORDER]
                  for i in range(len(names))]) * 100
    order = np.argsort(-M[:, 0])
    M, names = M[order], [names[i] for i in order]

    fig, ax = plt.subplots(figsize=(8.0, 9.4))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(TIER_ORDER)))
    ax.set_xticklabels([TIER_LABELS[t] for t in TIER_ORDER], fontsize=8.6)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=8.2)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=7.4,
                    color=S.INK if 25 < M[i, j] < 80 else "white")
    ax.set_title("Per-class annotator-marginalized F1 across strata\n"
                 "(3-seed mean; classes ordered by S-unanimous F1)", pad=10, fontsize=10.5)
    fig.colorbar(im, ax=ax, fraction=0.032, pad=0.03, label="F1 (%)")
    ax.grid(False)
    fig.tight_layout()
    return save(fig, "P3_F28_perclass_heatmap.png")


# ==========================================================================
# F29  O3 geometry with intervals (replaces the point-difference claim)
# ==========================================================================
def fig_o3_intervals():
    d = load("phase3b_sensitivity.json")
    if not d:
        return None
    s = d["o3_confusion_structure_with_intervals"]["summary"]
    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    rows = [("Wall confusions\ncircumferentially adjacent",
             s["wall_adjacent_pct_3seed"], s["wall_adjacent_ci95_3seed"],
             s["human_wall_adjacent_pct"], s["wall_consistent_with_human"]),
            ("Station confusions\nneighbouring",
             s["station_neighbouring_pct_3seed"], s["station_neighbouring_ci95_3seed"],
             s["human_station_neighbouring_pct"], s["station_consistent_with_human"])]
    y = np.arange(len(rows))[::-1]
    for i, (lab, v, ci, hum, ok) in zip(y, rows):
        ax.errorbar(v, i, xerr=[[v - ci[0]], [ci[1] - v]], fmt="o", color=S.BLUE,
                    ms=10, capsize=6, lw=2.0, mec="white", mew=1.2, zorder=3)
        ax.scatter([hum], [i], marker="D", s=95, color=S.ORANGE, zorder=4,
                   ec="white", lw=1.1)
        ax.annotate(f"model {v:.2f}%  [{ci[0]:.1f}, {ci[1]:.1f}]", (v, i),
                    textcoords="offset points", xytext=(0, 15), ha="center", fontsize=8.6)
        ax.annotate(f"human {hum}", (hum, i), textcoords="offset points",
                    xytext=(0, -20), ha="center", fontsize=8.6, color=S.ORANGE)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlabel("% of confusions that are anatomically adjacent "
                  "(patient-clustered bootstrap 95% CI)")
    ax.set_xlim(60, 105)
    ax.set_title("O3 restated with intervals: both model shares are consistent with the\n"
                 "human benchmark -- the originally reported point gaps are not resolvable",
                 pad=10, fontsize=10.5)
    ax.grid(axis="y", visible=False)
    S.despine(ax)
    fig.tight_layout()
    return save(fig, "P3_F29_o3_intervals.png")


# ==========================================================================
# F30  Confound controls: class mix and acquisition stream
# ==========================================================================
def fig_confounds():
    p = load("phase3b_perclass.json")
    s = load("phase3b_sensitivity.json")
    if not (p and s):
        return None
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    x = np.arange(len(TIER_ORDER))

    ax = axes[0]
    c = p["class_composition_control"]
    pred = [100 * c[t]["expected_accuracy_predicted_by_class_mix_alone"] for t in TIER_ORDER]
    obs = [100 * c[t]["observed_expected_accuracy"] for t in TIER_ORDER]
    ax.plot(x, pred, "^--", color=S.MUTED, lw=1.9, ms=9,
            label="predicted by class mix alone\n(S-unanimous per-class accuracy, re-weighted)")
    ax.plot(x, obs, "o-", color=S.BLUE, lw=2.3, ms=9, mec="white", mew=1.2,
            label="observed")
    for i in x:
        ax.vlines(i, obs[i], pred[i], color=S.RED, lw=3.2, alpha=0.5)
    ax.set_ylim(0, 100); ax.set_ylabel("expected accuracy (%)")
    ax.set_title("Class composition explains "
                 f"{c['S-no-majority']['share_of_drop_explained_by_class_mix_pct']:.1f}% "
                 "of the drop\n(red bar = unexplained by class mix)", fontsize=10, pad=8)
    ax.legend(fontsize=7.8, loc="lower left")

    ax = axes[1]
    st = s["acquisition_stream_sensitivity"]
    allv = [st["tier_curve_all_streams"][t] for t in TIER_ORDER]
    domv = [st["tier_curve_dominant_stream_only"][t] for t in TIER_ORDER]
    ax.plot(x, allv, "o-", color=S.BLUE, lw=2.3, ms=9, mec="white", mew=1.2,
            label="all acquisition streams")
    ax.plot(x, domv, "s--", color=S.GREEN, lw=1.8, ms=7,
            label=f"{st['dominant_stream_px']}px stream only")
    ax.set_ylim(0, 100); ax.set_ylabel("annotator-marginalized macro F1 (%)")
    ax.set_title(f"Stream composition does not differ across tiers "
                 f"(chi2 p={st['p_value']:.3f});\ncurve shifts by at most "
                 f"{st['max_abs_shift_points']} points", fontsize=10, pad=8)
    ax.legend(fontsize=8.2, loc="lower left")

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([TIER_LABELS[t] for t in TIER_ORDER], fontsize=8.4)
        ax.grid(axis="x", visible=False)
        S.despine(ax)
    fig.tight_layout()
    return save(fig, "P3_F30_confound_controls.png")


def main() -> None:
    print("Phase 3B figures ->", FIGDIR)
    for fn in (fig_ceiling_curve, fig_gap_forest, fig_calibration, fig_perclass,
               fig_o3_intervals, fig_confounds):
        if fn() is None:
            print(f"  SKIPPED {fn.__name__} (input JSON missing)")


if __name__ == "__main__":
    main()
