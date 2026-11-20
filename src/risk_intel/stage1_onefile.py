"""Stage 1 as ONE file, for reading and review.

This is a parallel copy of the package stage1_document/. Nothing else imports it.
Same logic, same names, read top to bottom:
  1. Models     - the shape of the output
  2. Layout     - columns, table lines, numbers, page type
  3. Headers    - section (blue menu words) and page title (largest text)
  4. Sections   - group consecutive pages into runs
  5. Reader     - open the PDF and tie it all together
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import pdfplumber
from pydantic import BaseModel, Field

# ============================================================================
# 1. MODELS
# ============================================================================

LayoutType = Literal[
    "graphic",          # almost no text: cover, divider, image page
    "numeric_table",    # mostly numbers + ruled lines (financial statements)
    "table_or_matrix",  # ruled lines with text (risk matrix, sustainability tables)
    "multi_column",     # 3 or more text columns
    "two_column",       # 2 text columns
    "single_block",     # one block of text
]


class PageLayout(BaseModel):
    page_number: int = Field(ge=1, description="1-based, same as the printed page number")
    width: float
    height: float
    word_count: int
    has_text_layer: bool = Field(description="False = scanned page that would need OCR")
    layout_type: LayoutType
    n_columns: int = Field(description="Text columns, found from vertical gaps")
    n_rule_lines: int = Field(description="Long horizontal lines: a sign of a table")
    numeric_ratio: float = Field(description="Share of words that are numbers")
    part: str | None = Field(None, description="Top menu item, e.g. 'Sustainability statement'")
    section: str | None = Field(None, description="Sub-section line under the menu")
    title: str | None = Field(None, description="Largest text on the page = page heading")
    text: str = Field(description="Body text in reading order, without top menu and footer")


class SectionSpan(BaseModel):
    """A run of consecutive pages sharing the same part and section."""

    part: str | None
    section: str | None
    start_page: int
    end_page: int


class DocumentLayout(BaseModel):
    source_file: str
    n_pages: int
    pages: list[PageLayout]
    sections: list[SectionSpan]


# ============================================================================
# 2. LAYOUT SIGNALS
# ============================================================================

HEADER_BAND = 40         # points from the top that hold the running menu
FOOTER_BAND = 45         # points from the bottom that hold the footer
GUTTER = 14              # empty width (points) that counts as a gap between columns
MIN_COLUMN_SHARE = 0.05  # ignore "columns" holding under 5% of the words

_NUMBER = re.compile(r"[\(\)\-–,.\d%]+")


def body_words(words: list[dict], page_height: float) -> list[dict]:
    """Words in the main body, without the top menu and the footer."""
    return [w for w in words if HEADER_BAND < w["top"] < page_height - FOOTER_BAND]


def count_columns(words: list[dict], page_width: float) -> int:
    """Count text columns by finding empty vertical strips between blocks of words."""
    if len(words) < 30:
        return 0
    covered = [0] * (int(page_width) + 2)
    for w in words:
        for x in range(int(w["x0"]), min(int(w["x1"]) + 1, len(covered))):
            covered[x] += 1
    xs = [x for x, c in enumerate(covered) if c]
    lo, hi = xs[0], xs[-1]

    blocks, start, last, gap = [], None, None, 0
    for x in range(lo, hi + 1):
        if covered[x]:
            if start is None:
                start = x
            last, gap = x, 0
        elif start is not None:
            gap += 1
            if gap == GUTTER:
                blocks.append((start, last))
                start = None
    if start is not None:
        blocks.append((start, hi))

    total = len(words)
    kept = [b for b in blocks if sum(b[0] <= w["x0"] <= b[1] for w in words) / total >= MIN_COLUMN_SHARE]
    return len(kept)


def count_rule_lines(page) -> int:
    """Long horizontal lines on the page (table rules)."""
    return sum(1 for e in page.edges if e["orientation"] == "h" and e["width"] > 100)


def numeric_ratio(words: list[dict]) -> float:
    if not words:
        return 0.0
    n = sum(1 for w in words if _NUMBER.fullmatch(w["text"]) and any(c.isdigit() for c in w["text"]))
    return n / len(words)


def classify(word_count: int, n_columns: int, n_rule_lines: int, numeric_ratio: float) -> LayoutType:
    """Rule-based page type. These thresholds are a heuristic: check them on new reports."""
    if word_count < 40:
        return "graphic"
    if numeric_ratio >= 0.30 and n_rule_lines >= 3:
        return "numeric_table"
    if n_rule_lines >= 8:
        return "table_or_matrix"
    if n_columns >= 3:
        return "multi_column"
    if n_columns == 2:
        return "two_column"
    return "single_block"


# ============================================================================
# 3. HEADERS: section from the blue menu, title from the biggest text
# ============================================================================

BLUE = (0.0, 0.35, 1.0)
MENU_LINE_SPLIT = 27   # y position separating menu line 1 (part) from line 2 (section)
TITLE_MIN_SIZE = 16.0


def _is_blue(color) -> bool:
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        return False
    return all(abs(a - b) < 0.05 for a, b in zip(color, BLUE))


def _join(words: list[dict]) -> str:
    return " ".join(w["text"] for w in sorted(words, key=lambda w: w["x0"]))


def read_running_header(words: list[dict]) -> tuple[str | None, str | None]:
    """Return (part, section) from the blue words in the top menu."""
    menu = [w for w in words if w["top"] < 40 and _is_blue(w.get("non_stroking_color"))]
    part = _join([w for w in menu if w["top"] < MENU_LINE_SPLIT])
    section = _join([w for w in menu if w["top"] >= MENU_LINE_SPLIT])
    return part or None, section or None


def find_title(words: list[dict]) -> str | None:
    """Largest text below the menu. Returns None on pages with only small text."""
    body = [w for w in words if w["top"] > 40]
    if not body:
        return None
    biggest = max(w["size"] for w in body)
    if biggest < TITLE_MIN_SIZE:
        return None
    big = [w for w in body if abs(w["size"] - biggest) < 0.5]
    big.sort(key=lambda w: (round(w["top"]), w["x0"]))
    return " ".join(w["text"] for w in big)[:150]


# ============================================================================
# 4. SECTIONS
# ============================================================================

def build_sections(pages: list[PageLayout]) -> list[SectionSpan]:
    """Group consecutive pages that share the same (part, section)."""
    spans: list[SectionSpan] = []
    for p in pages:
        if spans and (spans[-1].part, spans[-1].section) == (p.part, p.section):
            spans[-1].end_page = p.page_number
        else:
            spans.append(SectionSpan(part=p.part, section=p.section,
                                     start_page=p.page_number, end_page=p.page_number))
    return spans


# ============================================================================
# 5. READER
# ============================================================================

def analyse_page(page, page_number: int) -> PageLayout:
    words = page.extract_words(extra_attrs=["size", "non_stroking_color"])
    body = body_words(words, page.height)

    n_cols = count_columns(body, page.width)
    n_rules = count_rule_lines(page)
    ratio = numeric_ratio(body)

    body_box = (0, HEADER_BAND, page.width, page.height - FOOTER_BAND)
    text = (page.within_bbox(body_box).extract_text() or "").strip()
    part, section = read_running_header(words)

    return PageLayout(
        page_number=page_number,
        width=page.width,
        height=page.height,
        word_count=len(body),
        has_text_layer=bool(words) or not page.images,
        layout_type=classify(len(body), n_cols, n_rules, ratio),
        n_columns=n_cols,
        n_rule_lines=n_rules,
        numeric_ratio=round(ratio, 3),
        part=part,
        section=section,
        title=find_title(words),
        text=text,
    )


def read_document(path: str | Path) -> DocumentLayout:
    path = Path(path)
    pages: list[PageLayout] = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            pages.append(analyse_page(page, number))
            page.flush_cache()  # keeps memory low on long reports
    return DocumentLayout(source_file=path.name, n_pages=len(pages),
                          pages=pages, sections=build_sections(pages))




# ============================================================================
# RUN IT: python -m risk_intel.stage1_onefile <pdf>
# ============================================================================

if __name__ == "__main__":
    import sys

    from .config import INTERIM_DIR

    pdf = Path(sys.argv[1])
    print(f"Reading {pdf.name} ...")
    doc = read_document(pdf)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"{pdf.stem}.stage1_onefile.json"
    out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"{doc.n_pages} pages, {len(doc.sections)} section runs -> {out}")