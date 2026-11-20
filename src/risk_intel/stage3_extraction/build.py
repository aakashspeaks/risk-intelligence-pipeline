"""Turn one Stage 2 candidate into the final Risk record."""
from __future__ import annotations

import re

from ..stage2_candidates.models import RiskCandidate
from .categorise import categorise
from .kind import classify_kind
from .llm_summary import Summariser, summarise_with_fallback
from .models import Risk, Source
from .sentences import first_sentences


def make_id(candidate: RiskCandidate) -> str:
    """A readable id from the title. Table entries get an 'iro-' prefix so ids can't clash
    with a principal risk of the same name (for example the two cyber entries)."""
    slug = re.sub(r"[^a-z0-9]+", "-", candidate.title.lower()).strip("-")[:60]
    return f"iro-{slug}" if candidate.tier == "sustainability_iro" else slug


def to_risk(candidate: RiskCandidate, summariser: Summariser | None = None, label: str = "") -> Risk:
    """Build the final record. If a summariser is given, it is used for principal risks only,
    and only if its output passes the checks; otherwise the rule-based description is kept."""
    description = first_sentences(candidate.description, 3)
    origin = "rules"
    if summariser is not None and candidate.tier == "principal":
        description, origin = summarise_with_fallback(candidate, summariser, description, label)

    return Risk(
        id=make_id(candidate),
        title=candidate.title,
        description=description,
        description_origin=origin,
        category=categorise(candidate.title, candidate.description),
        kind=classify_kind(candidate.description, candidate.tier),
        tier=candidate.tier,
        potential_impact=candidate.potential_impact,
        mitigation=candidate.mitigation,
        value_chain=candidate.value_chain,
        source=Source(
            section=candidate.section,
            page=candidate.page,
            method=candidate.method,
            evidence=candidate.evidence,
        ),
    )