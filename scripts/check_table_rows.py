import pdfplumber

from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.table_reader import (
    _text, find_row_bands, find_sides, words_in_band)

with pdfplumber.open(RAW_DIR / "VestasAnnualReport2025.pdf") as pdf:
    for number in (71, 73):
        page = pdf.pages[number - 1]
        words = page.extract_words()
        for side in find_sides(page, words):
            bands = find_row_bands(page, side)
            print(f"page {number}, {side.name}: {len(bands)} rows")
            for top, bottom in bands:
                preview = _text(words_in_band(words, side, (top, bottom)))[:55]
                print(f"   {top:5.0f}-{bottom:5.0f}  {preview!r}")