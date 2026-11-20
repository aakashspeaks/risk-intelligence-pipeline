import re

from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())
principal = [c for c in stage2.candidates if c.tier == "principal"]

geo = principal[0]
print("has 'economies have':", "economies have" in geo.description)
print("has 'economieshave': ", "economieshave" in geo.description)

print("\nlongest words in each principal description (long ones can be glued words):")
for c in principal:
    words = sorted(set(re.findall(r"[A-Za-z]+", c.description)), key=len, reverse=True)[:5]
    print(f"  {c.title}: {words}")