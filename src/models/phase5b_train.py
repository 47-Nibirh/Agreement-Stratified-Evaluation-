"""
P5.16 -- self-training round on the pseudo-labelled external images.

Warm-starts from the frozen C2 checkpoint for the matching seed and fine-tunes on
the pseudo-labelled adapt split CONCATENATED with the original GastroHUN cohort E,
so a loss on the internal endpoints is attributable to adaptation rather than to
simple forgetting.

Model selection is macro F1 on the GastroHUN extended validation cohort. It never
touches the external eval split -- early stopping on the split the result is read
from would be the easiest possible way to manufacture a gain here.

Outputs
  checkpoints/phase5b_C2_seed{s}.pt
  reports/phase5b_run_C2_seed{s}.json
Run:  python src/models/phase5b_train.py [--seeds 1 2 3]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_train import (ANN_Y, build_model, evaluate, resolve_top_layers,  # noqa: E402
                          run_epochs, set_seed, LR_FINETUNE, TOP_FRACTION)

ROOT = Path(__file__).resolve().parents[2]
DATA, REPORTS, CKPT = ROOT / "data", ROOT / "reports", ROOT / "checkpoints"
PREREG = REPORTS / "phase5b_prereg.json"
CLASS_INDEX = DATA / "phase2_class_index.json"
NORM = REPORTS / "phase2_norm_stats.json"

INT_CACHE = DATA / "phase4_cache_224.npy"
INT_INDEX = DATA / "phase4_cache_index.csv"
EXT_CACHE = DATA / "phase5_cache_224.npy"

BATCH, ACCUM, WORKERS = 24, 2, 2


class MixedDataset(Dataset):
    """Two uint8 caches behind one index, so no combined copy is materialised.

    src 0 = the internal cohort-E cache, src 1 = the external Phase 5 cache.
    Memmaps are opened lazily per worker (Windows spawn), as in Phase 2.
    """

    def __init__(self, paths, src, rows, T, y, train, mean, std):
        self.paths = [str(p) for p in paths]
        self.src, self.rows, self.T, self.y, self.train = src, rows, T, y, train
        self._arr = None
        norm = transforms.Normalize(mean=mean, std=std)
        self.tf = transforms.Compose(
            ([transforms.RandomResizedCrop(
                224, scale=(0.85, 1.0), ratio=(0.9, 1.111),
                interpolation=transforms.InterpolationMode.BILINEAR, antialias=True),
              transforms.ColorJitter(0.2, 0.2, 0.2, 0.02)] if train else [])
            + [transforms.ToTensor(), norm])

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        if self._arr is None:
            self._arr = [np.load(p, mmap_mode="r") for p in self.paths]
        img = np.asarray(self._arr[self.src[i]][self.rows[i]])
        from PIL import Image
        x = self.tf(Image.fromarray(img))
        return x, torch.from_numpy(self.T[i]), int(self.y[i])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    args = ap.parse_args()

    if not PREREG.exists():
        print("[P5.16] run phase5b_prereg.py first.")
        return 1
    pre = json.loads(PREREG.read_text(encoding="utf-8"))
    arm = pre["arm"]
    seeds = args.seeds or pre["seeds"]
    cap, patience = 12, 5

    cls = json.loads(CLASS_INDEX.read_text(encoding="utf-8"))
    ns = json.loads(NORM.read_text(encoding="utf-8"))
    k = len(cls)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    idx = pd.read_csv(INT_INDEX)
    idx["y"] = idx["y"].astype(int)
    # C2 targets on cohort E: vote proportions, exactly as Phase 4 built them
    V = idx[ANN_Y].to_numpy()
    T_int = np.zeros((len(idx), k), dtype=np.float32)
    for a in range(V.shape[1]):
        T_int[np.arange(len(idx)), V[:, a]] += 0.25
    tr_int = np.where(idx.set_type == "Train")[0]
    va_int = np.where(idx.set_type == "Validation")[0]

    for seed in seeds:
        t0 = time.time()
        out_ck = CKPT / f"phase5b_{arm}_seed{seed}.pt"
        out_js = REPORTS / f"phase5b_run_{arm}_seed{seed}.json"
        if out_js.exists():
            print(f"[P5.16] seed{seed} already done, skipping")
            continue
        pl = pd.read_csv(DATA / f"phase5b_pseudolabels_seed{seed}.csv")
        ext_rows = pl["row_in_phase5_cache"].to_numpy()
        T_ext = np.zeros((len(pl), k), dtype=np.float32)
        T_ext[np.arange(len(pl)), pl["pseudo_label_idx"].to_numpy()] = 1.0

        # training set = internal Train + all pseudo-labelled external
        src = np.concatenate([np.zeros(len(tr_int), int), np.ones(len(pl), int)])
        rows = np.concatenate([tr_int, ext_rows])
        T = np.concatenate([T_int[tr_int], T_ext])
        y = np.concatenate([idx.y.values[tr_int], pl["pseudo_label_idx"].to_numpy()])

        set_seed(seed)
        # both loaders yield (x, target, y): run_epochs consumes the target and
        # evaluate() consumes y, so the same dataset class serves both.
        tr_ds = MixedDataset([INT_CACHE, EXT_CACHE], src, rows, T, y, True,
                             ns["mean"], ns["std"])
        va_ds = MixedDataset([INT_CACHE, EXT_CACHE], np.zeros(len(va_int), int),
                             va_int, T_int[va_int], idx.y.values[va_int], False,
                             ns["mean"], ns["std"])
        g = torch.Generator(); g.manual_seed(seed)
        tr_loader = DataLoader(tr_ds, batch_size=BATCH, shuffle=True,
                               num_workers=WORKERS, generator=g,
                               persistent_workers=WORKERS > 0)
        va_loader = DataLoader(va_ds, batch_size=BATCH, shuffle=False,
                               num_workers=0)

        model = build_model(k)
        blob = torch.load(CKPT / f"phase4_{arm}_seed{seed}.pt", map_location="cpu",
                          weights_only=False)
        model.load_state_dict(blob["state_dict"])
        model.to(device)
        # Same trainable set as the Phase 4 fine-tuning stage: features frozen
        # except the top TOP_FRACTION of blocks, classifier head always trainable.
        # There is no warm-up stage here because 5B warm-starts from a trained
        # checkpoint rather than an ImageNet one.
        layer_idx, layer_info = resolve_top_layers(model, TOP_FRACTION)
        for p in model.features.parameters():
            p.requires_grad = False
        for i in layer_idx:
            for p in model.features[i].parameters():
                p.requires_grad = True
        params = [p for p in model.parameters() if p.requires_grad]

        print(f"[P5.16] seed{seed}: {len(tr_int):,} internal + {len(pl):,} "
              f"pseudo-labelled external = {len(rows):,} training images", flush=True)
        history = []
        # run_epochs writes each improvement to best["path"], which defaults to
        # None, so the destination has to be supplied by the caller.
        tmp_best = CKPT / f"phase5b_{arm}_seed{seed}.best.pt"
        best, stop_reason = run_epochs(
            model, tr_loader, va_loader, device, k, params, LR_FINETUNE, cap,
            ACCUM, history, "phase5b", None, 0.0, patience=patience,
            best={"f1": -1.0, "epoch": -1, "path": str(tmp_best)},
            cosine_T=cap)

        # run_epochs writes the best epoch's weights to best["path"] but leaves the
        # live model at the LAST epoch, so the selected weights are reloaded from
        # disk rather than taken from the model in memory.
        sd = torch.load(best["path"], map_location="cpu", weights_only=False)
        torch.save({"state_dict": sd, "seed": seed, "arm": arm, "phase": "5B",
                    "selected_epoch": best.get("epoch"),
                    "selected_val_macro_f1": best.get("f1"),
                    "trainable_layers": layer_info}, out_ck)
        Path(best["path"]).unlink(missing_ok=True)
        rec = {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "5B", "step": "P5.16", "arm": arm, "seed": seed,
            "warm_start": f"checkpoints/phase4_{arm}_seed{seed}.pt",
            "n_internal_train": int(len(tr_int)),
            "n_pseudo_external": int(len(pl)),
            "n_train_total": int(len(rows)),
            "n_validation": int(len(va_int)),
            "validation_source": "GastroHUN extended validation cohort",
            "model_selection_touched_external_eval_split": False,
            "cap_finetune": cap, "patience": patience,
            "stop_reason": stop_reason if isinstance(stop_reason, str) else str(stop_reason),
            "best": best if isinstance(best, dict) else None,
            "history": history,
            "wallclock_sec": round(time.time() - t0, 1),
            "checkpoint": out_ck.name,
        }
        out_js.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        print(f"[P5.16] seed{seed} -> {out_ck.name} in "
              f"{rec['wallclock_sec'] / 60:.1f} min ({rec['stop_reason']})",
              flush=True)
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
