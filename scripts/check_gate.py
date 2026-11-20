from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.gate import THRESHOLDS, evaluate
from risk_intel.stage5_evaluation.golden import load_golden

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
golden = load_golden()
output = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())
page_tokens = load_page_tokens(pdf)


def show(label, out):
    report = evaluate(out, golden, page_tokens)
    print(f"\n{label}: {'PASS' if report.passed else 'FAIL'}")
    if report.failed:
        print("  failed gates:", report.failed)


show("real output", output)
print("  gates checked:", len(THRESHOLDS))

fewer = [r for r in output.risks if r.id != "project-execution"]
show("fault: project execution dropped", output.model_copy(update={"risks": fewer}))

cyber = next(r for r in output.risks if r.id == "cyber-attacks")
invented = [r.model_copy(update={"mitigation": cyber.mitigation + " Vestas also holds a EUR 500 million cyber insurance reserve."})
            if r.id == "cyber-attacks" else r for r in output.risks]
show("fault: one invented sentence", output.model_copy(update={"risks": invented}))