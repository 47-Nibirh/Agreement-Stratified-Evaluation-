"""
Phase 2 figure suite.

Every figure is generated from a JSON/CSV artefact under reports/ -- no value
is typed into this file. Figures that depend on training artefacts are skipped
with a notice if those artefacts do not yet exist, so the module can be run at
any point in the phase.

Run:  python src/report/figures_phase2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase2_style as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
DATA = ROOT / "data"

STATIONS = [1, 2, 3, 4, 5, 6]
WALLS = ["G", "A", "L", "P"]


def load(name):
    p = REP / name
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


def ordered_classes(classes):
    """Order the 23 classes by station then wall, so the confusion matrix
    reveals the (wall x station) grid structure instead of alphabetical noise."""
    out = []
    for s in STATIONS:
        for w in WALLS:
            c = f"{w}{s}"
            if c in classes:
                out.append(c)
    if "OTHERCLASS" in classes:
        out.append("OTHERCLASS")
    return out


# =========================================================================
# F2.1  Phase 2 methodological flow
# =========================================================================
def fig_flow():
    fig, ax = plt.subplots(figsize=(7.4, 8.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 22); ax.axis("off")

    def box(x, y, w, h, text, fc, ec, fs=8.4, weight="normal", tc=S.INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.12,rounding_size=0.18",
                                    fc=fc, ec=ec, lw=1.1, zorder=2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color=tc, zorder=3, fontweight=weight,
                linespacing=1.35)

    def arrow(x1, y1, x2, y2, color=S.MUTED, style="-|>"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                     mutation_scale=11, lw=1.1, color=color,
                                     zorder=1, shrinkA=2, shrinkB=2))

    LB, LE = "#eef2f7", "#9fb2c6"      # implementation
    GB, GE = "#fdeee6", "#e0894f"      # gate
    VB, VE = "#eaf4ee", "#5aa47a"      # validation
    PB, PE = "#f3eefa", "#8f7ab8"      # pre-registration

    rows = [
        (19.6, LB, LE, "STAGE A  Environment\nCUDA wheel - precision benchmark - batch ladder", "normal"),
        (17.9, GB, GE, "GATE 1   torch.cuda.is_available()", "bold"),
        (16.2, LB, LE, "STAGE B  Consensus cohort\n4/4-agreement images under official patient splits", "normal"),
        (14.5, GB, GE, "GATE 2   3,722 / 793 / 803  -  23 classes", "bold"),
        (12.8, GB, GE, "GATE 3   SHA-256 resolution against Phase 0 inventory", "bold"),
        (11.1, LB, LE, "STAGE C  Implementation\ncache - model - two-stage schedule - metrics - bootstrap", "normal"),
        (9.4, PB, PE, "STAGE D  PRE-REGISTRATION FROZEN\ntarget - band - seeds - intervals - diagnostic order", "bold"),
        (7.7, LB, LE, "STAGE E  Execution\n3 seeds x (10 warm-up + fine-tune to early stop)", "normal"),
        (6.0, VB, VE, "Model selection on VALIDATION macro F1", "normal"),
        (4.3, VB, VE, "Test set evaluated ONCE per seed\npatient-clustered bootstrap, 1,000 resamples", "normal"),
        (2.6, GB, GE, "GATE 5   |observed - published| <= 1.5 points", "bold"),
        (0.9, LB, LE, "STAGE F  Reporting\nartefacts - figures - DOCX/PDF - blueprint update", "normal"),
    ]
    for y, fc, ec, txt, w in rows:
        box(0.6, y, 8.8, 1.15, txt, fc, ec, weight=w)
    for i in range(len(rows) - 1):
        arrow(5.0, rows[i][0], 5.0, rows[i + 1][0] + 1.15)

    # failure branch
    ax.add_patch(FancyArrowPatch((9.4, 3.18), (9.9, 3.18), arrowstyle="-",
                                 lw=1.1, color=S.ORANGE))
    ax.plot([9.9, 9.9], [3.18, 8.28], color=S.ORANGE, lw=1.1, ls=(0, (4, 2)))
    arrow(9.9, 8.28, 9.4, 8.28, color=S.ORANGE)
    ax.text(9.72, 5.7, "FAIL -> pre-registered\ndiagnostic order", rotation=90,
            ha="center", va="center", fontsize=7.4, color=S.ORANGE)

    handles = [
        Rectangle((0, 0), 1, 1, fc=LB, ec=LE, label="Implementation"),
        Rectangle((0, 0), 1, 1, fc=PB, ec=PE, label="Pre-registration"),
        Rectangle((0, 0), 1, 1, fc=VB, ec=VE, label="Validation"),
        Rectangle((0, 0), 1, 1, fc=GB, ec=GE, label="Gate (hard stop)"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.035),
              ncol=4, fontsize=8)
    ax.set_title("Phase 2 execution order, with gates and the pre-registration "
                 "boundary", pad=12)
    return S.save(fig, "P2_F01_flow.png")


# =========================================================================
# F2.2  Cohort construction and attrition
# =========================================================================
def fig_cohort():
    p = load("phase2_split_provenance.json")
    if not p:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.9),
                             gridspec_kw={"width_ratios": [1.15, 1, 1]})

    # --- A: funnel -------------------------------------------------------
    ax = axes[0]
    corpus, cohort = p["corpus"]["n_images"], p["cohort"]["n_images"]
    stages = [("GastroHUN corpus", corpus, S.MUTED),
              ("Complete 4/4 agreement", cohort, S.BLUE)]
    for i, (lab, v, c) in enumerate(stages):
        ax.barh(i, v, color=c, height=0.5, zorder=3)
        ax.text(v + corpus * 0.02, i, f"{v:,}", va="center", fontsize=9.5,
                fontweight="bold", color=c)
    ax.barh(0.5, 0, color="none")
    drop = corpus - cohort
    ax.annotate(f"-{drop:,} images\n({100 * drop / corpus:.2f}%)\nlack unanimity",
                xy=(cohort + (corpus - cohort) / 2, 0.5), ha="center",
                va="center", fontsize=8, color=S.ORANGE)
    ax.set_yticks(range(len(stages)))
    ax.set_yticklabels([s[0] for s in stages], fontsize=9)
    ax.set_xlim(0, corpus * 1.18)
    ax.set_xlabel("images")
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    S.despine(ax, left=True)
    ax.set_title("Cohort restriction")
    S.panel(ax, "A", dx=-0.42)

    # --- B: retention by split ------------------------------------------
    ax = axes[1]
    splits = ["Train", "Validation", "Test"]
    allb = [p["corpus"]["by_split"][s] for s in splits]
    coh = [p["cohort"]["by_split"][s] for s in splits]
    x = np.arange(3)
    ax.bar(x, allb, width=0.62, color="#dfe6ee", zorder=2, label="all images")
    ax.bar(x, coh, width=0.62, color=[S.SPLIT_COLORS[s] for s in splits],
           zorder=3, label="complete agreement")
    for i, (a, c) in enumerate(zip(allb, coh)):
        ax.text(i, c / 2, f"{c:,}", ha="center", va="center", color="white",
                fontsize=9, fontweight="bold", zorder=4)
        ax.text(i, a + max(allb) * 0.025, f"{100 * c / a:.1f}% retained",
                ha="center", fontsize=8, color=S.MUTED)
    ax.set_xticks(x); ax.set_xticklabels(splits)
    ax.set_ylabel("images")
    ax.set_ylim(0, max(allb) * 1.16)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2,
              fontsize=8)
    ax.set_title("Retention by official split")
    S.panel(ax, "B")

    # --- C: patient attrition -------------------------------------------
    ax = axes[2]
    pc = p["cohort"]["patients_by_split_corpus"]
    pk = p["cohort"]["patients_by_split"]
    w = 0.34
    ax.bar(x - w / 2, [pc[s] for s in splits], w, color="#dfe6ee",
           zorder=2, label="corpus")
    ax.bar(x + w / 2, [pk[s] for s in splits], w,
           color=[S.SPLIT_COLORS[s] for s in splits], zorder=3, label="cohort")
    for i, s in enumerate(splits):
        d = pc[s] - pk[s]
        ax.text(i - w / 2, pc[s] + 4, str(pc[s]), ha="center", fontsize=8.2,
                color=S.MUTED)
        ax.text(i + w / 2, pk[s] + 4, str(pk[s]), ha="center", fontsize=8.2,
                fontweight="bold", color=S.SPLIT_COLORS[s])
        if d:
            ax.annotate(f"-{d}", xy=(i, pk[s] + 22), ha="center", fontsize=8.5,
                        color=S.ORANGE, fontweight="bold")
    lost = p["cohort"]["patients_lost_to_consensus"]
    txt = "; ".join(f"{k}: patient {', '.join(map(str, v))}"
                    for k, v in lost.items())
    ax.set_xticks(x); ax.set_xticklabels(splits)
    ax.set_ylabel("patients")
    ax.set_ylim(0, max(pc.values()) * 1.22)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2,
              fontsize=8)
    ax.set_title("Patient attrition")
    fig.text(0.5, -0.06, f"Patients lost entirely to consensus filtering - "
             f"{txt}", ha="center", fontsize=8, color=S.ORANGE)
    S.panel(ax, "C")

    fig.suptitle("Construction of the complete-agreement evaluation cohort",
                 fontsize=12, fontweight="bold", y=1.04)
    fig.tight_layout()
    return S.save(fig, "P2_F02_cohort.png")


# =========================================================================
# F2.3  Class composition and test-set statistical power
# =========================================================================
def fig_classes():
    p = load("phase2_split_provenance.json")
    if not p:
        return None
    classes = ordered_classes(p["cohort"]["classes"])
    disp = ["OTHER" if c == "OTHERCLASS" else c for c in classes]
    cbs = p["class_by_split"]
    splits = ["Train", "Validation", "Test"]

    fig, axes = plt.subplots(2, 1, figsize=(11.2, 6.6),
                             gridspec_kw={"height_ratios": [1.25, 1]})

    ax = axes[0]
    x = np.arange(len(classes))
    bottom = np.zeros(len(classes))
    for s in splits:
        v = np.array([cbs[s].get(c, 0) for c in classes], dtype=float)
        ax.bar(x, v, bottom=bottom, width=0.74, color=S.SPLIT_COLORS[s],
               label=s, zorder=3, edgecolor="white", linewidth=0.5)
        bottom += v
    for i, c in enumerate(classes):
        ax.text(i, bottom[i] + max(bottom) * 0.02, f"{int(bottom[i])}",
                ha="center", fontsize=7.4, color=S.MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels(disp, fontsize=8.2, rotation=0)
    ax.set_ylabel("images")
    ax.set_ylim(0, max(bottom) * 1.14)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(ncol=3, loc="upper left", fontsize=8.5)
    ax.set_title(f"Cohort class composition, ordered by station then wall "
                 f"(chi2 = {p['class_split_chi2']}, p = {p['class_split_p']:.3f})")
    for s in range(1, 6):
        ax.axvline(4 * s - 0.5, color=S.GRID, lw=1.0, zorder=1)
    ax.axvline(len(classes) - 1.5, color=S.MUTED, lw=1.0, ls=":", zorder=1)
    S.panel(ax, "A", dx=-0.055)

    # --- B: test support vs achievable precision -------------------------
    ax = axes[1]
    sup = np.array([p["test_class_support"].get(c, 0) for c in classes])

    def wilson_hw(n, phat=0.85, z=1.96):
        if n == 0:
            return np.nan
        d = 1 + z ** 2 / n
        return 100 * z * np.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2)) / d

    hw = np.array([wilson_hw(n) for n in sup])
    cols = [S.GREEN if h <= 10 else S.ORANGE for h in hw]
    ax.bar(x, hw, width=0.74, color=cols, zorder=3)
    ax.axhline(10, color=S.RED, lw=1.2, ls="--", zorder=4)
    ax.text(-0.35, 10.55, "G7 criterion: +/-10 pp", ha="left",
            fontsize=8, color=S.RED)
    for i, (n, h) in enumerate(zip(sup, hw)):
        ax.text(i, h + 0.5, f"n={n}", ha="center", fontsize=7, color=S.MUTED)
    ax.set_xticks(x); ax.set_xticklabels(classes, fontsize=8.2)
    ax.set_ylabel("Wilson 95% half-width (pp)\nat p = 0.85")
    ax.set_ylim(0, max(hw) * 1.22)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    n_fail = int((hw > 10).sum())
    ax.set_title(f"Achievable per-class precision on the 803-image test set - "
                 f"{n_fail}/{len(classes)} classes cannot meet +/-10 pp "
                 f"(limitation L1)")
    for s in range(1, 6):
        ax.axvline(4 * s - 0.5, color=S.GRID, lw=1.0, zorder=1)
    ax.axvline(len(classes) - 1.5, color=S.MUTED, lw=1.0, ls=":", zorder=1)
    S.panel(ax, "B", dx=-0.055)

    fig.tight_layout()
    return S.save(fig, "P2_F03_classes.png")


# =========================================================================
# F2.4  Normalisation statistics
# =========================================================================
def fig_norm():
    ns = load("phase2_norm_stats.json")
    if not ns:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.6))
    chans = ["Red", "Green", "Blue"]
    ccol = ["#c0392b", "#27ae60", "#2874c9"]
    x = np.arange(3); w = 0.36

    for k, (ax, key, ikey, ttl) in enumerate([
            (axes[0], "mean", "imagenet_mean", "Channel mean"),
            (axes[1], "std", "imagenet_std", "Channel standard deviation")]):
        ax.bar(x - w / 2, ns[ikey], w, color="#cfd6de", zorder=3,
               label="ImageNet default")
        ax.bar(x + w / 2, ns[key], w, color=ccol, zorder=3,
               label="GastroHUN training set")
        for i in range(3):
            ax.text(i - w / 2, ns[ikey][i] + 0.012, f"{ns[ikey][i]:.3f}",
                    ha="center", fontsize=7.8, color=S.MUTED)
            ax.text(i + w / 2, ns[key][i] + 0.012, f"{ns[key][i]:.3f}",
                    ha="center", fontsize=7.8, fontweight="bold", color=ccol[i])
            d = ns[key][i] - ns[ikey][i]
            ax.annotate(f"{d:+.3f}", xy=(i, max(ns[key][i], ns[ikey][i]) + 0.055),
                        ha="center", fontsize=8,
                        color=S.ORANGE if abs(d) > 0.05 else S.MUTED)
        ax.set_xticks(x); ax.set_xticklabels(chans)
        ax.set_ylim(0, max(max(ns[key]), max(ns[ikey])) * 1.34)
        ax.grid(axis="x", visible=False)
        S.despine(ax)
        ax.set_title(ttl)
        ax.legend(fontsize=8, loc="upper right")
        S.panel(ax, "AB"[k])

    ax = axes[2]
    cache = DATA / "phase2_cache_224.npy"
    if cache.exists():
        arr = np.load(cache, mmap_mode="r")
        idx = pd.read_csv(DATA / "phase2_cache_index.csv")
        tr = np.where(idx.set_type == "Train")[0]
        rng = np.random.default_rng(0)
        pick = rng.choice(tr, size=min(300, len(tr)), replace=False)
        sample = np.asarray(arr[np.sort(pick)]).reshape(-1, 3) / 255.0
        for c in range(3):
            ax.hist(sample[:, c], bins=64, range=(0, 1), histtype="step",
                    lw=1.5, color=ccol[c], label=chans[c], density=True,
                    zorder=3)
            ax.axvline(ns["mean"][c], color=ccol[c], lw=1.0, ls=":", zorder=2)
        ax.set_xlabel("normalised intensity")
        ax.set_ylabel("density")
        ax.legend(fontsize=8)
        S.despine(ax)
        ax.set_title("Training-set intensity distribution\n(300-image sample)")
        S.panel(ax, "C")

    fig.suptitle("Endoscopic images are strongly red-shifted relative to "
                 "ImageNet, so training-set normalisation is not cosmetic",
                 fontsize=11.5, fontweight="bold", y=1.05)
    fig.tight_layout()
    return S.save(fig, "P2_F04_normalisation.png")


# =========================================================================
# F2.5  Hardware characterisation -- the AMP finding
# =========================================================================
def fig_hardware():
    p = load("phase2_vram_probe.json")
    if not p or "precision_factorial" not in p:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2),
                             gridspec_kw={"width_ratios": [1.05, 1, 1]})

    # --- A: precision factorial -----------------------------------------
    ax = axes[0]
    f = p["precision_factorial"]
    labs, vals, cols = [], [], []
    for r in f:
        labs.append(("AMP fp16" if r["amp_fp16"] else "float32") +
                    ("\n+ channels_last" if r["channels_last"] else "\ncontiguous"))
        vals.append(r["images_per_sec"])
        cols.append(S.ORANGE if r["amp_fp16"] else S.BLUE)
    order = np.argsort(vals)
    labs = [labs[i] for i in order]; vals = [vals[i] for i in order]
    cols = [cols[i] for i in order]
    y = np.arange(len(vals))
    ax.barh(y, vals, color=cols, height=0.62, zorder=3)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.02, i, f"{v:.1f}", va="center",
                fontsize=9, fontweight="bold", color=cols[i])
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8.4)
    ax.set_xlabel("images / second  (batch 24, fwd+bwd)")
    ax.set_xlim(0, max(vals) * 1.2)
    ax.grid(axis="y", visible=False)
    S.despine(ax, left=True)
    ax.set_title(f"AMP float16 runs at {p['amp_vs_fp32_speedup']:.2f}x float32")
    ax.text(0.5, -0.34, "The GTX 1650 is the TU117 Turing die: no tensor "
            "cores, so FP16\ngains nothing while autocast and GradScaler cost "
            "throughput.",
            transform=ax.transAxes, ha="center", fontsize=8, color=S.ORANGE)
    S.panel(ax, "A", dx=-0.30)

    # --- B: peak memory across the batch ladder --------------------------
    lad = [r for r in p["batch_ladder"] if not r.get("oom")]
    b = [r["batch"] for r in lad]
    mem = [r["peak_alloc_mib"] for r in lad]
    ips = [r["images_per_sec"] for r in lad]
    fits = [r["fits"] for r in lad]
    xi = np.arange(len(b))
    cols = [S.GREEN if f else S.RED for f in fits]
    ch = p["chosen_batch"]
    ci_ = list(b).index(ch)
    tot = p["total_vram_mib"]
    ceil_ = tot - p["safety_margin_mib"]

    ax = axes[1]
    ax.bar(xi, mem, width=0.6, color=cols, zorder=3)
    ax.axhline(tot, color=S.RED, lw=1.4, zorder=5)
    ax.axhline(ceil_, color=S.ORANGE, lw=1.2, ls="--", zorder=5)
    ax.text(len(b) - 0.45, tot + 110, f"physical VRAM {tot:.0f} MiB",
            ha="right", fontsize=7.8, color=S.RED, zorder=6)
    ax.text(len(b) - 0.45, ceil_ - 300,
            f"usable ceiling ({p['safety_margin_mib']} MiB margin)",
            ha="right", fontsize=7.8, color=S.ORANGE, zorder=6)
    for i, m_ in enumerate(mem):
        ax.text(i, m_ + 90, f"{m_:.0f}", ha="center", fontsize=8,
                fontweight="bold", color=cols[i])
    ax.set_xticks(xi); ax.set_xticklabels(b)
    ax.set_xlabel("batch size")
    ax.set_ylabel("peak allocated VRAM (MiB)")
    ax.set_ylim(0, tot * 1.52)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.legend(handles=[Rectangle((0, 0), 1, 1, fc=S.GREEN, label="fits"),
                       Rectangle((0, 0), 1, 1, fc=S.RED,
                                 label="exceeds ceiling")],
              loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2,
              fontsize=8)
    ax.set_title("Peak memory")
    S.panel(ax, "B")

    # --- C: throughput across the batch ladder ---------------------------
    ax = axes[2]
    ax.plot(xi, ips, color=S.INK, lw=1.6, zorder=3)
    ax.scatter(xi, ips, s=52, c=cols, zorder=4, edgecolor="white",
               linewidth=1.1)
    for i, v in enumerate(ips):
        ax.annotate(f"{v:.1f}", (i, v), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=8.2,
                    fontweight="bold" if i == ci_ else "normal",
                    color=S.BLUE if i == ci_ else S.INK)
    ax.axvline(ci_, color=S.BLUE, lw=1.2, ls=":", zorder=1)
    ax.annotate(f"selected: batch {ch}\n{ips[ci_]:.1f} img/s",
                xy=(ci_, ips[ci_]), xytext=(ci_ + 0.45, max(ips) * 0.45),
                fontsize=8.4, fontweight="bold", color=S.BLUE, ha="left",
                arrowprops=dict(arrowstyle="->", color=S.BLUE, lw=1.1))
    ax.set_xticks(xi); ax.set_xticklabels(b)
    ax.set_xlabel("batch size")
    ax.set_ylabel("images / second")
    ax.set_ylim(0, max(ips) * 1.28)
    ax.grid(axis="x", visible=False)
    S.despine(ax)
    ax.set_title("Throughput")
    ax.text(0.5, -0.30, "Batches above the ceiling thrash: throughput\n"
            "collapses to 4.3 img/s at batch 48.", transform=ax.transAxes,
            ha="center", fontsize=8, color=S.MUTED)
    S.panel(ax, "C")

    fig.suptitle("Hardware characterisation: the blueprint's AMP prescription "
                 "is a pessimisation on this device",
                 fontsize=11.5, fontweight="bold", y=1.05)
    fig.tight_layout()
    return S.save(fig, "P2_F05_hardware.png")


# =========================================================================
# F2.6  Training dynamics
# =========================================================================
def fig_training():
    runs = sorted(REP.glob("phase2_run_seed*.json"))
    if not runs:
        return None
    R = [json.load(open(r, encoding="utf-8")) for r in runs]
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.9))
    wu = R[0]["warmup_epochs"]

    for ax in axes:
        ax.axvspan(0.5, wu + 0.5, color="#f2f5f9", zorder=0)

    for k, r in enumerate(R):
        h = pd.DataFrame(r["history"])
        h["step"] = np.arange(1, len(h) + 1)
        c = S.SEED_COLORS[k % len(S.SEED_COLORS)]
        axes[0].plot(h.step, h.train_loss, color=c, lw=1.4,
                     label=f"seed {r['seed']}")
        axes[1].plot(h.step, h.val_macro_f1, color=c, lw=1.4,
                     label=f"seed {r['seed']}")
        be = r["best_epoch_overall"]
        axes[1].plot(be, r["best_val_macro_f1"], "o", color=c, ms=7,
                     mec="white", mew=1.2, zorder=6,
                     label=f"seed {r['seed']} best: {r['best_val_macro_f1']:.4f}")
        if r["stop_reason"] == "early_stopping":
            axes[1].axvline(len(h), color=c, lw=1.0, ls=":", alpha=0.7)
        axes[2].plot(h.step, h.lr, color=c, lw=1.4, label=f"seed {r['seed']}")

    axes[0].set_ylabel("training loss")
    axes[0].set_title("Training loss")
    axes[1].set_ylabel("validation macro F1")
    axes[1].set_title("Validation macro F1 (model selection criterion)")
    h0, l0 = axes[1].get_legend_handles_labels()
    axes[1].legend(h0[len(R):] + h0[:len(R)], l0[len(R):] + l0[:len(R)],
                   fontsize=7.6, loc="lower right", ncol=1)
    axes[2].set_ylabel("learning rate")
    axes[2].set_yscale("log")
    axes[2].set_title("Learning-rate schedule")
    for i, ax in enumerate(axes):
        ax.set_xlabel("epoch (cumulative)")
        S.despine(ax)
        if ax is not axes[1]:
            ax.legend(fontsize=8)
        ax.text(wu / 2 + 0.5, ax.get_ylim()[1], "warm-up", ha="center",
                va="top", fontsize=8, color=S.MUTED)
        S.panel(ax, "ABC"[i])

    stops = ", ".join(f"seed {r['seed']}: {r['n_epochs_run']} epochs "
                      f"({r['stop_reason'].replace('_', ' ')})" for r in R)
    fig.suptitle("Training dynamics - " + stops,
                 fontsize=11, fontweight="bold", y=1.05)
    fig.tight_layout()
    return S.save(fig, "P2_F06_training.png")


# =========================================================================
# F2.7  Bootstrap distributions and seed agreement
# =========================================================================
def fig_bootstrap():
    m = load("phase2_test_metrics.json")
    if not m:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.0),
                             gridspec_kw={"width_ratios": [1.3, 1]})
    seeds = m["seeds"]

    ax = axes[0]
    for k, s in enumerate(seeds):
        d = m["per_seed"][str(s)]
        c = S.SEED_COLORS[k % len(S.SEED_COLORS)]
        lo, hi = d["macro_f1_ci95"]
        ax.axvspan(lo * 100, hi * 100, color=c, alpha=0.08, zorder=1)
        ax.axvline(d["macro_f1"] * 100, color=c, lw=1.8, zorder=4,
                   label=f"seed {s}: {100 * d['macro_f1']:.2f} "
                         f"[{100 * lo:.2f}, {100 * hi:.2f}]")
    ag = m["aggregate"]
    ax.axvline(ag["macro_f1_mean"] * 100, color=S.INK, lw=2.4, zorder=5,
               label=f"seed mean: {100 * ag['macro_f1_mean']:.2f}")
    ax.set_xlabel("macro F1 (%)  -  patient-clustered bootstrap")
    ax.set_yticks([])
    ax.legend(fontsize=8.2, loc="upper left")
    S.despine(ax, left=True)
    ax.set_title(f"Per-seed test macro F1 with 95% intervals\n"
                 f"({m['n_boot']:,} resamples of {m['n_test_patients']} "
                 f"test patients)")
    S.panel(ax, "A", dx=-0.06)

    ax = axes[1]
    y = np.arange(len(seeds) + 1)
    labels, cent, los, his, cols = [], [], [], [], []
    for k, s in enumerate(seeds):
        d = m["per_seed"][str(s)]
        labels.append(f"seed {s}")
        cent.append(d["macro_f1"] * 100)
        los.append(d["macro_f1_ci95"][0] * 100)
        his.append(d["macro_f1_ci95"][1] * 100)
        cols.append(S.SEED_COLORS[k % len(S.SEED_COLORS)])
    labels.append("seed mean")
    cent.append(ag["macro_f1_mean"] * 100)
    los.append(ag["seed_mean_boot_ci95"][0] * 100)
    his.append(ag["seed_mean_boot_ci95"][1] * 100)
    cols.append(S.INK)
    for i in range(len(cent)):
        ax.plot([los[i], his[i]], [i, i], color=cols[i], lw=2.2, zorder=3)
        ax.plot(cent[i], i, "D" if i == len(cent) - 1 else "o", color=cols[i],
                ms=8 if i == len(cent) - 1 else 6.5, zorder=4, mec="white")
        ax.text(his[i] + 0.15, i, f"{cent[i]:.2f}", va="center", fontsize=8.4,
                color=cols[i], fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("macro F1 (%)")
    sd = ag["macro_f1_sd"]
    ax.set_title("Seed agreement" +
                 (f"  (SD = {100 * sd:.2f} pp, range = "
                  f"{ag['macro_f1_range_points']:.2f} pp)" if sd else ""))
    ax.grid(axis="y", visible=False)
    S.despine(ax, left=True)
    S.panel(ax, "B")

    fig.tight_layout()
    return S.save(fig, "P2_F07_bootstrap.png")


# =========================================================================
# F2.8  Confusion matrix
# =========================================================================
def fig_confusion():
    m = load("phase2_test_metrics.json")
    p = load("phase2_split_provenance.json")
    if not m or not p:
        return None
    ci = json.load(open(DATA / "phase2_class_index.json", encoding="utf-8"))
    inv = {v: k for k, v in ci.items()}
    classes = [inv[i] for i in range(len(inv))]
    order = ordered_classes(classes)
    perm = [classes.index(c) for c in order]

    cms = np.mean([np.array(m["per_seed"][str(s)]["confusion_matrix"],
                            dtype=float) for s in m["seeds"]], axis=0)
    cm = cms[np.ix_(perm, perm)]
    row = cm.sum(1, keepdims=True)
    norm = np.divide(cm, row, out=np.zeros_like(cm), where=row > 0) * 100

    fig, ax = plt.subplots(figsize=(9.4, 8.2))
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=100, aspect="equal")
    n = len(order)
    for i in range(n):
        for j in range(n):
            v = norm[i, j]
            if v >= 0.5:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=6.6,
                        color="white" if v > 55 else S.INK)
    for s in range(1, 6):
        ax.axhline(4 * s - 0.5, color=S.ORANGE, lw=1.0)
        ax.axvline(4 * s - 0.5, color=S.ORANGE, lw=1.0)
    ax.axhline(n - 1.5, color=S.MUTED, lw=1.0)
    ax.axvline(n - 1.5, color=S.MUTED, lw=1.0)
    ax.set_xticks(range(n)); ax.set_xticklabels(order, fontsize=7.6, rotation=90)
    ax.set_yticks(range(n)); ax.set_yticklabels(order, fontsize=7.6)
    ax.set_xlabel("predicted class"); ax.set_ylabel("reference (4/4 consensus)")
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.041, pad=0.02)
    cb.set_label("% of reference class", fontsize=8.5)
    cb.outline.set_visible(False)
    diag = np.trace(cm) / cm.sum() * 100
    ax.set_title(f"Row-normalised confusion matrix, mean over "
                 f"{len(m['seeds'])} seeds\n803 complete-agreement test "
                 f"images - overall accuracy {diag:.2f}%\n"
                 f"orange rules separate the six SSS stations", pad=12)
    fig.tight_layout()
    return S.save(fig, "P2_F08_confusion.png")


# =========================================================================
# F2.9  Per-class performance with Wilson intervals
# =========================================================================
def fig_perclass():
    m = load("phase2_test_metrics.json")
    if not m:
        return None
    rows = {}
    for s in m["seeds"]:
        for r in m["per_seed"][str(s)]["per_class"]:
            rows.setdefault(r["class"], []).append(r)
    recs = []
    for c, rs in rows.items():
        recs.append({
            "class": c, "support": rs[0]["support"],
            "f1": float(np.mean([r["f1"] for r in rs])),
            "recall": float(np.mean([r["recall"] or 0 for r in rs])),
            "lo": float(np.mean([r["recall_wilson_lo"] for r in rs])),
            "hi": float(np.mean([r["recall_wilson_hi"] for r in rs])),
        })
    df = pd.DataFrame(recs).sort_values("f1", ascending=True).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(9.6, 7.4))
    y = np.arange(len(df))
    for i, r in df.iterrows():
        w = r.hi - r.lo
        ax.plot([r.lo * 100, r.hi * 100], [i, i],
                color=S.GRID if w > 0.2 else "#c9d3de", lw=6, zorder=2,
                solid_capstyle="round")
        ax.plot(r.recall * 100, i, "o", color=S.MUTED, ms=5, zorder=3)
        ax.plot(r.f1 * 100, i, "D", color=S.BLUE, ms=6.5, zorder=4,
                mec="white", mew=0.8)
        ax.text(101.5, i, f"n={int(r.support)}", va="center", fontsize=7.6,
                color=S.MUTED)
        ax.text(-1.5, i, f"{r.f1 * 100:.1f}", va="center", ha="right",
                fontsize=7.8, color=S.BLUE, fontweight="bold")
    mean_f1 = m["aggregate"]["macro_f1_mean"] * 100
    ax.axvline(mean_f1, color=S.ORANGE, lw=1.4, ls="--", zorder=1)
    ax.text(mean_f1 + 0.6, len(df) - 0.4, f"macro F1 {mean_f1:.2f}",
            fontsize=8.4, color=S.ORANGE, rotation=90, va="top")
    ax.set_yticks(y); ax.set_yticklabels(df["class"], fontsize=8.4)
    ax.set_xlim(-6, 108)
    ax.set_xlabel("percent")
    ax.grid(axis="y", visible=False)
    S.despine(ax, left=True)
    ax.legend(handles=[
        Line2D([], [], color=S.BLUE, marker="D", ls="", label="F1"),
        Line2D([], [], color=S.MUTED, marker="o", ls="", label="recall"),
        Line2D([], [], color=S.GRID, lw=6, label="recall Wilson 95% interval")],
        loc="lower right", fontsize=8.4)
    ax.set_title("Per-class performance, mean over seeds - EXPLORATORY ONLY\n"
                 "interval widths show why per-class claims are not supported "
                 "at this test-set size (L1)", pad=10)
    fig.tight_layout()
    return S.save(fig, "P2_F09_perclass.png")


# =========================================================================
# F2.10  Reproduction verdict
# =========================================================================
def fig_verdict():
    m = load("phase2_test_metrics.json")
    if not m:
        return None
    r = m["reproduction"]
    ag = m["aggregate"]
    fig, ax = plt.subplots(figsize=(10.4, 4.4))

    tgt, band = r["published_macro_f1"], r["acceptance_band_points"]
    ax.axvspan(tgt - band, tgt + band, color=S.GREEN, alpha=0.13, zorder=1)
    ax.axvline(tgt, color=S.GREEN, lw=1.8, zorder=3)

    anchors = [
        ("Human expert band (77.47-84.82)", 77.47, 84.82, S.MUTED, 0),
        ("Best single annotator G1 (84.82)", 84.82, None, S.PURPLE, 1),
        ("ResNet152 published (85.28)", 85.28, None, S.CYAN, 2),
        ("ConvNeXt-Tiny published target (~85.0)", tgt, None, S.GREEN, 3),
        ("ConvNeXt-Tiny FG-labels (87.05)", 87.05, None, S.YELLOW, 4),
        ("ConvNeXt-Large published ceiling (88.25)", 88.25, None, S.ORANGE, 5),
    ]
    for lab, a, b, c, i in anchors:
        if b is None:
            ax.plot([a], [i], "o", color=c, ms=7, zorder=4, mec="white")
        else:
            ax.plot([a, b], [i, i], color=c, lw=5, alpha=0.5, zorder=2,
                    solid_capstyle="round")
        ax.text(76.4, i, lab, ha="right", va="center", fontsize=8.4, color=c)

    yo = len(anchors)
    obs = r["observed_macro_f1"]
    lo, hi = [v * 100 for v in ag["seed_mean_boot_ci95"]]
    col = S.BLUE if r["verdict"] == "PASS" else S.RED
    ax.plot([lo, hi], [yo, yo], color=col, lw=3, zorder=5,
            solid_capstyle="round")
    ax.plot(obs, yo, "D", color=col, ms=11, zorder=6, mec="white", mew=1.4)
    ax.text(76.4, yo, "THIS WORK  (seed mean, 95% CI)", ha="right",
            va="center", fontsize=9, fontweight="bold", color=col)
    ax.annotate(f"{obs:.2f}\n[{lo:.2f}, {hi:.2f}]", xy=(obs, yo),
                textcoords="offset points", xytext=(0, 15), ha="center",
                fontsize=8.8, fontweight="bold", color=col)

    ax.set_ylim(-0.8, yo + 1.1)
    ax.set_yticks([])
    ax.set_xlim(76.5, 90)
    ax.set_xlabel("macro F1 (%) on the 803-image complete-agreement test set")
    ax.grid(axis="y", visible=False)
    S.despine(ax, left=True)
    ax.text(tgt, -0.65, f"acceptance band  {tgt - band:.1f} - {tgt + band:.1f}",
            ha="center", fontsize=8.4, color=S.GREEN)

    verdict_txt = (f"{r['verdict']}\ndelta = {r['delta_points']:+.2f} pts "
                   f"(band +/-{band})")
    ax.text(0.015, 0.06, verdict_txt, transform=ax.transAxes, ha="left",
            va="bottom", fontsize=10.5, fontweight="bold", color="white",
            linespacing=1.4,
            bbox=dict(boxstyle="round,pad=0.5",
                      fc=S.GREEN if r["verdict"] == "PASS" else S.RED,
                      ec="none"))
    ax.set_title("Reproduction verdict against the pre-registered target",
                 loc="center", pad=10)
    fig.tight_layout()
    return S.save(fig, "P2_F10_verdict.png")


# =========================================================================
# F2.11  Calibration baseline
# =========================================================================
def fig_calibration():
    m = load("phase2_test_metrics.json")
    if not m:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2),
                             gridspec_kw={"width_ratios": [1, 1]})
    ax = axes[0]
    ax.plot([0, 100], [0, 100], color=S.MUTED, ls="--", lw=1.2, zorder=2,
            label="perfect calibration")
    for k, s in enumerate(m["seeds"]):
        d = m["per_seed"][str(s)]
        b = [x for x in d["reliability_bins"] if x["n"] > 0]
        c = S.SEED_COLORS[k % len(S.SEED_COLORS)]
        ax.plot([x["conf"] * 100 for x in b], [x["acc"] * 100 for x in b],
                "o-", color=c, ms=4.5, lw=1.4, zorder=3,
                label=f"seed {s}  ECE = {d['ece'] * 100:.2f}%")
    ax.set_xlabel("mean predicted confidence (%)")
    ax.set_ylabel("empirical accuracy (%)")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.legend(fontsize=8.2, loc="upper left")
    S.despine(ax)
    ax.set_title("Reliability diagram")
    S.panel(ax, "A")

    ax = axes[1]
    for k, s in enumerate(m["seeds"]):
        d = m["per_seed"][str(s)]
        b = [x for x in d["reliability_bins"] if x["n"] > 0]
        c = S.SEED_COLORS[k % len(S.SEED_COLORS)]
        tot = sum(x["n"] for x in b)
        ax.step([x["conf"] * 100 for x in b],
                [100 * x["n"] / tot for x in b], where="mid", color=c, lw=1.5,
                label=f"seed {s}")
    ax.set_xlabel("predicted confidence (%)")
    ax.set_ylabel("% of test images")
    ax.set_xlim(0, 100)
    ax.legend(fontsize=8.2)
    S.despine(ax)
    briers = [m["per_seed"][str(s)]["brier"] for s in m["seeds"]]
    ax.set_title(f"Confidence distribution (mean Brier = {np.mean(briers):.4f})")
    S.panel(ax, "B")

    fig.suptitle("Calibration of the reproduced baseline - recorded as the "
                 "reference point for Phase 4, not as a Phase 2 claim",
                 fontsize=11, fontweight="bold", y=1.04)
    fig.tight_layout()
    return S.save(fig, "P2_F11_calibration.png")


def main() -> None:
    S.apply()
    print("Phase 2 figures ->", S.FIGDIR)
    made = []
    for fn in (fig_flow, fig_cohort, fig_classes, fig_norm, fig_hardware,
               fig_training, fig_bootstrap, fig_confusion, fig_perclass,
               fig_verdict, fig_calibration):
        try:
            r = fn()
            if r is None:
                print(f"  skipped {fn.__name__} (artefact not yet available)")
            else:
                made.append(r.name)
        except Exception as e:                       # noqa: BLE001
            print(f"  FAILED {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(made)} figures written")


if __name__ == "__main__":
    main()
