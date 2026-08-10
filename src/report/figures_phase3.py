"""
Phase 3 figure suite -- agreement-stratified evaluation (RQ1).

Every figure is generated from reports/phase3_*.json -- no value is typed
into this file. Run:  python src/report/figures_phase3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase2_style as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
FIGDIR = ROOT / "figures_phase3"
FIGDIR.mkdir(exist_ok=True)

TIER_ORDER = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]
TIER_ORDER_FULL = ["S-unanimous", "S-majority", "S-plurality", "S-tied", "S-dispersed"]
TIER_LABELS = {"S-unanimous": "4/4\nunanimous", "S-majority": "3/4\nmajority",
               "S-plurality": "2-1-1\nplurality", "S-no-majority": "2-2 / 1-1-1-1\npooled",
               "S-tied": "2-2\ntied", "S-dispersed": "1-1-1-1\ndispersed"}


def save(fig, name):
    p = FIGDIR / name
    fig.savefig(p, dpi=S.DPI)
    plt.close(fig)
    print(f"  wrote {name}")
    return p


def load(name):
    p = REP / name
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


# ==========================================================================
# F21  Stratified performance curve (primary RQ1 result)
# ==========================================================================
def fig_stratified_curve():
    m = load("phase3_stratified_metrics.json")
    if not m:
        return None
    agg = m["aggregate_3seed"]
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    x = np.arange(len(TIER_ORDER))

    marg = [agg[t]["annotator_marginalized_macro_f1_mean_3seed"] * 100 for t in TIER_ORDER]
    # Patient-clustered bootstrap CIs (averaged over the 3 seeds). The blueprint
    # specified this curve "with 95% CIs" and the intervals were computed into
    # phase3_stratified_metrics.json but never plotted; drawing them makes the
    # small-n tiers visibly less certain than the large ones.
    seeds_ = m["seeds"]
    lo = [100 * np.mean([m["per_seed_stratum"][str(s)][t]
                         ["annotator_marginalized_macro_f1_ci95"][0] for s in seeds_])
          for t in TIER_ORDER]
    hi = [100 * np.mean([m["per_seed_stratum"][str(s)][t]
                         ["annotator_marginalized_macro_f1_ci95"][1] for s in seeds_])
          for t in TIER_ORDER]
    ax.errorbar(x, marg, yerr=[np.array(marg) - np.array(lo), np.array(hi) - np.array(marg)],
                fmt="none", ecolor=S.BLUE, elinewidth=1.6, capsize=5, capthick=1.6,
                alpha=0.75, zorder=3)
    ax.plot(x, marg, "o-", color=S.BLUE, lw=2.2, ms=9, zorder=4, mec="white", mew=1.3,
            label="Annotator-marginalized macro F1 (primary, all strata; 95% CI)")
    for i, v in enumerate(marg):
        ax.annotate(f"{v:.1f}", (i, v), textcoords="offset points", xytext=(0, -18),
                    ha="center", fontsize=9.5, fontweight="bold", color=S.BLUE)

    single = [agg[t].get("single_label_macro_f1_mean_3seed") for t in TIER_ORDER]
    xs, ys = zip(*[(i, v * 100) for i, v in enumerate(single) if v is not None])
    ax.plot(xs, ys, "s--", color=S.ORANGE, lw=1.6, ms=7, zorder=3, mec="white",
            label="Single-label macro F1 (majority/pseudo-label; undefined for pooled tier)")
    for i, v in zip(xs, ys):
        ax.annotate(f"{v:.1f}", (i, v), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=8.6, color=S.ORANGE)

    gap = m["rq1"]["gap_S_unanimous_minus_S_no_majority_points"]
    arch = m["rq1"]["architecture_gap_benchmark_points"]
    ax.text(0.98, 0.60, f"S-unanimous - S-no-majority gap = {gap:.1f} pts\n"
            f"(architecture benchmark: {arch} pts)", transform=ax.transAxes,
            ha="right", va="top", fontsize=8.8, color=S.MUTED,
            bbox=dict(boxstyle="round,pad=0.4", fc="#f2f5f9", ec=S.GRID))

    ax.set_xticks(x)
    ax.set_xticklabels([f"{TIER_LABELS[t]}\nn={agg[t]['n_images']}" for t in TIER_ORDER])
    ax.set_ylabel("macro F1 (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(loc="upper right", fontsize=8.4)
    rq1 = m["rq1"]
    ax.set_title("RQ1: performance across agreement strata, frozen Phase 2 checkpoints\n"
                 f"Spearman rho={rq1['spearman_rho']:.2f} (p={rq1['spearman_p']:.3f}), "
                 f"strictly monotonic: {rq1['strictly_monotonic_non_increasing']}", pad=10)
    fig.tight_layout()
    return save(fig, "P3_F21_stratified_curve.png")


# ==========================================================================
# F22  Distribution-aware metrics, full unpooled breakdown (exploratory tail)
# ==========================================================================
def fig_distribution_metrics():
    m = load("phase3_stratified_metrics.json")
    if not m:
        return None
    seeds = m["seeds"]
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4))

    for ax, key, title in [
            (axes[0], "expected_accuracy", "Expected accuracy\n(prob. mass captured under the vote distribution)"),
            (axes[1], "any_annotator_hit_rate", "Any-annotator hit rate\n(prediction matches at least one annotator)")]:
        vals, errs = [], []
        for t in TIER_ORDER_FULL:
            v = [m["per_seed_stratum"][str(s)][t][key] for s in seeds if t in m["per_seed_stratum"][str(s)]]
            vals.append(100 * np.mean(v))
            errs.append(100 * np.std(v, ddof=1) if len(v) > 1 else 0)
        x = np.arange(len(TIER_ORDER_FULL))
        cols = [S.BLUE if t not in ("S-tied", "S-dispersed") else S.MUTED for t in TIER_ORDER_FULL]
        ax.bar(x, vals, yerr=errs, color=cols, width=0.62, zorder=3, capsize=4)
        for i, v in enumerate(vals):
            ax.text(i, v + max(vals) * 0.03, f"{v:.1f}", ha="center", fontsize=8.6,
                    fontweight="bold", color=cols[i])
        ax.set_xticks(x)
        ax.set_xticklabels([f"{TIER_LABELS[t]}\nn={m['aggregate_3seed'].get(t, {}).get('n_images', m['per_seed_stratum'][str(seeds[0])][t]['n_images'])}"
                            for t in TIER_ORDER_FULL], fontsize=8)
        ax.set_ylabel("%")
        ax.set_ylim(0, max(vals) * 1.25)
        ax.grid(axis="x", visible=False)
        S.despine(ax)
        ax.set_title(title, fontsize=9.8)
    axes[0].legend(handles=[Rectangle((0, 0), 1, 1, fc=S.MUTED,
                            label="S-tied / S-dispersed shown unpooled — exploratory, n too small for a standalone CI")],
                   loc="upper center", bbox_to_anchor=(1.05, -0.22), fontsize=8)
    fig.suptitle("Distribution-aware metrics across all five agreement tiers (3-seed mean +/- SD)",
                fontsize=11.5, fontweight="bold", y=1.03)
    fig.tight_layout()
    return save(fig, "P3_F22_distribution_metrics.png")


# ==========================================================================
# F23  Model vs. human confusion-structure comparison (O3)
# ==========================================================================
def fig_confusion_structure():
    c = load("phase3_confusion_structure.json")
    if not c:
        return None
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    labels = ["Wall confusions\nthat are adjacent", "Station confusions\nthat are neighbouring"]
    model_vals = [c["mean_wall_adjacent_pct_3seed"], c["mean_station_neighbouring_pct_3seed"]]
    human_vals = [c["human_wall_adjacent_pct"], c["human_station_neighbouring_pct"]]
    x = np.arange(2); w = 0.32
    ax.bar(x - w / 2, human_vals, w, color=S.MUTED, zorder=3, label="Human annotators (Phase 0)")
    ax.bar(x + w / 2, model_vals, w, color=S.BLUE, zorder=3, label="Model, S-unanimous stratum (Phase 3)")
    for i, (h, mo) in enumerate(zip(human_vals, model_vals)):
        ax.text(i - w / 2, h + 1.5, f"{h:.1f}", ha="center", fontsize=9, color=S.MUTED, fontweight="bold")
        ax.text(i + w / 2, mo + 1.5, f"{mo:.1f}", ha="center", fontsize=9, color=S.BLUE, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("% of that error type")
    ax.set_ylim(0, 105)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(loc="lower center", fontsize=8.6)
    ax.set_title("Does the model's error geometry mirror human disagreement geometry? (O3)\n"
                f"wall gap {c['wall_gap_points']:+.1f} pts, station gap {c['station_gap_points']:+.1f} pts",
                pad=10)
    fig.tight_layout()
    return save(fig, "P3_F23_confusion_structure.png")


# ==========================================================================
# F24  Per-seed stability across strata
# ==========================================================================
def fig_seed_stability():
    m = load("phase3_stratified_metrics.json")
    if not m:
        return None
    seeds = m["seeds"]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    x = np.arange(len(TIER_ORDER))
    for k, s in enumerate(seeds):
        vals = [m["per_seed_stratum"][str(s)][t]["annotator_marginalized_macro_f1"] * 100 for t in TIER_ORDER]
        ax.plot(x, vals, "o-", color=S.SEED_COLORS[k % len(S.SEED_COLORS)], lw=1.5, ms=6,
                label=f"seed {s}", zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([TIER_LABELS[t] for t in TIER_ORDER])
    ax.set_ylabel("annotator-marginalized macro F1 (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(fontsize=8.6)
    ax.set_title("Per-seed stability of the stratified performance curve\n"
                "(all 3 frozen Phase 2 checkpoints; no retraining in Phase 3)", pad=10)
    fig.tight_layout()
    return save(fig, "P3_F24_seed_stability.png")


def main() -> None:
    S.apply()
    print("Phase 3 figures ->", FIGDIR)
    made = []
    for fn in (fig_stratified_curve, fig_distribution_metrics, fig_confusion_structure,
               fig_seed_stability):
        try:
            r = fn()
            if r is None:
                print(f"  skipped {fn.__name__} (artefact not yet available)")
            else:
                made.append(r.name)
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(made)} figures written")


if __name__ == "__main__":
    main()
