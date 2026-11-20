from risk_intel.config import INTERIM_DIR
from risk_intel.stage3_extraction.models import Stage3Output
from risk_intel.stage4_validation.dedupe import merge_duplicates

stage3 = Stage3Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage3.json").read_text())

merged, merges = merge_duplicates(stage3.risks)
print(f"records: {len(stage3.risks)} -> {len(merged)}")
for m in merges:
    print(f"merged {m.merged_id} into {m.kept_id}\n   reason: {m.reason}")
cyber = next(r for r in merged if r.id == "cyber-attacks")
print("cross_references on cyber-attacks:", cyber.cross_references)

print("\n--- two cases that must NOT be merged ---")
template = next(r for r in stage3.risks if r.id == "iro-cyber-security-risks")
opportunity = template.model_copy(update={"id": "x-opp", "title": "Cyber insurance opportunity", "kind": "opportunity"})
unrelated = template.model_copy(update={"id": "x-breach", "title": "Data breach penalties"})
_, test_merges = merge_duplicates([r for r in stage3.risks if r.tier == "principal"] + [opportunity, unrelated])
print("merges:", len(test_merges), "(expected 0)")