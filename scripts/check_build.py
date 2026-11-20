from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.build import to_risk

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())
risks = [to_risk(c) for c in stage2.candidates]

print(f"{'id':62s} {'category':24s} {'kind':11s} {'page':>4s} mitigation")
for r in risks:
    print(f"{r.id:62s} {r.category.value:24s} {r.kind.value:11s} {r.source.page:4d} {bool(r.mitigation)}")

ids = [r.id for r in risks]
print("\nrecords:", len(risks))
print("ids unique:", len(ids) == len(set(ids)))
print("with mitigation:", sum(bool(r.mitigation) for r in risks))
print("opportunities:", sum(r.kind.value == "opportunity" for r in risks))