import pytest

from risk_intel.config import GOLDEN_DIR, INTERIM_DIR, RAW_DIR
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.faults import run_with_spliced_columns
from risk_intel.stage5_evaluation.gate import evaluate
from risk_intel.stage5_evaluation.golden import load_golden

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
STAGE1_JSON = INTERIM_DIR / "VestasAnnualReport2025.stage1.json"
STAGE4_JSON = INTERIM_DIR / "VestasAnnualReport2025.stage4.json"
GOLDEN_JSON = GOLDEN_DIR / "vestas_golden.json"
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in (PDF, STAGE1_JSON, STAGE4_JSON, GOLDEN_JSON)),
    reason="run Stages 1 to 4 first and put the golden file in data/golden",
)


@pytest.fixture(scope="module")
def golden():
    return load_golden()


@pytest.fixture(scope="module")
def page_tokens():
    return load_page_tokens(PDF)


@pytest.fixture(scope="module")
def baseline():
    return Stage4Output.model_validate_json(STAGE4_JSON.read_text(encoding="utf-8"))


def test_golden_set_has_the_expected_shape(golden):
    # If you edit the golden file (add or remove records), update these numbers to match.
    assert len(golden.risks) == 12
    assert sum(g.tier == "principal" for g in golden.risks) == 3
    assert sum(g.kind == "opportunity" for g in golden.risks) == 3
    assert len(golden.must_not_be_returned_as_risks) == 8


def test_real_pipeline_passes_every_gate(baseline, golden, page_tokens):
    report = evaluate(baseline, golden, page_tokens)
    assert report.passed, report.failed
    assert len(report.scores) == 13


def test_spliced_columns_regression_is_caught_by_the_contamination_gate(golden, page_tokens):
    broken = run_with_spliced_columns(PDF)
    report = evaluate(broken, golden, page_tokens)
    assert not report.passed
    # contamination is the primary detector: all three principal risks leak neighbour words
    assert "contamination_free" in report.failed
    assert len(report.details["contamination"]) >= 3
    # a phrase can also be broken at a line wrap, so mitigation coverage may fail too,
    # but the gates that compare text with the page must still pass: the spliced words are on the page
    assert {"grounding", "evidence_accuracy", "recall", "precision"}.isdisjoint(report.failed)

def test_fault_injection_puts_the_real_reader_back():
    from risk_intel.stage2_candidates import runner
    from risk_intel.stage2_candidates.matrix_reader import read_matrix

    run_with_spliced_columns(PDF)
    assert runner.read_matrix is read_matrix