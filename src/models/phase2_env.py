"""
Phase 2 / Stage A5 -- environment snapshot.

Records the exact interpreter, library, driver and hardware state under which
the Phase 2 results were produced, so a reviewer can reconstruct it. Written
as an artefact rather than transcribed into the report.

Output: reports/phase2_env.json
Run:    python src/models/phase2_env.py
"""
from __future__ import annotations

import json
import platform
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "phase2_env.json"

PKGS = ["torch", "torchvision", "numpy", "pandas", "scikit-learn", "scipy",
        "pillow", "matplotlib", "python-docx"]


def v(pkg: str):
    try:
        return version(pkg)
    except PackageNotFoundError:
        return None


def main() -> None:
    import torch

    try:
        smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
             "--format=csv,noheader"], capture_output=True, text=True,
            timeout=30).stdout.strip()
    except Exception:                                    # noqa: BLE001
        smi = None

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "packages": {p: v(p) for p in PKGS},
        "torch_build": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "compute_capability": (".".join(map(str, torch.cuda.get_device_capability(0)))
                               if torch.cuda.is_available() else None),
        "nvidia_smi": smi,
        "note": ("torch was reinstalled from the cu126 index; the previously "
                 "installed 2.12.0+cpu build is recorded in "
                 "reports/phase2_env_before.txt"),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT.name}")
    print(f"  {out['torch_build']} / CUDA {out['torch_cuda_version']} / "
          f"{out['gpu']}")


if __name__ == "__main__":
    main()
