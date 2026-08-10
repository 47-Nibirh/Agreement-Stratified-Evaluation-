"""
Finalise the GastroHUN Phase 0 / Phase 1 report: open it in Word, update the
table of contents, list of figures and list of tables, save the populated
.docx, and export a PDF.

The output filenames are unchanged from the superseded report, so `finalise.py`
already targets the right paths; this module exists so the regeneration
pipeline documented in Appendix C reads consistently.

Run:  python src/report/finalise_v2.py
"""

from __future__ import annotations

import sys

import finalise

if __name__ == "__main__":
    sys.exit(finalise.main())
