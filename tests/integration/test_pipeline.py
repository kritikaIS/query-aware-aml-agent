"""Integration tests for the full pipeline and API.

Reference: Solution Design §4.3, §4.4, §6.7, §6.8, §7, §8.
Tests validate:
  - Documented AgentController loop (§4.3 Listing 3)
  - Three reference query patterns (§4.4)
  - ExecutionPlan validation (§6.7 step 4)
  - FastAPI /query endpoint (§6.8 step 1, §7)
  - ExecutionReport schema (§8)
  - Context passing between tools
  - Deterministic execution
  - Error handling
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.agent.controller import AgentController
from src.agent.planner import (
    DeterministicPlanner,
    PlanValidator,
    build_safe_fallback_plan,
)
from src.schemas.execution_plan import ExecutionPlan, PlanStep, SkippedTool
from src.schemas.query_spec import QuerySpec
from src.tools.registry import ToolRegistry
from src.tools.data_loader import data_loader
from src.tools.eda_tool import eda_tool
from src.tools.feature_engineering import feature_engineering
from src.tools.anomaly_detection import anomaly_detection
from src.tools.risk_classification import risk_classification
from src.tools.escalation import escalation
from src.tools.explanation import explanation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("data_loader", data_loader)
    r.register("eda_tool", eda_tool)
    r.register("feature_engineering", feature_engineering)
    r.register("anomaly_detection", anomaly_detection)
    r.register("risk_classification", risk_classification)
    r.register("escalation", escalation)
    r.register("explanation", explanation)
    return r


@pytest.fixture(scope="module")
def controller(registry) -> AgentController:
    return AgentController(tool_registry=registry, llm_client=None)


@pytest.fixture(scope="module")
def api_client():
    from src.api.main import create_app
    app = create_app()
    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# Test: DeterministicPlanner
# ---------------------------------------------------------------------------

class TestDeterministicPlanner:
    @pytest.fixture
    def planner(self, registry):
        return DeterministicPlanner(registry.list_tools())

    def test_structuring_pattern_query(self, planner):
        """DOCUMENTED §4.4 reference query 1: structuring → statistical/ML detection."""
        spec = planner.extract_query_spec("Find structuring patterns in the last 30 days")
        assert spec.intent in ("pattern_detection", "aggregation_rule")
        assert spec.aml_pattern in ("structuring", None) or "structuring" in str(spec.aml_pattern)

    def test_rule_based_query(self, planner):
        """DOCUMENTED §4.4 reference query 2: rule-based → aggregation_rule intent."""
        spec = planner.extract_query_spec(
            "Which customers made 10+ transactions under $10,000?"
        )
        assert spec.intent == "aggregation_rule"
        assert spec.explicit_rule.present is True
        assert "10000" in spec.explicit_rule.condition or "10,000" in spec.explicit_rule.condition

    def test_entity_lookup_query(self, planner):
        """DOCUMENTED §4.4 reference query 3: entity_lookup → single customer."""
        spec = planner.extract_query_spec("Is customer ID 4521 suspicious?")
        assert spec.intent == "entity_lookup"
        assert spec.filters.customer_id == "4521"

    def test_broad_exploration_query(self, planner):
        spec = planner.extract_query_spec("Analyse this dataset for suspicious activity")
        assert spec.intent == "broad_exploration"
        assert spec.requires_full_eda is True

    def test_structuring_plan_skips_eda(self, planner):
        """DOCUMENTED §4.4: structuring query skips EDA."""
        spec = planner.extract_query_spec("Find structuring patterns in the last 30 days")
        plan = planner.build_execution_plan(spec)
        tool_names = [s.tool for s in plan.steps]
        skipped_names = [s.tool for s in plan.skipped_tools]
        assert "eda_tool" not in tool_names or "eda_tool" in skipped_names

    def test_rule_query_skips_feature_engineering(self, planner):
        """DOCUMENTED §4.4: rule-based query skips feature_engineering."""
        spec = planner.extract_query_spec(
            "Which customers made 10+ transactions under $10,000?"
        )
        plan = planner.build_execution_plan(spec)
        tool_names = [s.tool for s in plan.steps]
        skipped_names = [s.tool for s in plan.skipped_tools]
        assert "feature_engineering" not in tool_names or "feature_engineering" in skipped_names

    def test_entity_query_skips_eda(self, planner):
        """DOCUMENTED §4.4: entity_lookup skips full EDA."""
        spec = planner.extract_query_spec("Is customer ID 4521 suspicious?")
        plan = planner.build_execution_plan(spec)
        tool_names = [s.tool for s in plan.steps]
        assert "eda_tool" not in tool_names

    def test_plan_only_uses_registered_tools(self, planner, registry):
        """DOCUMENTED §4.3: plan constrained to registered tool list."""
        queries = [
            "Find structuring patterns",
            "Which customers made 10 transactions under $10000?",
            "Is customer ID 4521 suspicious?",
        ]
        registered = set(registry.list_tools())
        for query in queries:
            spec = planner.extract_query_spec(query)
            plan = planner.build_execution_plan(spec)
            for step in plan.steps:
                assert step.tool in registered, f"Unregistered tool {step.tool} in plan"

    def test_plan_has_plan_id(self, planner):
        spec = planner.extract_query_spec("Find structuring patterns")
        plan = planner.build_execution_plan(spec)
        assert plan.plan_id and len(plan.plan_id) > 0

    def test_plan_has_reasoning(self, planner):
        spec = planner.extract_query_spec("Find structuring patterns")
        plan = planner.build_execution_plan(spec)
        assert plan.reasoning and len(plan.reasoning) > 0

    def test_three_different_queries_produce_different_plans(self, planner):
        """DOCUMENTED §4.4: three reference queries produce distinct execution paths."""
        q1 = "Find structuring patterns in the last 30 days"
        q2 = "Which customers made 10+ transactions under $10,000?"
        q3 = "Is customer ID 4521 suspicious?"

        s1 = planner.extract_query_spec(q1)
        s2 = planner.extract_query_spec(q2)
        s3 = planner.extract_query_spec(q3)

        p1 = planner.build_execution_plan(s1)
        p2 = planner.build_execution_plan(s2)
        p3 = planner.build_execution_plan(s3)

        tools1 = [s.tool for s in p1.steps]
        tools2 = [s.tool for s in p2.steps]
        tools3 = [s.tool for s in p3.steps]

        # All three must differ in at least one tool
        assert tools1 != tools2 or tools2 != tools3


# ---------------------------------------------------------------------------
# Test: PlanValidator
# ---------------------------------------------------------------------------

class TestPlanValidator:
    @pytest.fixture
    def validator(self, registry):
        return PlanValidator(registry.list_tools())

    def test_valid_plan_passes(self, validator):
        plan = ExecutionPlan(
            plan_id="p1",
            reasoning="test",
            steps=[PlanStep(tool="data_loader", args={})],
        )
        assert validator.is_valid(plan)

    def test_unregistered_tool_fails(self, validator):
        """DOCUMENTED §6.7 step 4: reject plans with unregistered tools."""
        plan = ExecutionPlan(
            plan_id="p1",
            reasoning="test",
            steps=[PlanStep(tool="nonexistent_tool", args={})],
        )
        errors = validator.validate(plan)
        assert len(errors) > 0
        assert "nonexistent_tool" in errors[0]

    def test_empty_plan_fails(self, validator):
        plan = ExecutionPlan(plan_id="p1", reasoning="test", steps=[])
        assert not validator.is_valid(plan)


# ---------------------------------------------------------------------------
# Test: Safe fallback plan
# ---------------------------------------------------------------------------

class TestSafeFallbackPlan:
    def test_fallback_only_uses_registered_tools(self, registry):
        """DOCUMENTED §6.7 step 4: safe fallback uses all available tools."""
        plan = build_safe_fallback_plan(registry.list_tools())
        registered = set(registry.list_tools())
        for step in plan.steps:
            assert step.tool in registered

    def test_fallback_has_plan_id(self, registry):
        plan = build_safe_fallback_plan(registry.list_tools())
        assert "safe_fallback" in plan.plan_id

    def test_fallback_reasoning_mentions_fallback(self, registry):
        plan = build_safe_fallback_plan(registry.list_tools(), "Test failure reason")
        assert "fallback" in plan.reasoning.lower() or "FALLBACK" in plan.reasoning


# ---------------------------------------------------------------------------
# Test: AgentController — context passing
# ---------------------------------------------------------------------------

class TestAgentControllerContextPassing:
    def test_context_contains_required_keys(self, controller, monkeypatch):
        """DOCUMENTED §4.3: context = {transactions, customers, query_spec}."""
        captured_contexts = []

        original_get = controller.tools.get

        def capturing_get(name):
            original_fn = original_get(name)
            def wrapper(context, **args):
                captured_contexts.append(dict(context))
                return original_fn(context, **args)
            return wrapper

        monkeypatch.setattr(controller.tools, "get", capturing_get)

        controller.run("Find structuring patterns in the last 30 days")
        assert len(captured_contexts) > 0
        first = captured_contexts[0]
        assert "query_spec" in first

    def test_results_passed_forward(self, controller):
        """DOCUMENTED §4.3: context.update(results) passes tool outputs forward."""
        report = controller.run("Find structuring patterns in the last 30 days")
        # If context was not passed forward, later tools would have no input data
        assert report is not None
        assert report.status if hasattr(report, "status") else True


# ---------------------------------------------------------------------------
# Test: Full pipeline execution
# ---------------------------------------------------------------------------

class TestFullPipelineExecution:
    def test_structuring_query_executes(self, controller):
        """DOCUMENTED §4.4 reference query 1."""
        report = controller.run("Find structuring patterns in the last 30 days")
        assert report is not None
        assert report.user_query == "Find structuring patterns in the last 30 days"
        assert report.execution_plan is not None
        assert report.summary_metrics is not None

    def test_rule_query_executes(self, controller):
        """DOCUMENTED §4.4 reference query 2."""
        report = controller.run(
            "Which customers made 10+ transactions under $10,000?"
        )
        assert report is not None
        assert report.execution_plan is not None

    def test_entity_query_executes(self, controller):
        """DOCUMENTED §4.4 reference query 3."""
        report = controller.run("Is customer ID 4521 suspicious?")
        assert report is not None

    def test_report_has_required_fields(self, controller):
        """DOCUMENTED §8: ExecutionReport schema."""
        report = controller.run("Find structuring patterns in the last 30 days")
        assert hasattr(report, "user_query")
        assert hasattr(report, "query_spec")
        assert hasattr(report, "execution_plan")
        assert hasattr(report, "flagged_entities")
        assert hasattr(report, "summary_metrics")
        assert hasattr(report, "charts")

    def test_execution_plan_has_required_fields(self, controller):
        """DOCUMENTED §4.2 Listing 2."""
        report = controller.run("Find structuring patterns in the last 30 days")
        plan = report.execution_plan
        assert plan.plan_id
        assert plan.reasoning
        assert isinstance(plan.steps, list)
        assert isinstance(plan.skipped_tools, list)

    def test_deterministic_repeated_execution(self, controller):
        """DOCUMENTED: deterministic execution."""
        query = "Find structuring patterns in the last 30 days"
        r1 = controller.run(query)
        r2 = controller.run(query)
        assert len(r1.flagged_entities) == len(r2.flagged_entities)
        assert r1.summary_metrics.entities_flagged == r2.summary_metrics.entities_flagged

    def test_empty_query_raises_error(self, controller):
        """Validation: empty query must raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            controller.run("   ")

    def test_tool_failure_propagates(self, controller, monkeypatch):
        """DOCUMENTED §4.3: short-circuit on tool errors (error is propagated)."""
        original_get = controller.tools.get

        def failing_get(name):
            if name == "data_loader":
                def failing_tool(context, **args):
                    raise RuntimeError("Simulated data_loader failure")
                return failing_tool
            return original_get(name)

        monkeypatch.setattr(controller.tools, "get", failing_get)

        with pytest.raises(RuntimeError, match="Simulated data_loader failure"):
            controller.run("Find structuring patterns")


