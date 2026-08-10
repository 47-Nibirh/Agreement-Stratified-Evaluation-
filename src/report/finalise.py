"""
Finalise the report: open it in Word, update the table of contents, list of
figures and list of tables, save the populated .docx, and export a PDF.

Requires Microsoft Word (COM automation) and therefore runs on Windows only.
The .docx produced by build_docx.py is already correct without this step --
Word updates the fields on open -- but running it bakes the field results into
the file so the lists are populated in any viewer.

Run:  python src/report/finalise.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCX = ROOT / "Phase0_Phase1_Report.docx"
PDF = ROOT / "Phase0_Phase1_Report.pdf"

PS = r"""
$ErrorActionPreference = 'Stop'
$docx = '{docx}'
$pdf  = '{pdf}'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
$d = $w.Documents.Open($docx, $false, $false)
foreach ($t in $d.TablesOfContents) {{ $t.Update() }}
foreach ($t in $d.TablesOfFigures)  {{ $t.Update() }}
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
        print(f"missing {DOCX}; run build_docx.py first")
        return 1
    script = PS.format(docx=str(DOCX), pdf=str(PDF))
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
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
