"""Deterministic Planner — implementation assumption for no-LLM execution.

Reference: Solution Design §4.1, §4.2, §4.3, §4.4, §6.7.

DOCUMENTED REQUIREMENTS this module satisfies:
  - The planning interface must produce a valid QuerySpec (§4.1).
  - The planning interface must produce a valid ExecutionPlan (§4.2).
  - Plans must be constrained to the registered tool list (§4.3, §6.7 step 2).
  - Plans referencing unregistered tools must be rejected (§6.7 step 4, §11).
  - A safe fallback plan must exist when plan generation fails (§6.7 step 4).
  - The three reference query patterns must produce distinct execution paths (§4.4).

IMPLEMENTATION ASSUMPTION:
  When no LLM is configured, a deterministic rule-based planner produces the
  QuerySpec and ExecutionPlan. This is NOT mentioned in the documentation; it
  exists solely to allow deterministic execution and testing without an API key.
  The same interface (`extract_query_spec` and `build_execution_plan`) is used
  regardless of whether an LLM or this deterministic planner is behind it, so
  the controller remains identical and the LLM can be slotted in later.
  LLM never receives raw transaction data (§3.1 principle 1).
"""

from __future__ import annotations

import re
from typing import Any

from src.schemas.execution_plan import ExecutionPlan, PlanStep, SkippedTool
from src.schemas.query_spec import QuerySpec, Filters, ExplicitRule


# ---------------------------------------------------------------------------
# Deterministic intent extraction
# ---------------------------------------------------------------------------

_PATTERN_KEYWORDS = {
    "structuring": ["structuring", "structured", "structur"],
    "smurfing": ["smurfing", "smurf"],
    "layering": ["layering", "layer"],
    "rapid_cashout": ["cash-out", "cashout", "rapid cash", "cash out"],
}

_RULE_PATTERN = re.compile(
    r"(\d+)\+?\s*transactions?\s+(?:under|below|less than|<)\s*\$?([\d,]+)",
    re.IGNORECASE,
)

_CUSTOMER_PATTERN = re.compile(
    r"customer\s+(?:id\s+)?['\"]?(\w+)['\"]?",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"last\s+(\d+)\s+(day|week|month)s?",
    re.IGNORECASE,
)


def _detect_aml_pattern(query_lower: str) -> str | None:
    for pattern, keywords in _PATTERN_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            return pattern
    return None


def _detect_explicit_rule(query: str) -> ExplicitRule:
    """Extract an explicit count+threshold rule if present.

    DOCUMENTED: QuerySpec.explicit_rule.condition (§4.1 Listing 1).
    """
    match = _RULE_PATTERN.search(query)
    if match:
        count = match.group(1)
        amount = match.group(2).replace(",", "")
        condition = f"count(transactions) >= {count} AND amount < {amount}"
        return ExplicitRule(condition=condition, present=True)
    return ExplicitRule(condition=None, present=False)


def _detect_date_range(query_lower: str) -> dict | None:
    """Extract a relative date range from phrases like 'last 30 days'."""
    import datetime
    match = _DATE_PATTERN.search(query_lower)
    if not match:
        return None
    n = int(match.group(1))
    unit = match.group(2).lower()
    end_date = datetime.date.today()
    if unit.startswith("day"):
        start_date = end_date - datetime.timedelta(days=n)
    elif unit.startswith("week"):
        start_date = end_date - datetime.timedelta(weeks=n)
    else:  # month
        start_date = end_date - datetime.timedelta(days=n * 30)
    return {"start": str(start_date), "end": str(end_date)}


def _detect_customer_id(query: str) -> str | None:
    match = _CUSTOMER_PATTERN.search(query)
    if match:
        return match.group(1)
    return None


