"""What Stage 1 produces: a light description of every page."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# What the page looks like. Later stages choose their method from this.
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