from risk_intel.config import INTERIM_DIR
from risk_intel.stage1_document.models import DocumentLayout
from risk_intel.stage2_candidates.page_finder import find_candidate_pages

doc = DocumentLayout.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage1.json").read_text())
ranked = find_candidate_pages(doc)
rank = {c.page_number: i + 1 for i, c in enumerate(ranked)}
score = {c.page_number: c.score for c in ranked}

print("Where the case pages ranked, out of", len(ranked))
for n in [50, 51, 71, 72, 73, 74, 85, 118]:
    print(f"  page {n:3d}: rank {rank[n]:3d}, score {score[n]}")

print("\nFalse-alarm pages: what Stage 1 knows about them")
for n in [76, 77, 78, 101, 158]:
    p = doc.pages[n - 1]
    print(f"  page {n:3d}: {p.part} > {p.section} | {p.title}")