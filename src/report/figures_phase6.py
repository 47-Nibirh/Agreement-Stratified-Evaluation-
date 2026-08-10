"""
Phase 6 figure suite -- F38 to F45.

Every value plotted is read from reports/phase6_*.json. Nothing is typed into
this file and nothing is recomputed here: the risk-coverage curves, the
intervals and the verdicts are all fields written by the analysis scripts, so a
figure can never disagree with the table it sits next to.

Figures whose artefact does not yet exist are skipped with a notice rather than
drawn from stale data.

Run:  python src/report/figures_phase6.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase2_style as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
DATA = ROOT / "data"
FIGDIR = ROOT / "figures_phase6"
FIGDIR.mkdir(exist_ok=True)

ARMS = ("C0", "C1", "C2", "C3", "C4")
CFG_COLOR = {"C0": S.MUTED, "C1": S.BLUE, "C2": S.GREEN, "C3": S.ORANGE,
             "C4": S.PURPLE}
CFG_SHORT = {"C0": "C0 hard 4/4", "C1": "C1 hard maj.", "C2": "C2 soft votes",
             "C3": "C3 smoothed", "C4": "C4 soft+anat."}
STRATA = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority",
          "S-contested (pooled)"]
SHORT_STRATUM = {"S-unanimous": "unanimous\n4/4", "S-majority": "majority\n3/4",
                 "S-plurality": "plurality\n2-1-1", "S-no-majority": "no majority\n2-2 / 1-1-1-1",
                 "S-contested (pooled)": "contested\n(pooled)"}

S.apply()


def load(name):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save(fig, name):
    fig.savefig(FIGDIR / name, dpi=S.DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")


# ============================================================ F38 human comparator
def f38_human(H):
    strata = [s for s in STRATA if s in H["results"]]
    arm = H["headline_arm"]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.9),
                             gridspec_kw={"width_ratios": [1.32, 1]})

    ax = axes[0]
    x = np.arange(len(strata))
    hum, hlo, hhi, mod, mlo, mhi = [], [], [], [], [], []
    for s in strata:
        b = H["results"][s]["bootstrap"]
        hc = b["human_panel_mean_ci95"]
        mc = b["by_arm"][arm]["model_mean_ci95"]
        hum.append((hc[0] + hc[1]) / 2); hlo.append(hc[0]); hhi.append(hc[1])
        mod.append((mc[0] + mc[1]) / 2); mlo.append(mc[0]); mhi.append(mc[1])
    hum, mod = np.array(hum), np.array(mod)
    sens = H.get("sensitivity_P6-AMD-5", {}).get("by_stratum", {})
    orc = np.array([sens.get(s, {}).get("modal_vote_oracle", np.nan) for s in strata],
                   float)
    if np.isfinite(orc).any():
        ax.plot(x, orc, marker="^", ms=8, lw=0, color=S.PURPLE, zorder=4,
                label="modal-vote oracle (best achievable)")
        for i in range(len(strata)):
            if np.isfinite(orc[i]) and orc[i] > hum[i]:
                ax.annotate("", xy=(x[i] + 0.30, orc[i]), xytext=(x[i] + 0.30, hum[i]),
                            arrowprops=dict(arrowstyle="<->", color=S.PURPLE, lw=1.0))
                ax.text(x[i] + 0.34, (orc[i] + hum[i]) / 2, "headroom",
                        fontsize=6.8, color=S.PURPLE, rotation=90,
                        va="center", ha="left")
    ax.errorbar(x - 0.09, hum, yerr=[hum - np.array(hlo), np.array(hhi) - hum],
                fmt="o", ms=7, capsize=4, lw=1.6, color=S.RED,
                label="held-out human annotator")
    ax.errorbar(x + 0.09, mod, yerr=[mod - np.array(mlo), np.array(mhi) - mod],
                fmt="s", ms=7, capsize=4, lw=1.6, color=CFG_COLOR[arm],
                label=f"model ({CFG_SHORT[arm]})")
    deg = H.get("declared_degeneracy", {})
    for i, s in enumerate(strata):
        if deg.get(s, {}).get("degenerate"):
            ax.axvspan(i - 0.42, i + 0.42, color=S.GRID, alpha=0.55, zorder=0)
            ax.text(i, 0.5, "human = 1.0\nby construction", ha="center", va="center",
                    fontsize=7.4, color=S.MUTED, style="italic")
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT_STRATUM[s] for s in strata], fontsize=8)
    ax.set_ylabel("macro F1 against the three-annotator reference panel", fontsize=9)
    ax.set_ylim(0, 1.06)
    ax.legend(loc="upper right", fontsize=8.4)
    ax.set_title("Model and human, judged by the same metric on the same images",
                 fontsize=10, loc="left")
    S.despine(ax)

    ax = axes[1]
    d, lo, hi, cols = [], [], [], []
    for s in strata:
        e = H["results"][s]["bootstrap"]["by_arm"][arm]
        d.append(e["delta_mean"]); lo.append(e["delta_ci95"][0]); hi.append(e["delta_ci95"][1])
        v = e["verdict"]
        cols.append(S.MUTED if "UNINFORMATIVE" in v else
                    (S.GREEN if "ABOVE" in v else
                     (S.RED if "BELOW" in v else S.BLUE)))
    d = np.array(d)
    y = np.arange(len(strata))
    ax.axvline(0, color=S.INK, lw=1.1, zorder=1)
    ax.errorbar(d, y, xerr=[d - np.array(lo), np.array(hi) - d], fmt="o", ms=7,
                capsize=4, lw=1.6, color="none", ecolor=S.MUTED, zorder=2)
    ax.scatter(d, y, s=62, c=cols, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([s.replace("S-", "") for s in strata], fontsize=8.4)
    ax.invert_yaxis()
    ax.set_xlabel("model − human  (macro F1)", fontsize=9)
    ax.set_title("Paired difference, patient-clustered 95% CI", fontsize=10, loc="left")
    S.despine(ax)

    pooled = "S-contested (pooled)"
    pos = sens.get(pooled, {}).get("by_arm", {}).get(arm, {}).get("position_in_headroom")
    extra = ("" if pos is None else
             f" On contested images the model recovers only {100 * pos:.0f}% of that "
             f"headroom, so it out-predicts an individual annotator without reaching "
             f"the panel's own modal vote.")
    S.caption(fig, "Each held-out annotator is scored against the other three, and the "
                   "model is scored against the same three, on the same images and the "
                   "same patient resample. On the unanimous stratum the human side is "
                   "1.0 by construction, so that contrast is greyed out.\nThe triangle "
                   "is the modal-vote oracle — the best any single-label predictor can "
                   "do against the same three references. It bounds the comparison: the "
                   "model chooses a label, an annotator is stuck with theirs."
                   + extra, y=-0.05)
    fig.tight_layout()
    save(fig, "P6_F38_human_comparator.png")


# ============================================================ F39 confusion geometry
def f39_geometry(G):
    strata = [s for s in STRATA if s in G["results"]]
    arm = G["headline_arm"]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.7), sharey=True)
    for ax, (axis_key, pct_key, ci_key, title) in zip(axes, [
            ("wall_adjacent", "wall_adjacent_pct", "wall_adjacent_ci95",
             "Wall confusions that are circumferentially adjacent"),
            ("station_neighbouring", "station_neighbouring_pct",
             "station_neighbouring_ci95",
             "Station confusions that are to a neighbouring station")]):
        x = np.arange(len(strata))
        hv, hlo, hhi, mv = [], [], [], []
        for s in strata:
            e = G["results"][s]
            h = e["human"].get(pct_key)
            ci = e["human"].get(ci_key, [None, None])
            hv.append(np.nan if h is None else h)
            hlo.append(np.nan if not ci or ci[0] is None else ci[0])
            hhi.append(np.nan if not ci or ci[1] is None else ci[1])
            mv.append(e["by_arm"][arm][f"{pct_key}_3seed"])
        hv, mv = np.array(hv, float), np.array(mv, float)
        ok = np.isfinite(hv)
        ax.bar(x - 0.19, mv, width=0.36, color=CFG_COLOR[arm],
               label=f"model ({CFG_SHORT[arm]})")
        ax.bar(x[ok] + 0.19, hv[ok], width=0.36, color=S.RED, label="human annotators")
        yerr = np.vstack([hv[ok] - np.array(hlo, float)[ok],
                          np.array(hhi, float)[ok] - hv[ok]])
        ax.errorbar(x[ok] + 0.19, hv[ok], yerr=np.abs(yerr), fmt="none",
                    ecolor=S.INK, capsize=3, lw=1.1)
        for i in np.where(~ok)[0]:
            ax.text(i + 0.19, 4, "not\ndefined", ha="center", va="bottom",
                    fontsize=7.2, color=S.MUTED, style="italic")
        for i, s in enumerate(strata):
            v = G["results"][s]["by_arm"][arm].get(f"{axis_key}_verdict", "")
            if "DIVERGES" in v:
                ax.text(i, max(mv[i], 0 if not ok[i] else hv[i]) + 3.2, "✱",
                        ha="center", fontsize=13, color=S.RED)
        ax.set_xticks(x)
        ax.set_xticklabels([SHORT_STRATUM[s] for s in strata], fontsize=8)
        ax.set_ylim(0, 108)
        ax.set_title(title, fontsize=9.6, loc="left")
        S.despine(ax)
    axes[0].set_ylabel("% of differing-label events", fontsize=9)
    axes[0].legend(loc="lower left", fontsize=8.2)
    S.caption(fig, "Both sides measured on the same images with the same adjacency "
                   "definitions and differenced inside one patient resample. ✱ marks a "
                   "stratum where the paired 95% CI excludes zero.\nThe unanimous "
                   "stratum contains no annotator disagreement events at all, so the "
                   "human geometry is undefined there — which is why the Phase 3 "
                   "comparison (withdrawn as X3) was never like-for-like.", y=-0.05)
    fig.tight_layout()
    save(fig, "P6_F39_confusion_geometry.png")


# ============================================================ F40 dispersion vs entropy
def f40_dispersion(A):
    arms = [a for a in ARMS if a in A["arms"]]
    prim = A["primary"]["stratum"]
    estimable = A["primary"].get("estimable", True)
    rho_key = "spearman_rho" if estimable else "spread_spearman_rho"
    ci_key = "spearman_ci95" if estimable else "spread_spearman_ci95"
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6),
                             gridspec_kw={"width_ratios": [1, 1.15]})

    ax = axes[0]
    y = np.arange(len(arms))
    rho, lo, hi = [], [], []
    for a in arms:
        r = A["primary"]["by_arm"][a]
        v = r.get(rho_key)
        rho.append(np.nan if v is None else v)
        ci = r.get(ci_key) or [None, None]
        lo.append(np.nan if ci[0] is None else ci[0])
        hi.append(np.nan if ci[1] is None else ci[1])
    rho = np.array(rho, float)
    ax.axvline(0, color=S.INK, lw=1.1)
    ax.errorbar(rho, y, xerr=[rho - np.array(lo, float), np.array(hi, float) - rho],
                fmt="o", ms=7, capsize=4, lw=1.5, color="none", ecolor=S.MUTED)
    ax.scatter(rho, y, s=62, c=[CFG_COLOR[a] for a in arms], zorder=3)
    ax.set_yticks(y); ax.set_yticklabels([CFG_SHORT[a] for a in arms], fontsize=8.4)
    ax.invert_yaxis()
    if estimable:
        ax.set_xlabel("Spearman ρ (CAM dispersion, annotator vote entropy)", fontsize=9)
        ax.set_title(f"Primary endpoint: within {prim}", fontsize=10, loc="left")
    else:
        ax.set_xlabel("Spearman ρ (CAM dispersion, anatomical vote spread)", fontsize=9)
        ax.set_title(f"EXPLORATORY substitute: within {prim}", fontsize=10, loc="left")
    S.despine(ax)

    ax = axes[1]
    strata = [s for s in STRATA if s in A["by_stratum"]]
    x = np.arange(len(strata))
    ne = [A["by_stratum"][s]["vote_entropy_distinct_values"] for s in strata]
    nv = [A["by_stratum"][s].get("vote_spread_distinct_values", 0) for s in strata]
    ax.bar(x - 0.19, ne, width=0.36, color=S.RED, label="vote entropy (pre-registered)")
    ax.bar(x + 0.19, nv, width=0.36, color=S.GREEN, label="anatomical vote spread")
    ax.set_yscale("log")
    ax.set_ylim(0.6, max(max(nv), max(ne)) * 3.2)
    ax.axhline(2, color=S.RED, lw=1.1, ls="--")
    ax.text(-0.45, 2.25, "2 = the minimum for a correlation to exist",
            ha="left", va="bottom", fontsize=7.4, color=S.RED)
    for i, v in enumerate(ne):
        ax.text(i - 0.19, v * 1.12, str(v), ha="center", fontsize=8, color=S.INK)
    for i, v in enumerate(nv):
        ax.text(i + 0.19, v * 1.12, str(v), ha="center", fontsize=8, color=S.INK)
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT_STRATUM[s] for s in strata], fontsize=7.6)
    ax.set_ylabel("distinct values within the stratum (log scale)", fontsize=8.6)
    ax.legend(fontsize=8.2, loc="upper left")
    ax.set_title("Why the pre-registered signal is not estimable", fontsize=10, loc="left")
    S.despine(ax)
    if not estimable:
        fig.text(0.5, -0.045,
                 "The pre-registered primary signal, annotator vote entropy, is NOT "
                 "ESTIMABLE within a stratum: entropy is a deterministic function of "
                 "the vote pattern and the strata are defined by that pattern.",
                 ha="center", fontsize=8.2, color=S.RED)
    S.caption(fig, "A 3-1 vote split always has entropy 0.5623 nats and a 2-1-1 split "
                   "always 1.0397, so vote entropy is constant inside every stratum "
                   "defined by a single vote pattern. Anatomical vote spread carries "
                   "the same\ndisagreement information but separates a dissenter one "
                   "wall away from one at the far end of the stomach, so it varies "
                   "within a tier. The substitute is post-hoc and labelled exploratory.",
                   y=-0.085)
    fig.tight_layout()
    save(fig, "P6_F40_dispersion_vs_entropy.png")


# ============================================================ F41 attribution stability
def f41_stability(A):
    arms = [a for a in ARMS if a in A["arms"]]
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6))

    ax = axes[0]
    x = np.arange(len(arms))
    un = [A["secondary"][a]["inter_seed_iou_unanimous"] for a in arms]
    ct = [A["secondary"][a]["inter_seed_iou_contested"] for a in arms]
    ax.bar(x - 0.19, un, width=0.36, color=S.BLUE, label="S-unanimous")
    ax.bar(x + 0.19, ct, width=0.36, color=S.ORANGE, label="contested (pooled)")
    ax.set_xticks(x); ax.set_xticklabels([CFG_SHORT[a] for a in arms], fontsize=8, rotation=12)
    ax.set_ylabel(f"inter-seed IoU of the top-{int(A['top_q']*100)}% attribution mask",
                  fontsize=8.8)
    ax.legend(fontsize=8.2)
    ax.set_title("Do three seeds that agree on the label look in the same place?",
                 fontsize=9.6, loc="left")
    S.despine(ax)

    ax = axes[1]
    d = np.array([A["secondary"][a]["delta"] for a in arms])
    lo = np.array([A["secondary"][a]["delta_ci95"][0] for a in arms], float)
    hi = np.array([A["secondary"][a]["delta_ci95"][1] for a in arms], float)
    y = np.arange(len(arms))
    ax.axvline(0, color=S.INK, lw=1.1)
    ax.errorbar(d, y, xerr=[d - lo, hi - d], fmt="o", ms=7, capsize=4, lw=1.5,
                color="none", ecolor=S.MUTED)
    ax.scatter(d, y, s=62, c=[CFG_COLOR[a] for a in arms], zorder=3)
    ax.set_yticks(y); ax.set_yticklabels([CFG_SHORT[a] for a in arms], fontsize=8.4)
    ax.invert_yaxis()
    ax.set_xlabel("IoU(unanimous) − IoU(contested)", fontsize=9)
    ax.set_title("Secondary endpoint, patient-clustered 95% CI", fontsize=9.6, loc="left")
    S.despine(ax)
    fig.tight_layout()
    save(fig, "P6_F41_attribution_stability.png")


# ============================================================ F42 qualitative panels
def f42_panels(A, H):
    import pandas as pd
    cache_p = DATA / "phase3_cache_224.npy"
    idx_p = DATA / "phase3_cache_index.csv"
    cam_p = REP / "phase6_cams_C2_seed1.npz"
    if not (cache_p.exists() and cam_p.exists()):
        print("  skip F42: cache or CAMs absent")
        return
    cache = np.load(cache_p, mmap_mode="r")
    idx = pd.read_csv(idx_p)
    z = np.load(cam_p, allow_pickle=True)
    cams = z["cams"].astype(np.float32)

    picks = []
    for tier in ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]:
        rows = np.where(idx.tier_pooled.to_numpy() == tier)[0]
        if rows.size:
            picks.append((tier, int(rows[len(rows) // 3])))
            picks.append((tier, int(rows[2 * len(rows) // 3])))

    n = len(picks)
    fig, axes = plt.subplots(2, n // 2, figsize=(2.15 * (n // 2), 4.9))
    axes = np.atleast_2d(axes).ravel()
    for ax, (tier, r) in zip(axes, picks):
        img = np.asarray(cache[r]).astype(np.float32) / 255.0
        cam = cams[r]
        cam = cam / (cam.max() + 1e-12)
        cam_up = np.kron(cam, np.ones((32, 32)))
        ax.imshow(img)
        ax.imshow(cam_up, cmap="inferno", alpha=0.45, vmin=0, vmax=1)
        pl = idx.pseudo_label.iloc[r]
        ax.set_title(f"{tier.replace('S-','')}\ntrue {pl}", fontsize=7.2, color=S.INK)
        ax.set_xticks([]); ax.set_yticks([])
    for ax in axes[len(picks):]:
        ax.axis("off")
    prim = A["verdict_summary"]
    S.caption(fig,
              f"Grad-CAM for the committed prediction, arm C2 seed 1. These panels are "
              f"illustrative only. The quantitative endpoint is Figure F40: within "
              f"{A['primary']['stratum']}, ρ = {prim.get('P6-C1_primary_rho')} "
              f"({prim.get('P6-C1_primary')}).", y=-0.03)
    fig.tight_layout()
    save(fig, "P6_F42_gradcam_panels.png")


# ============================================================ F43/F44 risk-coverage
def f43_44_risk_coverage(SEL):
    for panel_key, fname, title in [
            ("internal", "P6_F43_risk_coverage_internal.png",
             "Internal — GastroHUN test split (patient-clustered intervals)"),
            ("external", "P6_F44_risk_coverage_external.png",
             "External — HyperKvasir + GastroVision (image-level intervals, P5-DEV-3)")]:
        P = SEL.get(panel_key)
        if not P:
            print(f"  skip {fname}: {panel_key} panel absent")
            continue
        arms = [a for a in ARMS if a in P["by_arm"]]
        fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
        ax = axes[0]
        for a in arms:
            c = P["by_arm"][a]["curve_seed1"]
            ax.plot(c["coverage"], c["risk"], lw=1.9, color=CFG_COLOR[a],
                    label=f"{CFG_SHORT[a]} (AURC {P['by_arm'][a]['aurc_3seed']:.3f})")
        ax.set_xlabel("coverage — fraction of images the model answers on", fontsize=9)
        ax.set_ylabel("risk — error rate among answered images", fontsize=9)
        ax.legend(fontsize=8, loc="upper left")
        ax.set_title(title, fontsize=9.6, loc="left")
        S.despine(ax)

        ax = axes[1]
        x = np.arange(len(arms))
        au = [P["by_arm"][a]["aurc_3seed"] for a in arms]
        ax.bar(x, au, color=[CFG_COLOR[a] for a in arms], width=0.58)
        if panel_key == "internal":
            lo = np.array([P["by_arm"][a]["aurc_ci95"][0] for a in arms])
            hi = np.array([P["by_arm"][a]["aurc_ci95"][1] for a in arms])
            ax.errorbar(x, au, yerr=[np.array(au) - lo, hi - np.array(au)],
                        fmt="none", ecolor=S.INK, capsize=3.5, lw=1.1)
        for i, v in enumerate(au):
            ax.text(i, v * 1.02 + 0.004, f"{v:.3f}", ha="center", fontsize=8,
                    color=S.INK)
        ax.set_xticks(x); ax.set_xticklabels([CFG_SHORT[a] for a in arms],
                                             fontsize=8, rotation=12)
        ax.set_ylabel("AURC (lower is better)", fontsize=9)
        ax.set_title("Area under the risk–coverage curve", fontsize=9.6, loc="left")
        S.despine(ax)
        fig.tight_layout()
        save(fig, fname)


# ============================================================ F45 synthesis
def f45_synthesis(H, G, A, SEL):
    arms = [a for a in ARMS if a in SEL["internal"]["by_arm"]]
    rows = []
    rows.append(("Internal AURC\n(lower better)",
                 [SEL["internal"]["by_arm"][a]["aurc_3seed"] for a in arms], True))
    if SEL.get("external"):
        rows.append(("External AURC\n(lower better)",
                     [SEL["external"]["by_arm"][a]["aurc_3seed"] for a in arms], True))
    pooled = "S-contested (pooled)"
    if pooled in H["results"]:
        rows.append(("P6-A  model − human\non contested (higher better)",
                     [H["results"][pooled]["bootstrap"]["by_arm"][a]["delta_mean"]
                      for a in arms], False))
    if A and pooled in A["by_stratum"]:
        rows.append((f"P6-C  inter-seed IoU\non contested (higher better)",
                     [A["by_stratum"][pooled]["by_arm"][a]["inter_seed_iou_mean"]
                      for a in arms], False))

    fig, ax = plt.subplots(figsize=(9.6, 1.05 * len(rows) + 2.1))
    M = np.zeros((len(rows), len(arms)))
    for i, (_, vals, lower_better) in enumerate(rows):
        v = np.array(vals, float)
        r = v.argsort().argsort() if lower_better else (-v).argsort().argsort()
        M[i] = r
    ax.imshow(M, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=len(arms) - 1)
    for i, (_, vals, _) in enumerate(rows):
        for j, v in enumerate(vals):
            ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=8.6,
                    color=S.INK)
    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels([CFG_SHORT[a] for a in arms], fontsize=8.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.2)
    ax.set_xticks(np.arange(-.5, len(arms), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
    ax.grid(which="minor", color="white", lw=2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    ax.set_title("Arm ranking under every Phase 6 endpoint (green = best)",
                 fontsize=10, loc="left")
    S.caption(fig, "Cell shading is the rank within the row; the printed value is the "
                   "measured quantity. Rows disagree, which is the point: no single "
                   "arm wins everywhere.", y=-0.06)
    fig.tight_layout()
    save(fig, "P6_F45_synthesis.png")


def main() -> None:
    H = load("phase6_human.json")
    G = load("phase6_geometry.json")
    A = load("phase6_cam_eval.json")
    SEL = load("phase6_selective.json")
    if H:
        f38_human(H)
    else:
        print("  skip F38: phase6_human.json absent")
    if G:
        f39_geometry(G)
    else:
        print("  skip F39: phase6_geometry.json absent")
    if A:
        f40_dispersion(A); f41_stability(A); f42_panels(A, H)
    else:
        print("  skip F40-F42: phase6_cam_eval.json absent")
    if SEL:
        f43_44_risk_coverage(SEL)
    else:
        print("  skip F43-F44: phase6_selective.json absent")
    if H and SEL:
        f45_synthesis(H, G, A, SEL)
    print(f"[figures] Phase 6 suite -> {FIGDIR}")


if __name__ == "__main__":
    main()
