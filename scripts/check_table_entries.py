import pdfplumber

from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.table_reader import (
    find_row_bands, find_sides, read_row)

with pdfplumber.open(RAW_DIR / "VestasAnnualReport2025.pdf") as pdf:
    for number in range(71, 75):
        page = pdf.pages[number - 1]
        words = page.extract_words(extra_attrs=["fontname"])
        print(f"=== page {number}")
        for side in find_sides(page, words):
            for band in find_row_bands(page, side):
                entry = read_row(words, side, band)
                if entry is None:
                    continue
                flag = "IMMATERIAL" if entry.immaterial else "entry     "
                print(f"{side.name[:3]} {flag} | {entry.name[:62]:62s} | {entry.value_chain:20s} | {entry.description[:30]!r}")