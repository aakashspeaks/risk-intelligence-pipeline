"""Evaluators: score the pipeline output against the golden set."""
from __future__ import annotations

from ..stage3_extraction.models import Risk
from .golden import Golden
from .matching import MATCH_THRESHOLD, match_records, normalise, similarity

FIELDS = ("category", "kind", "tier", "page")


def _value(risk: Risk, field: str) -> object:
    """The output record's value for a field, in the same form as the golden file."""
    if field == "page":
        return risk.source.page
    value = getattr(risk, field)
    return getattr(value, "value", value)   # enums become plain strings


def recall_precision(golden: Golden, risks: list[Risk]) -> dict:
    matched, missed, extra = match_records(golden.risks, risks)
    principal_total = [g for g in golden.risks if g.tier == "principal"]
    principal_found = [g for g, _ in matched if g.tier == "principal"]
    return {
        "recall": len(matched) / len(golden.risks) if golden.risks else 0.0,
        "precision": len(matched) / len(risks) if risks else 0.0,
        "principal_recall": len(principal_found) / len(principal_total) if principal_total else 1.0,
        "missed": [g.title for g in missed],
        "extra": [r.title for r in extra],
    }


def field_accuracy(golden: Golden, risks: list[Risk]) -> dict:
    """Share of matched records whose category, kind, tier and page agree with the golden set."""
    matched, _, _ = match_records(golden.risks, risks)
    correct = {f: 0 for f in FIELDS}
    mistakes: list[str] = []
    for g, r in matched:
        for f in FIELDS:
            want, got = getattr(g, f), _value(r, f)
            if want == got:
                correct[f] += 1
            else:
                mistakes.append(f"{g.title}: {f} is {got!r}, expected {want!r}")
    n = len(matched)
    scores = {f"{f}_accuracy": (correct[f] / n if n else 0.0) for f in FIELDS}
    return {**scores, "mistakes": mistakes}


def immaterial_leak(golden: Golden, risks: list[Risk]) -> dict:
    """Records that look like a topic the report itself rules out ("scored as immaterial")."""
    leaked = []
    for r in risks:
        for banned in golden.must_not_be_returned_as_risks:
            if similarity(r.title, banned) >= MATCH_THRESHOLD or normalise(banned) in normalise(r.title):
                leaked.append(r.title)
                break
    return {"leaked": leaked, "leak_free": not leaked}


def evaluate_basic(golden: Golden, risks: list[Risk]) -> dict:
    return {**recall_precision(golden, risks), **field_accuracy(golden, risks), **immaterial_leak(golden, risks)}