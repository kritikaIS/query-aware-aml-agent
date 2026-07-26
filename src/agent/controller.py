"""AgentController — core orchestration loop.

Reference: Solution Design §4.3, §6.7, Listing 3.

DOCUMENTED REQUIREMENTS implemented here:
  - tool_registry: name → callable (§4.3, §3.1 principle 2)
  - run(user_query, df_transactions, df_customers) (§4.3 Listing 3)
  - Step 1: extract QuerySpec from user query (§4.1, §4.3)
  - Step 2: build ExecutionPlan constrained to registered tools (§4.2, §4.3)
  - context = {transactions, customers, query_spec} (§4.3 Listing 3)
  - for step in plan.steps: tool_fn(context, **args) (§4.3 Listing 3)
  - context.update(results) — pass forward between tools (§4.3 Listing 3)
  - Short-circuit / plan validation on schema errors (§4.3, §6.7 step 4)
  - Reject plans with unregistered tools (§6.7 step 4, §11 Risks)
  - Fall back to safe default plan on rejection (§6.7 step 4)
  - LLM never touches raw transaction data (§3.1 principle 1)
  - Return ExecutionReport (§8, §4.3)

IMPLEMENTATION ASSUMPTIONS:
  - If no LLM client is provided, the DeterministicPlanner is used.
    This is not documented; it exists to allow testing without an API key.
  - The planner interface is identical for both LLM and deterministic paths,
    so the controller does not need to know which is active.
  - The LLM client interface requires: client.extract_query_spec(query) and
    client.build_execution_plan(spec, tool_names). Not formally specified
    beyond the pseudocode in §4.3 Listing 3.
  - Escalation runs after Risk Classification in the tool loop; its position
    in the pipeline follows §4.4 and the pipeline diagram in §3.
  - _assemble_report reads from tool results without recomputing anything.
"""

from __future__ import annotations

from typing import Any

from src.schemas.query_spec import QuerySpec
from src.schemas.execution_plan import ExecutionPlan
from src.schemas.execution_report import (
    ExecutionReport,
    FlaggedEntity,
    ContributingFeature,
    SummaryMetrics,
)
from src.tools.registry import ToolRegistry
from src.agent.planner import DeterministicPlanner, PlanValidator, build_safe_fallback_plan


