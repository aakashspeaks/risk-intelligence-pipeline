"""Risk or opportunity? The report marks this with an icon, so we use its wording as a proxy."""
from __future__ import annotations

import re

from .models import Kind

OPPORTUNITY_WORD = re.compile(r"\bopportunit(?:y|ies)\b", re.IGNORECASE)


def classify_kind(description: str, tier: str) -> Kind:
    """Principal risks are risks by definition. A table entry that calls itself an
    opportunity in its own description is an opportunity. Everything else is a risk."""
    if tier == "principal":
        return Kind.risk
    return Kind.opportunity if OPPORTUNITY_WORD.search(description) else Kind.risk