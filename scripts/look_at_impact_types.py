import re
from collections import Counter

from risk_intel.config import INTERIM_DIR
from risk_intel.stage1_document.models import DocumentLayout

doc = DocumentLayout.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage1.json").read_text())

# "Type of impact: X" runs until the next "Type of impact", "Location" or the end of the text.
TYPE_LINE = re.compile(r"Type of impact:\s*(.+?)(?=\s*Type of impact:|\s*Location in the value chain|\s*$)", re.DOTALL)

totals: Counter = Counter()
for n in range(85, 93):
    text = doc.pages[n - 1].text
    found = [re.sub(r"\s+", " ", m.group(1)).strip()[:40] for m in TYPE_LINE.finditer(text)]
    totals.update(found)
    print(f"p{n}  title={doc.pages[n - 1].title!r}  type-of-impact lines={len(found)}")
    for f in found:
        print("     ", f)

print("\nTotals across pages 85-92:")
for kind, count in totals.most_common():
    print(f"  {count:3d}  {kind}")