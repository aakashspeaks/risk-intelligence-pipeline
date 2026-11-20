import pytest

from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage3_extraction.runner import run_stage3
from risk_intel.stage3_extraction.sentences import split_sentences

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
STAGE2_JSON = INTERIM_DIR / "VestasAnnualReport2025.stage2.json"
pytestmark = pytest.mark.skipif(not STAGE2_JSON.exists(), reason="run Stage 2 first")

OPPORTUNITIES = {"Low-emission materials", "Growth rate of the wind industry", "Recyclable blades"}

# These expected categories are my own judgment, written at the same time as the rules.
# They protect against accidental changes; the golden set you label yourself will be the real test.
EXPECTED_CATEGORIES = {
    "Geopolitics and regulatory framework": "regulatory_geopolitical",
    "Project execution": "operational",
    "Cyber attacks": "cyber",
    "Low-emission materials": "climate",
    "Growth rate of the wind industry": "market",
    "Carbon taxes and tariffs": "climate",
    "Recyclable blades": "environmental",
    "Cost implication of injuries in own workforce": "health_safety",
    "Cost implications of injuries to contractors and sub-contractors": "health_safety",
    "Fines related to forced or child labour": "human_rights",
    "Insufficient market conditions": "market",
    "Cyber security risks": "cyber",
    "Risk of corruption and bribery": "compliance_conduct",
}


@pytest.fixture(scope="module")
def result():
    return run_stage3(PDF)


def test_thirteen_records_with_unique_ids(result):
    ids = [r.id for r in result.risks]
    assert len(ids) == 13
    assert len(set(ids)) == 13


def test_opportunities_are_labelled_and_kept_out_of_risks(result):
    opportunities = {r.title for r in result.risks if r.kind.value == "opportunity"}
    assert opportunities == OPPORTUNITIES
    risks = {r.title for r in result.risks if r.kind.value == "risk"}
    assert not (risks & OPPORTUNITIES)


def test_principal_risks_keep_impact_and_mitigation(result):
    principal = [r for r in result.risks if r.tier == "principal"]
    assert len(principal) == 3
    for r in principal:
        assert r.potential_impact and r.potential_impact.strip(), r.title
        assert r.mitigation and r.mitigation.strip(), r.title


def test_descriptions_are_at_most_three_sentences(result):
    for r in result.risks:
        assert 1 <= len(split_sentences(r.description)) <= 3, r.title


def test_categories(result):
    got = {r.title: r.category.value for r in result.risks}
    assert got == EXPECTED_CATEGORIES


def test_every_record_has_a_complete_source(result):
    for r in result.risks:
        assert r.source.page in {51, 71, 72, 73, 74}, r.title
        assert r.source.section, r.title
        assert r.source.evidence.strip(), r.title


def test_immaterial_topics_and_governance_are_carried_through(result):
    assert len(result.excluded_immaterial) == 8
    assert result.governance is not None
    assert result.governance.review_frequency == "every six months"