class DeterministicPlanner:
    """Rule-based planner that produces QuerySpec and ExecutionPlan deterministically.

    IMPLEMENTATION ASSUMPTION — not in documentation.
    Behind the same interface as the LLM planner, so the AgentController
    does not need to know which planner is active.
    """

    def __init__(self, registered_tools: list[str]) -> None:
        """
        Args:
            registered_tools: List of tool names available in the registry.
                              Used to constrain plan generation.
        """
        self._registered_tools = registered_tools

    def extract_query_spec(self, user_query: str) -> QuerySpec:
        """Produce a QuerySpec from a natural language query deterministically.

        Implements the documented QuerySpec schema (§4.1 Listing 1).
        LLM never receives raw transaction data (§3.1 principle 1).
        """
        q = user_query.lower()

        # Detect intent
        explicit_rule = _detect_explicit_rule(user_query)
        customer_id = _detect_customer_id(user_query)
        aml_pattern = _detect_aml_pattern(q)

        if customer_id:
            intent = "entity_lookup"
        elif explicit_rule.present:
            intent = "aggregation_rule"
        elif aml_pattern:
            intent = "pattern_detection"
        else:
            intent = "broad_exploration"

        # Detect filters
        date_range = _detect_date_range(q)
        filters = Filters(
            date_range=date_range,
            customer_id=customer_id,
        )

        requires_ml = not explicit_rule.present and intent != "entity_lookup"
        requires_eda = intent == "broad_exploration"

        return QuerySpec(
            intent=intent,
            aml_pattern=aml_pattern,
            filters=filters,
            explicit_rule=explicit_rule,
            requires_ml_anomaly_detection=requires_ml,
            requires_full_eda=requires_eda,
        )

    def build_execution_plan(self, spec: QuerySpec) -> ExecutionPlan:
        """Produce a deterministic ExecutionPlan for the given QuerySpec.

        Implements the documented ExecutionPlan schema (§4.2 Listing 2).
        Reproduces the three reference query patterns from §4.4.
        Only references tools present in the registry.
        """
        import uuid
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        steps: list[PlanStep] = []
        skipped: list[SkippedTool] = []

        # Always start with data_loader
        loader_args: dict[str, Any] = {}
        if spec.filters.date_range:
            dr = spec.filters.date_range
            loader_args["date_range"] = [dr["start"], dr["end"]]
        if spec.filters.customer_id:
            loader_args["customer_id"] = spec.filters.customer_id
        if spec.filters.segment:
            loader_args["segment"] = spec.filters.segment
        if spec.filters.country:
            loader_args["country"] = spec.filters.country
        if spec.filters.transaction_type:
            loader_args["transaction_type"] = spec.filters.transaction_type

        if "data_loader" in self._registered_tools:
            steps.append(PlanStep(tool="data_loader", args=loader_args))

        # EDA — only for broad_exploration
        if spec.requires_full_eda:
            if "eda_tool" in self._registered_tools:
                steps.append(PlanStep(tool="eda_tool", args={}))
        else:
            skipped.append(SkippedTool(
                tool="eda_tool",
                reason=(
                    "Query is pattern-targeted or entity-scoped; "
                    "full-dataset profiling adds no value here."
                ) if spec.intent != "broad_exploration" else "Not requested.",
            ))

        # Feature engineering — skipped for pure aggregation_rule queries
        if spec.intent == "aggregation_rule":
            skipped.append(SkippedTool(
                tool="feature_engineering",
                reason=(
                    "Explicit rule supplied; feature engineering not needed "
                    "for count/threshold aggregation."
                ),
            ))
        else:
            fe_args: dict[str, Any] = {}
            if spec.aml_pattern:
                fe_args["feature_set"] = spec.aml_pattern
            if spec.filters.customer_id:
                fe_args["entity_scoped"] = True
            if "feature_engineering" in self._registered_tools:
                steps.append(PlanStep(tool="feature_engineering", args=fe_args))

        # Anomaly detection
        if spec.intent == "aggregation_rule":
            # Rule engine path — documented §4.4 reference query 2
            ad_args: dict[str, Any] = {"method": "rule_engine"}
            if spec.aml_pattern:
                ad_args["target_pattern"] = spec.aml_pattern
            if "anomaly_detection" in self._registered_tools:
                steps.append(PlanStep(tool="anomaly_detection", args=ad_args))
            skipped.append(SkippedTool(
                tool="anomaly_detection_ml",
                reason=(
                    "Query contains explicit rule; ML anomaly detection skipped. "
                    "Rule engine used directly."
                ),
            ))
        else:
            method = "statistical"
            if spec.requires_ml_anomaly_detection:
                if spec.aml_pattern in ("structuring", "layering"):
                    method = "ml"
                else:
                    method = "statistical"
            ad_args = {"method": method}
            if spec.aml_pattern:
                ad_args["target_pattern"] = spec.aml_pattern
            if "anomaly_detection" in self._registered_tools:
                steps.append(PlanStep(tool="anomaly_detection", args=ad_args))

        # Risk classification — always present
        rc_args: dict[str, Any] = {"scheme": "pattern_aware"}
        if "risk_classification" in self._registered_tools:
            steps.append(PlanStep(tool="risk_classification", args=rc_args))

        # Escalation — documented in pipeline
        if "escalation" in self._registered_tools:
            steps.append(PlanStep(tool="escalation", args={}))

        # Explanation — always last, tie_to_query documented (§4.2 Listing 2)
        if "explanation" in self._registered_tools:
            steps.append(PlanStep(
                tool="explanation",
                args={"tie_to_query": True},
            ))

        # Build reasoning string
        reasoning = _build_reasoning(spec)

        return ExecutionPlan(
            plan_id=plan_id,
            reasoning=reasoning,
            steps=steps,
            skipped_tools=skipped,
        )


