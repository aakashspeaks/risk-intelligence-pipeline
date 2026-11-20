from collections import Counter

from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.runner import run_stage2, save_stage2

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
result = run_stage2(pdf)
path = save_stage2(result, pdf)

print("saved to:", path)
print("pages used:", result.pages_used)
print("candidates by tier:", dict(Counter(c.tier for c in result.candidates)))
print("immaterial statements:", len(result.immaterial_statements))
print("governance:", result.governance.review_frequency, result.governance.reviewed_by)
print("section on page 51 candidate:", result.candidates[0].section)
print("section on a page 74 candidate:", result.candidates[-1].section)