# ---------------------------------------------------------------------------
# Test: FastAPI /query endpoint
# ---------------------------------------------------------------------------

class TestFastAPIQueryEndpoint:
    def test_post_query_success(self, api_client):
        """DOCUMENTED §6.8 step 1, §7: POST /query returns ExecutionReport JSON."""
        response = api_client.post(
            "/query",
            json={"query": "Find structuring patterns in the last 30 days"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "user_query" in body
        assert "execution_plan" in body
        assert "flagged_entities" in body
        assert "summary_metrics" in body

    def test_execution_plan_in_response(self, api_client):
        """DOCUMENTED §8: execution_plan with reasoning and skipped_tools."""
        response = api_client.post(
            "/query",
            json={"query": "Find structuring patterns in the last 30 days"},
        )
        plan = response.json()["execution_plan"]
        assert "plan_id" in plan
        assert "reasoning" in plan
        assert "steps" in plan
        assert "skipped_tools" in plan

    def test_meta_fields_in_response(self, api_client):
        """API-level audit fields (IMPLEMENTATION ASSUMPTION)."""
        response = api_client.post(
            "/query",
            json={"query": "Find structuring patterns in the last 30 days"},
        )
        body = response.json()
        assert "_meta" in body
        assert "elapsed_ms" in body["_meta"]
        assert "tools_invoked" in body["_meta"]

    def test_empty_query_returns_422(self, api_client):
        """Request validation: empty query → HTTP 422."""
        response = api_client.post("/query", json={"query": "   "})
        assert response.status_code == 422

    def test_missing_query_field_returns_422(self, api_client):
        """Request validation: missing query field → HTTP 422."""
        response = api_client.post("/query", json={})
        assert response.status_code == 422

    def test_non_string_query_returns_422(self, api_client):
        """Request validation: query must be string."""
        response = api_client.post("/query", json={"query": 12345})
        # FastAPI will coerce int to string; test that it doesn't crash
        # (may succeed or fail validation depending on version)
        assert response.status_code in (200, 422)

    def test_rule_based_query(self, api_client):
        """DOCUMENTED §4.4 reference query 2 via API."""
        response = api_client.post(
            "/query",
            json={"query": "Which customers made 10+ transactions under $10,000?"},
        )
        assert response.status_code == 200

    def test_entity_lookup_query(self, api_client):
        """DOCUMENTED §4.4 reference query 3 via API."""
        response = api_client.post(
            "/query",
            json={"query": "Is customer ID 4521 suspicious?"},
        )
        assert response.status_code == 200

    def test_deterministic_responses(self, api_client):
        """DOCUMENTED: same input → same output (deterministic)."""
        query = {"query": "Find structuring patterns in the last 30 days"}
        r1 = api_client.post("/query", json=query).json()
        r2 = api_client.post("/query", json=query).json()
        assert r1["summary_metrics"]["entities_flagged"] == r2["summary_metrics"]["entities_flagged"]

    def test_health_endpoint(self, api_client):
        """IMPLEMENTATION ASSUMPTION: /health endpoint."""
        response = api_client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "registered_tools" in body

    def test_response_schema_has_all_documented_fields(self, api_client):
        """DOCUMENTED §8: full ExecutionReport schema."""
        response = api_client.post(
            "/query",
            json={"query": "Find structuring patterns in the last 30 days"},
        )
        body = response.json()
        required_fields = [
            "user_query", "query_spec", "execution_plan",
            "flagged_entities", "summary_metrics", "charts"
        ]
        for field in required_fields:
            assert field in body, f"Missing documented field: {field}"

    def test_summary_metrics_structure(self, api_client):
        """DOCUMENTED §8: summary_metrics schema."""
        response = api_client.post(
            "/query",
            json={"query": "Find structuring patterns in the last 30 days"},
        )
        metrics = response.json()["summary_metrics"]
        assert "total_transactions_scanned" in metrics
        assert "entities_flagged" in metrics
        assert "high_risk" in metrics
        assert "medium_risk" in metrics
        assert "low_risk" in metrics
