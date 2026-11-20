from risk_intel.config import INTERIM_DIR, PROJECT_ROOT, RAW_DIR
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.faults import run_with_spliced_columns
from risk_intel.stage5_evaluation.gate import THRESHOLDS, evaluate
from risk_intel.stage5_evaluation.golden import load_golden

pdf = RAW_DIR / "VestasAnnualReport2025.pdf"
out_file = PROJECT_ROOT / "reports" / "sample_run.md"

golden = load_golden()
page_tokens = load_page_tokens(pdf)
baseline = Stage4Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage4.json").read_text())
broken = run_with_spliced_columns(pdf)
good, bad = evaluate(baseline, golden, page_tokens), evaluate(broken, golden, page_tokens)

lines = [
    "# Sample run: a regression caught by the eval gate",
    "",
    "**Fault injected:** the page 51 matrix reader reads each row straight across all three risk "
    "columns, as a plain reader would. Titles stay correct, but every risk receives the spliced text "
    "of all three risks.",
    "",
    f"**Result:** baseline {'PASS' if good.passed else 'FAIL'}, "
    f"regression {'PASS' if bad.passed else 'FAIL'}.",
    "",
    "| gate | threshold | baseline | regression | status |",
    "|---|---|---|---|---|",
]
for name, minimum in THRESHOLDS.items():
    status = "FAIL" if bad.scores[name] < minimum else "ok"
    lines.append(f"| {name} | {minimum} | {good.scores[name]} | {bad.scores[name]} | {status} |")

lines += ["", "**What the evaluator reported:**", ""]
lines += [f"- {item}" for item in bad.details.get("contamination", [])]

lost = bad.details.get("mitigation_missing", [])
if lost:
    lines += ["", "**Mitigation phrases the broken run lost:**", ""]
    lines += [f"- {item}" for item in lost]

lines += [
    "",
    "**Why this matters:** contamination is the primary detector. All three principal risks received "
    "words from a neighbouring risk, and no other check looks for that. One expected mitigation phrase "
    "was also missing from the Cyber attacks record, so mitigation coverage failed too. "
    "We have not investigated why that particular phrase was lost.",
    "",
    "The gates that compare a record's text with its page (grounding, evidence accuracy) stayed at "
    "1.0, because the spliced words really are on page 51. A check that only asked whether the text "
    "appears on the page would have let this regression through.",
]

out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("saved to:", out_file)