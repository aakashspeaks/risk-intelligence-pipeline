import pytest

from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.stage4_validation.runner import run_stage4

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
STAGE1_JSON = INTERIM_DIR / "VestasAnnualReport2025.stage1.json"
STAGE3_JSON = INTERIM_DIR / "VestasAnnualReport2025.stage3.json"
pytestmark = pytest.mark.skipif(
    not (STAGE1_JSON.exists() and STAGE3_JSON.exists()),
    reason="run Stages 1 to 3 first",
)

OPPORTUNITIES = {"Low-emission materials", "Growth rate of the wind industry", "Recyclable blades"}


@pytest.fixture(scope="module")
def result():
    return run_stage4(PDF)


def test_twelve_records_with_unique_ids(result):
    ids = [r.id for r in result.risks]
    assert len(ids) == 12
    assert len(set(ids)) == 12


def test_cyber_is_merged_into_the_principal_risk(result):
    ids = {r.id for r in result.risks}
    assert "cyber-attacks" in ids
    assert "iro-cyber-security-risks" not in ids
    cyber = next(r for r in result.risks if r.id == "cyber-attacks")
    assert cyber.cross_references == [74]
    assert len(result.merges) == 1
    assert result.merges[0].merged_id == "iro-cyber-security-risks"
    assert result.merges[0].kept_id == "cyber-attacks"


def test_no_issues_on_the_real_records(result):
    assert result.issues == []


def test_risks_and_opportunities_stay_separate(result):
    opportunities = {r.title for r in result.risks if r.kind.value == "opportunity"}
    assert opportunities == OPPORTUNITIES
    assert sum(r.kind.value == "risk" for r in result.risks) == 9


def test_principal_risks_keep_impact_and_mitigation_after_merge(result):
    principal = [r for r in result.risks if r.tier == "principal"]
    assert len(principal) == 3
    for r in principal:
        assert r.potential_impact and r.mitigation, r.title


def test_immaterial_topics_and_governance_are_carried_through(result):
    assert len(result.excluded_immaterial) == 8
    assert result.governance is not None
    assert result.governance.review_frequency == "every six months"