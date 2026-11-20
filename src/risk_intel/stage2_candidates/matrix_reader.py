"""Matrix reader: rebuilds the main-risk matrix (page 51) from word positions.

The page is a grid. Columns = risks, rows = Description / Potential impact / How we manage it.
Plain text extraction mixes the columns, so we cut the grid ourselves using word positions.
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .models import RiskCandidate

ROW_LABELS = ("Description", "Potential impact", "How we manage it")
LABEL_COLUMN_MAX_X = 120   # the row labels sit in the left margin
TITLE_FONT_SIZE = 12.0     # column titles are 12 pt
COLUMN_START_GAP = 100     # title words closer than this belong to the same column


def _lines(words: list[dict], tolerance: float = 3) -> list[list[dict]]:
    """Group words into lines by their vertical position, left to right."""
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= tolerance:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _join(words: list[dict]) -> str:
    """Words to one clean string, in reading order."""
    text = " ".join(w["text"] for line in _lines(words) for w in line)
    return re.sub(r"\s+", " ", text).strip()


def _row_tops(words: list[dict]) -> dict[str, float]:
    """Vertical position of each row label in the left margin."""
    tops: dict[str, float] = {}
    for line in _lines([w for w in words if w["x0"] < LABEL_COLUMN_MAX_X]):
        text = " ".join(w["text"] for w in line)
        for label in ROW_LABELS:
            if text.startswith(label):
                tops[label] = line[0]["top"]
    return tops


def _column_starts(words: list[dict], first_row_top: float) -> list[int]:
    """Left edge of each risk column, taken from the 12 pt title words above the first row."""
    title_words = [w for w in words
                   if w["x0"] > 200 and w["top"] < first_row_top - 5
                   and abs(w["size"] - TITLE_FONT_SIZE) < 0.6]
    starts: list[int] = []
    for x in sorted({round(w["x0"]) for w in title_words}):
        if not starts or x - starts[-1] > COLUMN_START_GAP:
            starts.append(x)
    return starts


def read_matrix(pdf_path: str | Path, page_number: int, section: str | None = None) -> list[RiskCandidate]:
    """Read the risk matrix on one page and return one candidate per column."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number - 1]
        words = page.extract_words(extra_attrs=["size"])

        tops = _row_tops(words)
        missing = [label for label in ROW_LABELS if label not in tops]
        if missing:
            raise ValueError(f"Row labels not found on page {page_number}: {missing}")
        desc_top, impact_top, manage_top = (tops[label] for label in ROW_LABELS)
        footer_top = min((w["top"] for w in words if w["text"] == "Vestas" and w["top"] > 500),
                         default=page.height)

        starts = _column_starts(words, desc_top)
        edges = [s - 8 for s in starts] + [page.width + 1]

        candidates: list[RiskCandidate] = []
        for i in range(len(starts)):
            column = [w for w in words if edges[i] <= w["x0"] < edges[i + 1]]

            def rows(top: float, bottom: float, column: list[dict] = column) -> str:
                return _join([w for w in column if top - 2 <= w["top"] < bottom - 2])

            title = _join([w for w in column
                           if w["top"] < desc_top - 5 and abs(w["size"] - TITLE_FONT_SIZE) < 0.6])
            description = rows(desc_top, impact_top)
            candidates.append(RiskCandidate(
                title=title,
                description=description,
                potential_impact=rows(impact_top, manage_top) or None,
                mitigation=rows(manage_top, footer_top - 5) or None,
                tier="principal",
                page=page_number,
                section=section,
                method="matrix",
                evidence=description[:200],
            ))
    return candidates