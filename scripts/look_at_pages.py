from risk_intel.config import INTERIM_DIR
from risk_intel.stage1_document.models import DocumentLayout

doc = DocumentLayout.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage1.json").read_text())

for n in (118, 85):
    p = doc.pages[n - 1]
    print(f"\n{'=' * 70}\nPAGE {n}: {p.layout_type}, {p.n_columns} columns, {p.n_rule_lines} rules, title {p.title!r}")
    print(f"section: {p.part} > {p.section}")
    print(p.text[:1500])