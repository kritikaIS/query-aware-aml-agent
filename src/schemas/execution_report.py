"""ExecutionReport schema — the final structured output returned to the user.

Reference: Solution Design §8, Listing 5.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.query_spec import QuerySpec
from src.schemas.execution_plan import ExecutionPlan


class ContributingFeature(BaseModel):
    """A feature that contributed to a flagged entity's risk score."""

    feature: str = Field(description="Feature name.")
    value: float = Field(description="Feature value for this entity.")
    z_score: float = Field(description="Z-score relative to the cohort.")


class FlaggedEntity(BaseModel):
    """A customer/entity flagged as suspicious."""

    customer_id: str = Field(description="Customer identifier.")
    risk_score: float = Field(
        description="Continuous risk score between 0 and 1.",
    )
    risk_band: str = Field(
        description="Classified risk band: Low, Medium, or High.",
    )
    aml_pattern_matched: Optional[str] = Field(
        default=None,
        description="AML pattern detected (structuring, smurfing, layering, etc.).",
    )
    top_contributing_features: list[ContributingFeature] = Field(
        default_factory=list,
        description="Features that most contributed to the risk score.",
    )
    explanation: str = Field(
        description="Human-readable explanation of why this entity was flagged.",
    )
    recommended_action: str = Field(
        description="Escalation action: Monitor, Flag for review, or Report (SAR draft).",
    )


class SummaryMetrics(BaseModel):
    """Aggregate metrics for the execution run."""

    total_transactions_scanned: int = Field(
        description="Total number of transactions processed.",
    )
    entities_flagged: int = Field(
        description="Total entities flagged across all risk bands.",
    )
    high_risk: int = Field(description="Count of High risk entities.")
    medium_risk: int = Field(description="Count of Medium risk entities.")
    low_risk: int = Field(description="Count of Low risk entities.")


class ExecutionReport(BaseModel):
    """Final structured report returned to the user and rendered by the front-end.

    This is the single object judges inspect directly.
    """

    user_query: str = Field(
        description="The original natural language query.",
    )
    query_spec: QuerySpec = Field(
        description="Structured query specification produced by intent parsing.",
    )
    execution_plan: ExecutionPlan = Field(
        description="The execution plan including reasoning and skipped tools.",
    )
    flagged_entities: list[FlaggedEntity] = Field(
        default_factory=list,
        description="List of entities flagged as suspicious.",
    )
    summary_metrics: SummaryMetrics = Field(
        description="Aggregate metrics for this run.",
    )
    charts: list[str] = Field(
        default_factory=list,
        description="File paths to generated chart images.",
    )
