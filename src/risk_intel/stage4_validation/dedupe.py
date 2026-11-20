"""Duplicate detection: the same risk disclosed in more than one place."""
from __future__ import annotations

from ..stage3_extraction.models import Kind, Risk
from .checks import tokens
from .models import MergeNote

# Words too generic to show two titles are about the same risk.
GENERIC_WORDS = {"risk", "risks", "and", "of", "the", "in", "to", "for", "on", "with", "related"}


def significant_words(title: str) -> set[str]:
    return {w for w in tokens(title) if w not in GENERIC_WORDS and len(w) > 2}


def shared_words(principal: Risk, other: Risk) -> set[str]:
    return significant_words(principal.title) & significant_words(other.title)


def is_duplicate(principal: Risk, other: Risk) -> bool:
    """A table entry duplicates a principal risk if both are risks, in the same category,
    and their titles share a significant word."""
    return (
        principal.tier == "principal"
        and other.tier == "sustainability_iro"
        and principal.kind == Kind.risk
        and other.kind == Kind.risk
        and principal.category == other.category
        and bool(shared_words(principal, other))
    )


def merge_duplicates(risks: list[Risk]) -> tuple[list[Risk], list[MergeNote]]:
    """Fold duplicate table entries into their principal risk. Inputs are not changed."""
    principal = {r.id: r.model_copy(deep=True) for r in risks if r.tier == "principal"}
    kept: list[Risk] = []
    merges: list[MergeNote] = []

    for risk in risks:
        if risk.tier == "principal":
            continue
        match = next((p for p in principal.values() if is_duplicate(p, risk)), None)
        if match is None:
            kept.append(risk)
            continue
        match.cross_references = sorted(set(match.cross_references + [risk.source.page]))
        words = sorted(shared_words(match, risk))
        merges.append(MergeNote(
            kept_id=match.id,
            merged_id=risk.id,
            reason=f"same category ({match.category.value}), shared title words {words}; "
                   f"page {risk.source.page} entry folded into the principal risk",
        ))
    return list(principal.values()) + kept, merges