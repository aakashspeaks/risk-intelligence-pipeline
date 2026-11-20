"""The golden set: the hand-checked answer key the pipeline output is scored against."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..config import GOLDEN_DIR

DEFAULT_GOLDEN = GOLDEN_DIR / "vestas_golden.json"


class GoldenRisk(BaseModel):
    id: str
    title: str
    tier: str
    kind: str
    category: str
    page: int
    must_mention_in_mitigation: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)


class GoldenDuplicate(BaseModel):
    principal: str
    duplicate_title: str
    duplicate_page: int


class GoldenGovernance(BaseModel):
    review_frequency: str
    reviewed_by: list[str]
    page: int


class Golden(BaseModel):
    report: str
    governance: GoldenGovernance
    risks: list[GoldenRisk]
    merged_duplicates: list[GoldenDuplicate] = Field(default_factory=list)
    must_not_be_returned_as_risks: list[str] = Field(default_factory=list)


def load_golden(path: str | Path = DEFAULT_GOLDEN) -> Golden:
    return Golden.model_validate_json(Path(path).read_text(encoding="utf-8"))