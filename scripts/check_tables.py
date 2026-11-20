from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.table_reader import read_tables

candidates, immaterial = read_tables(RAW_DIR / "VestasAnnualReport2025.pdf", [71, 72, 73, 74])

print(len(candidates), "candidates")
for c in candidates:
    print(f"  p{c.page}  {c.title:62s} {c.value_chain}")
print(len(immaterial), "immaterial statements")