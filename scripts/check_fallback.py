import json

from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.llm_summary import summarise_with_fallback
from risk_intel.stage3_extraction.sentences import first_sentences

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())
candidate = next(c for c in stage2.candidates if c.title == "Geopolitics and regulatory framework")
fallback = first_sentences(candidate.description, 3)


def reply(text):
    return lambda messages: json.dumps({"summary": text})


def broken(messages):
    raise RuntimeError("simulated outage")


FAKES = {
    "faithful summary": reply("Vestas faced geopolitical tensions that disrupt supply chains and complicate global operations."),
    "invented figure": reply("Vestas holds a EUR 500 million reserve for geopolitical shocks."),
    "not JSON": lambda messages: "Sure! Here is a summary.",
    "model call fails": broken,
}

for label, fake in FAKES.items():
    text, origin = summarise_with_fallback(candidate, fake, fallback, "fake-model")
    print(f"{label:18s} -> {origin}")
    print(f"{'':21s}uses rule-based text: {text == fallback}")