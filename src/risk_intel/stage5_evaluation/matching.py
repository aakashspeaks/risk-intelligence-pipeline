"""Match output records to golden records by title, one to one."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from ..stage3_extraction.models import Risk
from .golden import GoldenRisk

MATCH_THRESHOLD = 0.85   # title similarity needed for a match (1.0 = identical)


def normalise(title: str) -> str:
    """Lowercase letters and digits only, so punctuation can't cause a miss."""
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalise(a), normalise(b)).ratio()


def match_records(
    golden: list[GoldenRisk], output: list[Risk], threshold: float = MATCH_THRESHOLD
) -> tuple[list[tuple[GoldenRisk, Risk]], list[GoldenRisk], list[Risk]]:
    """Return (matched pairs, golden records nobody matched = missed, output records nobody matched = extra)."""
    pairs = sorted(
        ((similarity(g.title, r.title), gi, ri)
         for gi, g in enumerate(golden) for ri, r in enumerate(output)),
        reverse=True,
    )
    used_golden: set[int] = set()
    used_output: set[int] = set()
    matched: list[tuple[GoldenRisk, Risk]] = []
    for score, gi, ri in pairs:
        if score < threshold:
            break
        if gi in used_golden or ri in used_output:
            continue
        used_golden.add(gi)
        used_output.add(ri)
        matched.append((golden[gi], output[ri]))

    missed = [g for gi, g in enumerate(golden) if gi not in used_golden]
    extra = [r for ri, r in enumerate(output) if ri not in used_output]
    return matched, missed, extra