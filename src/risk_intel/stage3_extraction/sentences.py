"""Split text into sentences, and keep the first few."""
from __future__ import annotations

import re

# A sentence ends at . ! or ? followed by a space and a capital letter or opening quote.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z“‘\"])")

# Abbreviations whose full stop must not end a sentence.
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "incl.", "approx.", "No.")
DOT_PLACEHOLDER = "<DOT>"


def split_sentences(text: str) -> list[str]:
    protected = text
    for abbreviation in ABBREVIATIONS:
        protected = protected.replace(abbreviation, abbreviation.replace(".", DOT_PLACEHOLDER))
    parts = SENTENCE_END.split(protected)
    return [p.replace(DOT_PLACEHOLDER, ".").strip() for p in parts if p.strip()]


def first_sentences(text: str, n: int = 3) -> str:
    """The first n sentences, joined with single spaces."""
    return " ".join(split_sentences(text)[:n])