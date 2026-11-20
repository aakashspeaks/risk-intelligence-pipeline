"""The gate: run every evaluator, compare each score with its threshold, report pass or fail."""
from __future__ import annotations

from pydantic import BaseModel

from ..stage4_validation.models import Stage4Output
from .content_evaluators import evaluate_content
from .evaluators import evaluate_basic
from .golden import Golden

# All 1.0: with a 12-record golden set, any single fault must fail the gate.
# With a bigger golden set or a model whose output varies, measure the variation and relax these.
THRESHOLDS: dict[str, float] = {
    "recall": 1.0,
    "precision": 1.0,
    "principal_recall": 1.0,
    "category_accuracy": 1.0,
    "kind_accuracy": 1.0,
    "tier_accuracy": 1.0,
    "page_accuracy": 1.0,
    "immaterial_leak_free": 1.0,
    "evidence_accuracy": 1.0,
    "grounding": 1.0,
    "mitigation_coverage": 1.0,
    "contamination_free": 1.0,
    "governance": 1.0,
}

DETAIL_KEYS = ("missed", "extra", "leaked", "mistakes", "evidence_flagged", "ungrounded",
               "mitigation_missing", "contamination", "governance_problems")


class EvalReport(BaseModel):
    passed: bool
    scores: dict[str, float]
    failed: dict[str, float]          # gate name -> score, for the gates that failed
    details: dict[str, list[str]]     # what went wrong, per evaluator


def evaluate(output: Stage4Output, golden: Golden, page_tokens: dict[int, list[str]]) -> EvalReport:
    basic = evaluate_basic(golden, output.risks)
    content = evaluate_content(golden, output.risks, output.governance, page_tokens)
    results = {**basic, **content}

    scores = {name: round(float(results[name]), 3) for name in THRESHOLDS if name != "immaterial_leak_free"}
    scores["immaterial_leak_free"] = 1.0 if basic["leak_free"] else 0.0

    failed = {name: scores[name] for name, minimum in THRESHOLDS.items() if scores[name] < minimum}
    details = {key: results[key] for key in DETAIL_KEYS if results.get(key)}
    return EvalReport(passed=not failed, scores=scores, failed=failed, details=details)