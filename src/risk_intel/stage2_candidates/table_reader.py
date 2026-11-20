"""Table reader: rebuilds the sustainability tables (pages 71-74) from word positions and rule lines.

Step A: find the two halves of the table (impacts on the left, financial risks on the right).
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

import pdfplumber
from pathlib import Path

import pdfplumber

from .models import RiskCandidate

MIN_RULE_WIDTH = 150   # the table's horizontal rules are between these widths (points)
MAX_RULE_WIDTH = 400
VALUE_CHAIN_MARGIN = 3  # stay this far left of the "Value chain" header


@dataclass
class Side:
    name: str               # 'impact' or 'financial'
    left: float             # left edge of this half
    value_chain_x: float    # the value-chain column starts here
    right: float            # right edge of this half


def find_sides(page, words: list[dict]) -> list[Side]:
    """Return the impact half and the financial half, or an empty list if the page has no such table."""
    rules = [e for e in page.edges
             if e["orientation"] == "h" and MIN_RULE_WIDTH < e["width"] < MAX_RULE_WIDTH]
    lefts = sorted({round(e["x0"]) for e in rules})                      # where the rules start
    value_headers = sorted(w["x0"] for w in words if w["text"] == "Value" and w["top"] > 100)
    if len(lefts) < 2 or len(value_headers) < 2:
        return []
    return [
        Side("impact", lefts[0], value_headers[0] - VALUE_CHAIN_MARGIN, lefts[1] - 4),
        Side("financial", lefts[1], value_headers[-1] - VALUE_CHAIN_MARGIN, 9999),
    ]

ROW_RULE_TOLERANCE = 4   # a rule belongs to a half if it starts within this distance of the half's left edge


def _text(words: list[dict]) -> str:
    """Words to one string, in reading order."""
    ordered = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    return " ".join(w["text"] for w in ordered)


def find_row_bands(page, side: Side) -> list[tuple[float, float]]:
    """Row boundaries (top, bottom) in one half of the table, from the horizontal rules."""
    rule_tops = sorted({
        round(e["top"], 1) for e in page.edges
        if e["orientation"] == "h"
        and MIN_RULE_WIDTH < e["width"] < MAX_RULE_WIDTH
        and abs(e["x0"] - side.left) <= ROW_RULE_TOLERANCE
    })
    return list(zip(rule_tops, rule_tops[1:]))


def words_in_band(words: list[dict], side: Side, band: tuple[float, float]) -> list[dict]:
    """Words of one row, in the main part of the half (value-chain column excluded)."""
    top, bottom = band
    return [w for w in words
            if side.left - 2 <= w["x0"] < side.value_chain_x
            and top - 1 <= w["top"] < bottom - 1]

NAME_FONT_MARKER = "Medium"   # entry names use VestasSans-Medium, descriptions use the Standard weight
LINE_TOLERANCE = 3


@dataclass
class TableEntry:
    name: str
    description: str
    value_chain: str
    immaterial: bool   # True = the report says this topic is scored as immaterial


def _lines(words: list[dict]) -> list[list[dict]]:
    """Group words into lines by vertical position, left to right."""
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= LINE_TOLERANCE:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def read_row(words: list[dict], side: Side, band: tuple[float, float]) -> TableEntry | None:
    """Split one row into name, description and value chain. Returns None for header rows."""
    main = words_in_band(words, side, band)
    if not main:
        return None
    text = re.sub(r"\s+", " ", _text(main)).strip()
    if "Name and description" in text:
        return None   # header row of a table, not an entry

    top, bottom = band
    tag = [w for w in words
           if side.value_chain_x <= w["x0"] < side.right and top - 1 <= w["top"] < bottom - 1]
    value_chain = re.sub(r"\s+", " ", _text(tag)).strip()

    # The name is the run of lines at the top of the row that use the bold font.
    name_lines: list[list[dict]] = []
    lines = _lines(main)
    for line in lines:
        if any(NAME_FONT_MARKER in w["fontname"] for w in line):
            name_lines.append(line)
        else:
            break

    if not name_lines:   # plain text only: an "scored as immaterial" statement
        return TableEntry(name=text, description="", value_chain=value_chain, immaterial=True)

    name = re.sub(r"\s+", " ", _text([w for line in name_lines for w in line])).strip()
    description = re.sub(r"\s+", " ", _text([w for line in lines[len(name_lines):] for w in line])).strip()
    return TableEntry(name=name, description=description, value_chain=value_chain,
                      immaterial="scored as immaterial" in text)

QUALIFIER = re.compile(r"\s*\((?:entity-specific|actual|potential)[^)]*\)")   # e.g. "(entity-specific)"


def read_tables(pdf_path: str | Path, pages: list[int],
                sections: dict[int, str | None] | None = None) -> tuple[list[RiskCandidate], list[str]]:
    """Read the financial side of the sustainability tables.

    Returns (candidates, immaterial_statements). Immaterial rows are not risks,
    but we keep them so a human can see what the report ruled out.
    """
    sections = sections or {}
    candidates: list[RiskCandidate] = []
    immaterial: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for number in pages:
            page = pdf.pages[number - 1]
            words = page.extract_words(extra_attrs=["fontname"])
            for side in find_sides(page, words):
                if side.name != "financial":
                    continue   # impacts on people and environment: a different record, later
                for band in find_row_bands(page, side):
                    entry = read_row(words, side, band)
                    if entry is None:
                        continue
                    if entry.immaterial:
                        immaterial.append(f"p{number}: {entry.name}")
                        continue
                    candidates.append(RiskCandidate(
                        title=QUALIFIER.sub("", entry.name).strip(),
                        description=entry.description,
                        tier="sustainability_iro",
                        page=number,
                        section=sections.get(number),
                        method="table",
                        evidence=entry.description[:200],
                        side="financial",
                        value_chain=entry.value_chain or None,
                    ))
    return candidates, immaterial