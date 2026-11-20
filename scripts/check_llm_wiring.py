import json
import re
from collections import Counter

from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.build import to_risk
from risk_intel.stage3_extraction.sentences import split_sentences

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())


def source_of(messages):
    return re.search(r"<source>\n(.*?)\n</source>", messages[1]["content"], re.DOTALL).group(1)


def echo_two_sentences(messages):
    """A fake model that returns the first two sentences of whatever source it is given."""
    return json.dumps({"summary": " ".join(split_sentences(source_of(messages))[:2])})


def invents_a_figure(messages):
    return json.dumps({"summary": "Vestas holds a EUR 500 million reserve."})


def show(label, summariser):
    risks = [to_risk(c, summariser, "fake") for c in stage2.candidates]
    origins = Counter(r.description_origin.split(" (")[0] for r in risks)
    print(f"\n{label}")
    print("  origins:", dict(origins))
    principal = [r for r in risks if r.tier == "principal"]
    print("  principal sentence counts:", [len(split_sentences(r.description)) for r in principal])
    return risks


show("no summariser (the default)", None)
show("a faithful fake model", echo_two_sentences)
show("a fake model that invents a figure", invents_a_figure)