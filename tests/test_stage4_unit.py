from risk_intel.stage3_extraction.models import Category, Kind, Risk, Source
from risk_intel.stage4_validation.checks import (
    check_evidence, check_section, ordered_coverage, tokens)
from risk_intel.stage4_validation.dedupe import merge_duplicates


def make_risk(id, title, category, tier="principal", kind=Kind.risk, page=51,
              evidence="some evidence", section="Sec"):
    return Risk(id=id, title=title, description="d", category=category, kind=kind, tier=tier,
                source=Source(section=section, page=page, method="matrix", evidence=evidence))


# ---- evidence check ---------------------------------------------------------------------------
def test_tokens_ignore_case_and_punctuation():
    assert tokens("Cyber-attacks, 2025!") == ["cyber", "attacks", "2025"]


def test_coverage_allows_words_in_between():
    assert ordered_coverage(tokens("alpha gamma"), tokens("alpha beta gamma delta")) == 1.0
    # the saved page text interleaves columns, so other words sit between the quote's words
    assert ordered_coverage(tokens("alpha beta gamma"), tokens("alpha x beta y gamma")) == 1.0


def test_coverage_requires_the_same_order():
    assert ordered_coverage(tokens("gamma alpha"), tokens("alpha beta gamma")) == 0.5


def test_last_word_may_be_a_cut_off_beginning():
    assert ordered_coverage(["the", "cybe"], ["the", "cyber", "attack"]) == 1.0


def test_empty_quote_has_zero_coverage():
    assert ordered_coverage([], tokens("alpha beta")) == 0.0


def test_evidence_check_flags_a_missing_page():
    risk = make_risk("a", "A", Category.cyber, page=999)
    coverage, issue = check_evidence(risk, {51: tokens("alpha beta")})
    assert coverage == 0.0
    assert issue.check == "page" and issue.severity == "error"


def test_evidence_check_passes_real_text_and_flags_invented_text():
    pages = {51: tokens("alpha beta gamma delta")}
    good = make_risk("a", "A", Category.cyber, evidence="alpha beta gamma")
    bad = make_risk("b", "B", Category.cyber, evidence="completely different words here")
    assert check_evidence(good, pages) == (1.0, None)
    coverage, issue = check_evidence(bad, pages)
    assert coverage == 0.0 and issue.severity == "error"


# ---- section check ----------------------------------------------------------------------------
def test_section_check():
    sections = {51: "Sec"}
    assert check_section(make_risk("a", "A", Category.cyber, section="Sec"), sections) is None
    issue = check_section(make_risk("a", "A", Category.cyber, section="Other"), sections)
    assert issue.check == "section" and issue.severity == "warning"
    assert check_section(make_risk("a", "A", Category.cyber, page=999), sections) is None


# ---- duplicate detection ----------------------------------------------------------------------
def test_table_entry_is_folded_into_matching_principal_risk():
    principal = make_risk("cyber-attacks", "Cyber attacks", Category.cyber)
    table = make_risk("iro-cyber-security-risks", "Cyber security risks", Category.cyber,
                      tier="sustainability_iro", page=74)
    merged, merges = merge_duplicates([principal, table])
    assert len(merged) == 1 and len(merges) == 1
    assert merged[0].cross_references == [74]
    assert principal.cross_references == []   # the input was not changed


def test_opportunity_is_never_merged_into_a_risk():
    principal = make_risk("cyber-attacks", "Cyber attacks", Category.cyber)
    opportunity = make_risk("x", "Cyber insurance opportunity", Category.cyber,
                            tier="sustainability_iro", kind=Kind.opportunity, page=74)
    merged, merges = merge_duplicates([principal, opportunity])
    assert len(merged) == 2 and merges == []


def test_different_category_is_not_merged():
    principal = make_risk("cyber-attacks", "Cyber attacks", Category.cyber)
    other = make_risk("x", "Cyber costs", Category.climate, tier="sustainability_iro", page=74)
    assert merge_duplicates([principal, other])[1] == []


def test_same_category_without_a_shared_word_is_not_merged():
    principal = make_risk("cyber-attacks", "Cyber attacks", Category.cyber)
    other = make_risk("x", "Data breach penalties", Category.cyber, tier="sustainability_iro", page=74)
    assert merge_duplicates([principal, other])[1] == []