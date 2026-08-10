"""
Phase 2 / Stage A3-A4 -- GATE 1, precision benchmark and batch-size selection.

Asserts the CUDA gate, then measures peak allocated memory and step time for
one forward+backward of ConvNeXt-Tiny at 224x224 across a factorial of
precision mode (AMP float16 vs float32), memory format (contiguous vs
channels_last) and batch size.

The precision arm is not a formality. Blueprint v3.0 sec.7 prescribes AMP
float16 + GradScaler on the assumption that Turing offers FP16 tensor-core
acceleration. The GTX 1650 is TU117, the one Turing die shipped WITHOUT
tensor cores, so FP16 provides no matrix-multiply speedup while autocast
casting and gradient scaling add overhead. This script measures whether the
prescription actually helps, and the training configuration follows the
measurement rather than the assumption.

Output: reports/phase2_vram_probe.json
Run:    python src/models/phase2_probe.py
"""
from __future__ import annotations

import json
import platform
import time
from pathlib import Path

import torch
import torch.nn as nn
from torchvision.models import convnext_tiny

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "phase2_vram_probe.json"
SAFETY_MIB = 400          # headroom for the desktop compositor and allocator
N_CLASSES = 23
N_WARM, N_REP = 3, 6


def one(batch: int, amp: bool, chlast: bool, frozen: bool, dev) -> dict:
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    crit = nn.CrossEntropyLoss()
    m = convnext_tiny(weights=None)
    m.classifier[2] = nn.Linear(m.classifier[2].in_features, N_CLASSES)
    m = m.to(dev)
    if chlast:
        m = m.to(memory_format=torch.channels_last)
    if frozen:
        for p in m.features.parameters():
            p.requires_grad = False
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=1e-4)
    sc = torch.amp.GradScaler("cuda", enabled=amp)
    x = torch.randn(batch, 3, 224, 224, device=dev)
    if chlast:
        x = x.to(memory_format=torch.channels_last)
    y = torch.randint(0, N_CLASSES, (batch,), device=dev)

    def step():
        with torch.autocast("cuda", dtype=torch.float16, enabled=amp):
            loss = crit(m(x), y)
        sc.scale(loss).backward()
        sc.step(opt); sc.update(); opt.zero_grad(set_to_none=True)

    try:
        for _ in range(N_WARM):
            step()
        torch.cuda.synchronize()
        t0 = time.time()
        for _ in range(N_REP):
            step()
        torch.cuda.synchronize()
        dt = (time.time() - t0) / N_REP
        peak = torch.cuda.max_memory_allocated() / 2 ** 20
        r = {"batch": batch, "amp_fp16": amp, "channels_last": chlast,
             "head_only": frozen, "oom": False,
             "sec_per_step": round(dt, 4),
             "images_per_sec": round(batch / dt, 2),
             "peak_alloc_mib": round(peak, 1)}
    except torch.cuda.OutOfMemoryError:
        r = {"batch": batch, "amp_fp16": amp, "channels_last": chlast,
             "head_only": frozen, "oom": True}
    finally:
        del m, opt, x, y, sc
        torch.cuda.empty_cache()
    return r


def main() -> None:
    gate1 = torch.cuda.is_available()
    info = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gate1_cuda_available": bool(gate1),
        "torch": torch.__version__, "torch_cuda": torch.version.cuda,
        "python": platform.python_version(),
    }
    if not gate1:
        OUT.write_text(json.dumps(info, indent=2), encoding="utf-8")
        raise SystemExit("GATE 1 FAILED: torch.cuda.is_available() is False")

    torch.backends.cudnn.benchmark = True
    dev = torch.device("cuda")
    cap = torch.cuda.get_device_capability(0)
    free_b, total_b = torch.cuda.mem_get_info()
    info |= {
        "device_name": torch.cuda.get_device_name(0),
        "compute_capability": f"{cap[0]}.{cap[1]}",
        "bf16_supported": torch.cuda.is_bf16_supported(),
        "total_vram_mib": round(total_b / 2 ** 20, 1),
        "free_vram_mib_at_probe": round(free_b / 2 ** 20, 1),
        "vram_occupied_by_desktop_mib": round((total_b - free_b) / 2 ** 20, 1),
    }

    # ---- precision x memory-format factorial at a fixed batch ------------
    factorial = []
    for amp in (True, False):
        for cl in (True, False):
            r = one(24, amp, cl, False, dev)
            factorial.append(r)
            print(f"b24 amp={amp} chlast={cl}: {r.get('sec_per_step')}s "
                  f"{r.get('images_per_sec')} img/s peak {r.get('peak_alloc_mib')} MiB",
                  flush=True)

    fp16 = next(r for r in factorial if r["amp_fp16"] and r["channels_last"])
    fp32 = next(r for r in factorial if not r["amp_fp16"] and r["channels_last"])
    amp_speedup = fp16["images_per_sec"] / fp32["images_per_sec"]
    use_amp = amp_speedup > 1.05          # adopt AMP only if it actually helps

    # ---- batch ladder in the winning precision --------------------------
    ladder = []
    chosen = None
    for b in (48, 32, 24, 16, 12, 8):
        r = one(b, use_amp, True, False, dev)
        fits = (not r["oom"]) and (r["peak_alloc_mib"] + SAFETY_MIB
                                   < info["total_vram_mib"])
        r["fits"] = bool(fits)
        ladder.append(r)
        print(f"batch {b}: {'OOM' if r['oom'] else str(r['peak_alloc_mib']) + ' MiB'}"
              f" {r.get('images_per_sec', 0)} img/s fits={fits}", flush=True)
        if fits and chosen is None:
            chosen = b

    head = one(chosen or 24, use_amp, True, True, dev)

    tr_n, va_n = 3722, 793
    ips = next(r["images_per_sec"] for r in ladder if r["batch"] == chosen)
    info |= {
        "precision_factorial": factorial,
        "amp_vs_fp32_speedup": round(amp_speedup, 3),
        "amp_adopted": bool(use_amp),
        "amp_decision_note": (
            "AMP float16 adopted" if use_amp else
            "AMP float16 REJECTED on measured evidence: TU117 has no tensor "
            "cores, so autocast and GradScaler cost more than FP16 saves"),
        "batch_ladder": ladder,
        "chosen_batch": chosen or 8,
        "safety_margin_mib": SAFETY_MIB,
        "head_only_step": head,
        "projected_epoch_sec_finetune": round(tr_n / ips + va_n / (ips * 2.5), 1),
        "projected_epoch_sec_warmup": round(
            tr_n / head["images_per_sec"] + va_n / (head["images_per_sec"] * 2.5), 1),
    }
    OUT.write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"\nGATE 1 pass; batch={info['chosen_batch']} amp={use_amp} "
          f"(AMP speedup {amp_speedup:.2f}x); "
          f"projected fine-tune epoch {info['projected_epoch_sec_finetune']}s")


if __name__ == "__main__":
    main()
