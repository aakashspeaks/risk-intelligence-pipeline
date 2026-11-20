#!/usr/bin/env python3
"""Stage 1 - Document intelligence (single file).

Scans the PDF once and writes a light description of every page:
  * layout signals (columns, ruled lines, numeric share) and a page type
  * running-menu section tracking (part / section / subsection)
  * headings, printed page label, quality flags
  * `regions`: column-aware / table-aware text, so Stage 2 never has to
    work with text that is interleaved across columns.

It does NOT look for risks. It answers "what is on each page, and where am I
in the report?".

Usage:
    pip install pdfplumber pydantic
    python stage1.py data/raw/VestasAnnualReport2025.pdf
    python stage1.py report.pdf -o out.json --pages 50-51,71-74 --regions all
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pdfplumber
from pydantic import BaseModel, Field

SCHEMA_VERSION = "2.0"
log = logging.getLogger("stage1")


# --------------------------------------------------------------------------
# 1. Profile: every report-specific assumption lives here (not in the code)
# --------------------------------------------------------------------------
@dataclass
class Profile:
    """Vestas 2025 settings. For another report, change these, not the code."""

    header_band: float = 40.0            # points from top that hold the running menu
    footer_band: float = 45.0            # points from bottom that hold the footer
    menu_line_split: float = 27.0        # y: above = menu line 1 (part), below = line 2 (section)
    menu_blue_rgb: tuple = (0.0, 0.35, 1.0)  # colour of the active menu item (RGB only)
    title_min_size: float = 16.0         # a heading must be at least this font size
    gutter: int = 14                     # empty width (pts) that counts as a column gap
    min_column_share: float = 0.05       # ignore "columns" holding under 5% of the words
    min_words_for_columns: int = 30
    graphic_max_words: int = 40          # below this = graphic page
    numeric_table_ratio: float = 0.30
    numeric_table_min_rules: int = 3
    table_min_rules: int = 8
    rule_min_width: float = 100.0        # a horizontal line must be this wide to count as a rule
    # Left/right split for the impacts-vs-financial-risks tables (p.71-74).
    split_header: tuple = ("Financial", "risks", "or", "opportunities")
    split_margin: float = 8.0
    label_margin: float = 60.0           # page number sits within this distance of the left/right edge


# --------------------------------------------------------------------------
# 2. Models: what Stage 1 produces
# --------------------------------------------------------------------------
LayoutType = Literal[
    "graphic",          # almost no text: cover, divider, image page
    "numeric_table",    # mostly numbers + ruled lines (financial statements)
    "table_or_matrix",  # ruled lines with text (risk matrix, sustainability tables)
    "multi_column",     # 3 or more text columns
    "two_column",       # 2 text columns
    "single_block",     # one block of text
]
RegionKind = Literal["column", "impacts_left", "financial_right"]


class Region(BaseModel):
    """A piece of the page in correct reading order (one column / one table half)."""

    kind: RegionKind
    x0: float
    x1: float
    top: float
    bottom: float
    text: str


class PageLayout(BaseModel):
    page_number: int = Field(ge=1, description="1-based position in the PDF file")
    page_label: str | None = Field(None, description="Page number printed in the footer")
    width: float
    height: float
    word_count: int
    has_text_layer: bool
    layout_type: LayoutType
    n_columns: int
    column_bounds: list[tuple[float, float]] = Field(default_factory=list)
    n_rule_lines: int
    rule_ys: list[float] = Field(default_factory=list, description="y of each distinct rule")
    numeric_ratio: float
    part: str | None = None
    section: str | None = None
    subsection: str | None = None
    section_source: Literal["menu", "inferred", "divider", "none"] = "none"
    citation_label: str | None = Field(None, description="Human-readable location for citations")
    title: str | None = Field(None, description="Largest text on the page")
    headings: list[str] = Field(default_factory=list, description="All large-text headings")
    text: str = Field(description="Body text, menu and footer removed (may interleave columns)")
    regions: list[Region] = Field(default_factory=list, description="Column-aware text")
    flags: list[str] = Field(default_factory=list, description="Quality warnings for this page")


class SectionSpan(BaseModel):
    """A run of consecutive pages sharing the same part and section."""

    part: str | None
    section: str | None
    start_page: int
    end_page: int


class DocumentLayout(BaseModel):
    schema_version: str
    source_file: str
    source_sha256: str
    created_at: str
    pdfplumber_version: str
    profile: dict
    n_pages: int
    pages: list[PageLayout]
    sections: list[SectionSpan]


# --------------------------------------------------------------------------
# 3. Layout signals
# --------------------------------------------------------------------------
_NUMBER = re.compile(r"[\(\)\-–,.\d%]+")


def body_words(words: list[dict], page_height: float, p: Profile) -> list[dict]:
    """Words in the main body, without the top menu and the footer."""
    return [w for w in words if p.header_band < w["top"] < page_height - p.footer_band]


def numeric_ratio(words: list[dict]) -> float:
    """Share of words that look like numbers, e.g. 1,234 or (56) or 12%."""
    if not words:
        return 0.0
    n = sum(1 for w in words if _NUMBER.fullmatch(w["text"]) and any(c.isdigit() for c in w["text"]))
    return n / len(words)


def find_column_blocks(words: list[dict], page_width: float, p: Profile) -> list[tuple[float, float]]:
    """Text columns as (x_start, x_end), found from empty vertical strips."""
    if len(words) < p.min_words_for_columns:
        return []
    covered = [0] * (int(page_width) + 2)
    for w in words:
        for x in range(max(int(w["x0"]), 0), min(int(w["x1"]) + 1, len(covered))):
            covered[x] += 1
    xs = [x for x, c in enumerate(covered) if c]
    if not xs:
        return []
    lo, hi = xs[0], xs[-1]

    blocks, start, last, gap = [], None, None, 0
    for x in range(lo, hi + 1):
        if covered[x]:
            if start is None:
                start = x
            last, gap = x, 0
        elif start is not None:
            gap += 1
            if gap == p.gutter:
                blocks.append((start, last))
                start = None
    if start is not None:
        blocks.append((start, hi))

    total = len(words)
    kept = [b for b in blocks
            if sum(b[0] <= w["x0"] <= b[1] for w in words) / total >= p.min_column_share]
    return [(float(a), float(b)) for a, b in kept]


def count_rule_lines(page, p: Profile) -> tuple[int, list[float]]:
    """(number of long horizontal lines, y of each distinct line)."""
    edges = [e for e in page.edges if e["orientation"] == "h" and e["width"] > p.rule_min_width]
    return len(edges), sorted({round(e["top"], 1) for e in edges})


def classify(word_count: int, n_columns: int, n_rules: int, ratio: float, p: Profile) -> LayoutType:
    """Rule-based page type. Thresholds are heuristics: re-check them on new reports."""
    if word_count < p.graphic_max_words:
        return "graphic"
    if ratio >= p.numeric_table_ratio and n_rules >= p.numeric_table_min_rules:
        return "numeric_table"
    if n_rules >= p.table_min_rules:
        return "table_or_matrix"
    if n_columns >= 3:
        return "multi_column"
    if n_columns == 2:
        return "two_column"
    return "single_block"


# --------------------------------------------------------------------------
# 4. Headers: section from the running menu, headings, printed page label
# --------------------------------------------------------------------------
@dataclass
class Menu:
    part: str | None = None
    section: str | None = None
    subsection: str | None = None
    has_menu: bool = False
    is_divider: bool = False


def _is_blue(color, p: Profile) -> bool:
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        return False
    return all(abs(a - b) < 0.05 for a, b in zip(color, p.menu_blue_rgb))


def _join_dedup(words: list[dict]) -> str:
    """Join words left to right. Over-printed (bold-faked) copies are dropped."""
    out: list[dict] = []
    for w in sorted(words, key=lambda w: (w["x0"], w["top"])):
        if any(o["text"] == w["text"] and abs(o["x0"] - w["x0"]) < 3 and abs(o["top"] - w["top"]) < 3
               for o in out):
            continue
        out.append(w)
    return " ".join(w["text"] for w in out)


def read_running_header(words: list[dict], p: Profile) -> Menu:
    """Part / section / subsection from the blue words of the top menu."""
    menu_words = [w for w in words if w["top"] < p.header_band]
    line1 = [w for w in menu_words if w["top"] < p.menu_line_split]
    blue = [w for w in menu_words if _is_blue(w.get("non_stroking_color"), p)]
    if not blue:
        return Menu()
    # Divider pages show every menu item in blue: there is no "active" item.
    if len(line1) >= 6 and all(_is_blue(w.get("non_stroking_color"), p) for w in line1):
        return Menu(has_menu=True, is_divider=True)
    part = _join_dedup([w for w in blue if w["top"] < p.menu_line_split]) or None
    raw = _join_dedup([w for w in blue if w["top"] >= p.menu_line_split]) or None
    section, subsection = None, None
    if raw:
        bits = re.split(r"\s+[–-]\s+", raw, maxsplit=1)
        section = bits[0]
        subsection = bits[1] if len(bits) > 1 else None
    return Menu(part=part, section=section, subsection=subsection, has_menu=True)


def find_title(words: list[dict], p: Profile) -> str | None:
    """Largest text below the menu. None if the page only has small text."""
    body = [w for w in words if w["top"] > p.header_band]
    if not body:
        return None
    biggest = max(w["size"] for w in body)
    if biggest < p.title_min_size:
        return None
    big = [w for w in body if abs(w["size"] - biggest) < 0.5]
    big.sort(key=lambda w: (round(w["top"]), w["x0"]))
    return " ".join(w["text"] for w in big)[:150]


def find_headings(words: list[dict], p: Profile, limit: int = 12) -> list[str]:
    """Every large-text heading, kept separate (find_title joins them)."""
    big = [w for w in words if w["top"] > p.header_band and w["size"] >= p.title_min_size]
    big.sort(key=lambda w: (round(w["top"]), w["x0"]))
    lines: list[dict] = []
    for w in big:  # 1) words -> lines (same row, small x gap)
        cur = lines[-1] if lines else None
        if (cur and abs(w["top"] - cur["top"]) < 3 and w["x0"] - cur["x1"] < 25
                and abs(w["size"] - cur["size"]) < 0.5):
            cur["text"] += " " + w["text"]
            cur["x1"] = w["x1"]
        else:
            lines.append({"text": w["text"], "x0": w["x0"], "x1": w["x1"], "top": w["top"],
                          "bottom": w["bottom"], "size": w["size"]})
    merged: list[dict] = []
    for ln in lines:  # 2) lines -> headings (same column, directly below)
        for m in reversed(merged):
            if (abs(m["x0"] - ln["x0"]) < 10 and abs(m["size"] - ln["size"]) < 0.5
                    and 0 <= ln["top"] - m["bottom"] < m["size"]):
                m["text"] += " " + ln["text"]
                m["bottom"] = ln["bottom"]
                break
        else:
            merged.append(dict(ln))
    merged.sort(key=lambda m: (round(m["top"]), m["x0"]))
    return [m["text"][:150] for m in merged[:limit]]


def read_page_label(words: list[dict], page_width: float, page_height: float, p: Profile) -> str | None:
    """Page number printed in the footer's outer margin (1-3 digits).

    Footnotes also sit in the footer band, but near the centre, so only digits
    in the outer margin count. The year 2025 is ignored (4 digits).
    """
    cands = [w for w in words
             if w["top"] >= page_height - p.footer_band
             and re.fullmatch(r"\d{1,3}", w["text"])
             and (w["x0"] < p.label_margin or w["x1"] > page_width - p.label_margin)]
    return max(cands, key=lambda w: w["top"])["text"] if cands else None


# --------------------------------------------------------------------------
# 5. Regions: text in the right reading order
# --------------------------------------------------------------------------
def _find_split_x(words: list[dict], p: Profile) -> float | None:
    """x of the 'Financial risks or opportunities' header, if the page has one."""
    toks = list(p.split_header)
    body = sorted((w for w in words if w["top"] > p.header_band), key=lambda w: (round(w["top"]), w["x0"]))
    for i in range(len(body) - len(toks) + 1):
        seq = body[i:i + len(toks)]
        if [w["text"] for w in seq] == toks and abs(seq[0]["top"] - seq[-1]["top"]) < 3:
            return seq[0]["x0"] - p.split_margin
    return None


def extract_regions(page, words: list[dict], layout_type: str,
                    blocks: list[tuple[float, float]], p: Profile) -> list[Region]:
    top, bottom = p.header_band, page.height - p.footer_band
    specs: list[tuple[str, float, float]] = []

    split_x = _find_split_x(words, p)
    if split_x is not None:
        specs = [("impacts_left", 0.0, split_x), ("financial_right", split_x, page.width)]
    elif layout_type in ("multi_column", "two_column", "table_or_matrix") and len(blocks) >= 2:
        # Cut in the middle of each gutter so no word is clipped.
        edges = [max(blocks[0][0] - 4, 0.0)]
        edges += [(blocks[i][1] + blocks[i + 1][0]) / 2 for i in range(len(blocks) - 1)]
        edges.append(min(blocks[-1][1] + 4, page.width))
        specs = [("column", edges[i], edges[i + 1]) for i in range(len(blocks))]

    regions = []
    for kind, x0, x1 in specs:
        text = (page.within_bbox((x0, top, x1, bottom)).extract_text() or "").strip()
        if text:
            regions.append(Region(kind=kind, x0=round(x0, 1), x1=round(x1, 1),
                                  top=top, bottom=round(bottom, 1), text=text))
    return regions


# --------------------------------------------------------------------------
# 6. Reader: one page, then the whole document
# --------------------------------------------------------------------------
def _citation_label(part, section, subsection, headings, title) -> str | None:
    path = [x for x in (part, section, subsection) if x]
    if not section:
        # No section line on this page: the first heading is the best locator.
        first = title if title in headings else (headings[0] if headings else title)
        if first:
            path.append(first)
    return " > ".join(path) or None


def analyse_page(page, page_number: int, p: Profile, with_regions: bool) -> tuple[PageLayout, Menu]:
    words = page.extract_words(extra_attrs=["size", "non_stroking_color"])
    body = body_words(words, page.height, p)

    blocks = find_column_blocks(body, page.width, p)
    n_rules, rule_ys = count_rule_lines(page, p)
    ratio = numeric_ratio(body)
    ltype = classify(len(body), len(blocks), n_rules, ratio, p)

    body_box = (0, p.header_band, page.width, page.height - p.footer_band)
    text = (page.within_bbox(body_box).extract_text() or "").strip()
    menu = read_running_header(words, p)
    title = find_title(words, p)

    flags = []
    if not words and page.images:
        flags.append("no_text_layer")      # looks like a scan: needs OCR
    if "(cid:" in text:
        flags.append("garbled_glyphs")     # fonts without a unicode map
    regions = extract_regions(page, words, ltype, blocks, p) if with_regions else []

    layout = PageLayout(
        page_number=page_number,
        page_label=read_page_label(words, page.width, page.height, p),
        width=page.width, height=page.height,
        word_count=len(body),
        has_text_layer=bool(words) and "no_text_layer" not in flags,
        layout_type=ltype,
        n_columns=len(blocks), column_bounds=blocks,
        n_rule_lines=n_rules, rule_ys=rule_ys,
        numeric_ratio=round(ratio, 3),
        part=menu.part, section=menu.section, subsection=menu.subsection,
        section_source="divider" if menu.is_divider else ("menu" if menu.has_menu else "none"),
        citation_label=None,
        title=title, headings=find_headings(words, p),
        text=text, regions=regions, flags=flags,
    )
    return layout, menu


def _failed_page(page, number: int, err: Exception) -> tuple[PageLayout, Menu]:
    """One bad page must not kill a 195-page run: keep a stub and report the error."""
    stub = PageLayout(page_number=number, width=float(page.width), height=float(page.height),
                      word_count=0, has_text_layer=False, layout_type="graphic", n_columns=0,
                      n_rule_lines=0, numeric_ratio=0.0, text="",
                      flags=[f"error:{type(err).__name__}:{err}"[:200]])
    return stub, Menu()


def fill_gaps(pages: list[PageLayout], menus: list[Menu]) -> None:
    """Menu-less pages inside one section (e.g. a full-page graphic) inherit its part.

    Only when the page before and the page after agree, so a page between two
    different parts is never guessed.
    """
    i, n = 0, len(pages)
    while i < n:
        if menus[i].has_menu:
            i += 1
            continue
        j = i
        while j < n and not menus[j].has_menu:
            j += 1
        if i > 0 and j < n and not menus[i - 1].is_divider and not menus[j].is_divider:
            a, b = pages[i - 1], pages[j]
            if a.part and a.part == b.part:
                for k in range(i, j):
                    pages[k].part = a.part
                    pages[k].section_source = "inferred"
                    if a.section and a.section == b.section:
                        pages[k].section = a.section
        i = j


def build_sections(pages: list[PageLayout]) -> list[SectionSpan]:
    """Group consecutive pages that share the same (part, section)."""
    spans: list[SectionSpan] = []
    for pg in pages:
        if spans and (spans[-1].part, spans[-1].section) == (pg.part, pg.section):
            spans[-1].end_page = pg.page_number
        else:
            spans.append(SectionSpan(part=pg.part, section=pg.section,
                                     start_page=pg.page_number, end_page=pg.page_number))
    return spans


def parse_pages(spec: str | None, n_pages: int) -> list[int]:
    """'50-51,71-74' -> [50, 51, 71, 72, 73, 74]. None -> all pages."""
    if not spec:
        return list(range(1, n_pages + 1))
    out: list[int] = []
    for part in spec.split(","):
        a, _, b = part.strip().partition("-")
        out.extend(range(int(a), int(b or a) + 1))
    return sorted({n for n in out if 1 <= n <= n_pages})


def read_document(path: str | Path, profile: Profile | None = None, pages: str | None = None,
                  regions: str = "all", key_pages: str = "50-51,71-74,85-92,118") -> DocumentLayout:
    """Describe every page of the PDF, then group the pages into sections.

    regions: 'all' (every column/table page), 'key' (only key_pages) or 'none'.
    """
    p = profile or Profile()
    path = Path(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    layouts: list[PageLayout] = []
    menus: list[Menu] = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        wanted = parse_pages(pages, total)
        key = set(parse_pages(key_pages, total))
        for number in wanted:
            page = pdf.pages[number - 1]
            with_regions = regions == "all" or (regions == "key" and number in key)
            try:
                lay, menu = analyse_page(page, number, p, with_regions)
            except Exception as err:  # noqa: BLE001 - keep going, record the failure
                log.warning("page %d failed: %s", number, err)
                lay, menu = _failed_page(page, number, err)
            layouts.append(lay)
            menus.append(menu)
            page.flush_cache()  # frees memory on long reports

    fill_gaps(layouts, menus)
    for lay in layouts:
        lay.citation_label = _citation_label(lay.part, lay.section, lay.subsection,
                                             lay.headings, lay.title)
    return DocumentLayout(
        schema_version=SCHEMA_VERSION, source_file=path.name, source_sha256=sha,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        pdfplumber_version=pdfplumber.__version__, profile=asdict(p),
        n_pages=total, pages=layouts, sections=build_sections(layouts),
    )


# --------------------------------------------------------------------------
# 7. Command line
# --------------------------------------------------------------------------
def _print_report(doc: DocumentLayout, key_pages: str, seconds: float) -> None:
    print(f"\n{doc.source_file}: {len(doc.pages)}/{doc.n_pages} pages, "
          f"{len(doc.sections)} section runs, {seconds:.1f}s")
    print("Page types:", dict(Counter(pg.layout_type for pg in doc.pages)))
    flagged = [(pg.page_number, pg.flags) for pg in doc.pages if pg.flags]
    print("Flagged pages:", flagged or "none")
    mismatch = [pg.page_number for pg in doc.pages
                if pg.page_label and pg.page_label != str(pg.page_number)]
    print("Printed page label differs from PDF index on:", mismatch[:15] or "none")
    by_num = {pg.page_number: pg for pg in doc.pages}
    print("\nKey pages")
    print(f"{'pg':>4} {'type':<16} {'col':>3} {'rules':>5} {'reg':>3}  location")
    for n in parse_pages(key_pages, doc.n_pages):
        pg = by_num.get(n)
        if pg:
            print(f"{pg.page_number:>4} {pg.layout_type:<16} {pg.n_columns:>3} {pg.n_rule_lines:>5} "
                  f"{len(pg.regions):>3}  {pg.citation_label}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 1: describe every page of an annual report.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="output JSON (default: <pdf name>.stage1.json next to the PDF)")
    ap.add_argument("--pages", default=None, help="only these pages, e.g. 50-51,71-74")
    ap.add_argument("--regions", choices=["all", "key", "none"], default="all")
    ap.add_argument("--key-pages", default="50-51,71-74,85-92,118")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")

    out = args.out or args.pdf.with_suffix(".stage1.json")
    t0 = time.time()
    doc = read_document(args.pdf, pages=args.pages, regions=args.regions, key_pages=args.key_pages)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    _print_report(doc, args.key_pages, time.time() - t0)
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
