import re

import pdfplumber
import pymupdf

from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage2_candidates.models import Stage2Output

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"

# 1. Where are the "partner" words on page 71, according to pdfplumber?
with pdfplumber.open(PDF) as pdf:
    words = pdf.pages[70].extract_words()
print("pdfplumber: 'partner' on page 71")
for w in words:
    if w["text"].lower() == "partner":
        print(f"  x={w['x0']:.1f}..{w['x1']:.1f}  top={w['top']:.1f}")

# 2. Does PyMuPDF's text for the page contain the doubled word?
text = pymupdf.open(PDF)[70].get_text()
print("\nPyMuPDF text has 'partner partner':", bool(re.search(r"partner\s+partner", text)))

# 3. Does our saved Stage 2 output contain any word repeated straight away?
stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())
REPEAT = re.compile(r"\b(\w{3,})\s+\1\b", re.IGNORECASE)
print("\nrepeated words in saved candidates:")
found = False
for c in stage2.candidates:
    for field in ("description", "potential_impact", "mitigation"):
        for m in REPEAT.finditer(getattr(c, field) or ""):
            found = True
            print(f"  {c.title} ({field}): {m.group(0)!r}")
if not found:
    print("  none")