from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.matrix_reader import read_matrix

geopolitics, _, cyber = read_matrix(RAW_DIR / "VestasAnnualReport2025.pdf", 51)

print("has 'increase costs':   ", "increase costs" in geopolitics.potential_impact)
print("has 'risks, both':      ", "risks, both" in cyber.mitigation)
print("has 'increasecosts':    ", "increasecosts" in geopolitics.potential_impact)
print("has 'risks,both':       ", "risks,both" in cyber.mitigation)
print(repr(geopolitics.potential_impact[130:160]))