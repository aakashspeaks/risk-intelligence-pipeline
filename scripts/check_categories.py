from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.categorise import categorise

EXPECTED = {
    "Geopolitics and regulatory framework": "regulatory_geopolitical",
    "Project execution": "operational",
    "Cyber attacks": "cyber",
    "Low-emission materials": "climate",
    "Growth rate of the wind industry": "market",
    "Carbon taxes and tariffs": "climate",
    "Recyclable blades": "environmental",
    "Cost implication of injuries in own workforce": "health_safety",
    "Cost implications of injuries to contractors and sub-contractors": "health_safety",
    "Fines related to forced or child labour": "human_rights",
    "Insufficient market conditions": "market",
    "Cyber security risks": "cyber",
    "Risk of corruption and bribery": "compliance_conduct",
}

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())

wrong = 0
for c in stage2.candidates:
    got = categorise(c.title, c.description).value
    want = EXPECTED.get(c.title, "?")
    status = "ok" if got == want else "MISMATCH"
    wrong += status != "ok"
    print(f"{status:9s} {c.title[:55]:55s} got={got:24s} expected={want}")
print(f"\n{len(stage2.candidates) - wrong} of {len(stage2.candidates)} match my expectation")