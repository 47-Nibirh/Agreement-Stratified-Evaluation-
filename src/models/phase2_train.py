"""
Phase 2 / Stage C+E -- ConvNeXt-Tiny baseline reproduction on the
complete-agreement cohort.

Implements the blueprint v3.0 sec.4 PHASE 2 protocol exactly:
  * ImageNet-pretrained ConvNeXt-Tiny, 23-way head
  * 224x224 Lanczos, normalised with TRAINING-SET statistics
  * two-stage schedule: 10-epoch head warm-up at constant LR, then fine-tune
    the top 40% of feature layers, early stopping on validation macro F1
    with patience 10
  * gradient accumulation to a fixed effective batch of 32

Numerical precision follows the measurement in reports/phase2_vram_probe.json
rather than the blueprint's assumption. On this GTX 1650 (TU117, no tensor
cores) AMP float16 was measured at 0.38x the throughput of float32, so
float32 + channels_last is used and the deviation is recorded as DEV-1 in the
pre-registration. The epoch cap likewise comes from the pre-registered
compute budget (DEV-2), not from a value hard-coded here.

Augmentation policy (fixed here for all later phases, and deliberately
conservative): the class label encodes an anatomical WALL (anterior,
posterior, greater curvature, lesser curvature). Horizontal or vertical
flipping, and large rotations, change the apparent wall and would therefore
corrupt the label. Only photometric jitter and a mild scale/translation crop
are applied.

Usage:  python src/models/phase2_train.py --seed 1
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
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import ConvNeXt_Tiny_Weights, convnext_tiny

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "phase2_cache_224.npy"
INDEX = ROOT / "data" / "phase2_cache_index.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
NORM = ROOT / "reports" / "phase2_norm_stats.json"
REPORTS = ROOT / "reports"
CKPT = ROOT / "checkpoints"

# ---- protocol constants (pre-registered; do not tune) --------------------
WARMUP_EPOCHS = 10
PATIENCE = 10
LR_HEAD = 1e-3
LR_FINETUNE = 1e-4
WEIGHT_DECAY = 0.05
EFFECTIVE_BATCH = 32
TOP_FRACTION = 0.40


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = False   # perf; seeds still logged
    torch.backends.cudnn.benchmark = True


class CohortDataset(Dataset):
    """Reads the 224x224 uint8 cache.

    The memmap is opened lazily inside each worker process rather than being
    held on the instance, because Windows uses spawn: a live memmap on the
    instance would be pickled and materialised in full in every worker.
    """

    def __init__(self, cache_path, rows, y, train: bool, mean, std):
        self.cache_path = str(cache_path)
        self.rows, self.y, self.train = rows, y, train
        self._arr = None
        norm = transforms.Normalize(mean=mean, std=std)
        if train:
            # The specification's Lanczos resampling to 224 is applied once,
            # when the cache is built. The augmentation crop that follows is
            # bilinear: it operates on an already-224 image, where the
            # interpolation kernel is immaterial and Lanczos costs ~3x more.
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
        return x, int(self.y[i])


def build_model(n_classes: int):
    m = convnext_tiny(weights=ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
    in_f = m.classifier[2].in_features
    m.classifier[2] = nn.Linear(in_f, n_classes)
    return m


def resolve_top_layers(model, fraction: float = TOP_FRACTION):
    """Resolve 'top 40% of feature layers' to an explicit, logged module list.

    torchvision ConvNeXt-Tiny exposes `features` as 8 top-level modules.
    round(0.40 * 8) = 3, so modules 5, 6, 7 (stage 3, its downsample and
    stage 4) are unfrozen. The choice and its parameter share are recorded.
    """
    blocks = list(model.features)
    n = len(blocks)
    k = int(round(fraction * n))
    idx = list(range(n - k, n))
    total = sum(p.numel() for p in model.features.parameters())
    unfrozen = sum(p.numel() for i in idx for p in blocks[i].parameters())
    return idx, {
        "n_feature_modules": n,
        "fraction_requested": fraction,
        "n_modules_unfrozen": k,
        "modules_unfrozen": idx,
        "module_fraction": round(k / n, 4),
        "feature_params_total": int(total),
        "feature_params_unfrozen": int(unfrozen),
        "param_fraction_unfrozen": round(unfrozen / total, 4),
    }


@torch.no_grad()
def evaluate(model, loader, device, n_classes, amp: bool = False):
    model.eval()
    ps, ys = [], []
    for x, y in loader:
        x = x.to(device, non_blocking=True).to(memory_format=torch.channels_last)
        with torch.autocast("cuda", dtype=torch.float16, enabled=amp):
            out = model(x)
        ps.append(out.float().argmax(1).cpu())
        ys.append(y)
    p = torch.cat(ps).numpy()
    t = torch.cat(ys).numpy()
    return f1_score(t, p, average="macro",
                    labels=list(range(n_classes)), zero_division=0), p, t


def run_epochs(model, tr_loader, va_loader, device, n_classes, params, lr,
               n_epochs, scaler, accum, history, phase, patience=None,
               best=None, cosine_T=None, amp: bool = False):
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=WEIGHT_DECAY)
    sched = (torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cosine_T)
             if cosine_T else None)
    crit = nn.CrossEntropyLoss()
    best = best or {"f1": -1.0, "epoch": -1, "path": None}
    bad = 0
    stop_reason = "epoch_cap"

    for ep in range(1, n_epochs + 1):
        model.train()
        t0, tot, seen = time.time(), 0.0, 0
        opt.zero_grad(set_to_none=True)
        for step, (x, y) in enumerate(tr_loader, 1):
            x = x.to(device, non_blocking=True).to(memory_format=torch.channels_last)
            y = y.to(device, non_blocking=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=amp):
                loss = crit(model(x), y) / accum
            scaler.scale(loss).backward()
            if step % accum == 0:
                scaler.step(opt)
                scaler.update()
                opt.zero_grad(set_to_none=True)
            tot += loss.item() * accum * y.size(0)
            seen += y.size(0)
        if sched:
            sched.step()

        vf1, _, _ = evaluate(model, va_loader, device, n_classes, amp)
        rec = {"phase": phase, "epoch": ep, "train_loss": round(tot / seen, 5),
               "val_macro_f1": round(float(vf1), 5),
               "lr": round(opt.param_groups[0]["lr"], 8),
               "sec": round(time.time() - t0, 1)}
        history.append(rec)
        print(f"  [{phase}] ep{ep:03d} loss={rec['train_loss']:.4f} "
              f"valF1={vf1:.4f} {rec['sec']}s", flush=True)

        if vf1 > best["f1"]:
            # Persist the best state to disk rather than holding successive
            # full copies in host RAM: repeatedly cloning a 28M-parameter
            # state_dict alongside pinned dataloader buffers crashed the CUDA
            # pinned-host allocator on this machine.
            torch.save(model.state_dict(), best["path"])
            best = {**best, "f1": float(vf1), "epoch": len(history)}
            bad = 0
        else:
            bad += 1
            if patience and bad >= patience:
                stop_reason = "early_stopping"
                print(f"  [{phase}] early stop at ep{ep} "
                      f"(no gain for {patience} epochs)", flush=True)
                break
    return best, stop_reason


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--batch", type=int, default=0, help="0 = auto from probe")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    CKPT.mkdir(exist_ok=True)
    t_start = time.time()
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise SystemExit("GATE 1 FAILED: CUDA unavailable; Phase 2 cannot run")

    torch.backends.cudnn.benchmark = True
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    n_classes = len(cls)
    ns = json.load(open(NORM, encoding="utf-8"))
    mean, std = ns["mean"], ns["std"]

    idx = pd.read_csv(INDEX)
    arr = np.load(CACHE, mmap_mode="r")

    probe = json.load(open(REPORTS / "phase2_vram_probe.json", encoding="utf-8"))
    pre = json.load(open(REPORTS / "phase2_prereg.json", encoding="utf-8"))
    batch = args.batch or probe["chosen_batch"]
    use_amp = bool(probe["amp_adopted"])          # measured, not assumed
    max_ft = int(next(d["adopted"].split()[0] for d in pre["deviations"]
                      if d["id"] == "DEV-2"))
    accum = max(1, EFFECTIVE_BATCH // batch)

    rows = {s: np.where(idx.set_type == s)[0] for s in
            ["Train", "Validation", "Test"]}
    ds = {s: CohortDataset(CACHE, rows[s], idx.y.values[rows[s]],
                           s == "Train", mean, std) for s in rows}
    g = torch.Generator(); g.manual_seed(args.seed)
    tr_loader = DataLoader(ds["Train"], batch_size=batch, shuffle=True,
                           num_workers=args.workers, pin_memory=False,
                           drop_last=False, generator=g,
                           persistent_workers=args.workers > 0)
    # Validation runs forward-only over 793 images; giving it its own worker
    # pool doubled the number of resident torch processes and exhausted host
    # RAM (16 GB total, ~7 GB free). It is served from the main process.
    va_loader = DataLoader(ds["Validation"], batch_size=batch, shuffle=False,
                           num_workers=0, pin_memory=False)

    model = build_model(n_classes).to(device).to(memory_format=torch.channels_last)
    layer_idx, layer_info = resolve_top_layers(model)
    (REPORTS / "phase2_trainable_layers.json").write_text(
        json.dumps(layer_info, indent=2), encoding="utf-8")

    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    history: list[dict] = []
    best_path = CKPT / f"_best_seed{args.seed}.pt"
    best0 = {"f1": -1.0, "epoch": -1, "path": best_path}

    # ---- stage 1: head warm-up, constant LR ------------------------------
    for p in model.features.parameters():
        p.requires_grad = False
    best, _ = run_epochs(
        model, tr_loader, va_loader, device, n_classes,
        [p for p in model.parameters() if p.requires_grad],
        LR_HEAD, WARMUP_EPOCHS, scaler, accum, history, "warmup",
        best=best0, amp=use_amp)

    # ---- stage 2: fine-tune top 40% of feature layers --------------------
    for i in layer_idx:
        for p in model.features[i].parameters():
            p.requires_grad = True
    best, stop_reason = run_epochs(
        model, tr_loader, va_loader, device, n_classes,
        [p for p in model.parameters() if p.requires_grad],
        LR_FINETUNE, max_ft, scaler, accum, history, "finetune",
        patience=PATIENCE, best=best, cosine_T=max_ft, amp=use_amp)

    torch.save({"state_dict": torch.load(best["path"], map_location="cpu"),
                "seed": args.seed, "class_index": cls,
                "norm": {"mean": mean, "std": std}},
               CKPT / f"phase2_convnext_tiny_seed{args.seed}.pt")
    best["path"].unlink(missing_ok=True)

    peak = torch.cuda.max_memory_allocated() / 2 ** 20
    manifest = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "seed": args.seed,
        "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "python": platform.python_version(),
        "batch_size": batch,
        "grad_accum_steps": accum,
        "effective_batch": batch * accum,
        "precision": "float16 (AMP)" if use_amp else "float32",
        "memory_format": "channels_last",
        "lr_head": LR_HEAD, "lr_finetune": LR_FINETUNE,
        "weight_decay": WEIGHT_DECAY,
        "warmup_epochs": WARMUP_EPOCHS,
        "max_finetune_epochs": max_ft,
        "patience": PATIENCE,
        "trainable_layers": layer_info,
        "norm_stats": {"mean": mean, "std": std},
        "n_train": int(len(rows["Train"])), "n_val": int(len(rows["Validation"])),
        "n_test": int(len(rows["Test"])),
        "best_val_macro_f1": round(best["f1"], 5),
        "best_epoch_overall": best["epoch"],
        "n_epochs_run": len(history),
        "stop_reason": stop_reason,
        "peak_vram_mib": round(peak, 1),
        "wallclock_sec": round(time.time() - t_start, 1),
        "history": history,
    }
    (REPORTS / f"phase2_run_seed{args.seed}.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"seed {args.seed}: best val macro F1 = {best['f1']:.4f} "
          f"at epoch {best['epoch']} ({stop_reason}), "
          f"{manifest['wallclock_sec']}s, peak {peak:.0f} MiB")


if __name__ == "__main__":
    main()
