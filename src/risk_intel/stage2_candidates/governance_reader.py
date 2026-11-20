"""Governance reader: how often the principal risks are reviewed, and by whom (page 50)."""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .models import GovernanceCandidate

# The narrative sits in the middle of page 50. Cutting to this box keeps the diagram text out.
MIDDLE_COLUMN = (290, 100, 628, 500)

REVIEW_SENTENCE = re.compile(
    r"most significant risks.{0,160}?are reviewed (?P<frequency>every [a-z]+ months?) "
    r"by the (?P<bodies>.+?)\.",
    re.IGNORECASE,
)


def read_governance(pdf_path: str | Path, page_number: int = 50) -> GovernanceCandidate | None:
    """Find the sentence that says how often risks are reviewed. Returns None if it isn't found."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number - 1]
        text = page.within_bbox(MIDDLE_COLUMN).extract_text() or ""
    text = re.sub(r"\s+", " ", text)

    match = REVIEW_SENTENCE.search(text)
    if not match:
        return None

    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", match.group("bodies"))
    bodies = [re.sub(r"^the\s+", "", p.strip()) for p in parts if p.strip()]
    return GovernanceCandidate(
        review_frequency=match.group("frequency"),
        reviewed_by=bodies,
        page=page_number,
        evidence=match.group(0)[:300],
    )