class AgentController:
    """Orchestrates the query → plan → execute → report pipeline.

    Implements Solution Design §4.3 Listing 3 exactly:

      context = {transactions, customers, query_spec}
      for step in plan.steps:
          results[step.tool] = tool_fn(context, **step.args)
          context.update(results)

    The planning step is behind a swappable interface:
    - DeterministicPlanner (when llm_client is None, implementation assumption)
    - LLM client (when provided, documented requirement §4.3)
    """

    def __init__(self, tool_registry: ToolRegistry, llm_client: Any = None) -> None:
        """Initialize the controller.

        Args:
            tool_registry: Registry mapping tool names → callables.
            llm_client: LLM client implementing extract_query_spec() and
                        build_execution_plan(). If None, the DeterministicPlanner
                        is used (IMPLEMENTATION ASSUMPTION).
        """
        self.tools = tool_registry
        self.llm = llm_client
        self._validator = PlanValidator(self.tools.list_tools())

        # IMPLEMENTATION ASSUMPTION: deterministic planner when no LLM configured.
        if self.llm is None:
            self._planner: Any = DeterministicPlanner(self.tools.list_tools())
        else:
            self._planner = None  # LLM client used directly via self.llm

    def run(
        self,
        user_query: str,
        df_transactions: Any = None,
        df_customers: Any = None,
    ) -> ExecutionReport:
        """Execute the full agent pipeline.

        DOCUMENTED §4.3 Listing 3:
          spec  = extract_query_spec(user_query)
          plan  = build_execution_plan(spec, list(tools))
          context = {transactions, customers, query_spec}
          for step: tool_fn(context, **args); context.update(results)
          return report

        Args:
            user_query: Natural language query from the user.
            df_transactions: Transactions DataFrame (loaded by data_loader
                             when None; passed through to tools when provided).
            df_customers: Customers DataFrame.

        Returns:
            ExecutionReport with full results.

        Raises:
            ValueError: If the user_query is empty.
        """
        if not user_query or not user_query.strip():
            raise ValueError("user_query must not be empty.")

        # ---------- Step 1: Intent & Entity Extraction → QuerySpec ----------
        # DOCUMENTED §4.3: "spec = self.llm.extract_query_spec(user_query)"
        spec = self._extract_query_spec(user_query)

        # ---------- Step 2: Dynamic Execution Planning → ExecutionPlan ----------
        # DOCUMENTED §4.3: "plan = self.llm.build_execution_plan(spec, list(tools))"
        plan = self._build_execution_plan(spec)

        # ---------- Step 3: Tool Execution Loop ----------
        # DOCUMENTED §4.3 Listing 3 exactly:
        #   context = {"transactions": df_transactions, "customers": df_customers, "query_spec": spec}
        context: dict[str, Any] = {
            "transactions": df_transactions,
            "customers": df_customers,
            "query_spec": spec.model_dump(),
        }

        results: dict[str, Any] = {}
        for step in plan.steps:
            tool_fn = self.tools.get(step.tool)
            step_result = tool_fn(context, **step.args)
            results[step.tool] = step_result
            context.update(results)   # DOCUMENTED: "pass forward for later tools"

        # ---------- Step 4: Assemble ExecutionReport ----------
        return self._assemble_report(user_query, spec, plan, results)

    # ------------------------------------------------------------------
    # Planning interfaces (swappable: LLM or deterministic)
    # ------------------------------------------------------------------

    def _extract_query_spec(self, user_query: str) -> QuerySpec:
        """Extract structured QuerySpec from the user query.

        DOCUMENTED §4.3: calls LLM for real extraction.
        IMPLEMENTATION ASSUMPTION: uses DeterministicPlanner when no LLM.
        """
        if self.llm is not None:
            # DOCUMENTED §4.3: real LLM call
            # LLM receives only the user query string, never raw data (§3.1 p.1)
            spec_dict = self.llm.extract_query_spec(user_query)
            if isinstance(spec_dict, dict):
                return QuerySpec(**spec_dict)
            return spec_dict  # assume already a QuerySpec

        # IMPLEMENTATION ASSUMPTION: deterministic planner
        return self._planner.extract_query_spec(user_query)

    def _build_execution_plan(self, spec: QuerySpec) -> ExecutionPlan:
        """Build ExecutionPlan from QuerySpec.

        DOCUMENTED §4.3: "plan = self.llm.build_execution_plan(spec, list(tools))"
        DOCUMENTED §6.7 step 4, §11: validate plan; reject/fallback on error.
        IMPLEMENTATION ASSUMPTION: uses DeterministicPlanner when no LLM.
        """
        if self.llm is not None:
            # DOCUMENTED §4.3: real LLM call constrained to registered tool list
            plan_dict = self.llm.build_execution_plan(spec, self.tools.list_tools())
            if isinstance(plan_dict, dict):
                plan = ExecutionPlan(**plan_dict)
            else:
                plan = plan_dict
        else:
            # IMPLEMENTATION ASSUMPTION: deterministic planner
            plan = self._planner.build_execution_plan(spec)

        # DOCUMENTED §6.7 step 4, §11: validate and reject/fallback
        errors = self._validator.validate(plan)
        if errors:
            # DOCUMENTED §6.7 step 4: "fall back to a safe default plan"
            plan = build_safe_fallback_plan(
                registered_tools=self.tools.list_tools(),
                reason=f"Plan validation errors: {'; '.join(errors)}",
            )

        return plan

    # ------------------------------------------------------------------
    # Report assembly
    # ------------------------------------------------------------------

    def _assemble_report(
        self,
        user_query: str,
        spec: QuerySpec,
        plan: ExecutionPlan,
        results: dict[str, Any],
    ) -> ExecutionReport:
        """Assemble the final ExecutionReport from accumulated tool results.

        DOCUMENTED §8: schema for ExecutionReport (Listing 5).
        Reads from results without recomputing anything.
        """
        # ---- Gather per-entity data from tool results ----
        risk_results = results.get("risk_classification", {})
        explanation_results = results.get("explanation", {})
        escalation_results = results.get("escalation", {})
        anomaly_results = results.get("anomaly_detection", {})

        classifications = risk_results.get("classifications", [])

        # Build lookup maps
        explanations_by_id: dict[str, str] = {
            e["customer_id"]: e.get("explanation", "")
            for e in explanation_results.get("explanations", [])
        }

        escalation_by_id: dict[str, str] = {
            e["customer_id"]: e.get("recommended_action", "")
            for e in escalation_results.get("escalations", [])
        }

        anomaly_by_id: dict[str, dict] = {
            e["customer_id"]: e
            for e in anomaly_results.get("all_entities", [])
        }
        # Also check flagged_entities if all_entities not present
        if not anomaly_by_id:
            anomaly_by_id = {
                e["customer_id"]: e
                for e in anomaly_results.get("flagged_entities", [])
            }

        # ---- Build flagged_entities list (DOCUMENTED §8 schema) ----
        flagged_entities: list[FlaggedEntity] = []
        for classification in classifications:
            cid = classification["customer_id"]
            anomaly_data = anomaly_by_id.get(cid, {})

            contributing = [
                ContributingFeature(
                    feature=f.get("feature", ""),
                    value=float(f.get("value", 0)),
                    z_score=float(f.get("z_score", 0.0)),
                )
                for f in anomaly_data.get("top_contributing_features", [])
            ]

            # recommended_action from escalation, then fallback to risk-band lookup
            recommended_action = escalation_by_id.get(
                cid, self._get_escalation_action(classification["risk_band"])
            )

            flagged_entities.append(
                FlaggedEntity(
                    customer_id=cid,
                    risk_score=classification["risk_score"],
                    risk_band=classification["risk_band"],
                    aml_pattern_matched=spec.aml_pattern,
                    top_contributing_features=contributing,
                    explanation=explanations_by_id.get(cid, ""),
                    recommended_action=recommended_action,
                )
            )

        # ---- Summary metrics (DOCUMENTED §8 schema) ----
        data_loader_result = results.get("data_loader", {})
        total_scanned = data_loader_result.get("rows_after_filter", 0)
        if not total_scanned:
            total_scanned = data_loader_result.get("rows_loaded", 0)

        summary = SummaryMetrics(
            total_transactions_scanned=total_scanned,
            entities_flagged=len(flagged_entities),
            high_risk=sum(1 for e in flagged_entities if e.risk_band == "High"),
            medium_risk=sum(1 for e in flagged_entities if e.risk_band == "Medium"),
            low_risk=sum(1 for e in flagged_entities if e.risk_band == "Low"),
        )

        return ExecutionReport(
            user_query=user_query,
            query_spec=spec,
            execution_plan=plan,
            flagged_entities=flagged_entities,
            summary_metrics=summary,
            charts=[],
        )

    def _get_escalation_action(self, risk_band: str) -> str:
        """Fallback risk-band → action lookup used if escalation tool was not run.

        Reference: Solution Design §5.7.
        """
        return {
            "High": "Report (SAR draft)",
            "Medium": "Flag for review",
            "Low": "Monitor",
        }.get(risk_band, "Monitor")
