from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.sentences import split_sentences

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())

for c in (c for c in stage2.candidates if c.tier == "sustainability_iro"):
    words = len(c.description.split())
    print(f"p{c.page}  {c.title}")
    print(f"    {len(split_sentences(c.description))} sentence(s), {words} words, value chain: {c.value_chain}")
    print(f"    {c.description}\n")