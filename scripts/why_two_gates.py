from risk_intel.config import RAW_DIR
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage5_evaluation.faults import run_with_spliced_columns
from risk_intel.stage5_evaluation.gate import evaluate
from risk_intel.stage5_evaluation.golden import load_golden

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
report = evaluate(run_with_spliced_columns(pdf), load_golden(), load_page_tokens(pdf))

print("failed gates:", report.failed)
print("\nmitigation phrases the broken run lost:")
for item in report.details.get("mitigation_missing", []):
    print("  ", item)
print("\ncontamination:")
for item in report.details.get("contamination", []):
    print("  ", item)