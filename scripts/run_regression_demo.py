from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.faults import run_with_spliced_columns
from risk_intel.stage5_evaluation.gate import evaluate
from risk_intel.stage5_evaluation.golden import load_golden

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
golden = load_golden()
page_tokens = load_page_tokens(pdf)


def show(label, output):
    report = evaluate(output, golden, page_tokens)
    print(f"\n{label}: {'PASS' if report.passed else 'FAIL'}")
    print("  scores:", report.scores)
    if report.failed:
        print("  failed gates:", report.failed)
    for key in ("contamination", "ungrounded", "evidence_flagged", "mitigation_missing"):
        if report.details.get(key):
            print(f"  {key}:", report.details[key][:4])


baseline = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())
show("baseline (real pipeline)", baseline)

broken = run_with_spliced_columns(pdf)
show("regression: columns spliced", broken)

geo = next(r for r in broken.risks if r.id == "geopolitics-and-regulatory-framework")
print("\nin the broken run, the geopolitics description contains 'cyber':", "cyber" in geo.description.lower())