"""QuerySpec schema — produced by the LLM Intent & Entity Parser.

Reference: Solution Design §4.1, Listing 1.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Filters(BaseModel):
    """Filters extracted from the user query to scope data loading."""

    date_range: Optional[dict[str, str]] = Field(
        default=None,
        description="Date range with 'start' and 'end' keys in YYYY-MM-DD format.",
    )
    customer_id: Optional[str] = Field(
        default=None,
        description="Specific customer ID to scope the analysis.",
    )
    segment: Optional[str] = Field(
        default=None,
        description="Customer segment filter.",
    )
    country: Optional[str] = Field(
        default=None,
        description="Country filter.",
    )
    transaction_type: Optional[str] = Field(
        default=None,
        description="Transaction type filter (deposit/withdrawal/transfer/atm).",
    )


class ExplicitRule(BaseModel):
    """An explicit rule stated in the user query (e.g., '10+ transactions under $10,000')."""

    condition: Optional[str] = Field(
        default=None,
        description="The rule condition as a string expression.",
    )
    present: bool = Field(
        default=False,
        description="Whether an explicit rule was detected in the query.",
    )


class QuerySpec(BaseModel):
    """Structured representation of the user's natural language query.

    Produced by the Intent & Entity Extraction LLM call.
    This is the contract between the intent parser and the execution planner.
    """

    intent: Literal[
        "pattern_detection",
        "aggregation_rule",
        "entity_lookup",
        "broad_exploration",
    ] = Field(
        description="Classified intent of the user query.",
    )
    aml_pattern: Optional[
        Literal["structuring", "smurfing", "layering", "rapid_cashout"]
    ] = Field(
        default=None,
        description="Target AML pattern if detected, null otherwise.",
    )
    filters: Filters = Field(
        default_factory=Filters,
        description="Data filters extracted from the query.",
    )
    explicit_rule: ExplicitRule = Field(
        default_factory=ExplicitRule,
        description="Explicit rule/threshold stated in the query, if any.",
    )
    requires_ml_anomaly_detection: bool = Field(
        default=True,
        description="Whether the query requires ML-based anomaly detection.",
    )
    requires_full_eda: bool = Field(
        default=False,
        description="Whether the query requires full exploratory data analysis.",
    )
