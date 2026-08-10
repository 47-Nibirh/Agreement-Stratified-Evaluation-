"""
Finalise the decision report: open it in Word, build the table of contents,
save the populated .docx and export a PDF.

Mirrors finalise.py -- Word COM automation, Windows only.

Run:  python src/report/finalise_decision.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCX = ROOT / "Dataset_Decision_Report.docx"
PDF = ROOT / "Dataset_Decision_Report.pdf"

PS = r"""
$ErrorActionPreference = 'Stop'
$docx = '{docx}'
$pdf  = '{pdf}'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
$d = $w.Documents.Open($docx, $false, $false)
foreach ($t in $d.TablesOfContents) {{ $t.Update() }}
$d.Fields.Update() | Out-Null
$d.Repaginate()
$pages = $d.ComputeStatistics(2)
$words = $d.ComputeStatistics(0)
$d.Save()
$d.SaveAs([ref]$pdf, [ref]17)
$d.Close($false)
$w.Quit()
Write-Output "pages=$pages words=$words"
"""


def main() -> int:
    if not DOCX.exists():
        print(f"missing {DOCX}; run build_decision_docx.py first")
        return 1
    script = PS.format(docx=str(DOCX), pdf=str(PDF))
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print("Word automation failed:\n", r.stderr[:2000])
        return r.returncode
    print(f"[finalise] {r.stdout.strip()}")
    print(f"[finalise] docx -> {DOCX}")
    print(f"[finalise] pdf  -> {PDF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
