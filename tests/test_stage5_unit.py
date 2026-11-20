import pytest

from risk_intel.stage2_candidates.models import GovernanceCandidate
from risk_intel.stage3_extraction.models import Category, Kind, Risk, Source
from risk_intel.stage4_validation.checks import tokens
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.content_evaluators import (
    contamination, evidence_accuracy, governance_check, grounding, mitigation_coverage)
from risk_intel.stage5_evaluation.evaluators import field_accuracy, immaterial_leak, recall_precision
from risk_intel.stage5_evaluation.gate import evaluate
from risk_intel.stage5_evaluation.golden import Golden, GoldenGovernance, GoldenRisk
from risk_intel.stage5_evaluation.matching import match_records, normalise

PAGE_TOKENS = {51: tokens("alpha beta gamma delta epsilon zeta")}
GOVERNANCE = GovernanceCandidate(review_frequency="every six months",
                                 reviewed_by=["Board of Directors"], page=50, evidence="x")


def g_risk(title, tier="principal", kind="risk", category="cyber", page=51, must=None, forbidden=None):
    return GoldenRisk(id=title.lower().replace(" ", "-"), title=title, tier=tier, kind=kind,
                      category=category, page=page, must_mention_in_mitigation=must or [],
                      forbidden_terms=forbidden or [])


def make_golden(risks, banned=None):
    return Golden(report="test",
                  governance=GoldenGovernance(review_frequency="every six months",
                                              reviewed_by=["Board of Directors"], page=50),
                  risks=risks, must_not_be_returned_as_risks=banned or [])


def make_risk(title, category=Category.cyber, tier="principal", kind=Kind.risk, page=51,
              evidence="alpha beta gamma", description="Alpha beta gamma delta.", mitigation=None):
    return Risk(id=title.lower().replace(" ", "-"), title=title, description=description,
                category=category, kind=kind, tier=tier, mitigation=mitigation,
                source=Source(section="Sec", page=page, method="matrix", evidence=evidence))


# ---- matching ---------------------------------------------------------------------------------
def test_normalise_ignores_case_and_punctuation():
    assert normalise("Cyber-attacks, 2025!") == "cyber attacks 2025"


def test_small_wording_change_still_matches():
    matched, missed, extra = match_records([g_risk("Cyber attacks")], [make_risk("Cyber attack")])
    assert len(matched) == 1 and missed == [] and extra == []


def test_dropped_record_is_missed():
    golden = [g_risk("Cyber attacks"), g_risk("Project execution", category="operational")]
    _, missed, _ = match_records(golden, [make_risk("Cyber attacks")])
    assert [g.title for g in missed] == ["Project execution"]


def test_invented_record_is_extra():
    output = [make_risk("Cyber attacks"), make_risk("Satellite launch delays")]
    _, _, extra = match_records([g_risk("Cyber attacks")], output)
    assert [r.title for r in extra] == ["Satellite launch delays"]


def test_one_output_record_cannot_match_two_golden_records_or_the_reverse():
    matched, _, extra = match_records([g_risk("Cyber attacks")],
                                      [make_risk("Cyber attacks"), make_risk("Cyber attack")])
    assert len(matched) == 1 and len(extra) == 1


# ---- basic evaluators ---------------------------------------------------------------------------
def test_recall_and_precision_when_a_principal_risk_is_dropped():
    golden = make_golden([
        g_risk("Cyber attacks"),
        g_risk("Project execution", category="operational"),
        g_risk("Carbon taxes and tariffs", tier="sustainability_iro", category="climate", page=71),
    ])
    risks = [make_risk("Cyber attacks"),
             make_risk("Carbon taxes and tariffs", category=Category.climate,
                       tier="sustainability_iro", page=71)]
    result = recall_precision(golden, risks)
    assert result["recall"] == pytest.approx(2 / 3)
    assert result["principal_recall"] == pytest.approx(1 / 2)
    assert result["precision"] == 1.0
    assert result["missed"] == ["Project execution"]


