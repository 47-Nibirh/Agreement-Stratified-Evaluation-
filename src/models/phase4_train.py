"""
Phase 4 / Stage E -- soft-label and structured-loss training (C1-C4).

Everything about the model, the optimiser, the schedule, the augmentation, the
preprocessing and the numerical precision is inherited UNCHANGED from
phase2_train.py. The single thing that varies between configurations is how
the 23-dimensional target vector is built from the four annotator votes, and
(for C4 alone) one additive penalty term. That is the whole design: any
difference in the results is attributable to the target, because nothing else
was allowed to move.

Configurations (blueprint v3.3 sec.4 PHASE 4; frozen in reports/phase4_prereg.json)

  C0  hard label, 4/4 cohort only          reference arm = the Phase 2 run,
                                           NOT retrained here
  C1  hard majority label, cohort E        isolates the effect of adding the
                                           3/4 contested images
  C2  vote proportions, cohort E           RQ2: soft targets from all 4 votes
  C3  hard label + label smoothing,        the control. Without it a C2 gain is
      cohort E                             indistinguishable from ordinary
                                           regularisation
  C4  vote proportions + anatomical        RQ4: exploit the (wall x station)
      penalty, cohort E                    grid structure

Loss. All four arms minimise the same soft-target cross-entropy
    L_ce = - sum_j t_j log softmax(z)_j
which is bit-equivalent to nn.CrossEntropyLoss when t is one-hot, so C1 and C3
are not disadvantaged by a different code path. C4 adds
    L_struct = lambda * sum_i sum_j t_i q_j d(i,j),    q = softmax(z)
the expected anatomical distance between the target distribution and the
predicted distribution under the pre-registered distance matrix of
phase4_structure.py. It is zero for a confident correct prediction, small for
an adjacent-wall or neighbouring-station error and maximal for an error that
is both the wrong wall and the far end of the stomach.

epsilon (C3) and lambda (C4) are read from the frozen pre-registration; they
are not command-line tunable, so they cannot drift between runs.

Usage:  python src/models/phase4_train.py --config C2 --seed 1
        python src/models/phase4_train.py --probe          (timing only)
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import ConvNeXt_Tiny_Weights, convnext_tiny

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "phase4_cache_224.npy"
INDEX = ROOT / "data" / "phase4_cache_index.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
DIST = ROOT / "data" / "phase4_distance_matrix.npy"
NORM = ROOT / "reports" / "phase2_norm_stats.json"
PREREG = ROOT / "reports" / "phase4_prereg.json"
PROBE2 = ROOT / "reports" / "phase2_vram_probe.json"
REPORTS = ROOT / "reports"
CKPT = ROOT / "checkpoints"

# ---- protocol constants, identical to phase2_train.py (do not tune) --------
WARMUP_EPOCHS = 10
PATIENCE = 10
LR_HEAD = 1e-3
LR_FINETUNE = 1e-4
WEIGHT_DECAY = 0.05
EFFECTIVE_BATCH = 32
TOP_FRACTION = 0.40

ANN_Y = ["vote_0_y", "vote_1_y", "vote_2_y", "vote_3_y"]
CONFIGS = ("C1", "C2", "C3", "C4")


# =====================================================================
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.benchmark = True


def build_targets(idx: pd.DataFrame, config: str, k: int, eps: float) -> np.ndarray:
    """(n, k) float32 target matrix. One row per cached image."""
    n = len(idx)
    y = idx["y"].to_numpy()
    if config in ("C1",):
        T = np.zeros((n, k), dtype=np.float32)
        T[np.arange(n), y] = 1.0
    elif config == "C3":
        T = np.full((n, k), eps / k, dtype=np.float32)
        T[np.arange(n), y] += 1.0 - eps
    elif config in ("C2", "C4"):
        V = idx[ANN_Y].to_numpy()
        T = np.zeros((n, k), dtype=np.float32)
        for a in range(V.shape[1]):
            T[np.arange(n), V[:, a]] += 0.25
    else:
        raise SystemExit(f"unknown config {config}")
    s = T.sum(1)
    if not np.allclose(s, 1.0, atol=1e-5):
        raise SystemExit(f"target rows do not sum to 1 (max deviation {np.abs(s - 1).max()})")
    return T


class SoftCohortDataset(Dataset):
    """Phase 2's CohortDataset with a soft target vector instead of an int.

    The memmap is opened lazily inside each worker (Windows spawn), exactly as
    in phase2_train.CohortDataset.
    """

    def __init__(self, cache_path, rows, targets, hard_y, train: bool, mean, std):
        self.cache_path = str(cache_path)
        self.rows, self.targets, self.hard_y, self.train = rows, targets, hard_y, train
        self._arr = None
        norm = transforms.Normalize(mean=mean, std=std)
        if train:
            self.tf = transforms.Compose([
                transforms.RandomResizedCrop(
                    224, scale=(0.85, 1.0), ratio=(0.9, 1.111),
                    interpolation=transforms.InterpolationMode.BILINEAR,
                    antialias=True),
                transforms.ColorJitter(brightness=0.2, contrast=0.2,
                                       saturation=0.2, hue=0.02),
                transforms.ToTensor(), norm,
            ])
        else:
            self.tf = transforms.Compose([transforms.ToTensor(), norm])

    @property
    def arr(self):
        if self._arr is None:
            self._arr = np.load(self.cache_path, mmap_mode="r")
        return self._arr

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i):
        from PIL import Image
        a = np.asarray(self.arr[self.rows[i]])
        x = self.tf(Image.fromarray(a))
        return x, torch.from_numpy(self.targets[i]), int(self.hard_y[i])


def build_model(n_classes: int):
    m = convnext_tiny(weights=ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
    m.classifier[2] = nn.Linear(m.classifier[2].in_features, n_classes)
    return m


def resolve_top_layers(model, fraction: float = TOP_FRACTION):
    blocks = list(model.features)
    n = len(blocks)
    k = int(round(fraction * n))
    idx = list(range(n - k, n))
    total = sum(p.numel() for p in model.features.parameters())
    unfrozen = sum(p.numel() for i in idx for p in blocks[i].parameters())
    return idx, {"n_feature_modules": n, "fraction_requested": fraction,
                 "n_modules_unfrozen": k, "modules_unfrozen": idx,
                 "feature_params_total": int(total),
                 "feature_params_unfrozen": int(unfrozen),
                 "param_fraction_unfrozen": round(unfrozen / total, 4)}


def soft_ce(logits, target):
    """-sum_j t_j log softmax(z)_j, mean over the batch.

    Equal to nn.CrossEntropyLoss for one-hot targets; asserted in selftest().
    """
    return -(target * F.log_softmax(logits, dim=1)).sum(1).mean()


def struct_penalty(logits, target, D):
    """lambda-free expected anatomical distance E_{i~t, j~q}[d(i,j)]."""
    q = F.softmax(logits, dim=1)
    return torch.einsum("bi,bj,ij->b", target, q, D).mean()


def selftest() -> None:
    torch.manual_seed(0)
    z = torch.randn(7, 23)
    y = torch.randint(0, 23, (7,))
    t = F.one_hot(y, 23).float()
    a = soft_ce(z, t).item()
    b = nn.CrossEntropyLoss()(z, y).item()
    assert abs(a - b) < 1e-6, f"soft_ce != CrossEntropyLoss ({a} vs {b})"


selftest()


# =====================================================================
@torch.no_grad()
def evaluate(model, loader, device, n_classes):
    """Macro F1 against the hard majority label -- the pre-registered
    model-selection criterion, identical for every configuration."""
    model.eval()
    ps, ys = [], []
    for x, _, y in loader:
        x = x.to(device, non_blocking=True).to(memory_format=torch.channels_last)
        ps.append(model(x).float().argmax(1).cpu())
        ys.append(y)
    p = torch.cat(ps).numpy()
    t = torch.cat(ys).numpy()
    return f1_score(t, p, average="macro", labels=list(range(n_classes)),
                    zero_division=0)


def run_epochs(model, tr_loader, va_loader, device, n_classes, params, lr,
               n_epochs, accum, history, phase, D, lam, patience=None,
               best=None, cosine_T=None):
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=WEIGHT_DECAY)
    sched = (torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cosine_T)
             if cosine_T else None)
    best = best or {"f1": -1.0, "epoch": -1, "path": None}
    bad = 0
    stop_reason = "epoch_cap"

    for ep in range(1, n_epochs + 1):
        model.train()
        t0, tot, tot_s, seen = time.time(), 0.0, 0.0, 0
        opt.zero_grad(set_to_none=True)
        for step, (x, t, _) in enumerate(tr_loader, 1):
            x = x.to(device, non_blocking=True).to(memory_format=torch.channels_last)
            t = t.to(device, non_blocking=True)
            out = model(x)
            l_ce = soft_ce(out, t)
            l_st = struct_penalty(out, t, D) if lam > 0 else torch.zeros((), device=device)
            loss = (l_ce + lam * l_st) / accum
            loss.backward()
            if step % accum == 0:
                opt.step()
                opt.zero_grad(set_to_none=True)
            tot += l_ce.item() * t.size(0)
            tot_s += float(l_st) * t.size(0)
            seen += t.size(0)
        if sched:
            sched.step()

        vf1 = evaluate(model, va_loader, device, n_classes)
        rec = {"phase": phase, "epoch": ep, "train_ce": round(tot / seen, 5),
               "train_struct": round(tot_s / seen, 5),
               "val_macro_f1": round(float(vf1), 5),
               "lr": round(opt.param_groups[0]["lr"], 8),
               "sec": round(time.time() - t0, 1)}
        history.append(rec)
        print(f"  [{phase}] ep{ep:03d} ce={rec['train_ce']:.4f} "
              f"struct={rec['train_struct']:.4f} valF1={vf1:.4f} {rec['sec']}s",
              flush=True)

        if vf1 > best["f1"]:
            torch.save(model.state_dict(), best["path"])
            best = {**best, "f1": float(vf1), "epoch": len(history)}
            bad = 0
        else:
            bad += 1
            if patience and bad >= patience:
                stop_reason = "early_stopping"
                print(f"  [{phase}] early stop at ep{ep}", flush=True)
                break
    return best, stop_reason


# =====================================================================
def load_common():
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    ns = json.load(open(NORM, encoding="utf-8"))
    idx = pd.read_csv(INDEX)
    D = np.load(DIST)
    return cls, ns, idx, D


def make_loaders(idx, T, ns, batch, workers, seed):
    rows = {s: np.where(idx.set_type == s)[0] for s in ("Train", "Validation")}
    ds = {s: SoftCohortDataset(CACHE, rows[s], T[rows[s]], idx.y.values[rows[s]],
                               s == "Train", ns["mean"], ns["std"]) for s in rows}
    g = torch.Generator(); g.manual_seed(seed)
    tr = DataLoader(ds["Train"], batch_size=batch, shuffle=True,
                    num_workers=workers, pin_memory=False, drop_last=False,
                    generator=g, persistent_workers=workers > 0)
    va = DataLoader(ds["Validation"], batch_size=batch, shuffle=False,
                    num_workers=0, pin_memory=False)
    return rows, tr, va


def probe(args) -> None:
    """Measure one real warm-up epoch and one real fine-tuning epoch on the
    extended cohort. Written before the pre-registration, which reads the
    projected epoch cost from it -- the same order Phase 2 used."""
    set_seed(1)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise SystemExit("GATE 1 FAILED: CUDA unavailable")
    cls, ns, idx, D = load_common()
    k = len(cls)
    T = build_targets(idx, "C2", k, 0.0)
    batch = json.load(open(PROBE2, encoding="utf-8"))["chosen_batch"]
    rows, tr, va = make_loaders(idx, T, ns, batch, args.workers, 1)
    Dt = torch.from_numpy(D).to(device)
    model = build_model(k).to(device).to(memory_format=torch.channels_last)
    layer_idx, _ = resolve_top_layers(model)
    accum = max(1, EFFECTIVE_BATCH // batch)

    hist = []
    for p in model.features.parameters():
        p.requires_grad = False
    best = {"f1": -1.0, "epoch": -1, "path": CKPT / "_probe.pt"}
    CKPT.mkdir(exist_ok=True)
    run_epochs(model, tr, va, device, k,
               [p for p in model.parameters() if p.requires_grad],
               LR_HEAD, 1, accum, hist, "warmup", Dt, 1.0, best=best)
    for i in layer_idx:
        for p in model.features[i].parameters():
            p.requires_grad = True
    run_epochs(model, tr, va, device, k,
               [p for p in model.parameters() if p.requires_grad],
               LR_FINETUNE, 1, accum, hist, "finetune", Dt, 1.0, best=best)
    best["path"].unlink(missing_ok=True)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": ("measured epoch cost on the extended Phase 4 cohort, including "
                    "the C4 structured-penalty term (the most expensive arm), used "
                    "to set the pre-registered epoch cap"),
        "device": torch.cuda.get_device_name(0),
        "batch_size": batch, "grad_accum_steps": accum,
        "n_train": int(len(rows["Train"])), "n_val": int(len(rows["Validation"])),
        "measured_warmup_epoch_sec": hist[0]["sec"],
        "measured_finetune_epoch_sec": hist[1]["sec"],
        "phase2_finetune_epoch_sec_measured": 75.0,
        "peak_vram_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1),
    }
    (REPORTS / "phase4_probe.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwarm-up epoch {out['measured_warmup_epoch_sec']}s, "
          f"fine-tune epoch {out['measured_finetune_epoch_sec']}s, "
          f"peak {out['peak_vram_mib']} MiB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", choices=CONFIGS)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--tag", default="", help="suffix for sensitivity variants")
    ap.add_argument("--drop-annotator", type=int, default=-1,
                    help="LOAO: rebuild C2/C4 targets from the other 3 annotators")
    args = ap.parse_args()

    if args.probe:
        return probe(args)
    if not args.config:
        raise SystemExit("--config is required unless --probe is given")

    CKPT.mkdir(exist_ok=True)
    t_start = time.time()
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise SystemExit("GATE 1 FAILED: CUDA unavailable; Phase 4 cannot run")

    pre = json.load(open(PREREG, encoding="utf-8"))
    eps = pre["configurations"]["C3"]["label_smoothing_epsilon"]
    lam = pre["configurations"]["C4"]["structure_penalty_lambda"]
    max_ft = pre["epoch_cap_finetune"]
    batch = pre["batch_size"]
    accum = max(1, EFFECTIVE_BATCH // batch)

    cls, ns, idx, D = load_common()
    k = len(cls)

    if args.drop_annotator >= 0:
        keep = [c for i, c in enumerate(ANN_Y) if i != args.drop_annotator]
        n = len(idx)
        T = np.zeros((n, k), dtype=np.float32)
        V = idx[keep].to_numpy()
        for a in range(V.shape[1]):
            T[np.arange(n), V[:, a]] += 1.0 / len(keep)
    else:
        T = build_targets(idx, args.config, k, eps)

    rows, tr_loader, va_loader = make_loaders(idx, T, ns, batch, args.workers, args.seed)
    Dt = torch.from_numpy(D).to(device)
    lam_used = lam if args.config == "C4" else 0.0

    model = build_model(k).to(device).to(memory_format=torch.channels_last)
    layer_idx, layer_info = resolve_top_layers(model)

    name = f"{args.config}{args.tag}_seed{args.seed}"
    history: list[dict] = []
    best_path = CKPT / f"_best_p4_{name}.pt"
    best0 = {"f1": -1.0, "epoch": -1, "path": best_path}

    for p in model.features.parameters():
        p.requires_grad = False
    best, _ = run_epochs(model, tr_loader, va_loader, device, k,
                         [p for p in model.parameters() if p.requires_grad],
                         LR_HEAD, WARMUP_EPOCHS, accum, history, "warmup",
                         Dt, lam_used, best=best0)
    for i in layer_idx:
        for p in model.features[i].parameters():
            p.requires_grad = True
    best, stop_reason = run_epochs(model, tr_loader, va_loader, device, k,
                                   [p for p in model.parameters() if p.requires_grad],
                                   LR_FINETUNE, max_ft, accum, history, "finetune",
                                   Dt, lam_used, patience=PATIENCE, best=best,
                                   cosine_T=max_ft)

    torch.save({"state_dict": torch.load(best["path"], map_location="cpu"),
                "config": args.config, "tag": args.tag, "seed": args.seed,
                "class_index": cls, "norm": {"mean": ns["mean"], "std": ns["std"]},
                "epsilon": eps if args.config == "C3" else None,
                "lambda": lam_used,
                "drop_annotator": args.drop_annotator},
               CKPT / f"phase4_{name}.pt")
    best["path"].unlink(missing_ok=True)

    tgt_ent = float(-(T * np.log(np.clip(T, 1e-12, 1))).sum(1)[rows["Train"]].mean())
    manifest = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 4, "config": args.config, "tag": args.tag, "seed": args.seed,
        "drop_annotator": args.drop_annotator,
        "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__, "cuda": torch.version.cuda,
        "python": platform.python_version(),
        "batch_size": batch, "grad_accum_steps": accum,
        "effective_batch": batch * accum,
        "precision": "float32", "memory_format": "channels_last",
        "lr_head": LR_HEAD, "lr_finetune": LR_FINETUNE,
        "weight_decay": WEIGHT_DECAY, "warmup_epochs": WARMUP_EPOCHS,
        "max_finetune_epochs": max_ft, "patience": PATIENCE,
        "label_smoothing_epsilon": eps if args.config == "C3" else None,
        "structure_penalty_lambda": lam_used,
        "mean_train_target_entropy_nats": round(tgt_ent, 5),
        "trainable_layers": layer_info,
        "norm_stats": {"mean": ns["mean"], "std": ns["std"]},
        "n_train": int(len(rows["Train"])), "n_val": int(len(rows["Validation"])),
        "selection_criterion": ("macro F1 on the extended validation cohort "
                                "(n=1103) against the hard majority label"),
        "best_val_macro_f1": round(best["f1"], 5),
        "best_epoch_overall": best["epoch"],
        "n_epochs_run": len(history),
        "stop_reason": stop_reason,
        "peak_vram_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1),
        "wallclock_sec": round(time.time() - t_start, 1),
        "history": history,
    }
    (REPORTS / f"phase4_run_{name}.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{name}: best val macro F1 = {best['f1']:.4f} at epoch {best['epoch']} "
          f"({stop_reason}), {manifest['wallclock_sec']}s")


if __name__ == "__main__":
    main()
