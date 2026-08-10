"""
Phase 4 figure suite -- soft-label and uncertainty training (RQ2, RQ3, RQ4).

Every value plotted is read from reports/phase4_*.json. Nothing is typed into
this file, so re-running the pipeline regenerates the figures and the report
together. Figures whose artefact does not yet exist are skipped with a notice
rather than drawn from stale data.

Run:  python src/report/figures_phase4.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase2_style as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
FIGDIR = ROOT / "figures_phase4"
FIGDIR.mkdir(exist_ok=True)

TIERS = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]
POOLED = "S-contested (pooled)"
STRATA = TIERS + [POOLED]
TIER_LAB = {"S-unanimous": "4/4\nunanimous", "S-majority": "3/4\nmajority",
            "S-plurality": "2-1-1\nplurality", "S-no-majority": "2-2 / 1-1-1-1\npooled",
            POOLED: "all contested\n(pooled)"}
CFG_COLOR = {"C0": S.MUTED, "C1": S.BLUE, "C2": S.GREEN, "C3": S.ORANGE, "C4": S.PURPLE}
CFG_SHORT = {"C0": "C0 hard 4/4", "C1": "C1 hard maj.", "C2": "C2 soft votes",
             "C3": "C3 smoothed", "C4": "C4 soft+anat."}


def save(fig, name):
    p = FIGDIR / name
    fig.savefig(p, dpi=S.DPI)
    plt.close(fig)
    print(f"  wrote {name}")
    return p


def load(name):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def cfgs_of(m):
    return [c for c in ("C0", "C1", "C2", "C3", "C4")
            if c in m.get("configurations_evaluated", [])]


# ==========================================================================
# F25  Design: what each configuration changes and what each contrast isolates
# ==========================================================================
def fig_design():
    coh = load("phase4_cohort.json")
    pre = load("phase4_prereg.json")
    if not (coh and pre):
        return None
    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")

    eps = pre["configurations"]["C3"]["label_smoothing_epsilon"]
    lam = pre["configurations"]["C4"]["structure_penalty_lambda"]
    n_tr = coh["by_split"]["Train"]
    n_un = coh["tier_by_split"]["Train"]["S-unanimous"]
    n_mj = coh["tier_by_split"]["Train"]["S-majority"]

    boxes = [
        ("C0", 0.35, 4.2, f"hard label\n4/4 only\nn={n_un:,}"),
        ("C1", 2.35, 4.2, f"hard majority\nn={n_tr:,}"),
        ("C2", 4.35, 4.2, "vote proportions\n(0.75 / 0.25 on\nthe 3/4 images)"),
        ("C3", 6.35, 4.2, f"hard + smoothing\nepsilon={eps:.4f}\n(mass-matched to C2)"),
        ("C4", 8.35, 4.2, f"vote proportions\n+ anatomical penalty\nlambda={lam:g}"),
    ]
    for cfg, x, y, txt in boxes:
        ax.add_patch(Rectangle((x - 0.85, y - 0.95), 1.7, 1.9, fc="white",
                               ec=CFG_COLOR[cfg], lw=1.8, zorder=3))
        ax.text(x, y + 0.62, cfg, ha="center", va="center", fontsize=12,
                fontweight="bold", color=CFG_COLOR[cfg], zorder=4)
        ax.text(x, y - 0.22, txt, ha="center", va="center", fontsize=7.8,
                color=S.INK, zorder=4)

    arrows = [
        (0.35, 2.35, 2.55, "C0 -> C1: cohort effect\n+{:,} contested images".format(n_mj),
         S.MUTED, 0.5),
        (2.35, 4.35, 2.55, "C1 -> C2: target softened\nwhere they disagreed",
         S.MUTED, 0.5),
        (4.35, 6.35, 2.55, "C2 vs C3: THE CONTROL\nequally soft, uninformative",
         S.RED, 0.5),
        (4.35, 8.35, 1.35, "C2 -> C4: + anatomical penalty", S.MUTED, 0.72),
    ]
    for x0, x1, y, lab, colr, tpos in arrows:
        ax.add_patch(FancyArrowPatch((x0 + 0.9, y + 0.55), (x1 - 0.9, y + 0.55),
                                     arrowstyle="-|>", mutation_scale=13,
                                     color=colr, lw=1.2, zorder=2))
        ax.text(x0 + (x1 - x0) * tpos, y + 0.15, lab, ha="center", va="top",
                fontsize=7.4, color=colr, style="italic")

    ax.text(5.0, 0.75, "Cohort E (majority-or-better) is identical for C1-C4, so those four "
                       "arms differ only in how the\ntarget vector is built from the same "
                       "four annotator votes on the same images.",
            ha="center", va="center", fontsize=8.4, color=S.INK,
            bbox=dict(boxstyle="round,pad=0.5", fc="#f2f5f9", ec=S.GRID))
    ax.set_title("Phase 4 design: one factor varied at a time", fontsize=12, pad=6)
    fig.tight_layout()
    return save(fig, "P4_F25_design.png")


# ==========================================================================
# F26  Stratified performance, one curve per configuration (primary RQ2)
# ==========================================================================
def fig_stratified():
    m = load("phase4_stratified_metrics.json")
    if not m:
        return None
    cfgs = cfgs_of(m)
    agg = m["aggregate_3seed"]
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.9))
    x = np.arange(len(TIERS))

    for ax, key, ttl, ylab in [
            (axes[0], "annotator_marginalized_macro_f1_mean_3seed",
             "Raw scale", "annotator-marginalized macro F1 (%)"),
            (axes[1], "ceiling_normalised_macro_f1_mean_3seed",
             "Ceiling-normalised (% of what is attainable on that stratum)",
             "% of the modal-vote oracle")]:
        for c in cfgs:
            v = [100 * agg[c][t][key] for t in TIERS]
            ax.plot(x, v, "o-", color=CFG_COLOR[c], lw=2.0, ms=7, mec="white",
                    mew=1.1, zorder=3, label=CFG_SHORT[c])
        ax.set_xticks(x)
        ax.set_xticklabels([f"{TIER_LAB[t]}\nn={agg[cfgs[0]][t]['n_images']}" for t in TIERS],
                           fontsize=8)
        ax.set_ylabel(ylab)
        ax.set_ylim(0, 100)
        ax.grid(axis="x", visible=False)
        S.despine(ax)
        ax.set_title(ttl, fontsize=9.8)
    ceil = m["ceilings"]
    axes[1].text(0.98, 0.04, "ceiling: " + " / ".join(
        f"{100 * ceil[t]['oracle_marginalized_macro_f1_mean']:.1f}" for t in TIERS),
        transform=axes[1].transAxes, ha="right", fontsize=7.8, color=S.MUTED)
    axes[0].legend(loc="upper right", fontsize=8.2)
    fig.suptitle("RQ2: agreement-stratified performance of every training-target "
                 "configuration "
                 f"({len(m['seeds'])}-seed mean)", fontsize=11.5,
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return save(fig, "P4_F26_stratified_by_config.png")


# ==========================================================================
# F27  Forest plot of the pre-registered paired contrasts
# ==========================================================================
def fig_contrasts():
    m = load("phase4_stratified_metrics.json")
    if not m or not m.get("contrasts"):
        return None
    con = m["contrasts"]
    keys = [k for k in ("C1 - C0", "C2 - C1", "C2 - C3", "C3 - C1", "C4 - C2", "C4 - C1")
            if k in con]
    fig, ax = plt.subplots(figsize=(9.6, 0.52 * len(keys) * len(STRATA) + 1.8))

    y, ticks, labels = 0, [], []
    for kk in keys:
        for st in STRATA:
            d = con[kk]["by_stratum"][st]
            lo, hi = d["ci95_points_3seed_mean"]
            pt = d["diff_points_3seed_mean"]
            colour = (S.GREEN if lo > 0 else S.RED if hi < 0 else S.MUTED)
            ax.plot([lo, hi], [y, y], color=colour, lw=2.0, zorder=3,
                    solid_capstyle="round")
            ax.plot([pt], [y], "o", color=colour, ms=6, mec="white", mew=1.0, zorder=4)
            ticks.append(y)
            labels.append(f"{kk}   {st.replace('S-', '').replace(' (pooled)', '')}")
            y -= 1
        y -= 0.6
    ax.axvline(0, color=S.INK, lw=1.0, ls="--", zorder=2)
    ax.set_yticks(ticks); ax.set_yticklabels(labels, fontsize=7.6)
    ax.set_xlabel("difference in annotator-marginalized macro F1 (percentage points)\n"
                  "paired patient-clustered bootstrap, 95% CI")
    ax.grid(axis="y", visible=False)
    S.despine(ax)
    prim = m.get("verdicts", {}).get("RQ2_primary", {})
    ttl = "Pre-registered configuration contrasts"
    if prim:
        ttl += f"\nRQ2 primary (C2 - C3, pooled contested): {prim['verdict']}"
    ax.set_title(ttl, pad=10)
    fig.tight_layout()
    return save(fig, "P4_F27_contrast_forest.png")


# ==========================================================================
# F28  Calibration: ECE by configuration and stratum + reliability curves
# ==========================================================================
def fig_calibration():
    c = load("phase4_calibration.json")
    if not c:
        return None
    cfgs = cfgs_of(c)
    agg = c["aggregate_3seed"]
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8))

    ax = axes[0]
    x = np.arange(len(TIERS)); w = 0.8 / max(len(cfgs), 1)
    for i, cf in enumerate(cfgs):
        v = [100 * agg[cf][t]["ece_vs_expected_accuracy"] for t in TIERS]
        ax.bar(x + (i - (len(cfgs) - 1) / 2) * w, v, w * 0.92, color=CFG_COLOR[cf],
               zorder=3, label=CFG_SHORT[cf])
    ax.set_xticks(x); ax.set_xticklabels([TIER_LAB[t] for t in TIERS], fontsize=8)
    ax.set_ylabel("ECE vs expected accuracy (%)")
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(fontsize=8.0)
    ax.set_title(f"Expected calibration error by stratum "
                 f"({len(c['seeds'])}-seed mean)", fontsize=9.8)

    ax = axes[1]
    ax.plot([0, 1], [0, 1], ls="--", color=S.INK, lw=1.0, zorder=2, label="perfect")
    for cf in cfgs:
        bins = c["per_seed"][cf][str(c["seeds"][0])][POOLED][
            "reliability_bins_vs_expected_accuracy"]
        xs = [b["mean_confidence"] for b in bins if b["n"]]
        ys = [b["mean_target"] for b in bins if b["n"]]
        ax.plot(xs, ys, "o-", color=CFG_COLOR[cf], lw=1.7, ms=5, zorder=3,
                label=CFG_SHORT[cf])
    ax.set_xlabel("mean top-1 confidence"); ax.set_ylabel("expected accuracy")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    S.despine(ax)
    ax.legend(fontsize=8.0, loc="upper left")
    ax.set_title(f"Reliability, pooled contested stratum (seed {c['seeds'][0]})",
                 fontsize=9.8)

    v = c.get("verdicts", {}).get("RQ2_calibration", {})
    sup = f"  —  C2 - C3 dECE = {v['delta_ece_points']:+.2f} pts, {v['verdict']}" if v else ""
    fig.suptitle("RQ2 calibration endpoint" + sup, fontsize=11.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    return save(fig, "P4_F28_calibration.png")


# ==========================================================================
# F29  Confidence against attainable accuracy -- the overconfidence gap
# ==========================================================================
def fig_overconfidence():
    c = load("phase4_calibration.json")
    if not c:
        return None
    cfgs = cfgs_of(c)
    agg = c["aggregate_3seed"]
    fig, ax = plt.subplots(figsize=(9.0, 4.9))
    x = np.arange(len(TIERS))
    for cf in cfgs:
        conf = [100 * agg[cf][t]["mean_confidence"] for t in TIERS]
        acc = [100 * agg[cf][t]["expected_accuracy"] for t in TIERS]
        ax.plot(x, conf, "o-", color=CFG_COLOR[cf], lw=2.0, ms=6, zorder=4,
                label=f"{CFG_SHORT[cf]} — confidence")
        ax.plot(x, acc, "s--", color=CFG_COLOR[cf], lw=1.3, ms=5, alpha=0.55, zorder=3)
        ax.fill_between(x, acc, conf, color=CFG_COLOR[cf], alpha=0.08, zorder=2)
    ax.set_xticks(x); ax.set_xticklabels([TIER_LAB[t] for t in TIERS], fontsize=8)
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(fontsize=8.0, ncol=2)
    ax.set_title("Solid = mean confidence, dashed = expected accuracy; the shaded gap is "
                 "overconfidence\n(the failure mode Phase 3 identified and Phase 4 is "
                 "meant to fix)", pad=10)
    fig.tight_layout()
    return save(fig, "P4_F29_overconfidence.png")


# ==========================================================================
# F30  RQ3 -- entropy correlation, within stratum vs pooled
# ==========================================================================
def fig_uncertainty():
    u = load("phase4_uncertainty.json")
    if not u:
        return None
    cfgs = cfgs_of(u)
    defined = u["strata_where_defined"]
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.7))

    ax = axes[0]
    x = np.arange(len(defined) + 1); w = 0.8 / max(len(cfgs), 1)
    for i, cf in enumerate(cfgs):
        a = u["results"][f"{cf}|softmax"]["aggregate"]
        pooled = float(np.mean([u["results"][f"{cf}|softmax"]["per_member"][str(s)]
                                ["_pooled_all_1353_images"]["spearman_rho"]
                                for s in u["results"][f"{cf}|softmax"]["per_member"]]))
        v = [a[st]["mean_rho"] if a[st]["mean_rho"] is not None else np.nan
             for st in defined] + [pooled]
        ax.bar(x + (i - (len(cfgs) - 1) / 2) * w, v, w * 0.92, color=CFG_COLOR[cf],
               zorder=3, label=CFG_SHORT[cf])
    ax.axhline(0, color=S.INK, lw=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([st.replace("S-", "").replace(" (pooled)", "") for st in defined]
                       + ["POOLED\n(all 1,353)"], fontsize=8)
    ax.set_ylabel("Spearman rho (predictive vs vote entropy)")
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(fontsize=8.0)
    ax.set_title("RQ3: the pooled correlation is a between-stratum artefact\n"
                 "(the rightmost group is not the endpoint)", fontsize=9.8)

    ax = axes[1]
    key = [k for k in u["results"] if k.endswith("|mc_stochastic_depth")]
    if key:
        cf0 = key[0].split("|")[0]
        dec = u["results"][key[0]]["per_member"]
        members = list(dec)
        tot = [np.mean([dec[mk]["_uncertainty_decomposition"][t]["total"] for mk in members])
               for t in TIERS]
        epi = [np.mean([dec[mk]["_uncertainty_decomposition"][t]
                        ["epistemic_mutual_information"] for mk in members]) for t in TIERS]
        xs = np.arange(len(TIERS))
        ax.bar(xs, np.array(tot) - np.array(epi), 0.55, color=S.BLUE, zorder=3,
               label="aleatoric (mean entropy)")
        ax.bar(xs, epi, 0.55, bottom=np.array(tot) - np.array(epi), color=S.ORANGE,
               zorder=3, label="epistemic (mutual information)")
        ax.set_xticks(xs); ax.set_xticklabels([TIER_LAB[t] for t in TIERS], fontsize=8)
        ax.set_ylabel("nats")
        ax.grid(axis="x", visible=False)
        S.despine(ax)
        ax.legend(fontsize=8.0)
        ax.set_title(f"MC stochastic-depth uncertainty decomposition ({cf0}, "
                     f"{u['n_mc_samples']} samples)", fontsize=9.8)
    else:
        ax.axis("off")
    fig.tight_layout()
    return save(fig, "P4_F30_uncertainty.png")


# ==========================================================================
# F31  RQ4 -- anatomical error distance and error geometry
# ==========================================================================
def fig_structure():
    st = load("phase4_structure_eval.json")
    if not st:
        return None
    cfgs = cfgs_of(st)
    agg = st["aggregate_3seed"]
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8))

    ax = axes[0]
    x = np.arange(len(TIERS)); w = 0.8 / max(len(cfgs), 1)
    for i, cf in enumerate(cfgs):
        v = [agg[cf][t]["mean_anatomical_distance_3seed"] for t in TIERS]
        ax.bar(x + (i - (len(cfgs) - 1) / 2) * w, v, w * 0.92, color=CFG_COLOR[cf],
               zorder=3, label=CFG_SHORT[cf])
    ax.set_xticks(x); ax.set_xticklabels([TIER_LAB[t] for t in TIERS], fontsize=8)
    ax.set_ylabel("mean anatomical distance (0 = every annotator's label)")
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(fontsize=8.0)
    ax.set_title("RQ4 primary endpoint: annotator-marginalized anatomical\n"
                 "error distance (lower is better)", fontsize=9.8)

    ax = axes[1]
    g0 = agg[cfgs[0]]["_error_geometry_S_unanimous"]
    labels = ["wall confusions\nthat are adjacent", "station confusions\nthat are neighbouring"]
    xs = np.arange(2); w = 0.8 / (len(cfgs) + 1)
    ax.bar(xs - (len(cfgs)) / 2 * w, [g0["human_wall_adjacent_pct"],
                                      g0["human_station_neighbouring_pct"]],
           w * 0.92, color=S.INK, zorder=3, label="human (Phase 0)")
    for i, cf in enumerate(cfgs):
        g = agg[cf]["_error_geometry_S_unanimous"]
        ax.bar(xs + (i + 1 - len(cfgs) / 2) * w,
               [g["wall_adjacent_pct_3seed"], g["station_neighbouring_pct_3seed"]],
               w * 0.92, color=CFG_COLOR[cf], zorder=3, label=CFG_SHORT[cf])
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=8.4)
    ax.set_ylabel("% of that error type")
    ax.set_ylim(0, 105)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(fontsize=7.6, ncol=2, loc="lower center")
    ax.set_title("Independent check: error geometry on S-unanimous,\n"
                 "against the human benchmark C4 was not trained on", fontsize=9.8)
    v = st.get("verdicts", {}).get("RQ4", {})
    sup = f"  —  C4 - C2 anatomical distance {v['delta_distance']:+.4f}, {v['verdict']}" if v else ""
    fig.suptitle("RQ4: does the anatomy-aware loss reshape the errors?" + sup,
                 fontsize=11.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    return save(fig, "P4_F31_structure.png")


# ==========================================================================
# F32  Robustness: per-seed spread and leave-one-annotator-out
# ==========================================================================
def fig_robustness():
    m = load("phase4_stratified_metrics.json")
    lo = load("phase4_loao.json")
    if not m:
        return None
    cfgs = cfgs_of(m)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.7))

    ax = axes[0]
    x = np.arange(len(TIERS))
    for cf in cfgs:
        for j, s in enumerate(m["seeds"]):
            v = [100 * m["per_seed"][cf][str(s)][t]["annotator_marginalized_macro_f1"]
                 for t in TIERS]
            ax.plot(x, v, "o-", color=CFG_COLOR[cf], lw=1.0, ms=4, alpha=0.55, zorder=3,
                    label=CFG_SHORT[cf] if j == 0 else None)
    ax.set_xticks(x); ax.set_xticklabels([TIER_LAB[t] for t in TIERS], fontsize=8)
    ax.set_ylabel("annotator-marginalized macro F1 (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(fontsize=8.0)
    ax.set_title(f"Per-seed spread ({len(m['seeds'])} seed(s) per configuration, "
                 f"all drawn)", fontsize=9.8)

    ax = axes[1]
    if lo and lo.get("rq2_verdict_stability"):
        names = list(lo["rq2_verdict_stability"])
        ys = np.arange(len(names))[::-1]
        for y, nm in zip(ys, names):
            d = lo["rq2_verdict_stability"][nm]
            a, b = d["ci95_points_3seed_mean"]
            col = S.GREEN if a > 0 else S.RED if b < 0 else S.MUTED
            ax.plot([a, b], [y, y], color=col, lw=2.2, solid_capstyle="round", zorder=3)
            ax.plot([d["diff_points_3seed_mean"]], [y], "o", color=col, ms=6,
                    mec="white", mew=1.0, zorder=4)
        ax.axvline(0, color=S.INK, lw=1.0, ls="--")
        ax.set_yticks(ys)
        ax.set_yticklabels([n.replace("_", " ") for n in names], fontsize=8.6)
        ax.set_xlabel("C2 - C3 on the pooled contested stratum (points)")
        ax.grid(axis="y", visible=False)
        S.despine(ax)
        ax.set_title("Leave-one-annotator-out: does the RQ2 verdict survive\n"
                     "dropping each rater, FG2 included?", fontsize=9.8)
    else:
        ax.axis("off")
    fig.tight_layout()
    return save(fig, "P4_F32_robustness.png")


def main() -> None:
    S.apply()
    print("Phase 4 figures ->", FIGDIR)
    made = []
    for fn in (fig_design, fig_stratified, fig_contrasts, fig_calibration,
               fig_overconfidence, fig_uncertainty, fig_structure, fig_robustness):
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
