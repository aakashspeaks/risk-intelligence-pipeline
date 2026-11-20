from collections import Counter

from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.pipeline import run_pipeline

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
result = run_pipeline(pdf)
output = result.output

print("final file:", result.final_file)
print("records:", len(output.risks), dict(Counter(r.kind.value for r in output.risks)))
print("issues:", len(output.issues), "| merges:", len(output.merges))
print("governance:", output.governance.review_frequency if output.governance else None)
print("descriptions from:", dict(Counter(r.description_origin for r in output.risks)))

print("\nseconds per stage:")
for stage, secs in result.seconds.items():
    print(f"  {stage:20s} {secs:5.1f}")
print(f"  {'total':20s} {sum(result.seconds.values()):5.1f}")

stage4_file = INTERIM_DIR / "VestasAnnualReport2025.stage4.json"
print("\nfinal file identical to the Stage 4 file:", result.final_file.read_text() == stage4_file.read_text())

for bad in ("missing.pdf", "notes.txt"):
    try:
        run_pipeline(RAW_DIR / bad)
    except (FileNotFoundError, ValueError) as error:
        print(f"{bad}: {type(error).__name__}")