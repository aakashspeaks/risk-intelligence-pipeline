from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage3_extraction.models import Stage3Output
from risk_intel.stage4_validation.checks import check_section, load_page_sections

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
page_sections = load_page_sections(pdf)
stage3 = Stage3Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage3.json").read_text())

print("--- real records ---")
problems = [i for r in stage3.risks if (i := check_section(r, page_sections))]
print(f"{len(stage3.risks) - len(problems)} of {len(stage3.risks)} ok")
for issue in problems:
    print("  ", issue.risk_id, issue.message)

print("\n--- one deliberate fault (should be flagged) ---")
geo = stage3.risks[0]
moved = geo.model_copy(update={"source": geo.source.model_copy(update={"page": 71})})
issue = check_section(moved, page_sections)
print(issue.severity + ": " + issue.message if issue else "NOT FLAGGED")