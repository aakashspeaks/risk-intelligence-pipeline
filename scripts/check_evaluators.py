from risk_intel.config import INTERIM_DIR
from risk_intel.stage3_extraction.models import Category, Kind
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.evaluators import evaluate_basic
from risk_intel.stage5_evaluation.golden import load_golden

golden = load_golden()
output = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())
SCORES = ["recall", "precision", "principal_recall", "category_accuracy", "kind_accuracy", "tier_accuracy", "page_accuracy"]


def show(label, risks):
    result = evaluate_basic(golden, risks)
    print(f"\n{label}")
    print("  " + "  ".join(f"{name}={result[name]:.2f}" for name in SCORES))
    for key in ("missed", "extra", "leaked", "mistakes"):
        if result[key]:
            print(f"  {key}: {result[key]}")


show("real output", output.risks)

# Four deliberate faults. Each should hurt a different score.
show("1. drop 'Project execution'", [r for r in output.risks if r.title != "Project execution"])

wrong_category = [r.model_copy(update={"category": Category.financial}) if r.id == "project-execution" else r
                  for r in output.risks]
show("2. wrong category on one record", wrong_category)

wrong_kind = [r.model_copy(update={"kind": Kind.risk}) if r.id == "iro-recyclable-blades" else r
              for r in output.risks]
show("3. an opportunity labelled as a risk", wrong_kind)

leak = output.risks[0].model_copy(update={"id": "leak", "title": "Biodiversity-related risks and opportunities"})
show("4. a ruled-out topic returned as a risk", output.risks + [leak])