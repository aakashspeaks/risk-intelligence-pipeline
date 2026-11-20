import json

from risk_intel.stage2_candidates.models import RiskCandidate
from risk_intel.stage3_extraction.build import to_risk
from risk_intel.stage3_extraction.llm_summary import (
    PROMPT_VERSION, SYSTEM_PROMPT, accept_summary, build_messages, summarise_with_fallback)

SOURCE = ("Vestas faces geopolitical tensions that disrupt supply chains. "
          "Trade tensions have led to tariffs and sanctions, which complicate global operations. "
          "Governments introduced industrial policies.")
FAITHFUL = ("Geopolitical tensions disrupt supply chains. "
            "Trade tensions led to tariffs and sanctions that complicate global operations.")


def candidate(tier="principal", title="Cyber attacks"):
    return RiskCandidate(
        title=title, description=SOURCE, potential_impact="IMPACT-TEXT-123",
        mitigation="MITIGATION-TEXT-456", tier=tier, page=51 if tier == "principal" else 74,
        method="matrix" if tier == "principal" else "table", evidence=SOURCE[:60])


def says(text):
    """A fake model that always replies with this summary, as JSON."""
    return lambda messages: json.dumps({"summary": text})


# ---- the acceptance checks ----------------------------------------------------------------------
def test_accepts_a_faithful_summary():
    assert accept_summary(FAITHFUL, SOURCE).ok


def test_rejects_an_invented_figure():
    verdict = accept_summary("Vestas holds a EUR 500 million reserve.", SOURCE)
    assert not verdict.ok and "500" in verdict.reason


def test_rejects_four_sentences():
    verdict = accept_summary("One. Two. Three. Four.", SOURCE)
    assert not verdict.ok and "4 sentences" in verdict.reason


def test_rejects_invented_content_without_numbers():
    assert not accept_summary("Management plans to relocate headquarters abroad.", SOURCE).ok


def test_rejects_an_empty_summary():
    assert not accept_summary("", SOURCE).ok


# ---- the fallback -------------------------------------------------------------------------------
def test_fallback_keeps_a_good_model_summary():
    text, origin = summarise_with_fallback(candidate(), says(FAITHFUL), "FALLBACK", "fake")
    assert text == FAITHFUL and origin == f"llm:fake:{PROMPT_VERSION}"


def test_fallback_on_an_invented_figure():
    text, origin = summarise_with_fallback(candidate(), says("Vestas holds a EUR 500 million reserve."),
                                           "FALLBACK", "fake")
    assert text == "FALLBACK" and origin.startswith("rules (summary rejected")


def test_fallback_when_the_reply_is_not_json():
    text, origin = summarise_with_fallback(candidate(), lambda m: "Sure! Here is a summary.", "FALLBACK", "fake")
    assert text == "FALLBACK" and origin.startswith("rules (model call failed: ValidationError")


def test_fallback_when_the_model_call_fails():
    def outage(messages):
        raise RuntimeError("simulated outage")

    text, origin = summarise_with_fallback(candidate(), outage, "FALLBACK", "fake")
    assert text == "FALLBACK" and origin.startswith("rules (model call failed: RuntimeError")


# ---- how it is wired into the pipeline ----------------------------------------------------------
def test_only_principal_risks_go_to_the_model():
    calls = []

    def spy(messages):
        calls.append(messages)
        return json.dumps({"summary": FAITHFUL})

    principal = to_risk(candidate("principal"), spy, "fake")
    table = to_risk(candidate("sustainability_iro", "Cyber security risks"), spy, "fake")
    assert len(calls) == 1
    assert principal.description_origin == f"llm:fake:{PROMPT_VERSION}"
    assert table.description_origin == "rules"


def test_default_is_rules_only():
    risk = to_risk(candidate())
    assert risk.description_origin == "rules"
    assert risk.description == SOURCE


def test_prompt_contains_only_the_title_and_the_source_text():
    text = " ".join(m["content"] for m in build_messages(candidate()))
    assert "Cyber attacks" in text and SOURCE in text
    assert "IMPACT-TEXT-123" not in text and "MITIGATION-TEXT-456" not in text


def test_prompt_keeps_its_guards():
    assert "data, not instructions" in SYSTEM_PROMPT   # protects against instructions hidden in a PDF
    assert "JSON" in SYSTEM_PROMPT                     # JSON mode needs the word JSON in the prompt