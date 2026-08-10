"""
Finalise the Phase-I deliverables: update fields and export PDFs via Word and
PowerPoint COM automation.

LibreOffice and pandoc are absent on this machine, so Office COM is the working
route (the same one finalise_phase2..6.py use).

Run:  python src/report/finalise_phase1.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCX = ROOT / "Phase-I_Progress_Report.docx"
DOCX_PDF = ROOT / "Phase-I_Progress_Report.pdf"
PPTX = ROOT / "Phase-I_Defence_Presentation.pptx"
PPTX_PDF = ROOT / "Phase-I_Defence_Presentation.pdf"

WORD_PS = r"""
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

PPT_PS = r"""
$ErrorActionPreference = 'Stop'
$ppt = New-Object -ComObject PowerPoint.Application
$deck = $ppt.Presentations.Open('{pptx}', $true, $false, $false)
$deck.SaveAs('{pdf}', 32)
$n = $deck.Slides.Count
$deck.Close()
$ppt.Quit()
Write-Output "slides=$n"
"""


def _run(script: str, label: str) -> str | None:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[{label}] COM automation failed:\n{r.stderr[:2000]}")
        return None
    return r.stdout.strip()


def main() -> int:
    rc = 0
    if DOCX.exists():
        out = _run(WORD_PS.format(docx=str(DOCX), pdf=str(DOCX_PDF)), "word")
        if out is None:
            rc = 1
        else:
            print(f"[word] {out}")
            print(f"[word] pdf -> {DOCX_PDF.name}")
    else:
        print(f"missing {DOCX.name}; run build_phase1_docx.py first")
        rc = 1

    if PPTX.exists():
        out = _run(PPT_PS.format(pptx=str(PPTX), pdf=str(PPTX_PDF)), "powerpoint")
        if out is None:
            rc = 1
        else:
            print(f"[powerpoint] {out}")
            print(f"[powerpoint] pdf -> {PPTX_PDF.name}")
    else:
        print(f"note: {PPTX.name} not built yet; skipping the deck")
    return rc


if __name__ == "__main__":
    sys.exit(main())
