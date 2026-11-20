from risk_intel.config import INTERIM_DIR
from risk_intel.stage1_document.models import DocumentLayout
from risk_intel.stage2_candidates.page_finder import find_candidate_pages

doc = DocumentLayout.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage1.json").read_text())
ranked = find_candidate_pages(doc)
rank = {c.page_number: i + 1 for i, c in enumerate(ranked)}
by_page = {c.page_number: c for c in ranked}

for label, pages in (("LOW-RANKED CASE PAGES", [72, 73, 74, 85]),
                     ("HIGH-RANKED FALSE ALARMS", [76, 77, 78, 101, 158])):
    print(f"\n=== {label}")
    for n in pages:
        p, c = doc.pages[n - 1], by_page[n]
        print(f"p{n}  rank {rank[n]}  score {c.score}  [{p.layout_type}]")
        print(f"    {p.part} > {p.section} | {p.title}")
        print(f"    reasons: {c.reasons}")