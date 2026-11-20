from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.kind import OPPORTUNITY_WORD, classify_kind

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())

for c in stage2.candidates:
    kind = classify_kind(c.description, c.tier)
    match = OPPORTUNITY_WORD.search(c.description)
    where = ""
    if match:
        where = repr(c.description[max(0, match.start() - 40): match.end() + 15])
    print(f"{kind.value:11s} {c.title[:50]:50s} {where}")