from risk_intel.config import INTERIM_DIR
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.golden import load_golden
from risk_intel.stage5_evaluation.matching import match_records

golden = load_golden()
output = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())

matched, missed, extra = match_records(golden.risks, output.risks)
print(f"real output: matched {len(matched)}, missed {len(missed)}, extra {len(extra)}")

print("\n--- three deliberate cases ---")

# 1. A record is dropped: it must show up as missed.
dropped = [r for r in output.risks if r.title != "Project execution"]
_, missed1, _ = match_records(golden.risks, dropped)
print("dropped record  -> missed:", [g.title for g in missed1])

# 2. A made-up record is added: it must show up as extra.
fake = output.risks[0].model_copy(update={"id": "fake", "title": "Satellite launch delays"})
_, _, extra2 = match_records(golden.risks, output.risks + [fake])
print("invented record -> extra:", [r.title for r in extra2])

# 3. A small wording change must still match.
tweaked = [r.model_copy(update={"title": "Cyber attack"}) if r.id == "cyber-attacks" else r for r in output.risks]
matched3, missed3, extra3 = match_records(golden.risks, tweaked)
print("'Cyber attack'  -> matched", len(matched3), "missed", len(missed3), "extra", len(extra3))