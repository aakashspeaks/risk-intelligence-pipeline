"""Content evaluators: is the text of each record right, grounded and clean?"""
from __future__ import annotations

from ..stage2_candidates.models import GovernanceCandidate
from ..stage3_extraction.models import Risk
from ..stage3_extraction.sentences import split_sentences
from ..stage4_validation.checks import check_evidence, tokens
from .golden import Golden
from .matching import match_records, normalise

GROUNDED_AT = 0.75   # a sentence counts as grounded if 75% of its content words are on the cited page
STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "are", "was", "were", "has", "have", "from",
    "its", "their", "our", "which", "can", "may", "also", "vestas", "both", "such", "than",
}


def evidence_accuracy(risks: list[Risk], page_tokens: dict[int, list[str]]) -> dict:
    """Share of records whose quote is fully found, in order, on the page they cite."""
    flagged = []
    for r in risks:
        _, issue = check_evidence(r, page_tokens)
        if issue:
            flagged.append(f"{r.title}: {issue.message}")
    return {"evidence_accuracy": 1 - len(flagged) / len(risks) if risks else 0.0, "evidence_flagged": flagged}


def grounding(risks: list[Risk], page_tokens: dict[int, list[str]]) -> dict:
    """Share of sentences (description, impact, mitigation) whose content words are on the cited page."""
    page_words = {page: set(words) for page, words in page_tokens.items()}
    total = grounded = 0
    flagged = []
    for r in risks:
        on_page = page_words.get(r.source.page, set())
        for field in ("description", "potential_impact", "mitigation"):
            for sentence in split_sentences(getattr(r, field) or ""):
                content = [t for t in tokens(sentence) if t not in STOP_WORDS and len(t) > 2]
                if not content:
                    continue
                total += 1
                share = sum(t in on_page for t in content) / len(content)
                if share >= GROUNDED_AT:
                    grounded += 1
                else:
                    flagged.append(f"{r.title} ({field}): {share:.0%} of words on page {r.source.page}: {sentence[:70]!r}")
    return {"grounding": grounded / total if total else 0.0, "ungrounded": flagged}


def mitigation_coverage(golden: Golden, risks: list[Risk]) -> dict:
    """Share of the key mitigation phrases (from the golden set) that the output mitigation still contains."""
    matched, _, _ = match_records(golden.risks, risks)
    found = {g.id: r for g, r in matched}
    total = hits = 0
    missing = []
    for g in golden.risks:
        record = found.get(g.id)
        text = normalise(record.mitigation or "") if record else ""
        for term in g.must_mention_in_mitigation:
            total += 1
            if normalise(term) in text:
                hits += 1
            else:
                missing.append(f"{g.title}: mitigation lacks {term!r}")
    return {"mitigation_coverage": hits / total if total else 1.0, "mitigation_missing": missing}


def contamination(golden: Golden, risks: list[Risk]) -> dict:
    """Words that belong to a neighbouring risk leaking into this one (the column-mixing failure)."""
    matched, _, _ = match_records(golden.risks, risks)
    leaks = []
    checked = 0
    for g, r in matched:
        if not g.forbidden_terms:
            continue
        checked += 1
        text = normalise(f"{r.description} {r.potential_impact or ''} {r.mitigation or ''}")
        for term in g.forbidden_terms:
            if normalise(term) in text:
                leaks.append(f"{g.title}: contains {term!r}")
    clean = checked - len({leak.split(':')[0] for leak in leaks})
    return {"contamination_free": clean / checked if checked else 1.0, "contamination": leaks}


def governance_check(golden: Golden, governance: GovernanceCandidate | None) -> dict:
    if governance is None:
        return {"governance": 0.0, "governance_problems": ["no governance finding returned"]}
    problems = []
    if governance.review_frequency != golden.governance.review_frequency:
        problems.append(f"frequency is {governance.review_frequency!r}")
    if set(governance.reviewed_by) != set(golden.governance.reviewed_by):
        problems.append(f"reviewed_by is {governance.reviewed_by}")
    if governance.page != golden.governance.page:
        problems.append(f"page is {governance.page}")
    return {"governance": 0.0 if problems else 1.0, "governance_problems": problems}


def evaluate_content(golden: Golden, risks: list[Risk], governance: GovernanceCandidate | None,
                     page_tokens: dict[int, list[str]]) -> dict:
    return {
        **evidence_accuracy(risks, page_tokens),
        **grounding(risks, page_tokens),
        **mitigation_coverage(golden, risks),
        **contamination(golden, risks),
        **governance_check(golden, governance),
    }