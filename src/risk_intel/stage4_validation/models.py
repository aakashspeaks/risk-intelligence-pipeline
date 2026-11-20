"""What Stage 4 produces: validated records, plus a log of what it found and changed."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..stage2_candidates.models import GovernanceCandidate
from ..stage3_extraction.models import Risk


class Issue(BaseModel):
    """One problem found while checking a record."""

    risk_id: str
    check: Literal["evidence", "page", "section", "duplicate"]
    severity: Literal["error", "warning"]
    message: str


class MergeNote(BaseModel):
    """A record folded into another one, kept so a human can see what was merged and why."""

    kept_id: str
    merged_id: str
    reason: str


class Stage4Output(BaseModel):
    """The validated records, with an audit trail."""

    source_file: str
    risks: list[Risk]
    excluded_immaterial: list[str]
    governance: GovernanceCandidate | None = None
    issues: list[Issue] = Field(default_factory=list)
    merges: list[MergeNote] = Field(default_factory=list)