from collections import Counter

from risk_intel.config import RAW_DIR
from risk_intel.stage4_validation.runner import run_stage4, save_stage4

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
result = run_stage4(pdf)
path = save_stage4(result, pdf)

print("saved to:", path)
print("records:", len(result.risks))
print("by kind:", dict(Counter(r.kind.value for r in result.risks)))
print("issues:", len(result.issues), dict(Counter(i.severity for i in result.issues)))
print("merges:", len(result.merges))
print("cyber cross-references:", next(r for r in result.risks if r.id == "cyber-attacks").cross_references)
print("excluded as immaterial:", len(result.excluded_immaterial))
print("governance:", result.governance.review_frequency if result.governance else None)