"""Section identification from the running menu at the top of each page."""
from __future__ import annotations

BLUE = (0.0, 0.35, 1.0)   # colour of the active menu item
MENU_LINE_SPLIT = 27      # y position: above = menu line 1 (part), below = line 2 (section)
TITLE_MIN_SIZE = 16.0     # a page title must be at least this font size


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
    """Largest text below the menu. Returns None if the page only has small text."""
    body = [w for w in words if w["top"] > 40]
    if not body:
        return None
    biggest = max(w["size"] for w in body)
    if biggest < TITLE_MIN_SIZE:
        return None
    big = [w for w in body if abs(w["size"] - biggest) < 0.5]
    big.sort(key=lambda w: (round(w["top"]), w["x0"]))
    return " ".join(w["text"] for w in big)[:150]