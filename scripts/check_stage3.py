from collections import Counter

from risk_intel.config import RAW_DIR
from risk_intel.stage3_extraction.runner import run_stage3, save_stage3

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
result = run_stage3(pdf)
path = save_stage3(result, pdf)

print("saved to:", path)
print("records:", len(result.risks))
print("by kind:", dict(Counter(r.kind.value for r in result.risks)))
print("by category:", dict(Counter(r.category.value for r in result.risks)))
print("excluded as immaterial:", len(result.excluded_immaterial))
print("governance:", result.governance.review_frequency if result.governance else None)