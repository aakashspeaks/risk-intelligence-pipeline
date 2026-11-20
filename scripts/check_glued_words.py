import re

import pdfplumber
import pymupdf

PDF = "data/raw/VestasAnnualReport2025.pdf"
GLUED = ["increasecosts", "risks,both"]
PATTERNS = [r"increase.{0,3}costs", r"risks,.{0,3}both"]

with pdfplumber.open(PDF) as pdf:
    words = pdf.pages[50].extract_words()
fitz_text = pymupdf.open(PDF)[50].get_text()

print("pdfplumber: glued words found as a single word")
for w in words:
    if w["text"] in GLUED:
        print(f"  {w['text']!r} at x={w['x0']:.0f}..{w['x1']:.0f}, top={w['top']:.0f}")

print("\nPyMuPDF: the same spots in its text")
for pattern in PATTERNS:
    m = re.search(pattern, fitz_text)
    print(f"  {pattern}: {m.group(0)!r}" if m else f"  {pattern}: not found")