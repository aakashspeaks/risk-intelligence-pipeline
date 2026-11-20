"""Validation checks. Check 1: is the quoted evidence really on the page the record cites?"""
from __future__ import annotations

import re
from pathlib import Path

from ..config import INTERIM_DIR
from ..stage1_document.models import DocumentLayout
from ..stage3_extraction.models import Risk
from .models import Issue

TOKEN = re.compile(r"[a-z0-9]+")
ERROR_BELOW = 0.90   # under 90% of the quote's words found in order: the record is probably wrong


def tokens(text: str) -> list[str]:
    """Lowercase words made of letters and digits only, so punctuation can't cause a miss."""
    return TOKEN.findall(text.lower())


def load_page_tokens(pdf_path: str | Path) -> dict[int, list[str]]:
    """Page number -> the page's words, from the saved Stage 1 file (the PDF is not re-read)."""
    stage1 = INTERIM_DIR / f"{Path(pdf_path).stem}.stage1.json"
    doc = DocumentLayout.model_validate_json(stage1.read_text(encoding="utf-8"))
    return {p.page_number: tokens(p.text) for p in doc.pages}


def ordered_coverage(quote_tokens: list[str], page_tokens: list[str]) -> float:
    """Share of the quote's words found on the page in the same order.

    Other words may sit in between (the page text interleaves columns). The last word may be a
    cut-off beginning of a word, because the quote is a 200-character slice.
    """
    if not quote_tokens:
        return 0.0
    position, hits, last = 0, 0, len(quote_tokens) - 1
    for i, word in enumerate(quote_tokens):
        for j in range(position, len(page_tokens)):
            found = page_tokens[j].startswith(word) if i == last else page_tokens[j] == word
            if found:
                hits += 1
                position = j + 1
                break
    return hits / len(quote_tokens)


def check_evidence(risk: Risk, page_tokens: dict[int, list[str]]) -> tuple[float, Issue | None]:
    """Return the coverage and an Issue if the quote is not (fully) on the cited page."""
    page = risk.source.page
    if page not in page_tokens:
        return 0.0, Issue(risk_id=risk.id, check="page", severity="error",
                          message=f"cited page {page} does not exist in the document")
    coverage = ordered_coverage(tokens(risk.source.evidence), page_tokens[page])
    if coverage >= 1.0:
        return coverage, None
    severity = "error" if coverage < ERROR_BELOW else "warning"
    return coverage, Issue(risk_id=risk.id, check="evidence", severity=severity,
                           message=f"only {coverage:.0%} of the quote's words found in order on page {page}")

def load_page_sections(pdf_path: str | Path) -> dict[int, str | None]:
    """Page number -> section line, from the saved Stage 1 file."""
    stage1 = INTERIM_DIR / f"{Path(pdf_path).stem}.stage1.json"
    doc = DocumentLayout.model_validate_json(stage1.read_text(encoding="utf-8"))
    return {p.page_number: p.section for p in doc.pages}


def check_section(risk: Risk, page_sections: dict[int, str | None]) -> Issue | None:
    """The record's section must match the section Stage 1 found on the page it cites."""
    page = risk.source.page
    if page not in page_sections:
        return None  # a missing page is already reported by the evidence check
    expected = page_sections[page]
    if risk.source.section == expected:
        return None
    return Issue(risk_id=risk.id, check="section", severity="warning",
                 message=f"record says section {risk.source.section!r}, "
                         f"but Stage 1 found {expected!r} on page {page}")