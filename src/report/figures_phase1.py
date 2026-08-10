"""
Phase-I deliverables -- the three figures the Phase-I documents need and that
no earlier phase drew.

Everything else the Phase-I report and defence deck use already exists:
figures_v2/ (Phase 0-1), figures_phase2/ (baseline) and figures_phase3/
(stratified evaluation). Those are reused unchanged, because redrawing a
figure creates a second code path capable of disagreeing with the first.

Three things were never drawn, because no earlier phase needed them as a
single picture:

  PH1_F01  the pre-processing chain -- annotation, resampling, normalisation,
           augmentation and the transfer-learned representation, which is
           what Phase-I is explicitly assessed on.
  PH1_F02  the backbone, its two-stage transfer schedule and which parameter
           blocks are frozen. Layer widths and parameter counts are read out
           of torchvision at run time rather than transcribed.
  PH1_F03  training dynamics, redrawn from the run histories with the three
           panels laid out so the titles do not collide.

Style comes from src/report/phase2_style.py, so these sit in the same visual
system as the rest of the suite; no new palette is introduced.

Outputs:  figures_phase1/PH1_F0{1,2,3}_*.png  (300 dpi)
Run:      python src/report/figures_phase1.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase2_style as S            # noqa: E402
from phase1_facts import facts      # noqa: E402

OUT = ROOT / "figures_phase1"
OUT.mkdir(exist_ok=True)


def _box(ax, x, y, w, h, text, face, edge=None, fs=8.6, tc="white", weight="bold"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor=face, edgecolor=edge or face, linewidth=1.1, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, weight=weight, zorder=3, linespacing=1.5)


def _arrow(ax, x0, y0, x1, y1, color=None):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11,
        linewidth=1.2, color=color or S.MUTED, zorder=1,
        shrinkA=0, shrinkB=0))


def _blank(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


# ---------------------------------------------------------------------------
# PH1_F01 -- the pre-processing chain
# ---------------------------------------------------------------------------
def fig01_preprocessing(F: dict) -> None:
    c, pp, co, tr = F["corpus"], F["preprocess"], F["cohort"], F["training"]
    ag = F["agreement"]

    fig, ax = plt.subplots(figsize=(13.8, 5.0))
    _blank(ax)

    stages = [
        ("1 · ANNOTATION", S.BLUE,
         f"{c['n_annotators']} independent annotators\n"
         f"{c['n_classes']} classes, {c['n_images']:,} images\n"
         f"Fleiss $\\kappa$ = {F['agreement']['fleiss']:.4f}\n"
         f"{c['n_annotators']} vote columns kept\n"
         f"separate, never merged"),
        ("2 · COHORT SELECTION", S.BLUE,
         f"unanimous {c['n_annotators']}/{c['n_annotators']} subset\n"
         f"{co['n_images']:,} images = {co['retention_pct']:.1f}%\n"
         f"train {co['train']:,} / val {co['val']:,}\n"
         f"test {co['test']:,}\n"
         f"{co['overlap_total']} patient overlaps"),
        ("3 · RESAMPLING", S.GREEN,
         f"{pp['size']} × {pp['size']} px RGB\n"
         f"{pp['resample'].title()} kernel\n"
         f"decoded once into an\n"
         f"on-disk cache, reused\n"
         f"bit-identically after"),
        ("4 · NORMALISATION", S.GREEN,
         f"training-set mean / SD,\n"
         f"not ImageNet defaults\n"
         f"$\\mu$ = {', '.join(f'{v:.3f}' for v in pp['mean'])}\n"
         f"$\\sigma$ = {', '.join(f'{v:.3f}' for v in pp['std'])}\n"
         f"differs by up to {pp['max_delta']:.3f}"),
        ("5 · AUGMENTATION", S.ORANGE,
         f"RandomResizedCrop\n"
         f"scale {pp['crop_scale'][0]}–{pp['crop_scale'][1]}, "
         f"ratio {pp['crop_ratio'][0]}–{pp['crop_ratio'][1]:.2f}\n"
         f"ColorJitter b/c/s {pp['jitter']['brightness']}\n"
         f"hue {pp['jitter']['hue']}\n"
         f"no flip, no large rotation"),
        ("6 · FEATURE ENGINEERING", S.PURPLE,
         f"transfer learning, not\n"
         f"hand-crafted descriptors\n"
         f"{tr['backbone']}, {tr['weights'].split(' ')[0]}\n"
         f"{tr['params_total'] / 1e6:.1f} M feature params\n"
         f"top {tr['n_modules_unfrozen']}/{tr['n_feature_modules']} blocks re-fitted"),
    ]

    n = len(stages)
    gap, x0, x1 = 0.013, 0.008, 0.992
    w = ((x1 - x0) - gap * (n - 1)) / n
    y, h, hh = 0.315, 0.375, 0.072
    for i, (head, col, body) in enumerate(stages):
        x = x0 + i * (w + gap)
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.003,rounding_size=0.012",
            facecolor="white", edgecolor=col, linewidth=1.4, zorder=2))
        ax.add_patch(FancyBboxPatch(
            (x, y + h - hh), w, hh,
            boxstyle="round,pad=0.003,rounding_size=0.012",
            facecolor=col, edgecolor=col, linewidth=1.4, zorder=3))
        ax.text(x + w / 2, y + h - hh / 2, head, ha="center", va="center",
                fontsize=7.6, color="white", weight="bold", zorder=4)
        ax.text(x + w / 2, y + (h - hh) / 2, body, ha="center",
                va="center", fontsize=7.0, color=S.INK, zorder=4,
                linespacing=1.75)
        if i < n - 1:
            _arrow(ax, x + w + 0.0015, y + h / 2, x + w + gap - 0.0015, y + h / 2)

    ax.text(0.5, 0.955,
            "Pre-processing chain: every stage is fixed once and reused unchanged by "
            "all later phases",
            ha="center", va="center", fontsize=11.5, weight="bold", color=S.INK)

    # the label-construction note -- the reason annotation is stage 1 and not
    # a footnote
    ax.text(0.5, 0.835,
            f"The {c['n_annotators']} vote columns are never collapsed to a single label at "
            f"ingest. {ag['unanimous_pct']:.1f}% of images are unanimous and become the "
            f"baseline cohort;\nthe remaining {ag['contested_pct']:.1f}% "
            f"({ag['contested_n']:,} images) are retained for the agreement-stratified "
            f"evaluation instead of being discarded.",
            ha="center", va="center", fontsize=8.6, color=S.MUTED,
            linespacing=1.7)

    ax.text(0.5, 0.163,
            "Augmentation is deliberately conservative: the class label encodes an anatomical "
            "WALL, so horizontal or vertical flipping and large rotations\nwould relabel the "
            "image. Only photometric jitter and a mild scale/translation crop are applied.",
            ha="center", va="center", fontsize=8.4, color=S.INK,
            linespacing=1.8,
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#f4f6f8",
                      edgecolor=S.GRID, linewidth=0.8))

    ax.text(0.5, 0.025,
            f"Normalisation statistics measured over "
            f"{pp['n_norm_images']:,} training images "
            f"({pp['n_pixels']:,} pixels per channel). Sources: "
            f"reports/phase2_norm_stats.json, reports/phase2_split_provenance.json.",
            ha="center", va="center", fontsize=7.2, color=S.MUTED, style="italic")

    fig.savefig(OUT / "PH1_F01_preprocessing_pipeline.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F02 -- backbone and transfer schedule
# ---------------------------------------------------------------------------
def fig02_architecture(F: dict) -> None:
    from torchvision.models import convnext_tiny

    tr = F["training"]
    model = convnext_tiny(weights=None)

    blocks = []
    for i, mod in enumerate(model.features):
        params = sum(p.numel() for p in mod.parameters())
        ch = None
        for p in mod.parameters():
            if p.dim() >= 1:
                ch = p.shape[0]
        n_cnb = sum(1 for s in mod if type(s).__name__ == "CNBlock")
        if i == 0:
            label, kind = "Stem\n4x4 conv, s4", "stem"
        elif n_cnb:
            label, kind = f"Stage\n{n_cnb} x CNBlock", "stage"
        else:
            label, kind = "Down-\nsample", "down"
        blocks.append(dict(i=i, params=params, ch=ch, label=label, kind=kind))

    head_params = sum(p.numel() for p in model.classifier.parameters())
    unfrozen = set(range(tr["n_feature_modules"] - tr["n_modules_unfrozen"],
                         tr["n_feature_modules"]))

    fig, ax = plt.subplots(figsize=(13.8, 5.2))
    _blank(ax)

    ax.text(0.5, 0.965,
            f"{tr['backbone']} backbone and the two-stage transfer schedule",
            ha="center", va="center", fontsize=11.5, weight="bold", color=S.INK)

    # Box width tracks depth, not parameter count: a two-layer downsample must
    # stay legible next to a nine-block stage. Height carries the parameter
    # count instead.
    gap, x0, x_end = 0.010, 0.075, 0.988
    head_w = 0.088
    raw = [0.135 if b["kind"] == "stage" else 0.070 for b in blocks]
    avail = (x_end - x0) - head_w - gap * len(blocks)
    widths = [w * avail / sum(raw) for w in raw]

    y_base, h_max = 0.575, 0.285
    p_max = max(b["params"] for b in blocks)

    def pstr(n: int) -> str:
        """A 4,896-parameter stem must not print as '0.00 M'."""
        return f"{n / 1e6:.2f} M" if n >= 1e5 else f"{n / 1e3:.1f} K"

    x = x0
    for b, w in zip(blocks, widths):
        frozen = b["i"] not in unfrozen
        face = "#eef1f4" if frozen else S.BLUE
        edge = S.MUTED if frozen else S.BLUE
        tcol = S.INK if frozen else "white"
        h = h_max * (0.45 + 0.55 * (b["params"] / p_max) ** 0.35)
        ax.add_patch(FancyBboxPatch(
            (x, y_base), w, h, boxstyle="round,pad=0.003,rounding_size=0.010",
            facecolor=face, edgecolor=edge, linewidth=1.3, zorder=2))
        ax.text(x + w / 2, y_base + h - 0.048, b["label"], ha="center", va="center",
                fontsize=7.2, color=tcol, weight="bold", zorder=3, linespacing=1.5)
        # narrow blocks get two lines; wide ones get one
        sep = "\n" if b["kind"] != "stage" else " · "
        ax.text(x + w / 2, y_base + 0.032,
                f"{b['ch']} ch{sep}{pstr(b['params'])}",
                ha="center", va="center", fontsize=6.7, color=tcol, zorder=3,
                linespacing=1.5)
        ax.text(x + w / 2, y_base - 0.032, f"features[{b['i']}]", ha="center",
                va="center", fontsize=6.3, color=S.MUTED)
        x += w + gap

    # classification head
    hx = x
    hh = h_max * 0.68
    ax.add_patch(FancyBboxPatch(
        (hx, y_base), head_w, hh,
        boxstyle="round,pad=0.003,rounding_size=0.010",
        facecolor=S.ORANGE, edgecolor=S.ORANGE, linewidth=1.3, zorder=2))
    ax.text(hx + head_w / 2, y_base + hh - 0.048,
            "Head\nLN + Linear", ha="center", va="center", fontsize=7.2,
            color="white", weight="bold", zorder=3, linespacing=1.5)
    ax.text(hx + head_w / 2, y_base + 0.032,
            f"{F['corpus']['n_classes']} classes\n{pstr(head_params)}",
            ha="center", va="center", fontsize=6.7, color="white", zorder=3,
            linespacing=1.5)
    ax.text(hx + head_w / 2, y_base - 0.032, "classifier", ha="center", va="center",
            fontsize=6.3, color=S.MUTED)

    ax.annotate("", xy=(x0 - 0.006, y_base + 0.10), xytext=(0.012, y_base + 0.10),
                arrowprops=dict(arrowstyle="-|>", color=S.MUTED, linewidth=1.2))
    ax.text(0.012, y_base + 0.150,
            f"{F['preprocess']['size']}×{F['preprocess']['size']}×3",
            fontsize=7.0, color=S.MUTED)

    # frozen / fine-tuned brackets
    n_frozen = len(blocks) - tr["n_modules_unfrozen"]
    frozen_x1 = x0 + sum(widths[:n_frozen]) + gap * (n_frozen - 1)
    ax.plot([x0, frozen_x1], [0.505, 0.505], color=S.MUTED, linewidth=1.5)
    ax.text((x0 + frozen_x1) / 2, 0.475,
            f"FROZEN — {n_frozen} of {tr['n_feature_modules']} feature modules "
            f"({(1 - tr['param_fraction_unfrozen']) * 100:.1f}% of feature parameters)",
            ha="center", va="top", fontsize=8.0, color=S.MUTED)

    ax.plot([frozen_x1 + gap, hx + head_w], [0.505, 0.505], color=S.BLUE,
            linewidth=1.5)
    ax.text((frozen_x1 + gap + hx + head_w) / 2, 0.475,
            f"FINE-TUNED — top {tr['n_modules_unfrozen']} modules + head "
            f"({tr['param_fraction_unfrozen'] * 100:.1f}% of feature parameters)",
            ha="center", va="top", fontsize=8.0, color=S.BLUE, weight="bold")

    # schedule strip
    sched = [
        ("STAGE 1 — head warm-up", S.GREEN,
         f"{tr['warmup_epochs']} epochs at constant LR = {tr['lr_head']:g}\n"
         f"backbone entirely frozen; only the "
         f"{F['corpus']['n_classes']}-way head is fitted"),
        ("STAGE 2 — partial fine-tune", S.BLUE,
         f"up to {tr['max_finetune_epochs']} epochs, LR = {tr['lr_finetune']:g}, "
         f"cosine decay, weight decay {tr['weight_decay']:g}\n"
         f"early stopping on validation macro F1, patience {tr['patience']}"),
    ]
    for i, (head, col, body) in enumerate(sched):
        bx = 0.075 + i * 0.470
        _box(ax, bx, 0.275, 0.440, 0.058, head, col, fs=8.2)
        ax.text(bx + 0.440 / 2, 0.196, body, ha="center", va="center",
                fontsize=7.8, color=S.INK, linespacing=1.75)

    ax.text(0.5, 0.048,
            f"Layer widths and parameter counts read out of torchvision at run time. "
            f"Trained on one {tr['device']}, {tr['precision']} / "
            f"{tr['memory_format']}, batch {tr['batch']}, peak "
            f"{tr['peak_vram_mib']:.0f} MiB VRAM.\nSource: reports/phase2_run_seed*.json.",
            ha="center", va="center", fontsize=7.2, color=S.MUTED, style="italic",
            linespacing=1.7)

    fig.savefig(OUT / "PH1_F02_architecture.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F03 -- training dynamics
# ---------------------------------------------------------------------------
def fig03_training(F: dict) -> None:
    tr = F["training"]
    hist = tr["history"]
    seeds = sorted(hist, key=int)
    warm = tr["warmup_epochs"]

    fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.6))
    fig.suptitle("Training dynamics — three seeds, identical schedule, "
                 "all stopped by early stopping rather than the epoch cap",
                 fontsize=11.0, weight="bold", color=S.INK, y=1.035)

    for ax in axes:
        S.despine(ax)
    # The run histories restart their epoch counter at the stage boundary, so
    # the cumulative axis is the position in the history, not the 'epoch' field.
    cum = {s: list(range(1, len(hist[s]) + 1)) for s in seeds}

    for ax in axes[:2]:
        ax.axvspan(0.5, warm + 0.5, color="#eef1f4", zorder=0, linewidth=0)

    # A: training loss
    ax = axes[0]
    for k, s in enumerate(seeds):
        ax.plot(cum[s], [h["train_loss"] for h in hist[s]],
                color=S.SEED_COLORS[k], linewidth=1.4, label=f"seed {s}")
    ax.set_title("A · Training loss", loc="left")
    ax.set_xlabel("epoch (cumulative)")
    ax.set_ylabel("cross-entropy loss")
    ax.legend(loc="upper right")
    ax.text(warm / 2 + 0.5, ax.get_ylim()[1] * 0.97, "warm-up", ha="center",
            va="top", fontsize=7.4, color=S.MUTED)

    # B: validation macro F1 with the selected epoch marked
    ax = axes[1]
    for k, s in enumerate(seeds):
        vf = [h["val_macro_f1"] for h in hist[s]]
        ax.plot(cum[s], vf, color=S.SEED_COLORS[k], linewidth=1.4)
        be = tr["per_seed"][s]["best_epoch"]
        bv = tr["per_seed"][s]["best_val_macro_f1"]
        ax.plot([be], [bv], marker="o", markersize=6, color=S.SEED_COLORS[k],
                markeredgecolor="white", markeredgewidth=0.9, zorder=5)
    ax.set_title("B · Validation macro F1 (selection criterion)", loc="left")
    ax.set_xlabel("epoch (cumulative)")
    ax.set_ylabel("validation macro F1")
    ax.text(warm / 2 + 0.5, ax.get_ylim()[0] + 0.012, "warm-up", ha="center",
            va="bottom", fontsize=7.4, color=S.MUTED)
    # selected-epoch table, parked clear of the curves
    lines = "\n".join(
        f"seed {s}:  {tr['per_seed'][s]['best_val_macro_f1']:.4f} "
        f"@ epoch {tr['per_seed'][s]['best_epoch']}" for s in seeds)
    ax.text(0.97, 0.05, "selected checkpoint\n" + lines, transform=ax.transAxes,
            ha="right", va="bottom", fontsize=7.2, color=S.INK, linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor=S.GRID, linewidth=0.8))

    # C: per-seed outcome against the pre-registered acceptance band
    ax = axes[2]
    ax.grid(False)
    xs = list(range(len(seeds)))
    vals = [F["baseline"]["per_seed"][s] for s in seeds]
    errs = [[v - F["baseline"]["per_seed_ci"][s][0] for v, s in zip(vals, seeds)],
            [F["baseline"]["per_seed_ci"][s][1] - v for v, s in zip(vals, seeds)]]
    pub, band = F["baseline"]["published"], F["baseline"]["band"]
    ax.axhspan(pub - band, pub + band, color=S.GREEN, alpha=0.13, zorder=0)
    ax.axhline(pub, color=S.GREEN, linewidth=1.2, linestyle="--", zorder=1)
    ax.axhline(F["baseline"]["observed"], color=S.ORANGE, linewidth=1.3, zorder=2)
    ax.errorbar(xs, vals, yerr=errs, fmt="o", markersize=6,
                color=S.BLUE, ecolor=S.MUTED, elinewidth=1.2, capsize=4, zorder=4)
    for x, v in zip(xs, vals):
        ax.annotate(f"{v:.2f}", xy=(x, v), xytext=(10, -9),
                    textcoords="offset points", fontsize=7.6, color=S.INK)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"seed {s}" for s in seeds])
    # a left gutter so the two reference-line labels never cross an error bar
    ax.set_xlim(-1.35, len(seeds) - 0.35)
    ax.set_ylabel("test macro F1 (%)")
    ax.set_title(f"C · Test result vs the pre-registered band "
                 f"[{F['baseline']['verdict']}]", loc="left")
    ax.text(-1.28, pub + band, f"published\n{pub:g} ± {band:g}", fontsize=7.2,
            color=S.GREEN, ha="left", va="top", linespacing=1.5)
    ax.text(-1.28, F["baseline"]["observed"],
            f"seed mean\n{F['baseline']['observed']:.2f} "
            f"(Δ {F['baseline']['delta']:+.2f})",
            fontsize=7.2, color=S.ORANGE, ha="left", va="top", linespacing=1.5)

    fig.text(0.5, -0.055,
             f"Error bars are patient-clustered bootstrap 95% intervals "
             f"({F['baseline']['n_boot']:,} resamples over "
             f"{F['baseline']['n_test_patients']} test patients). "
             f"Total training time {tr['total_train_min']:.0f} min on a single "
             f"{tr['device']}. Sources: reports/phase2_run_seed*.json, "
             f"reports/phase2_test_metrics.json.",
             ha="center", fontsize=7.0, color=S.MUTED, style="italic")

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F03_training_dynamics.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F04 -- the seven-phase workflow and where Phase-I sits
# ---------------------------------------------------------------------------
def fig04_workflow(F: dict) -> None:
    phases = [
        ("PHASE 0", "Data provenance\n& integrity gate",
         f"{F['corpus']['n_images']:,} images audited\n8 criteria · verdict PROCEED", True),
        ("PHASE 1", "Literature review\n& problem framing",
         f"PRISMA 2020 · {F['prisma']['unique']:,} records\n"
         f"{F['prisma']['included']} studies included", True),
        ("PHASE 2", "Baseline\nreproduction",
         f"ConvNeXt-Tiny, 3 seeds\nmacro F1 {F['baseline']['observed']:.2f} — "
         f"{F['baseline']['verdict']}", True),
        ("PHASE 3", "Agreement-stratified\nevaluation",
         f"{F['strata']['n_test_total']:,}-image test split\n"
         f"4 strata · RQ1 answered", True),
        ("PHASE 4", "Soft-label &\nuncertainty training",
         "5 target constructions\nRQ2 · RQ3 · RQ4", False),
        ("PHASE 5", "External\nvalidation",
         "HyperKvasir + GastroVision\nno adaptation", False),
        ("PHASE 6-7", "Explainability,\nsynthesis & defence",
         "human comparator\nthesis and defence", False),
    ]

    fig, ax = plt.subplots(figsize=(13.8, 4.7))
    _blank(ax)

    ax.text(0.5, 0.965,
            "Seven gated phases; each one may not start until the previous "
            "phase's validation criterion is met",
            ha="center", va="center", fontsize=11.5, weight="bold", color=S.INK)

    n = len(phases)
    gap, x0, x1 = 0.012, 0.008, 0.992
    w = ((x1 - x0) - gap * (n - 1)) / n
    y, h, hh = 0.480, 0.400, 0.062

    for i, (tag, name, detail, in_scope) in enumerate(phases):
        x = x0 + i * (w + gap)
        col = S.BLUE if in_scope else S.MUTED
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.003,rounding_size=0.012",
            facecolor="white" if in_scope else "#f6f7f8", edgecolor=col,
            linewidth=1.5 if in_scope else 1.0, zorder=2,
            linestyle="-" if in_scope else (0, (3, 2))))
        ax.add_patch(FancyBboxPatch(
            (x, y + h - hh), w, hh,
            boxstyle="round,pad=0.003,rounding_size=0.012",
            facecolor=col, edgecolor=col, linewidth=1.2, zorder=3))
        ax.text(x + w / 2, y + h - hh / 2, tag, ha="center", va="center",
                fontsize=8.0, color="white", weight="bold", zorder=4)
        ax.text(x + w / 2, y + h - hh - 0.078, name, ha="center", va="center",
                fontsize=8.2, color=S.INK if in_scope else S.MUTED,
                weight="bold", zorder=4, linespacing=1.6)
        ax.text(x + w / 2, y + 0.070, detail, ha="center", va="center",
                fontsize=7.2, color=S.INK if in_scope else S.MUTED, zorder=4,
                linespacing=1.7)
        if i < n - 1:
            _arrow(ax, x + w + 0.0015, y + h / 2, x + w + gap - 0.0015, y + h / 2,
                   color=S.MUTED)

    # Phase-I scope bracket
    scope_x1 = x0 + 4 * w + 3 * gap
    ax.plot([x0, scope_x1], [0.428, 0.428], color=S.BLUE, linewidth=2.0)
    ax.text((x0 + scope_x1) / 2, 0.395,
            "REPORTED IN THIS PHASE-I PROGRESS REPORT\n"
            "problem identification · literature review · gap analysis · data "
            "collection · pre-processing · a trained and tested baseline",
            ha="center", va="top", fontsize=8.2, color=S.BLUE, weight="bold",
            linespacing=1.8)

    ax.plot([scope_x1 + gap, x0 + n * w + (n - 1) * gap], [0.428, 0.428],
            color=S.MUTED, linewidth=1.3, linestyle=(0, (3, 2)))
    ax.text((scope_x1 + gap + x0 + n * w + (n - 1) * gap) / 2, 0.395,
            "Executed after Phase-I and\nreported at the Final Defence",
            ha="center", va="top", fontsize=8.0, color=S.MUTED, linespacing=1.8)

    ax.text(0.5, 0.130,
            "Every phase freezes its hypotheses, primary endpoint and verdict rules in a "
            "pre-registration file before any model is run,\nand every reported quantity "
            "regenerates from committed scripts and versioned JSON artefacts.",
            ha="center", va="center", fontsize=8.2, color=S.INK, linespacing=1.8,
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#f4f6f8",
                      edgecolor=S.GRID, linewidth=0.8))

    fig.savefig(OUT / "PH1_F04_workflow.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F05 -- the wall x station label space
# ---------------------------------------------------------------------------
def fig05_label_space(F: dict) -> None:
    st = F["structure"]
    tax = {t["code"]: t for t in st["taxonomy"]}
    walls = ["G", "A", "L", "P"]
    stations = [1, 2, 3, 4, 5, 6]

    # The released station names are long enough to collide at grid pitch, so
    # each is given an explicit two-line short form.
    short_station = {
        1: "Antrum", 2: "Distal\nbody", 3: "Upper-mid\nbody",
        4: "Retroflex\ncardia", 5: "Retroflex\nlesser curv.",
        6: "Final\nview",
    }

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 4.8),
                             gridspec_kw={"width_ratios": [1.62, 1]})
    fig.suptitle("The label space is a (wall × station) grid — the project's main "
                 "analytical lever, and the dataset descriptor does not treat it as one",
                 fontsize=11.5, weight="bold", color=S.INK, y=1.0)

    # --- left: the grid ---------------------------------------------------
    ax = axes[0]
    _blank(ax)
    cw, ch = 0.133, 0.152
    ox, oy = 0.200, 0.240
    for j, s in enumerate(stations):
        ax.text(ox + j * cw + cw / 2, oy + 4 * ch + 0.088,
                f"S{s}", ha="center", va="center", fontsize=8.8,
                weight="bold", color=S.INK)
        ax.text(ox + j * cw + cw / 2, oy + 4 * ch + 0.035,
                short_station[s], ha="center", va="center", fontsize=6.5,
                color=S.MUTED, linespacing=1.45)
    for i, wl in enumerate(walls):
        y = oy + (3 - i) * ch
        ax.text(ox - 0.016, y + ch / 2, wl, ha="right", va="center",
                fontsize=8.8, weight="bold", color=S.INK)
        ax.text(ox - 0.040, y + ch / 2, st["walls"][wl].replace(" ", "\n"),
                ha="right", va="center", fontsize=6.6, color=S.MUTED,
                linespacing=1.45)
        for j, s in enumerate(stations):
            code = f"{wl}{s}"
            x = ox + j * cw
            exists = code in tax
            ax.add_patch(FancyBboxPatch(
                (x + 0.006, y + 0.008), cw - 0.012, ch - 0.016,
                boxstyle="round,pad=0.002,rounding_size=0.010",
                facecolor=S.BLUE if exists else "white",
                edgecolor=S.BLUE if exists else S.GRID,
                linewidth=1.1, zorder=2))
            ax.text(x + cw / 2, y + ch / 2, code if exists else "—",
                    ha="center", va="center", fontsize=9.2,
                    color="white" if exists else S.GRID,
                    weight="bold", zorder=3)

    ax.add_patch(FancyBboxPatch(
        (ox, 0.105), cw * 1.95, 0.082,
        boxstyle="round,pad=0.002,rounding_size=0.010",
        facecolor=S.MUTED, edgecolor=S.MUTED, linewidth=1.1, zorder=2))
    ax.text(ox + cw * 0.975, 0.146, "OTHERCLASS", ha="center", va="center",
            fontsize=8.0, color="white", weight="bold", zorder=3)
    ax.text(ox + cw * 2.10, 0.146,
            "image unsuitable for assessment — a quality judgement,\n"
            f"not an anatomical one. Per-annotator rate spans "
            f"{min(st['otherclass_rate'].values()):.2f}%–"
            f"{max(st['otherclass_rate'].values()):.2f}%, a "
            f"{st['otherclass_spread']:.0f}× spread.",
            ha="left", va="center", fontsize=7.2, color=S.INK, linespacing=1.7)

    ax.text(0.0, 0.028,
            f"{F['corpus']['n_classes']} classes = 22 landmarks (4 walls × 6 "
            f"stations, minus the 2 combinations the protocol does not photograph) "
            f"+ OTHERCLASS.",
            ha="left", va="center", fontsize=7.4, color=S.MUTED)
    ax.set_title("A · The Systematic Screening label space", loc="left",
                 fontsize=9.5, pad=12)

    # --- right: collapsing one axis at a time -----------------------------
    ax = axes[1]
    S.despine(ax)
    labels = [f"Full\n({F['corpus']['n_classes']} classes)", "Station only\n(7)",
              "Wall only\n(5)"]
    kap = [st["kappa_full"], st["kappa_station"], st["kappa_wall"]]
    una = [st["unan_full"] / 100, st["unan_station"] / 100, st["unan_wall"] / 100]
    xs = range(3)
    bw = 0.36
    b1 = ax.bar([x - bw / 2 for x in xs], kap, bw, color=S.BLUE,
                label="mean pairwise $\\kappa$")
    b2 = ax.bar([x + bw / 2 for x in xs], una, bw, color=S.GREEN,
                label="4/4 unanimity rate")
    for b, v in zip(b1, kap):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.020, f"{v:.3f}",
                ha="center", fontsize=7.8, color=S.INK)
    for b, v in zip(b2, una):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.020, f"{v * 100:.1f}%",
                ha="center", fontsize=7.8, color=S.INK)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=8.2)
    ax.set_ylim(0, 1.30)
    ax.set_ylabel("value")
    ax.legend(loc="upper center", ncol=2, fontsize=7.8,
              bbox_to_anchor=(0.5, 1.0))
    ax.set_title("B · Collapsing the station recovers agreement;\ncollapsing the "
                 "wall recovers almost none", loc="left", fontsize=9.5,
                 linespacing=1.5)

    fig.text(0.5, -0.035,
             "Endoscopists agree on how deep the scope is and disagree about which "
             "way it points — so the wall axis carries almost all the ambiguity.  "
             "Source: reports/gastrohun_structure.json.",
             ha="center", fontsize=7.8, color=S.MUTED)

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F05_label_space.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F06 -- annotator agreement
# ---------------------------------------------------------------------------
def fig06_agreement(F: dict) -> None:
    ag = F["agreement"]
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.0),
                             gridspec_kw={"width_ratios": [1, 1, 1.15]})
    fig.suptitle("Expert agreement is the object of study, not a nuisance: "
                 f"only {ag['unanimous_pct']:.1f}% of the corpus is unanimous",
                 fontsize=11.5, weight="bold", color=S.INK, y=1.03)

    # A: the cascade
    ax = axes[0]
    S.despine(ax)
    rows = [("All images", ag["tiers"]["all_images"], S.MUTED),
            ("≥3/4 agree", ag["tiers"]["triple_agreement_3of4"], S.BLUE),
            ("Team B agree", ag["tiers"]["G_team_agreement"], S.BLUE),
            ("Team A agree", ag["tiers"]["FG_team_agreement"], S.BLUE),
            ("4/4 unanimous", ag["tiers"]["complete_agreement_4of4"], S.ORANGE)]
    ys = range(len(rows))
    ax.barh(list(ys), [r[1] for r in rows], color=[r[2] for r in rows],
            height=0.62)
    for i, (lab, v, _) in enumerate(rows):
        ax.text(v + 120, i, f"{v:,}  ({v / ag['tiers']['all_images'] * 100:.1f}%)",
                va="center", fontsize=7.6, color=S.INK)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.0)
    ax.invert_yaxis()
    ax.set_xlim(0, ag["tiers"]["all_images"] * 1.42)
    ax.set_xlabel("images")
    ax.set_title("A · The agreement cascade", loc="left", fontsize=9.5)

    # B: vote patterns
    ax = axes[1]
    S.despine(ax)
    order = ["4", "3-1", "2-1-1", "2-2", "1-1-1-1"]
    vals = [ag["vote_patterns"][k] for k in order]
    cols = [S.ORANGE, S.BLUE, S.GREEN, S.PURPLE, S.MUTED]
    bars = ax.bar(range(len(order)), vals, color=cols, width=0.66)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 90,
                f"{v:,}\n{v / ag['tiers']['all_images'] * 100:.2f}%",
                ha="center", fontsize=7.4, color=S.INK, linespacing=1.5)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(["4–0\nunanimous", "3–1\nmajority", "2–1–1\nplurality",
                        "2–2\ntied", "1–1–1–1\ndispersed"], fontsize=7.6)
    ax.set_ylim(0, max(vals) * 1.30)
    ax.set_ylabel("images")
    ax.set_title(f"B · Vote patterns — {ag['n_no_majority']:,} images "
                 f"({ag['pct_no_majority']:.2f}%)\nadmit no majority under any rule",
                 loc="left", fontsize=9.5, linespacing=1.5)

    # C: pairwise kappa
    ax = axes[2]
    S.despine(ax)
    pk = sorted(ag["pairwise"].items(), key=lambda kv: kv[1])
    labs = [k.replace("-", " – ") for k, _ in pk]
    vals = [v for _, v in pk]
    cols = [S.ORANGE if ag["pairwise_within"][k] else S.BLUE for k, _ in pk]
    ys = range(len(pk))
    lo = [ag["pairwise_ci"][k][0] for k, _ in pk]
    hi = [ag["pairwise_ci"][k][1] for k, _ in pk]
    ax.barh(list(ys), vals, color=cols, height=0.58,
            xerr=[[v - l for v, l in zip(vals, lo)],
                  [h - v for v, h in zip(vals, hi)]],
            error_kw=dict(ecolor=S.INK, elinewidth=1.0, capsize=3))
    for i, v in enumerate(vals):
        ax.text(v + 0.022, i, f"{v:.4f}", va="center", fontsize=7.6, color=S.INK)
    ax.set_yticks(list(ys))
    ax.set_yticklabels(labs, fontsize=8.0)
    ax.set_xlim(0.60, 0.90)
    ax.set_xlabel("Cohen's $\\kappa$ (95% CI)")
    ax.set_title("C · Seniority does not predict agreement", loc="left",
                 fontsize=9.5)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=S.ORANGE, label="within team"),
                       Patch(facecolor=S.BLUE, label="between teams")],
              loc="lower right", fontsize=7.6)

    fig.text(0.5, -0.085,
             f"Fleiss' $\\kappa$ = {ag['fleiss']:.4f}, Krippendorff's $\\alpha$ = "
             f"{ag['alpha']:.4f} and Gwet's AC1 = {ag['ac1']:.4f} coincide because "
             f"the screening protocol keeps the class marginal near-uniform, so the "
             f"kappa paradox does not arise here.\nEach resident agrees more closely "
             f"with either gastroenterologist than with the other resident. "
             f"Source: reports/gastrohun_agreement.json.",
             ha="center", fontsize=7.6, color=S.MUTED, linespacing=1.7)

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F06_agreement.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F07 -- disagreement is anatomically structured
# ---------------------------------------------------------------------------
def fig07_disagreement(F: dict) -> None:
    st = F["structure"]
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 4.0),
                             gridspec_kw={"width_ratios": [1.25, 1]})
    fig.suptitle(f"Disagreement is anatomically structured, not random noise — "
                 f"which is what makes it modellable",
                 fontsize=11.5, weight="bold", color=S.INK, y=1.03)

    # A: decomposition
    ax = axes[0]
    S.despine(ax)
    items = [("Same station,\ndifferent wall", "same_station_different_wall", S.ORANGE),
             ("Landmark vs\nOTHERCLASS", "landmark_vs_OTHERCLASS", S.PURPLE),
             ("Same wall,\ndifferent station", "same_wall_different_station", S.YELLOW),
             ("Both differ", "different_wall_and_station", S.MUTED)]
    ys = range(len(items))
    vals = [st["decomp_pct"][k] for _, k, _ in items]
    ax.barh(list(ys), vals, color=[c for _, _, c in items], height=0.60)
    for i, (lab, key, _) in enumerate(items):
        ax.text(vals[i] + 0.9, i, f"{vals[i]:.2f}%  ({st['decomp'][key]:,})",
                va="center", fontsize=8.0, color=S.INK, weight="bold")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([lab for lab, _, _ in items], fontsize=8.2)
    ax.invert_yaxis()
    ax.set_xlim(0, 68)
    ax.set_xlabel("% of all pairwise disagreement events")
    ax.set_title(f"A · Decomposition of "
                 f"{F['agreement']['n_disagreement_events']:,} disagreement events",
                 loc="left", fontsize=9.5)

    # B: which walls get confused
    ax = axes[1]
    S.despine(ax)
    pairs = sorted(st["wall_confusion_pairs"].items(), key=lambda kv: -kv[1])
    adjacent = {"A-L", "L-P", "A-G", "G-P"}   # circumferentially neighbouring
    labs = [p.replace("-", "–") for p, _ in pairs]
    vals = [v for _, v in pairs]
    cols = [S.ORANGE if p in adjacent else S.BLUE for p, _ in pairs]
    bars = ax.bar(range(len(pairs)), vals, color=cols, width=0.66)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 38, f"{v:,}",
                ha="center", fontsize=7.6, color=S.INK)
    ax.set_xticks(range(len(pairs)))
    ax.set_xticklabels(labs, fontsize=8.4)
    ax.set_ylim(0, max(vals) * 1.20)
    ax.set_ylabel("disagreement events")
    adj_share = 100 * sum(v for p, v in pairs if p in adjacent) / sum(vals)
    ax.set_title(f"B · {adj_share:.1f}% of wall confusions involve\n"
                 f"circumferentially adjacent walls", loc="left", fontsize=9.5,
                 linespacing=1.5)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=S.ORANGE, label="adjacent walls"),
                       Patch(facecolor=S.BLUE, label="opposite walls")],
              loc="upper right", fontsize=7.8)

    fig.text(0.5, -0.095,
             "Half of all conflicts place two experts on different walls of the same "
             "station, and those walls are almost always neighbours.\n"
             "Disagreement respects the anatomy. Source: reports/gastrohun_structure.json.",
             ha="center", fontsize=7.8, color=S.MUTED, linespacing=1.7)

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F07_disagreement_structure.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F08 -- PRISMA 2020 flow and the included set
# ---------------------------------------------------------------------------
def fig08_prisma(F: dict) -> None:
    P = F["prisma"]
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 4.7),
                             gridspec_kw={"width_ratios": [1, 1.05]})
    fig.suptitle(f"PRISMA 2020 systematic review — {P['n_themes']} themed queries, "
                 f"{P['included']} studies included",
                 fontsize=11.5, weight="bold", color=S.INK, y=1.0)

    # A: the flow
    ax = axes[0]
    _blank(ax)
    steps = [
        (f"Records identified\nacross {P['n_themes']} themed PubMed queries",
         f"n = {P['identified']:,}", S.BLUE),
        (f"Records after duplicates removed",
         f"n = {P['unique']:,}   (−{P['duplicates']})", S.BLUE),
        ("Records screened on title and abstract",
         f"n = {P['screened']:,}", S.BLUE),
        ("Records passing eligibility screen",
         f"n = {P['passing']:,}   (−{P['excluded']})", S.GREEN),
        (f"Studies included in the review\n"
         f"{P['included_db']} database + {P['included_hand']} hand-searched",
         f"n = {P['included']}", S.ORANGE),
    ]
    bh, bgap = 0.132, 0.050
    top = 0.945
    for i, (label, count, col) in enumerate(steps):
        y = top - i * (bh + bgap) - bh
        ax.add_patch(FancyBboxPatch(
            (0.045, y), 0.80, bh,
            boxstyle="round,pad=0.004,rounding_size=0.012",
            facecolor="white", edgecolor=col, linewidth=1.5, zorder=2))
        ax.text(0.075, y + bh / 2, label, ha="left", va="center",
                fontsize=8.0, color=S.INK, linespacing=1.6, zorder=3)
        ax.text(0.825, y + bh / 2, count, ha="right", va="center",
                fontsize=8.6, color=col, weight="bold", zorder=3)
        if i < len(steps) - 1:
            _arrow(ax, 0.445, y - 0.004, 0.445, y - bgap + 0.004)

    ax.set_title("A · Identification, screening and inclusion", loc="left",
                 fontsize=9.5)

    # B: what the included set is made of
    ax = axes[1]
    S.despine(ax)
    tc = sorted(P["included_by_theme"].items(), key=lambda kv: kv[1])
    labs = [t.split(" ", 1)[1] for t, _ in tc]
    vals = [v for _, v in tc]
    cols = [S.BLUE, S.CYAN, S.GREEN, S.YELLOW, S.PURPLE, S.PINK, S.ORANGE]
    ax.barh(range(len(tc)), vals, color=cols[:len(tc)], height=0.62)
    for i, v in enumerate(vals):
        ax.text(v + 0.25, i, str(v), va="center", fontsize=8.0, weight="bold",
                color=S.INK)
    ax.set_yticks(range(len(tc)))
    ax.set_yticklabels(labs, fontsize=8.0)
    ax.set_xlim(0, max(vals) * 1.22)
    ax.set_xlabel("included studies")
    ax.set_title(f"B · Composition of the {P['n_included_rows']} included studies — "
                 f"{P['pct_since_2020']:.0f}% published 2020 or later",
                 loc="left", fontsize=9.5)

    fig.text(0.5, -0.035,
             f"Exclusions at screening ({P['excluded']}) were dominated by "
             f"{', '.join(f'{k.split(chr(40))[0].strip().lower()} ({v})' for k, v in list(P['exclusion_reasons'].items())[:3])}. "
             f"Search window {P['date_from']}–{P['date_to']}. "
             f"Source: literature_v2/prisma_counts.json, extraction_table.csv.",
             ha="center", fontsize=7.6, color=S.MUTED, linespacing=1.7)

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F08_prisma.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F09 -- the gap analysis
# ---------------------------------------------------------------------------
def fig09_gap(F: dict) -> None:
    ag, st = F["agreement"], F["structure"]
    fig, ax = plt.subplots(figsize=(13.8, 5.4))
    _blank(ax)

    ax.text(0.5, 0.965,
            "Gap analysis — what the literature reports, what it omits, and what "
            "this project measures instead",
            ha="center", va="center", fontsize=11.5, weight="bold", color=S.INK)

    gaps = [
        ("GAP 1", "Evaluation is conditioned\non expert unanimity",
         f"Published macro F1 of {F['baseline']['published']:g}–88 for this task is measured "
         f"only on frames all annotators agreed on.\n"
         f"On this corpus that is {ag['unanimous_pct']:.1f}% of the data; the other "
         f"{ag['contested_pct']:.1f}% ({ag['contested_n']:,} images) is removed before scoring.",
         "Report performance separately for every agreement stratum, with "
         "patient-clustered intervals."),
        ("GAP 2", "Annotator disagreement is\ndiscarded rather than used",
         f"Per-annotator labels are rarely released, so the vote distribution is collapsed to one "
         f"label at ingest.\nHere {st['decomp_pct']['same_station_different_wall']:.2f}% of the "
         f"{ag['n_disagreement_events']:,} conflicts are same-station different-wall — a "
         f"structured signal, not noise.",
         "Train on the full four-vote distribution and test it against a "
         "matched label-smoothing control."),
        ("GAP 3", "Calibration is reported\nrarely, and never by stratum",
         "Systematic reviews of diagnostic deep learning find calibration and external "
         "validation routinely omitted.\nNothing establishes whether confidence estimated on "
         "unanimous frames stays trustworthy on contested ones.",
         "Treat expected calibration error by stratum as a primary endpoint, "
         "not an optional extra."),
    ]

    y0, bh, bgap = 0.690, 0.198, 0.036
    for i, (tag, title, evidence, response) in enumerate(gaps):
        y = y0 - i * (bh + bgap)
        ax.add_patch(FancyBboxPatch(
            (0.010, y), 0.980, bh,
            boxstyle="round,pad=0.004,rounding_size=0.012",
            facecolor="white", edgecolor=S.GRID, linewidth=1.2, zorder=2))
        ax.add_patch(FancyBboxPatch(
            (0.010, y), 0.072, bh,
            boxstyle="round,pad=0.004,rounding_size=0.012",
            facecolor=S.ORANGE, edgecolor=S.ORANGE, linewidth=1.2, zorder=3))
        ax.text(0.046, y + bh / 2, tag, ha="center", va="center", fontsize=8.6,
                color="white", weight="bold", zorder=4, rotation=0)
        ax.text(0.098, y + bh / 2, title, ha="left", va="center", fontsize=8.8,
                color=S.INK, weight="bold", zorder=4, linespacing=1.6)
        ax.text(0.300, y + bh * 0.68, evidence, ha="left", va="center",
                fontsize=7.5, color=S.INK, zorder=4, linespacing=1.7)
        ax.text(0.300, y + bh * 0.215, "→  " + response, ha="left", va="center",
                fontsize=7.6, color=S.BLUE, zorder=4, weight="bold",
                linespacing=1.6)

    ax.text(0.5, 0.088,
            "The contribution is diagnostic rather than architectural: it measures which "
            "part of the task current accuracy figures describe,\nand what a deployed "
            "system would face on exactly the frames clinicians themselves find ambiguous.",
            ha="center", va="center", fontsize=8.6, color=S.INK, linespacing=1.8,
            bbox=dict(boxstyle="round,pad=0.65", facecolor="#f4f6f8",
                      edgecolor=S.GRID, linewidth=0.8))

    fig.savefig(OUT / "PH1_F09_gap_analysis.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F10 -- the stratified result, raw and ceiling-normalised
# ---------------------------------------------------------------------------
def fig10_stratified(F: dict) -> None:
    S_ = F["strata"]
    ce = F["ceiling"]
    order = S_["order"]
    nice = {"S-unanimous": "4/4\nunanimous", "S-majority": "3/4\nmajority",
            "S-plurality": "2–1–1\nplurality", "S-no-majority": "2–2 / 1–1–1–1\npooled"}

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 4.4))
    fig.suptitle("Performance falls sharply as expert agreement falls — but so does "
                 "the attainable ceiling, and the two must be separated",
                 fontsize=11.5, weight="bold", color=S.INK, y=1.01)

    xs = list(range(len(order)))

    # A: raw
    ax = axes[0]
    S.despine(ax)
    obs = [S_["f1"][k] for k in order]
    ceil = [ce["oracle_f1"][k] for k in order]
    ax.plot(xs, ceil, marker="s", markersize=6, linewidth=1.6, linestyle="--",
            color=S.MUTED, label="attainable ceiling (modal-vote oracle)")
    ax.plot(xs, obs, marker="o", markersize=7, linewidth=2.0, color=S.BLUE,
            label="model, annotator-marginalized macro F1")
    ax.fill_between(xs, obs, ceil, color=S.BLUE, alpha=0.07)
    for x, v in zip(xs, obs):
        ax.annotate(f"{v:.2f}", xy=(x, v), xytext=(0, -16),
                    textcoords="offset points", ha="center", fontsize=8.0,
                    color=S.BLUE, weight="bold")
    for x, v in zip(xs, ceil):
        ax.annotate(f"{v:.2f}", xy=(x, v), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=8.0,
                    color=S.MUTED)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{nice[k]}\nn={S_['n'][k]}" for k in order], fontsize=7.8)
    ax.set_ylim(0, 112)
    ax.set_ylabel("macro F1 (%)")
    ax.set_title("A · Observed performance against what is attainable", loc="left",
                 fontsize=9.5)
    ax.legend(loc="upper right", fontsize=7.6)

    # B: the pre-registered gaps
    ax = axes[1]
    S.despine(ax)
    want = [("S-unanimous - S-majority", "4/4 − 3/4"),
            ("S-unanimous - S-plurality", "4/4 − 2–1–1"),
            ("S-unanimous - S-no-majority", "4/4 − no majority")]
    ys = list(range(len(want)))
    for i, (key, lab) in enumerate(want):
        g = ce["gaps"][f"{key} [ceiling_normalised]"]
        lo, hi = g["ci95"]
        col = S.BLUE if g["excludes_zero"] else S.ORANGE
        ax.plot([lo, hi], [i, i], color=col, linewidth=2.4, zorder=3)
        ax.plot([lo, lo], [i - 0.09, i + 0.09], color=col, linewidth=2.0, zorder=3)
        ax.plot([hi, hi], [i - 0.09, i + 0.09], color=col, linewidth=2.0, zorder=3)
        ax.plot([g["mean"]], [i], marker="o", markersize=8, color=col, zorder=4)
        ax.text(hi + 1.4, i, f"{g['mean']:.2f}  [{lo:.2f}, {hi:.2f}]",
                va="center", fontsize=8.0, color=S.INK)
    ax.axvline(0, color=S.INK, linewidth=1.1, zorder=2)
    ax.axvline(S_["arch_benchmark"], color=S.GREEN, linewidth=1.3,
               linestyle="--", zorder=2)
    from matplotlib.transforms import blended_transform_factory
    ax.text(S_["arch_benchmark"] + 0.9, 0.97,
            f"between-architecture\nbenchmark = {S_['arch_benchmark']:g} pts",
            transform=blended_transform_factory(ax.transData, ax.transAxes),
            fontsize=7.4, color=S.GREEN, va="top", linespacing=1.5)
    ax.set_yticks(ys)
    ax.set_yticklabels([lab for _, lab in want], fontsize=8.4)
    ax.invert_yaxis()
    ax.set_xlim(-9, 52)
    ax.set_xlabel("ceiling-normalised gap in macro F1 (points, 95% CI)")
    ax.set_title("B · Pre-registered contrasts, patient-clustered bootstrap",
                 loc="left", fontsize=9.5)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=S.BLUE, label="interval excludes zero"),
                       Patch(facecolor=S.ORANGE, label="interval contains zero")],
              loc="lower right", fontsize=7.6)

    fig.text(0.5, -0.055,
             f"Raw macro F1 falls {S_['f1'][order[0]]:.2f} → "
             f"{S_['f1'][order[-1]]:.2f}, a gap of {S_['gap']:.2f} points against a "
             f"{S_['arch_benchmark']:g}-point between-architecture benchmark. Holding the "
             f"attainable ceiling constant, two of the three contrasts remain resolvable "
             f"and one does not.\nSources: reports/phase3_stratified_metrics.json, "
             f"reports/phase3b_ceiling_gaps.json.",
             ha="center", fontsize=7.6, color=S.MUTED, linespacing=1.7)

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F10_stratified_result.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F11 -- calibration by stratum
# ---------------------------------------------------------------------------
def fig11_calibration(F: dict) -> None:
    cal, S_ = F["calibration"], F["strata"]
    order = S_["order"]
    nice = {"S-unanimous": "4/4\nunanimous", "S-majority": "3/4\nmajority",
            "S-plurality": "2–1–1\nplurality", "S-no-majority": "2–2 / 1–1–1–1\npooled"}

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 4.2))
    fig.suptitle("Confidence degrades further and faster than discrimination — "
                 "the finding that survives every later phase",
                 fontsize=11.5, weight="bold", color=S.INK, y=1.02)

    xs = list(range(len(order)))

    # A: confidence vs accuracy
    ax = axes[0]
    S.despine(ax)
    conf = [cal["confidence"][k] for k in order]
    acc = [cal["expected_accuracy"][k] for k in order]
    ax.plot(xs, conf, marker="o", markersize=7, linewidth=2.0, color=S.ORANGE,
            label="mean predicted confidence")
    ax.plot(xs, acc, marker="s", markersize=6.5, linewidth=2.0, color=S.BLUE,
            label="expected accuracy")
    ax.fill_between(xs, acc, conf, color=S.ORANGE, alpha=0.12)
    for x, k in zip(xs, order):
        ax.annotate(f"{cal['overconfidence'][k]:.1f} pts",
                    xy=(x, (conf[x] + acc[x]) / 2), xytext=(0, 0),
                    textcoords="offset points", ha="center", va="center",
                    fontsize=7.8, color=S.INK, weight="bold",
                    bbox=dict(boxstyle="round,pad=0.28", facecolor="white",
                              edgecolor=S.GRID, linewidth=0.7))
    ax.set_xticks(xs)
    ax.set_xticklabels([nice[k] for k in order], fontsize=7.8)
    ax.set_ylim(0, 108)
    # the leftmost overconfidence badge sits on the first stratum, so the axis
    # needs a margin or the box is clipped by the spine
    ax.set_xlim(-0.35, len(order) - 0.65)
    ax.set_ylabel("%")
    ax.set_title("A · Confidence barely moves while accuracy collapses",
                 loc="left", fontsize=9.5)
    ax.legend(loc="lower left", fontsize=7.8)

    # B: ECE
    ax = axes[1]
    S.despine(ax)
    ece = [cal["ece"][k] for k in order]
    cols = [S.GREEN, S.YELLOW, S.ORANGE, S.RED]
    bars = ax.bar(xs, ece, color=cols, width=0.62)
    for b, v in zip(bars, ece):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.4, f"{v:.2f}%",
                ha="center", fontsize=8.4, color=S.INK, weight="bold")
    ax.set_xticks(xs)
    ax.set_xticklabels([nice[k] for k in order], fontsize=7.8)
    ax.set_ylim(0, max(ece) * 1.24)
    ax.set_ylabel("expected calibration error (%)")
    ax.set_title("B · ECE rises "
                 f"{cal['ece'][order[0]]:.2f}% → {max(ece):.2f}%",
                 loc="left", fontsize=9.5)

    fig.text(0.5, -0.06,
             f"Mean confidence falls only "
             f"{cal['confidence'][order[0]] - cal['confidence'][order[2]]:.2f} points "
             f"between the unanimous and plurality strata while expected accuracy falls "
             f"{cal['expected_accuracy'][order[0]] - cal['expected_accuracy'][order[2]]:.2f}. "
             f"A deployed model would be assuredly wrong exactly where four experts "
             f"could not agree.\nSource: reports/phase3b_calibration.json.",
             ha="center", fontsize=7.6, color=S.MUTED, linespacing=1.7)

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F11_calibration.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F12 -- the data-integrity gate
# ---------------------------------------------------------------------------
def fig12_integrity(F: dict) -> None:
    c, ct, ag, st = (F["corpus"], F["contamination"], F["agreement"],
                     F["structure"])
    gates = [
        ("G1", "Provenance, ethics, licence", "PASS",
         "peer-reviewed descriptor; ethics CEI-2019-06-10; consent; CC BY 4.0"),
        ("G2", "Physical integrity", "PASS",
         f"{c['n_decoded']:,}/{c['n_images']:,} decoded · {c['n_missing']} missing · "
         f"{c['n_orphan']} orphan · {c['n_corrupt']} corrupt"),
        ("G3", "Duplication & contamination", "PASS",
         f"{c['n_exact_dupes']} exact duplicates; "
         f"{ct['n_pairs_scanned']:,}-pair perceptual scan → "
         f"{ct['reassessment']['n_confirmed_by_calibrated_rule']} cross-split duplicates"),
        ("G4", "Label architecture", "PASS",
         f"{c['n_annotators']} annotators retained separately across "
         f"{c['n_classes']} classes"),
        ("G5", "Agreement quantified", "PASS",
         f"Fleiss $\\kappa$ = {ag['fleiss']:.4f}; all 6 pairwise $\\kappa$ with "
         f"patient-clustered CIs"),
        ("G6", "Split integrity", "PASS",
         f"0 patient overlaps; class $\\chi^2$ p = {F['cohort']['class_chi2_p']:.6f}; "
         f"per-patient $\\kappa$ Kruskal–Wallis p = 0.982"),
        ("G7", "Statistical power", "CONDITIONAL",
         f"{st['n_underpowered_classes']}/{c['n_classes']} classes exceed a ±10 pp "
         f"Wilson half-width → per-class claims are exploratory (L1)"),
        ("G8", "Population description", "CONDITIONAL",
         "no age or sex anywhere in the release → no demographic or fairness "
         "claim is possible (L2)"),
    ]

    fig, ax = plt.subplots(figsize=(13.8, 5.6))
    _blank(ax)

    n_pass = sum(1 for g in gates if g[2] == "PASS")
    ax.text(0.5, 0.965,
            f"Phase 0 data-integrity gate — verdict PROCEED "
            f"({n_pass} PASS, {len(gates) - n_pass} CONDITIONAL)",
            ha="center", va="center", fontsize=11.5, weight="bold", color=S.INK)

    bh, bgap, top = 0.078, 0.014, 0.890
    for i, (tag, name, verdict, note) in enumerate(gates):
        y = top - i * (bh + bgap) - bh
        col = S.GREEN if verdict == "PASS" else S.YELLOW
        ax.add_patch(FancyBboxPatch(
            (0.010, y), 0.980, bh,
            boxstyle="round,pad=0.003,rounding_size=0.010",
            facecolor="white", edgecolor=S.GRID, linewidth=1.0, zorder=2))
        ax.add_patch(FancyBboxPatch(
            (0.010, y), 0.048, bh,
            boxstyle="round,pad=0.003,rounding_size=0.010",
            facecolor=col, edgecolor=col, linewidth=1.0, zorder=3))
        ax.text(0.034, y + bh / 2, tag, ha="center", va="center", fontsize=8.4,
                color="white", weight="bold", zorder=4)
        ax.text(0.070, y + bh / 2, name, ha="left", va="center", fontsize=8.4,
                color=S.INK, weight="bold", zorder=4)
        ax.text(0.335, y + bh / 2, verdict, ha="center", va="center",
                fontsize=8.0, color=col, weight="bold", zorder=4)
        ax.text(0.395, y + bh / 2, note, ha="left", va="center", fontsize=7.4,
                color=S.INK, zorder=4)

    ax.text(0.5, 0.070,
            "An uncalibrated threshold is not a measurement. The contamination scan first "
            f"reported {ct['provisional_verified']} cross-split duplicate pairs; "
            f"anchoring the decision rule on a synthetic-duplicate positive control "
            f"({ct['pos_n']:,} pairs)\nand a class-matched null "
            f"({ct['null_n']:,} pairs) reduced that to "
            f"{ct['reassessment']['n_confirmed_by_calibrated_rule']}, and visual audit "
            f"confirmed the flagged pairs were different patients photographed at the "
            f"same landmark.",
            ha="center", va="center", fontsize=8.0, color=S.INK, linespacing=1.8,
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#f4f6f8",
                      edgecolor=S.GRID, linewidth=0.8))

    fig.savefig(OUT / "PH1_F12_integrity_gate.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PH1_F13 -- real sample images with their four annotator labels
# ---------------------------------------------------------------------------
def fig13_samples(F: dict) -> None:
    """A sample-dataset panel that shows the thing the project is about.

    Images are drawn from the official test split by agreement tier, so the
    contrast a reader sees -- four experts agreeing, then three, then two, then
    none -- is the corpus's own, not an illustration of it.
    """
    import csv
    from PIL import Image

    manifest = ROOT / "data" / "phase3_test_manifest.csv"
    images = ROOT / "Labeled Images"
    if not manifest.exists() or not images.exists():
        print("skipping PH1_F13: corpus images or manifest not available")
        return

    with open(manifest, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    tiers = [("S-unanimous", "4/4 unanimous"), ("S-majority", "3/4 majority"),
             ("S-plurality", "2–1–1 plurality"), ("S-tied", "2–2 tied")]
    picked = {}
    for key, _ in tiers:
        cand = [r for r in rows
                if r["tier"] == key
                and "OTHERCLASS" not in {r[f"vote_{i}"] for i in range(4)}
                and (images / r["relpath"]).exists()]
        # deterministic choice: the first two by filename, so the figure is
        # reproducible rather than a lucky draw
        picked[key] = sorted(cand, key=lambda r: r["filename"])[:2]

    ncol, nrow = 4, 2
    fig, axes = plt.subplots(nrow, ncol, figsize=(13.8, 6.4))
    fig.suptitle("Sample images from the corpus, with the label each of the four "
                 "annotators gave",
                 fontsize=11.5, weight="bold", color=S.INK, y=1.005)

    ann = F["corpus"]["annotators"]
    for c, (key, label) in enumerate(tiers):
        for r_i in range(nrow):
            ax = axes[r_i][c]
            ax.axis("off")
            if r_i >= len(picked[key]):
                continue
            rec = picked[key][r_i]
            with Image.open(images / rec["relpath"]) as im:
                ax.imshow(im.convert("RGB"))
            votes = [rec[f"vote_{i}"] for i in range(4)]
            agree = len(set(votes)) == 1
            if r_i == 0:
                ax.set_title(label, fontsize=10, weight="bold",
                             color=S.GREEN if agree else S.ORANGE, pad=8)
            txt = "   ".join(f"{a}:{v}" for a, v in zip(ann, votes))
            ax.text(0.5, -0.045, txt, transform=ax.transAxes, ha="center",
                    va="top", fontsize=7.4, color=S.INK,
                    bbox=dict(boxstyle="round,pad=0.32",
                              facecolor="#eef7f2" if agree else "#fdf1e8",
                              edgecolor=S.GREEN if agree else S.ORANGE,
                              linewidth=0.9))
            # the patient id goes inside the frame; below it, it collided with
            # the next row's vote strip and with the figure footnote
            ax.text(0.018, 0.975, f"patient {rec['patient']}",
                    transform=ax.transAxes, ha="left", va="top",
                    fontsize=6.8, color="white",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#00000088",
                              edgecolor="none"))

    fig.text(0.5, -0.055,
             f"Left to right, agreement falls. Every image is a legitimate frame "
             f"from the screening protocol; the disagreement is about which "
             f"landmark it shows, not about image quality.\n"
             f"Published evaluations on this corpus score only the leftmost "
             f"column. Source: data/phase3_test_manifest.csv.",
             ha="center", fontsize=7.8, color=S.MUTED, linespacing=1.7)

    fig.tight_layout()
    fig.savefig(OUT / "PH1_F13_sample_images.png")
    plt.close(fig)


def main() -> None:
    S.apply()
    # These three are line art rather than data-dense plots, so a higher export
    # resolution costs only file size and buys sharpness at slide scale, where a
    # figure may be projected two metres wide.
    plt.rcParams["savefig.dpi"] = 600
    F = facts()
    fig01_preprocessing(F)
    fig02_architecture(F)
    fig03_training(F)
    fig04_workflow(F)
    fig05_label_space(F)
    fig06_agreement(F)
    fig07_disagreement(F)
    fig08_prisma(F)
    fig09_gap(F)
    fig10_stratified(F)
    fig11_calibration(F)
    fig12_integrity(F)
    fig13_samples(F)
    for p in sorted(OUT.glob("PH1_*.png")):
        print("wrote", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
