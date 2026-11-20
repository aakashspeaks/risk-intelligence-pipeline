from risk_intel.config import RAW_DIR
from risk_intel.stage2_candidates.matrix_reader import read_matrix
from risk_intel.stage2_candidates.table_reader import read_tables

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
GROUPS = {
    "FALSE ALARMS": [76, 77, 78, 101, 158],
    "CASE PAGES, for comparison": [51, 71, 85],
}

for label, pages in GROUPS.items():
    print(f"\n=== {label}")
    for n in pages:
        try:
            matrix = f"{len(read_matrix(PDF, n))} candidates"
        except ValueError:
            matrix = "rejected (no row labels)"
        tables, _ = read_tables(PDF, [n])
        print(f"p{n}: matrix reader -> {matrix}; table reader -> {len(tables)} candidates")