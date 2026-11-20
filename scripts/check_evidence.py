from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage3_extraction.models import Stage3Output
from risk_intel.stage4_validation.checks import check_evidence, load_page_tokens

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
page_tokens = load_page_tokens(pdf)
stage3 = Stage3Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage3.json").read_text())

print("--- real records ---")
for r in stage3.risks:
    coverage, issue = check_evidence(r, page_tokens)
    print(f"{coverage:5.0%}  p{r.source.page}  {r.title[:55]:55s} {issue.severity if issue else 'ok'}")

print("\n--- two deliberate faults (should both be flagged) ---")
geo = stage3.risks[0]
wrong_page = geo.model_copy(update={"source": geo.source.model_copy(update={"page": 73})})
invented = geo.model_copy(update={"source": geo.source.model_copy(update={
    "evidence": "Vestas holds a EUR 500 million reserve fund specifically for geopolitical shocks."})})
for label, fault in (("wrong page", wrong_page), ("invented text", invented)):
    coverage, issue = check_evidence(fault, page_tokens)
    print(f"{label:14s} coverage {coverage:4.0%} -> {issue.severity if issue else 'NOT FLAGGED'}")