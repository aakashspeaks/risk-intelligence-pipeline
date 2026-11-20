from risk_intel.config import INTERIM_DIR
from risk_intel.stage2_candidates.models import Stage2Output
from risk_intel.stage3_extraction.llm_summary import PROMPT_VERSION, SummaryResult, build_messages
from risk_intel.stage3_extraction.sentences import split_sentences

stage2 = Stage2Output.model_validate_json((INTERIM_DIR / "VestasAnnualReport2025.stage2.json").read_text())
principal = [c for c in stage2.candidates if c.tier == "principal"]

print("prompt version:", PROMPT_VERSION)
for c in principal:
    print(f"  {c.title}: source has {len(split_sentences(c.description))} sentences, {len(c.description.split())} words")

print("\n--- the messages for the first risk ---")
for message in build_messages(principal[0]):
    print(f"[{message['role']}]")
    print(message["content"][:700])
    print()

print("schema fields:", list(SummaryResult.model_json_schema()["properties"]))
print("valid answer accepted:", SummaryResult(summary="Some short summary.").summary)