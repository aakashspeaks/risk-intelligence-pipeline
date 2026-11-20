from risk_intel.config import INTERIM_DIR, PROJECT_ROOT
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.golden import load_golden

output = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())
golden = {g.id: g for g in load_golden().risks}

lines = []
for r in output.risks:
    if r.tier != "principal":
        continue
    g = golden[r.id]
    lines += [
        "=" * 70,
        f"{r.title}  (page {r.source.page})",
        "",
        f"IMPACT: {r.potential_impact}",
        "",
        f"MITIGATION: {r.mitigation}",
        "",
        f"golden must_mention_in_mitigation: {g.must_mention_in_mitigation}",
        f"golden forbidden_terms: {g.forbidden_terms}",
        "",
    ]

out = PROJECT_ROOT / "reports" / "golden_review.txt"
out.parent.mkdir(exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8")
print("written to:", out)