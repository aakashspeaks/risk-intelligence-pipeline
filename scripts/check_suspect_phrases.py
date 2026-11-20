from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())
sources = {c.title: c.description for c in stage2.candidates if c.tier == "principal"}

# Word stems from the three phrases above (stems, so spelling variants like destabilize/destabilise match).
SUSPECT = {
    "Geopolitics and regulatory framework": ["competit", "clean"],
    "Project execution": ["skilled", "mobil"],
    "Cyber attacks": ["extort", "destabili"],
}

for title, stems in SUSPECT.items():
    text = sources[title]
    print(title)
    for stem in stems:
        i = text.lower().find(stem)
        if i < 0:
            print(f"   {stem:10s} NOT in the source description")
        else:
            print(f"   {stem:10s} in source: ...{text[max(0, i - 50): i + 60]}...")