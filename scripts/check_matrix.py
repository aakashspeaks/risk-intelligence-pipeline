from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.matrix_reader import read_matrix

candidates = read_matrix(RAW_DIR / "VestasAnnualReport2025.pdf", 51, "Corporate governance – Risk management")
print(len(candidates), "candidates")
for c in candidates:
    print("=" * 60)
    print("TITLE:", c.title)
    print("DESCRIPTION:", c.description[:150], "...")
    print("IMPACT:", (c.potential_impact or "")[:150], "...")
    print("MITIGATION:", (c.mitigation or "")[:150], "...")