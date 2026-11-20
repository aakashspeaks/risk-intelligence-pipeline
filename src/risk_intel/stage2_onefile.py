"""Stage 2 as ONE file, for reading and review.

This is a parallel copy of the package stage2_candidates/. Nothing else imports it.
Same logic, same names, read top to bottom:
  1. Models      - the shape of the output
  2. Page finder - score every page for "does it hold principal risks?" (not used by the run)
  3. Matrix      - page 51: the main-risk grid, cut by word positions
  4. Tables      - pages 71-74: the sustainability tables, cut by rule lines
  5. Governance  - page 50: how often risks are reviewed, and by whom
  6. Runner      - run the readers on the case pages and save one file for Stage 3

It reads Stage 1's output from stage1_onefile (models and JSON), so run that first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pydantic import BaseModel, Field

from .config import INTERIM_DIR
from .stage1_onefile import DocumentLayout, PageLayout

# ============================================================================
# 1. MODELS
# ============================================================================


class CandidatePage(BaseModel):
    page_number: int = Field(ge=1)
    score: float = Field(description="Higher means more likely to contain principal risks")
    reasons: list[str] = Field(description="Why the page scored as it did, so a human can check")


class RiskCandidate(BaseModel):
    """One possible principal risk, cut out of the report with its source."""

    title: str
    description: str
    potential_impact: str | None = None
    mitigation: str | None = None
    tier: str = Field(description="'principal' = the report's own main-risk list")
    page: int = Field(ge=1)
    section: str | None = Field(None, description="Section line from the top menu, e.g. 'Corporate governance – Risk management'")
    method: str = Field(description="Which reader produced it, e.g. 'matrix'")
    evidence: str = Field(description="Verbatim start of the description, so a human can find it on the page")
    topic: str | None = Field(None, description="Topic group in the table, e.g. 'E1 Climate Change'")
    side: str | None = Field(None, description="'impact' or 'financial' for the sustainability tables")
    value_chain: str | None = Field(None, description="Where in the value chain it applies, e.g. 'Downstream'")


class GovernanceCandidate(BaseModel):
    """How the company says it reviews its principal risks."""

    review_frequency: str = Field(description="e.g. 'every six months'")
    reviewed_by: list[str] = Field(description="Bodies that review the risks, e.g. 'Board of Directors'")
    page: int = Field(ge=1)
    evidence: str = Field(description="Verbatim sentence from the page")


class Stage2Output(BaseModel):
    """Everything Stage 2 hands over to Stage 3."""

    source_file: str
    pages_used: list[int] = Field(description="Pages the candidates were read from")
    candidates: list[RiskCandidate]
    immaterial_statements: list[str] = Field(
        description="Topics the report itself scores as immaterial: not risks, kept for audit")
    governance: GovernanceCandidate | None = None


# ============================================================================
# SHARED HELPERS (used by the matrix and the table reader)
# ============================================================================

LINE_TOLERANCE = 3   # words whose tops differ by less than this sit on the same line


def _lines(words: list[dict]) -> list[list[dict]]:
    """Group words into lines by their vertical position, left to right."""
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= LINE_TOLERANCE:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _join(words: list[dict]) -> str:
    """Words to one clean string, in reading order (matrix reader)."""
    text = " ".join(w["text"] for line in _lines(words) for w in line)
    return re.sub(r"\s+", " ", text).strip()


def _text(words: list[dict]) -> str:
    """Words to one string, sorted by (top, x). Whitespace is cleaned by the caller (table reader)."""
    ordered = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    return " ".join(w["text"] for w in ordered)


# ============================================================================
# 2. PAGE FINDER: score every page. A scalable alternative to the fixed case pages.
# ============================================================================

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


# ============================================================================
# 3. MATRIX READER: the main-risk grid on page 51
# The page is a grid. Columns = risks, rows = Description / Potential impact / How we manage it.
# Plain text extraction mixes the columns, so we cut the grid ourselves using word positions.
# ============================================================================

ROW_LABELS = ("Description", "Potential impact", "How we manage it")
LABEL_COLUMN_MAX_X = 120   # the row labels sit in the left margin
TITLE_FONT_SIZE = 12.0     # column titles are 12 pt
COLUMN_START_GAP = 100     # title words closer than this belong to the same column


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


# ============================================================================
# 4. TABLE READER: the sustainability tables on pages 71-74
# Each page has two halves (impacts on the left, financial risks on the right).
# Rows are cut by the horizontal rule lines. Only the financial half becomes candidates.
# ============================================================================

MIN_RULE_WIDTH = 150      # the table's horizontal rules are between these widths (points)
MAX_RULE_WIDTH = 400
VALUE_CHAIN_MARGIN = 3    # stay this far left of the "Value chain" header
ROW_RULE_TOLERANCE = 4    # a rule belongs to a half if it starts within this distance of the half's left edge
NAME_FONT_MARKER = "Medium"   # entry names use VestasSans-Medium, descriptions use the Standard weight
QUALIFIER = re.compile(r"\s*\((?:entity-specific|actual|potential)[^)]*\)")   # e.g. "(entity-specific)"


@dataclass
class Side:
    name: str               # 'impact' or 'financial'
    left: float             # left edge of this half
    value_chain_x: float    # the value-chain column starts here
    right: float            # right edge of this half


@dataclass
class TableEntry:
    name: str
    description: str
    value_chain: str
    immaterial: bool   # True = the report says this topic is scored as immaterial


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

    if not name_lines:   # plain text only: a "scored as immaterial" statement
        return TableEntry(name=text, description="", value_chain=value_chain, immaterial=True)

    name = re.sub(r"\s+", " ", _text([w for line in name_lines for w in line])).strip()
    description = re.sub(r"\s+", " ", _text([w for line in lines[len(name_lines):] for w in line])).strip()
    return TableEntry(name=name, description=description, value_chain=value_chain,
                      immaterial="scored as immaterial" in text)


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


# ============================================================================
# 5. GOVERNANCE READER: how often the principal risks are reviewed, and by whom (page 50)
# ============================================================================

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


# ============================================================================
# 6. RUNNER: run the three readers and save one file for Stage 3
# ============================================================================

# Pages named in the case. The page finder (section 2) is the scalable alternative:
# it proposes pages for reports where we don't know them.
CASE_SCOPE = {"governance": 50, "matrix": [51], "tables": [71, 72, 73, 74]}


def _load_sections(pdf_path: Path) -> dict[int, str | None]:
    """Page number -> section line, taken from the Stage 1 one-file output."""
    stage1 = INTERIM_DIR / f"{pdf_path.stem}.stage1_onefile.json"
    if not stage1.exists():
        raise FileNotFoundError(f"{stage1} not found. Run: python -m risk_intel.stage1_onefile <pdf>")
    doc = DocumentLayout.model_validate_json(stage1.read_text(encoding="utf-8"))
    return {p.page_number: p.section for p in doc.pages}


def run_stage2(pdf_path: str | Path, scope: dict | None = None) -> Stage2Output:
    """Run all three readers and return one combined result."""
    pdf_path = Path(pdf_path)
    scope = scope or CASE_SCOPE
    sections = _load_sections(pdf_path)

    candidates: list[RiskCandidate] = []
    for page in scope["matrix"]:
        candidates += read_matrix(pdf_path, page, sections.get(page))
    table_candidates, immaterial = read_tables(pdf_path, scope["tables"], sections)
    candidates += table_candidates
    governance = read_governance(pdf_path, scope["governance"])

    return Stage2Output(
        source_file=pdf_path.name,
        pages_used=sorted({scope["governance"], *scope["matrix"], *scope["tables"]}),
        candidates=candidates,
        immaterial_statements=immaterial,
        governance=governance,
    )


def save_stage2(output: Stage2Output, pdf_path: str | Path) -> Path:
    """Save the result so Stage 3 never has to re-read the PDF."""
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"{Path(pdf_path).stem}.stage2_onefile.json"
    out.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    return out


# ============================================================================
# RUN IT: python -m risk_intel.stage2_onefile <pdf>
# ============================================================================

if __name__ == "__main__":
    import sys

    pdf = Path(sys.argv[1])
    print(f"Reading {pdf.name} ...")
    result = run_stage2(pdf)
    out = save_stage2(result, pdf)
    n_principal = sum(c.tier == "principal" for c in result.candidates)
    print(f"{len(result.candidates)} candidates ({n_principal} principal), "
          f"{len(result.immaterial_statements)} immaterial statements, "
          f"governance: {'found' if result.governance else 'MISSING'} -> {out}")
