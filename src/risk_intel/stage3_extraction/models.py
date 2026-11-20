"""What Stage 3 produces: the final risk record."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    """A fixed list, so companies can be compared and filtered ("every company with cyber risk")."""

    financial = "financial"
    operational = "operational"
    regulatory_geopolitical = "regulatory_geopolitical"
    market = "market"
    climate = "climate"
    environmental = "environmental"
    cyber = "cyber"
    supply_chain = "supply_chain"
    health_safety = "health_safety"
    human_rights = "human_rights"
    compliance_conduct = "compliance_conduct"
    other = "other"


class Kind(str, Enum):
    """The report marks risk vs opportunity with an icon. We keep both, labelled, so an
    opportunity can never leak into a "risks" query."""

    risk = "risk"
    opportunity = "opportunity"


class Source(BaseModel):
    section: str | None = Field(None, description="Section line from the report's top menu")
    page: int = Field(ge=1, description="Page where the risk was found")
    method: str = Field(description="Which reader produced it: 'matrix' or 'table'")
    evidence: str = Field(description="Verbatim start of the source text, so a human can find it on the page")


class Risk(BaseModel):
    id: str
    title: str = Field(max_length=120)
    #description: str = Field(description="2 to 3 sentences")
    description: str = Field(description="At most 3 sentences. The report gives one sentence for table entries; we do not pad.")
    description_origin: str = Field("rules", description="'rules', or 'llm:<model>:<prompt version>'. If a model summary was rejected, this says why the rules were used.")
    category: Category
    kind: Kind = Kind.risk
    tier: str = Field(description="'principal' (the report's own main-risk list) or 'sustainability_iro' (the materiality tables)")
    potential_impact: str | None = None
    mitigation: str | None = Field(None, description="Management action stated in the report, if any")
    value_chain: str | None = Field(None, description="Where it applies, e.g. 'Downstream'. Tables only.")
    source: Source
    cross_references: list[int] = Field(default_factory=list,
                                        description="Other pages where the same risk appears")

from ..stage2_candidates.models import GovernanceCandidate


class Stage3Output(BaseModel):
    """Everything Stage 3 hands over to Stage 4."""

    source_file: str
    risks: list[Risk]
    excluded_immaterial: list[str] = Field(
        description="Topics the report itself scores as immaterial: not risks, kept for audit")
    governance: GovernanceCandidate | None = None