def test_field_accuracy_names_the_mistake():
    golden = make_golden([g_risk("Cyber attacks", category="cyber")])
    result = field_accuracy(golden, [make_risk("Cyber attacks", category=Category.financial)])
    assert result["category_accuracy"] == 0.0
    assert "category is 'financial'" in result["mistakes"][0]


def test_immaterial_topic_returned_as_a_risk_is_flagged():
    golden = make_golden([], banned=["Biodiversity-related risks and opportunities"])
    leaked = immaterial_leak(golden, [make_risk("Biodiversity-related risks and opportunities")])
    assert leaked["leak_free"] is False
    assert immaterial_leak(golden, [make_risk("Cyber attacks")])["leak_free"] is True


# ---- content evaluators -------------------------------------------------------------------------
def test_evidence_accuracy_flags_a_quote_that_is_not_on_the_page():
    good = make_risk("Cyber attacks", evidence="alpha beta gamma")
    bad = make_risk("Project execution", evidence="something else entirely")
    assert evidence_accuracy([good, bad], PAGE_TOKENS)["evidence_accuracy"] == 0.5


def test_grounding_catches_an_invented_sentence():
    good = make_risk("Cyber attacks", description="Alpha beta gamma delta.")
    bad = make_risk("Project execution", description="Completely invented sentence appears here.")
    assert grounding([good], PAGE_TOKENS)["grounding"] == 1.0
    result = grounding([bad], PAGE_TOKENS)
    assert result["grounding"] == 0.0 and result["ungrounded"]


def test_mitigation_coverage_needs_the_key_phrase():
    golden = make_golden([g_risk("Cyber attacks", must=["alpha beta"])])
    present = mitigation_coverage(golden, [make_risk("Cyber attacks", mitigation="Alpha beta gamma.")])
    absent = mitigation_coverage(golden, [make_risk("Cyber attacks", mitigation="Gamma only.")])
    assert present["mitigation_coverage"] == 1.0
    assert absent["mitigation_coverage"] == 0.0
    assert "alpha beta" in absent["mitigation_missing"][0]


def test_contamination_score_and_message():
    golden = make_golden([
        g_risk("Cyber attacks", forbidden=["tariffs"]),
        g_risk("Project execution", category="operational", forbidden=["cyber"]),
    ])
    risks = [make_risk("Cyber attacks", description="Alpha beta. Tariffs and sanctions."),
             make_risk("Project execution", category=Category.operational)]
    result = contamination(golden, risks)
    assert result["contamination_free"] == 0.5
    assert len(result["contamination"]) == 1 and "tariffs" in result["contamination"][0]


def test_governance_check():
    golden = make_golden([])
    assert governance_check(golden, GOVERNANCE)["governance"] == 1.0
    assert governance_check(golden, None)["governance"] == 0.0
    wrong = governance_check(golden, GOVERNANCE.model_copy(update={"review_frequency": "every year"}))
    assert wrong["governance"] == 0.0 and "frequency" in wrong["governance_problems"][0]


# ---- the gate -----------------------------------------------------------------------------------
def gate_fixture():
    golden = make_golden([
        g_risk("Cyber attacks", must=["alpha"], forbidden=["tariffs"]),
        g_risk("Project execution", category="operational"),
    ])
    risks = [make_risk("Cyber attacks", mitigation="Alpha beta."),
             make_risk("Project execution", category=Category.operational)]
    return golden, risks


def stage4(risks):
    return Stage4Output(source_file="x.pdf", risks=risks, excluded_immaterial=[], governance=GOVERNANCE)


def test_gate_passes_on_a_correct_output():
    golden, risks = gate_fixture()
    report = evaluate(stage4(risks), golden, PAGE_TOKENS)
    assert report.passed and report.failed == {}


def test_gate_fails_when_a_principal_risk_is_dropped():
    golden, risks = gate_fixture()
    report = evaluate(stage4(risks[:1]), golden, PAGE_TOKENS)
    assert not report.passed
    assert set(report.failed) == {"recall", "principal_recall"}