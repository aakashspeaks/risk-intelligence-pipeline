from risk_intel.config import INTERIM_DIR
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.matching import normalise

# Fill in your choices. Keys are risk ids.
# CHOICES = {
#     "geopolitics-and-regulatory-framework": {"must": ["regionalised manufacturing"], "forbidden": ["cyber"]},
#     "project-execution": {"must": ["project governance", "planning"], "forbidden": []},
#     "cyber-attacks": {"must": [], "forbidden": ["tariffs", "sanctions"]},
# }
CHOICES = {
    "geopolitics-and-regulatory-framework": {"must": ["regionalised manufacturing"], "forbidden": ["cyber"]},
    "project-execution": {"must": ["project governance", "planning"], "forbidden": ["hedging", "indexation", "cyber"]},
    "cyber-attacks": {"must": ["cyber security services", "navigate cyber risks", "critical infrastructure"],
                      "forbidden": ["tariffs", "sanctions"]},
}

output = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())
principal = {r.id: r for r in output.risks if r.tier == "principal"}


def full_text(risk):
    return normalise(f"{risk.description} {risk.potential_impact or ''} {risk.mitigation or ''}")


problems = 0
for risk_id, choice in CHOICES.items():
    risk = principal[risk_id]
    mitigation = normalise(risk.mitigation or "")
    own = full_text(risk)
    others = " ".join(full_text(o) for i, o in principal.items() if i != risk_id)
    print(f"\n{risk.title}")
    for phrase in choice["must"]:
        ok = normalise(phrase) in mitigation
        problems += not ok
        print(f"  must mention {phrase!r}: {'ok' if ok else 'NOT in this risk mitigation'}")
    for term in choice["forbidden"]:
        absent = normalise(term) not in own
        elsewhere = normalise(term) in others
        problems += not (absent and elsewhere)
        note = "ok" if absent and elsewhere else (
            "PROBLEM: appears in this risk's own text" if not absent else "WEAK: appears in no other risk, so it can't signal a leak")
        print(f"  forbidden {term!r}: {note}")

print(f"\n{problems} problem(s)")