"""
Finalise the Phase 6 report: open it in Word, update the table of contents,
list of figures and list of tables, save the populated .docx, and export a PDF.

LibreOffice and pandoc are absent on this machine; Word COM automation via
PowerShell is the working route (same as finalise_phase2..5.py).

Run:  python src/report/finalise_phase6.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCX = ROOT / "Phase6_Report.docx"
PDF = ROOT / "Phase6_Report.pdf"

PS = r"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open('{docx}')
foreach ($toc in $doc.TablesOfContents)  {{ $toc.Update() }}
foreach ($tof in $doc.TablesOfFigures)   {{ $tof.Update() }}
$doc.Fields.Update() | Out-Null
$doc.Repaginate()
$doc.Save()
$doc.SaveAs([ref]'{pdf}', [ref]17)
$pages = $doc.ComputeStatistics(2)
$words = $doc.ComputeStatistics(0)
$doc.Close(0)
$word.Quit()
Write-Output "pages=$pages words=$words"
"""


def main() -> int:
    if not DOCX.exists():
        print(f"missing {DOCX}; run build_phase6_docx.py first")
        return 1
    script = PS.format(docx=str(DOCX), pdf=str(PDF))
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True)
    if r.returncode != 0:
        print("Word automation failed:\n", r.stderr[:2000])
        return r.returncode
    print(f"[finalise] {r.stdout.strip()}")
    print(f"[finalise] docx fields populated -> {DOCX}")
    print(f"[finalise] pdf exported          -> {PDF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