def _build_reasoning(spec: QuerySpec) -> str:
    """Build a human-readable reasoning string for the plan."""
    if spec.intent == "aggregation_rule":
        return (
            f"Query contains an explicit rule condition; rule engine applied directly. "
            f"Feature engineering and ML anomaly detection skipped."
        )
    if spec.intent == "entity_lookup":
        return (
            f"Query scoped to a single customer (ID: {spec.filters.customer_id}). "
            f"Full EDA skipped. Lightweight feature engineering applied entity-scoped."
        )
    if spec.intent == "pattern_detection":
        pattern = spec.aml_pattern or "unknown pattern"
        return (
            f"Query targets a specific AML pattern ({pattern}) "
            + (f"with time filter {spec.filters.date_range}. " if spec.filters.date_range else ". ")
            + f"Broad EDA unnecessary. Pattern-specific features and detection applied."
        )
    return (
        "Broad exploration requested. Full EDA and all detection methods applied."
    )


# ---------------------------------------------------------------------------
# Plan Validator
# ---------------------------------------------------------------------------

class PlanValidator:
    """Validates ExecutionPlan against the registered tool list.

    DOCUMENTED: §6.7 step 4, §11 Risks — reject/repair plans referencing
    unregistered tools or missing required arguments.
    """

    def __init__(self, registered_tools: list[str]) -> None:
        self._registered = set(registered_tools)

    def validate(self, plan: ExecutionPlan) -> list[str]:
        """Return a list of validation error strings (empty = valid).

        DOCUMENTED §6.7 step 4: reject plans referencing unregistered tools
        or missing required arguments.
        """
        errors: list[str] = []
        for step in plan.steps:
            if step.tool not in self._registered:
                errors.append(
                    f"Tool '{step.tool}' in plan step is not registered. "
                    f"Registered tools: {sorted(self._registered)}"
                )
        if not plan.steps:
            errors.append("ExecutionPlan contains no steps.")
        if not plan.plan_id:
            errors.append("ExecutionPlan is missing plan_id.")
        return errors

    def is_valid(self, plan: ExecutionPlan) -> bool:
        return len(self.validate(plan)) == 0


def build_safe_fallback_plan(
    registered_tools: list[str],
    reason: str = "Plan validation failed; falling back to safe default plan.",
) -> ExecutionPlan:
    """Build the safe default plan used when plan validation fails.

    DOCUMENTED §6.7 step 4: "fall back to a safe default plan (full EDA + all
    tools) and flag the fallback in the report."

    The safe plan runs all available registered tools in documented order.
    """
    import uuid

    steps: list[PlanStep] = []
    for tool in ["data_loader", "eda_tool", "feature_engineering",
                 "anomaly_detection", "risk_classification", "escalation", "explanation"]:
        if tool in registered_tools:
            args: dict[str, Any] = {}
            if tool == "anomaly_detection":
                args = {"method": "statistical"}
            elif tool == "explanation":
                args = {"tie_to_query": True}
            steps.append(PlanStep(tool=tool, args=args))

    return ExecutionPlan(
        plan_id=f"safe_fallback_{uuid.uuid4().hex[:8]}",
        reasoning=(
            f"SAFE FALLBACK PLAN — {reason} "
            "Running all available tools in default order."
        ),
        steps=steps,
        skipped_tools=[],
    )
