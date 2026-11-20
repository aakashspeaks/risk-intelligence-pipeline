from __future__ import annotations

from .models import PageLayout, SectionSpan


def build_sections(pages: list[PageLayout]) -> list[SectionSpan]:
    """Group consecutive pages that share the same (part, section)."""
    spans: list[SectionSpan] = []
    for p in pages:
        if spans and (spans[-1].part, spans[-1].section) == (p.part, p.section):
            spans[-1].end_page = p.page_number  # same section as the previous page: extend it
        else:
            spans.append(SectionSpan(part=p.part, section=p.section,
                                     start_page=p.page_number, end_page=p.page_number))
    return spans