import os
from collections import Counter

from dotenv import load_dotenv
from openai import OpenAI

from risk_intel.config import RAW_DIR
from risk_intel.stage3_extraction import llm_summary
from risk_intel.stage3_extraction.runner import run_stage3
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage4_validation.dedupe import merge_duplicates
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.gate import evaluate
from risk_intel.stage5_evaluation.golden import load_golden

load_dotenv()
PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
MODEL = os.environ["RISK_LLM_MODEL"]
golden = load_golden()
page_tokens = load_page_tokens(PDF)
summariser = llm_summary.openai_summariser(OpenAI(), MODEL)

REAL_PROMPT = llm_summary.SYSTEM_PROMPT
REAL_ACCEPT = llm_summary.accept_summary
PERMISSIVE_PROMPT = """You write engaging executive summaries of corporate risks for investors.
Write 3 insightful sentences that explain what the risk means for the business and its investors,
adding useful context. Reply with JSON only, in the form {"summary": "..."}."""


def accept_everything(summary, source):
    return llm_summary.Verdict(True, "safety net switched off for this demo")


def run(label, prompt, net_on, prompt_version):
    llm_summary.SYSTEM_PROMPT = prompt
    llm_summary.PROMPT_VERSION = prompt_version
    llm_summary.accept_summary = REAL_ACCEPT if net_on else accept_everything
    try:
        stage3 = run_stage3(PDF, summariser, MODEL)
    finally:   # always restore the real prompt and the real safety net
        llm_summary.SYSTEM_PROMPT = REAL_PROMPT
        llm_summary.PROMPT_VERSION = "v1"
        llm_summary.accept_summary = REAL_ACCEPT
    risks, merges = merge_duplicates(stage3.risks)
    output = Stage4Output(source_file=stage3.source_file, risks=risks, excluded_immaterial=stage3.excluded_immaterial,
                          governance=stage3.governance, merges=merges)
    report = evaluate(output, golden, page_tokens)

    principal = [r for r in output.risks if r.tier == "principal"]
    origins = Counter("accepted" if r.description_origin.startswith("llm") else "fell back to rules" for r in principal)
    print(f"\n{'=' * 78}\n{label}: {'PASS' if report.passed else 'FAIL'}")
    print("  principal descriptions:", dict(origins))
    for r in principal:
        if not r.description_origin.startswith("llm"):
            print(f"    {r.id}: {r.description_origin}")
    if report.failed:
        print("  failed gates:", report.failed)
        for item in report.details.get("ungrounded", [])[:4]:
            print("    ungrounded:", item)
    return principal


run("1. real prompt, safety net on", REAL_PROMPT, True, "v1")
run("2. permissive prompt, safety net on", PERMISSIVE_PROMPT, True, "v1-permissive")
bare = run("3. permissive prompt, safety net OFF", PERMISSIVE_PROMPT, False, "v1-permissive")

print("\nWhat the model wrote in scenario 3 (first 220 characters each):")
for r in bare:
    print(f"  {r.title}: {r.description[:220]}")