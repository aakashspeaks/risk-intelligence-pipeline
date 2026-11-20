import pytest

from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage2_candidates.runner import run_stage2

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
STAGE1_JSON = INTERIM_DIR / "VestasAnnualReport2025.stage1.json"
pytestmark = pytest.mark.skipif(
    not (PDF.exists() and STAGE1_JSON.exists()),
    reason="needs the PDF in data/raw and the Stage 1 output in data/interim",
)

PRINCIPAL_TITLES = {
    "Geopolitics and regulatory framework",
    "Project execution",
    "Cyber attacks",
}
TABLE_TITLES = {
    "Low-emission materials",
    "Growth rate of the wind industry",
    "Carbon taxes and tariffs",
    "Recyclable blades",
    "Cost implication of injuries in own workforce",
    "Cost implications of injuries to contractors and sub-contractors",
    "Fines related to forced or child labour",
    "Insufficient market conditions",
    "Cyber security risks",
    "Risk of corruption and bribery",
}


@pytest.fixture(scope="module")
def result():
    return run_stage2(PDF)  # reads the PDF once, shared by every test below


def titles(result, tier):
    return {c.title for c in result.candidates if c.tier == tier}


def test_principal_risk_titles(result):
    assert titles(result, "principal") == PRINCIPAL_TITLES


def test_sustainability_table_titles(result):
    assert titles(result, "sustainability_iro") == TABLE_TITLES


def test_immaterial_statements_are_kept_not_returned_as_risks(result):
    assert len(result.immaterial_statements) == 8
    assert not any("scored as immaterial" in c.title for c in result.candidates)


def test_governance_review(result):
    g = result.governance
    assert g is not None
    assert g.review_frequency == "every six months"
    assert set(g.reviewed_by) == {"Executive Management Team", "Board of Directors", "Audit Committee"}
    assert g.page == 50


def test_every_candidate_has_text_and_a_source_page(result):
    for c in result.candidates:
        assert c.description.strip(), c.title
        assert c.page in result.pages_used, c.title
        assert c.evidence and c.description.startswith(c.evidence[:40]), c.title


def test_no_text_leaks_between_matrix_columns(result):
    by_title = {c.title: c for c in result.candidates if c.tier == "principal"}
    geo = by_title["Geopolitics and regulatory framework"]
    cyber = by_title["Cyber attacks"]
    assert "cyber" not in (geo.description + (geo.mitigation or "")).lower()
    assert "tariffs" not in (cyber.description + (cyber.mitigation or "")).lower()


def test_sections_attached(result):
    principal = [c for c in result.candidates if c.tier == "principal"]
    assert all("Risk management" in (c.section or "") for c in principal)
    assert all(c.section for c in result.candidates)