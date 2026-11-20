from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.governance_reader import read_governance

g = read_governance(RAW_DIR / "VestasAnnualReport2025.pdf")
print(g)