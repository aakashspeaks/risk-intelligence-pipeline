"""Layout signals for one page. Part 1: body words, numbers, page type."""
from __future__ import annotations

import re

from .models import LayoutType

HEADER_BAND = 40  # points from the top that hold the running menu
FOOTER_BAND = 45  # points from the bottom that hold the footer

_NUMBER = re.compile(r"[\(\)\-–,.\d%]+")


def body_words(words: list[dict], page_height: float) -> list[dict]:
    """Words in the main body, without the top menu and the footer."""
    return [w for w in words if HEADER_BAND < w["top"] < page_height - FOOTER_BAND]


def numeric_ratio(words: list[dict]) -> float:
    """Share of words that look like numbers, e.g. 1,234 or (56) or 12%."""
    if not words:
        return 0.0
    n = sum(1 for w in words if _NUMBER.fullmatch(w["text"]) and any(c.isdigit() for c in w["text"]))
    return n / len(words)


def classify(word_count: int, n_columns: int, n_rule_lines: int, numeric_ratio: float) -> LayoutType:
    """Rule-based page type. The thresholds are a heuristic: re-check them on new reports."""
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

GUTTER = 14              # empty width (points) that counts as a gap between columns
MIN_COLUMN_SHARE = 0.05  # ignore "columns" holding under 5% of the words


def count_columns(words: list[dict], page_width: float) -> int:
    """Count text columns by finding empty vertical strips between blocks of words."""
    if len(words) < 30:
        return 0

    # Mark every horizontal position (x) that has at least one word over it.
    covered = [0] * (int(page_width) + 2)
    for w in words:
        for x in range(int(w["x0"]), min(int(w["x1"]) + 1, len(covered))):
            covered[x] += 1
    xs = [x for x, c in enumerate(covered) if c]
    lo, hi = xs[0], xs[-1]

    # Walk left to right. A run of empty positions at least GUTTER wide ends a block.
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

    # Keep only blocks that hold a real share of the words.
    total = len(words)
    kept = [b for b in blocks if sum(b[0] <= w["x0"] <= b[1] for w in words) / total >= MIN_COLUMN_SHARE]
    return len(kept)


def count_rule_lines(page) -> int:
    """Long horizontal lines on the page. Many of them usually means a table."""
    return sum(1 for e in page.edges if e["orientation"] == "h" and e["width"] > 100)