from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.llm_summary import accept_summary
from risk_intel.stage3_extraction.sentences import first_sentences

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())
source = next(c for c in stage2.candidates if c.title == "Geopolitics and regulatory framework").description

CASES = {
    "first two source sentences (should pass)": first_sentences(source, 2),
    "a faithful paraphrase (should pass)":
        "Vestas faced geopolitical tensions that disrupt supply chains and complicate global operations.",
    "an invented figure (should fail)":
        "Vestas holds a EUR 500 million reserve for geopolitical shocks.",
    "four sentences (should fail)": "One. Two. Three. Four.",
    "invented content, no numbers (should fail)":
        "Vestas plans to relocate its headquarters to avoid political pressure from regulators.",
    "empty (should fail)": "",
}

for label, summary in CASES.items():
    verdict = accept_summary(summary, source)
    print(f"{'ACCEPT' if verdict.ok else 'REJECT'}  {label}")
    if not verdict.ok:
        print(f"        reason: {verdict.reason}")