import pdfplumber

from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.table_reader import find_sides

with pdfplumber.open(RAW_DIR / "VestasAnnualReport2025.pdf") as pdf:
    for number in range(71, 76):
        page = pdf.pages[number - 1]
        sides = find_sides(page, page.extract_words())
        print(f"page {number}:")
        for s in sides:
            print(f"   {s.name:9s} left={s.left:.0f}  value_chain_x={s.value_chain_x:.0f}  right={s.right:.0f}")
        if not sides:
            print("   no table halves found")