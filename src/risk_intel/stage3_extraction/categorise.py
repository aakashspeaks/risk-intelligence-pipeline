"""Category rules: assign each candidate one category from the fixed list.

Rules are checked in order, and the first match wins. Titles are checked first because they
are the strongest signal. The description is only a fallback.
"""
from __future__ import annotations

import re

from .models import Category

RULES: list[tuple[str, Category]] = [
    (r"cyber", Category.cyber),
    (r"carbon tax|emission|ghg|climate", Category.climate),          # before 'tariff', see above
    (r"injur|health and safety", Category.health_safety),
    (r"forced|child labour|human rights|indigenous", Category.human_rights),
    (r"corruption|bribery", Category.compliance_conduct),
    (r"geopolit|sanction|export control|regulat|tariff", Category.regulatory_geopolitical),
    (r"market condition|growth rate|wind industry|grid", Category.market),
    (r"recycl|circular|waste|biodiversity|raw material", Category.environmental),
    (r"supplier|supply chain|logistic", Category.supply_chain),
    (r"project execution|manufactur|delivery|quality", Category.operational),
]


def categorise(title: str, description: str = "") -> Category:
    """Return the first matching category, checking the title before the description."""
    for text in (title.lower(), f"{title} {description}".lower()):
        for pattern, category in RULES:
            if re.search(pattern, text):
                return category
    return Category.other