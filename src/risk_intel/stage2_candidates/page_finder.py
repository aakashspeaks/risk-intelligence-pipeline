"""Page finder: score every page by how likely it is to contain principal risks."""
from __future__ import annotations

import re

from ..stage1_document.models import DocumentLayout, PageLayout
from .models import CandidatePage

# Phrases in a page title that strongly suggest a risk disclosure page.
STRONG_TITLE_PHRASES = [
    "main risks", "principal risks", "key risks", "risk factors",
    "risk management", "material impacts, risks",
]
# Phrases that real risk disclosures contain (page 51 has "potential impact" and "how we manage it").
MARKER_PHRASES = [
    "potential impact", "how we manage", "mitigat", "likelihood", "risk appetite", "emerging risk",
]
RISK_WORD = re.compile(r"\brisks?\b")


def score_page(page: PageLayout) -> CandidatePage:
    score = 0.0
    reasons: list[str] = []
    title = (page.title or "").lower()
    section = (page.section or "").lower()
    text = page.text.lower()

    # Clue 1: the page title.
    for phrase in STRONG_TITLE_PHRASES:
        if phrase in title:
            score += 5
            reasons.append(f"title has '{phrase}' (+5)")
            break

    # Clue 2: the section line from the top menu.
    if "risk" in section:
        score += 3
        reasons.append("section line mentions risk (+3)")

    # Clue 3: phrases typical of a risk disclosure, at most 3 count.
    found = [m for m in MARKER_PHRASES if m in text]
    if found:
        points = 2 * min(len(found), 3)
        score += points
        reasons.append(f"marker phrases {found[:3]} (+{points})")

    # Clue 4: how often "risk" appears. A small weight, because many pages mention risk in passing.
    density = len(RISK_WORD.findall(text)) / max(page.word_count, 1) * 100
    points = round(min(density, 6) * 0.3, 1)
    if points > 0:
        score += points
        reasons.append(f"risk-word density {density:.1f} per 100 words (+{points})")

    # Penalties for pages we know are false alarms.
    if page.part == "Financial statements":
        score -= 4
        reasons.append("financial statements section (-4)")
    if page.layout_type == "graphic":
        score -= 5
        reasons.append("graphic or menu page (-5)")
    if page.layout_type == "numeric_table":
        score -= 3
        reasons.append("numeric table (-3)")

    return CandidatePage(page_number=page.page_number, score=round(score, 1), reasons=reasons)


def find_candidate_pages(doc: DocumentLayout) -> list[CandidatePage]:
    """Score every page and return them, best first."""
    scored = [score_page(p) for p in doc.pages]
    return sorted(scored, key=lambda c: c.score, reverse=True)