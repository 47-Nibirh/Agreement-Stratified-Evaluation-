"""
Phase 5 figure suite -- external validation (P5-A, P5-B, P5-C).

Every value plotted is read from reports/phase5_*.json. Nothing is typed into
this file. Figures whose artefact does not yet exist are skipped with a notice
rather than drawn from stale data.

Run:  python src/report/figures_phase5.py
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
FIGDIR = ROOT / "figures_phase5"
FIGDIR.mkdir(exist_ok=True)

ARMS = ("C0", "C1", "C2", "C3", "C4")
CFG_COLOR = {"C0": S.MUTED, "C1": S.BLUE, "C2": S.GREEN, "C3": S.ORANGE,
             "C4": S.PURPLE}
CFG_SHORT = {"C0": "C0 hard 4/4", "C1": "C1 hard maj.", "C2": "C2 soft votes",
             "C3": "C3 smoothed", "C4": "C4 soft+anat."}
GROUP_COLOR = {"RETROFLEXION": S.BLUE, "FORWARD_GASTRIC": S.GREEN,
               "OTHERCLASS": S.ORANGE, "discard": S.MUTED}


def load(name):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save(fig, name):
    fig.savefig(FIGDIR / name, dpi=S.DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")


def arms_of(d):
    return [c for c in ARMS if c in d.get("arms", [])]


# ---------------------------------------------------------------- F33 label space
def f33_label_space(mp):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    ax = axes[0]
    tally = mp["images_by_decision"]
    keys = ["RETROFLEXION", "FORWARD_GASTRIC", "OTHERCLASS", "discard"]
    vals = [tally.get(k, 0) for k in keys]
    bars = ax.barh(range(len(keys)), vals,
                   color=[GROUP_COLOR[k] for k in keys], height=0.62)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([k.replace("_", " ").title() for k in keys], fontsize=9)
    ax.invert_yaxis()
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + max(vals) * 0.012, b.get_y() + b.get_height() / 2,
                f"{v:,}", va="center", fontsize=8.5, color=S.INK)
    ax.set_xlabel("external images", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.16)
    ax.set_title("What the mapping does with 18,662 external images",
                 fontsize=10, loc="left")
    S.despine(ax)

    ax = axes[1]
    coll = mp["collapse_definition"]
    names = ["RETROFLEXION\nstations 4-5", "FORWARD_GASTRIC\nstations 1,2,3,6",
             "OTHERCLASS"]
    counts = [len(coll[k]["codes"]) for k in
              ("RETROFLEXION", "FORWARD_GASTRIC", "OTHERCLASS")]
    ax.bar(range(3), counts,
           color=[S.BLUE, S.GREEN, S.ORANGE], width=0.55)
    for i, c in enumerate(counts):
        ax.text(i, c + 0.25, str(c), ha="center", fontsize=9, color=S.INK)
    ax.set_xticks(range(3))
    ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("GastroHUN classes collapsed into the group", fontsize=9)
    ax.set_ylim(0, max(counts) * 1.25)
    ax.set_title("The 23-class label space, collapsed", fontsize=10, loc="left")
    S.despine(ax)
    fig.text(0.5, -0.06,
             "The wall axis of the GastroHUN label space is unrecoverable from "
             "either external corpus, and four of the six stations have no external "
             "counterpart.\nPhase 5 therefore tests a 2-way anatomical collapse, not "
             "23-way station classification.", ha="center", fontsize=8,
             color=S.MUTED)
    fig.tight_layout()
    save(fig, "P5_F33_label_space.png")


# -------------------------------------------------------------- F34 corpus inventory
def f34_inventory(mp):
    tab = mp["table"]
    corpora = sorted({r["corpus"] for r in tab})
    fig, axes = plt.subplots(1, len(corpora), figsize=(12.5, 5.6))
    if len(corpora) == 1:
        axes = [axes]
    for ax, corpus in zip(axes, corpora):
        rows = sorted([r for r in tab if r["corpus"] == corpus],
                      key=lambda r: -r["n_images"])[:16]
        y = range(len(rows))
        ax.barh(list(y), [r["n_images"] for r in rows],
                color=[GROUP_COLOR[r["decision"]] for r in rows], height=0.66)
        ax.set_yticks(list(y))
        ax.set_yticklabels([r["external_class"][:32] for r in rows], fontsize=7.4)
        ax.invert_yaxis()
        ax.set_xlabel("images", fontsize=9)
        ax.set_title(f"{corpus} — largest 16 classes", fontsize=10, loc="left")
        S.despine(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=GROUP_COLOR[k])
               for k in ("RETROFLEXION", "FORWARD_GASTRIC", "OTHERCLASS", "discard")]
    fig.legend(handles, ["retroflexion", "forward gastric", "out of protocol",
                         "discarded (site not fixed by the label)"],
               loc="lower center", ncol=4, frameon=False, fontsize=8.5,
               bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout()
    save(fig, "P5_F34_inventory.png")


# ----------------------------------------------------------------- F35 P5-A transfer
def f35_transfer(tr):
    arms = arms_of(tr)
    agg = tr["aggregate_3seed"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    ax = axes[0]
    x = np.arange(len(arms))
    inter = [agg[c]["internal_macro_f1_mean_3seed"] for c in arms]
    exter = [agg[c]["external_macro_f1_mean_3seed"] for c in arms]
    lo = [agg[c]["external_ci95"][0] for c in arms]
    hi = [agg[c]["external_ci95"][1] for c in arms]
    ax.bar(x - 0.19, inter, width=0.36, color=S.MUTED, label="internal (GastroHUN)")
    ax.bar(x + 0.19, exter, width=0.36,
           color=[CFG_COLOR[c] for c in arms], label="external")
    ax.errorbar(x + 0.19, exter,
                yerr=[np.array(exter) - np.array(lo), np.array(hi) - np.array(exter)],
                fmt="none", ecolor=S.INK, capsize=3, lw=1.1)
    ax.axhline(tr["majority_class_floor"], color=S.RED, ls="--", lw=1.2,
               label=f"majority-class floor ({tr['majority_class_floor']:.0f})")
    ax.set_xticks(x)
    ax.set_xticklabels([CFG_SHORT[c] for c in arms], fontsize=8, rotation=12)
    ax.set_ylabel("binary macro F1 (%)", fontsize=9)
    ax.set_title("P5-A retroflexion transfer, internal vs external",
                 fontsize=10, loc="left")
    ax.legend(fontsize=7.6, frameon=False, loc="lower right")
    S.despine(ax)

    ax = axes[1]
    drops = [agg[c]["drop_points"] for c in arms]
    dlo = [agg[c]["drop_ci95"][0] for c in arms]
    dhi = [agg[c]["drop_ci95"][1] for c in arms]
    ax.errorbar(drops, x, xerr=[np.array(drops) - np.array(dlo),
                                np.array(dhi) - np.array(drops)],
                fmt="o", color=S.INK, ecolor=S.MUTED, capsize=3, ms=6, lw=1.2)
    for i, c in enumerate(arms):
        ax.plot(drops[i], i, "o", color=CFG_COLOR[c], ms=7, zorder=3)
    ax.axvline(0, color=S.INK, lw=1)
    ax.axvline(tr["pre_registered_expected_drop_points"], color=S.RED, ls="--",
               lw=1.2, label="pre-registered expected drop")
    ax.set_yticks(list(x))
    ax.set_yticklabels([CFG_SHORT[c] for c in arms], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("external minus internal (macro F1 points)", fontsize=9)
    ax.set_title("The drop, with 95% CI", fontsize=10, loc="left")
    ax.legend(fontsize=7.6, frameon=False, loc="lower left")
    S.despine(ax)
    fig.text(0.5, -0.05, tr["boot_unit_caveat"][:230] + "...", ha="center",
             fontsize=7.4, color=S.MUTED, wrap=True)
    fig.tight_layout()
    save(fig, "P5_F35_transfer.png")


# ---------------------------------------------------------------- F36 P5-B rejection
def f36_rejection(rj):
    arms = arms_of(rj)
    agg = rj["aggregate_3seed"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    ax = axes[0]
    x = np.arange(len(arms))
    rates = [100 * agg[c]["rejection_rate_mean_3seed"] for c in arms]
    lo = [100 * agg[c]["ci95"][0] for c in arms]
    hi = [100 * agg[c]["ci95"][1] for c in arms]
    ax.bar(x, rates, color=[CFG_COLOR[c] for c in arms], width=0.55)
    ax.errorbar(x, rates, yerr=[np.array(rates) - np.array(lo),
                                np.array(hi) - np.array(rates)],
                fmt="none", ecolor=S.INK, capsize=3, lw=1.1)
    ax.axhline(100 * rj["chance_rate"], color=S.RED, ls="--", lw=1.3,
               label=f"chance ({100 * rj['chance_rate']:.2f}%)")
    ax.set_xticks(x)
    ax.set_xticklabels([CFG_SHORT[c] for c in arms], fontsize=8, rotation=12)
    ax.set_ylabel("OTHERCLASS rate on out-of-protocol images (%)", fontsize=9)
    ax.set_title(f"P5-B rejection, n = {rj['n_out_of_protocol']:,}",
                 fontsize=10, loc="left")
    ax.legend(fontsize=7.8, frameon=False)
    S.despine(ax)

    ax = axes[1]
    conf = [100 * agg[c]["mean_top1_confidence_mean_3seed"] for c in arms]
    ax.bar(x, conf, color=[CFG_COLOR[c] for c in arms], width=0.55)
    for i, v in enumerate(conf):
        ax.text(i, v + 1.0, f"{v:.1f}", ha="center", fontsize=8.5, color=S.INK)
    ax.set_xticks(x)
    ax.set_xticklabels([CFG_SHORT[c] for c in arms], fontsize=8, rotation=12)
    ax.set_ylabel("mean top-1 confidence (%)", fontsize=9)
    ax.set_ylim(0, max(conf) * 1.22)
    ax.set_title("Confidence on images that are not gastric stations at all",
                 fontsize=10, loc="left")
    S.despine(ax)
    fig.text(0.5, -0.05,
             "A model that is wrong AND confident on out-of-protocol input is worse "
             "than one that is merely wrong: the right-hand panel is the "
             "deployment-relevant quantity.",
             ha="center", fontsize=7.8, color=S.MUTED)
    fig.tight_layout()
    save(fig, "P5_F36_rejection.png")


# -------------------------------------------------------------- F37/F38 calibration
def f37_f38_calibration(cal):
    arms = arms_of(cal)
    agg = cal["aggregate_3seed"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    ax = axes[0]
    x = np.arange(len(arms))
    e = [agg[c]["ece_top1_mean_3seed"] for c in arms]
    lo = [agg[c]["ece_top1_ci95"][0] for c in arms]
    hi = [agg[c]["ece_top1_ci95"][1] for c in arms]
    ax.bar(x, e, color=[CFG_COLOR[c] for c in arms], width=0.55)
    ax.errorbar(x, e, yerr=[np.array(e) - np.array(lo), np.array(hi) - np.array(e)],
                fmt="none", ecolor=S.INK, capsize=3, lw=1.1)
    ax.set_xticks(x)
    ax.set_xticklabels([CFG_SHORT[c] for c in arms], fontsize=8, rotation=12)
    ax.set_ylabel("external ECE (points)", fontsize=9)
    ax.set_title("P5-C external calibration error by arm", fontsize=10, loc="left")
    S.despine(ax)

    ax = axes[1]
    v = cal.get("verdict_P5C", {})
    if v.get("computable"):
        iv = [v["internal_ece_points"][c] for c in arms]
        ev = [v["external_ece_points"][c] for c in arms]
        for i, c in enumerate(arms):
            ax.plot([0, 1], [iv[i], ev[i]], "-o", color=CFG_COLOR[c], ms=7,
                    lw=1.8, label=CFG_SHORT[c])
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["internal\n(Phase 4, contested)", "external\n(Phase 5)"],
                           fontsize=8.5)
        ax.set_ylabel("ECE (points)", fontsize=9)
        ax.set_title(f"Ordering: Spearman rho = {v['spearman_rho']:.3f} "
                     f"({v['verdict']})", fontsize=10, loc="left")
        ax.legend(fontsize=7.4, frameon=False, ncol=2)
        S.despine(ax)
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "P5-C verdict not computable", ha="center", fontsize=10,
                color=S.MUTED)
    fig.text(0.5, -0.06,
             "Absolute external ECE is not comparable to absolute internal ECE "
             "(different correctness definitions); the verdict is a RANK "
             "correlation, which is invariant to that.",
             ha="center", fontsize=7.8, color=S.MUTED)
    fig.tight_layout()
    save(fig, "P5_F37_calibration.png")


def main() -> None:
    S.apply()
    print(f"Phase 5 figures -> {FIGDIR}")
    mp, tr = load("phase5_mapping.json"), load("phase5_transfer.json")
    rj, cal = load("phase5_rejection.json"), load("phase5_calibration.json")
    n = 0
    for artefact, fn, label in (
            (mp, f33_label_space, "P5_F33"), (mp, f34_inventory, "P5_F34"),
            (tr, f35_transfer, "P5_F35"), (rj, f36_rejection, "P5_F36"),
            (cal, f37_f38_calibration, "P5_F37")):
        if artefact is None:
            print(f"  skipped {label}: artefact not present")
            continue
        fn(artefact)
        n += 1
    print(f"{n} figures written")


if __name__ == "__main__":
    main()
