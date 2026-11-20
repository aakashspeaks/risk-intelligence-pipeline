"""What Stage 2 produces. Part 1: the page finder's output."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CandidatePage(BaseModel):
    page_number: int = Field(ge=1)
    score: float = Field(description="Higher means more likely to contain principal risks")
    reasons: list[str] = Field(description="Why the page scored as it did, so a human can check")

class RiskCandidate(BaseModel):
    """One possible principal risk, cut out of the report with its source."""

    title: str
    description: str
    potential_impact: str | None = None
    mitigation: str | None = None
    tier: str = Field(description="'principal' = the report's own main-risk list")
    page: int = Field(ge=1)
    section: str | None = Field(None, description="Section line from the top menu, e.g. 'Corporate governance – Risk management'")
    method: str = Field(description="Which reader produced it, e.g. 'matrix'")
    evidence: str = Field(description="Verbatim start of the description, so a human can find it on the page")
    topic: str | None = Field(None, description="Topic group in the table, e.g. 'E1 Climate Change'")
    side: str | None = Field(None, description="'impact' or 'financial' for the sustainability tables")
    value_chain: str | None = Field(None, description="Where in the value chain it applies, e.g. 'Downstream'")

class GovernanceCandidate(BaseModel):
    """How the company says it reviews its principal risks."""

    review_frequency: str = Field(description="e.g. 'every six months'")
    reviewed_by: list[str] = Field(description="Bodies that review the risks, e.g. 'Board of Directors'")
    page: int = Field(ge=1)
    evidence: str = Field(description="Verbatim sentence from the page")

class Stage2Output(BaseModel):
    """Everything Stage 2 hands over to Stage 3."""

    source_file: str
    pages_used: list[int] = Field(description="Pages the candidates were read from")
    candidates: list[RiskCandidate]
    immaterial_statements: list[str] = Field(
        description="Topics the report itself scores as immaterial: not risks, kept for audit")
    governance: GovernanceCandidate | None = None