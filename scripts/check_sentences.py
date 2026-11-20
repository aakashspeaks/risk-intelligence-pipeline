from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.sentences import first_sentences, split_sentences

# Self-check on a made-up string: "e.g." must not split a sentence.
sample = "Governments, e.g. the EU, add rules. Costs rise. Margins fall. A fourth sentence."
assert len(split_sentences(sample)) == 4, split_sentences(sample)
print("abbreviation check: ok")

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())

print(f"\n{'title':45s} {'before':>6s} {'after':>5s}  ends cleanly")
for c in stage2.candidates:
    before = len(split_sentences(c.description))
    short = first_sentences(c.description, 3)
    after = len(split_sentences(short))
    clean = short.rstrip().endswith((".", "!", "?"))
    print(f"{c.title[:45]:45s} {before:6d} {after:5d}  {clean}")