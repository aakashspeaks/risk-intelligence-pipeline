"""Read the PDF once and describe every page."""
from __future__ import annotations

from pathlib import Path

import pdfplumber

from .headers import find_title, read_running_header
from .layout import (FOOTER_BAND, HEADER_BAND, body_words, classify, count_columns,
                     count_rule_lines, numeric_ratio)
from .models import DocumentLayout, PageLayout
from .sections import build_sections


def analyse_page(page, page_number: int) -> PageLayout:
    """Describe one page."""
    words = page.extract_words(extra_attrs=["size", "non_stroking_color"])
    body = body_words(words, page.height)  # without the top menu and the footer

    n_cols = count_columns(body, page.width)
    n_rules = count_rule_lines(page)
    ratio = numeric_ratio(body)

    # Plain body text, cut to the body area so the menu and footer stay out.
    body_box = (0, HEADER_BAND, page.width, page.height - FOOTER_BAND)
    text = (page.within_bbox(body_box).extract_text() or "").strip()
    part, section = read_running_header(words)

    return PageLayout(
        page_number=page_number,
        width=page.width,
        height=page.height,
        word_count=len(body),
        has_text_layer=bool(words) or not page.images,  # no words but images = probably a scan
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
    """Describe every page of the PDF, then group the pages into sections."""
    path = Path(path)
    pages: list[PageLayout] = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            pages.append(analyse_page(page, number))
            page.flush_cache()  # frees memory on long reports
    return DocumentLayout(source_file=path.name, n_pages=len(pages),
                          pages=pages, sections=build_sections(pages))