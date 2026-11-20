"""Run the pipeline with a real model and compare it with the rule-based baseline.

    uv run python scripts/compare_llm.py                       # model from .env
    uv run python scripts/compare_llm.py model-a model-b       # several models, one after the other
"""
import os
import sys
from collections import Counter

from dotenv import load_dotenv
from openai import OpenAI

from risk_intel.config import RAW_DIR
from risk_intel.stage3_extraction.llm_summary import openai_summariser
from risk_intel.stage3_extraction.runner import run_stage3
from risk_intel.stage4_validation.checks import load_page_tokens
from risk_intel.stage4_validation.dedupe import merge_duplicates
from risk_intel.stage4_validation.models import Stage4Output
from risk_intel.stage5_evaluation.gate import evaluate
from risk_intel.stage5_evaluation.golden import load_golden

load_dotenv()
PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
golden = load_golden()
page_tokens = load_page_tokens(PDF)


def run(label, summariser=None):
    """Stage 3 and Stage 4 in memory, then the gate."""
    stage3 = run_stage3(PDF, summariser, label)
    risks, merges = merge_duplicates(stage3.risks)
    output = Stage4Output(source_file=stage3.source_file, risks=risks, excluded_immaterial=stage3.excluded_immaterial,
                          governance=stage3.governance, merges=merges)
    return output, evaluate(output, golden, page_tokens)


def principal_by_id(output):
    return {r.id: r for r in output.risks if r.tier == "principal"}


baseline, baseline_report = run("rules")
print(f"BASELINE (rules only): {'PASS' if baseline_report.passed else 'FAIL'}")

models = sys.argv[1:] or [os.environ["RISK_LLM_MODEL"]]
client = OpenAI()
for model in models:
    output, report = run(model, openai_summariser(client, model))
    print(f"\n{'=' * 78}\nMODEL {model}: {'PASS' if report.passed else 'FAIL'}")
    for risk in principal_by_id(output).values():
        print(f"  {risk.id}: {risk.description_origin}")
    if report.failed:
        print("  failed gates:", report.failed)
        for key in ("ungrounded", "contamination", "evidence_flagged"):
            for item in report.details.get(key, [])[:3]:
                print(f"    {key}: {item}")
    base = principal_by_id(baseline)
    for risk_id, risk in principal_by_id(output).items():
        print(f"\n  --- {risk.title} ---")
        print("  rules:", base[risk_id].description)
        print("  model:", risk.description)