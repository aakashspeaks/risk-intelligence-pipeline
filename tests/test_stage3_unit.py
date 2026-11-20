from risk_intel.stage3_extraction.categorise import categorise
from risk_intel.stage3_extraction.kind import classify_kind
from risk_intel.stage3_extraction.models import Category, Kind
from risk_intel.stage3_extraction.sentences import first_sentences, split_sentences


def test_category_rules_and_their_order():
    assert categorise("Cyber security risks") == Category.cyber
    # 'carbon tax' must win over the later 'tariff' rule, so this is climate, not regulatory
    assert categorise("Carbon taxes and tariffs") == Category.climate
    assert categorise("Something unrelated") == Category.other


def test_kind_risk_or_opportunity():
    opportunity_text = "Offering low emission materials presents a financial opportunity."
    assert classify_kind(opportunity_text, "sustainability_iro") == Kind.opportunity
    assert classify_kind("Cyber attacks might disrupt business.", "sustainability_iro") == Kind.risk
    # principal risks are risks by definition, whatever their wording
    assert classify_kind(opportunity_text, "principal") == Kind.risk


def test_abbreviation_does_not_split_a_sentence():
    text = "Governments, e.g. the EU, add rules. Costs rise. Margins fall. A fourth sentence."
    assert len(split_sentences(text)) == 4


def test_first_sentences_keeps_at_most_n():
    text = "One. Two. Three. Four."
    assert first_sentences(text, 3) == "One. Two. Three."
    assert first_sentences("Only one.", 3) == "Only one."