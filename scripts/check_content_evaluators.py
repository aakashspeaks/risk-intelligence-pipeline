from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.content_evaluators import evaluate_content
from risk_intel.stage5_evaluation.golden import load_golden

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
golden = load_golden()
output = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())
page_tokens = load_page_tokens(pdf)
SCORES = ["evidence_accuracy", "grounding", "mitigation_coverage", "contamination_free", "governance"]


def show(label, risks, governance=output.governance):
    result = evaluate_content(golden, risks, governance, page_tokens)
    print(f"\n{label}")
    print("  " + "  ".join(f"{name}={result[name]:.2f}" for name in SCORES))
    for key in ("evidence_flagged", "ungrounded", "mitigation_missing", "contamination", "governance_problems"):
        if result[key]:
            print(f"  {key}: {result[key][:3]}")


def change(risk_id, **fields):
    return [r.model_copy(update=fields) if r.id == risk_id else r for r in output.risks]


cyber = next(r for r in output.risks if r.id == "cyber-attacks")
project = next(r for r in output.risks if r.id == "project-execution")
geo = next(r for r in output.risks if r.id == "geopolitics-and-regulatory-framework")

show("real output", output.risks)

show("A. an invented sentence in the cyber mitigation",
     change("cyber-attacks", mitigation=cyber.mitigation + " Vestas also holds a EUR 500 million cyber insurance reserve."))

show("B. words from a neighbouring column leak into the cyber description",
     change("cyber-attacks", description=cyber.description + " Tariffs and sanctions."))

show("C. the project execution mitigation is cut short",
     change("project-execution", mitigation=project.mitigation[:30]))

show("D. a record points at the wrong page",
     change("geopolitics-and-regulatory-framework", source=geo.source.model_copy(update={"page": 73})))

wrong_governance = output.governance.model_copy(update={"review_frequency": "every year"})
show("E. wrong review frequency", output.risks, wrong_governance)