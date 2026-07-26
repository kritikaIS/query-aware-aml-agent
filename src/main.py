"""Main entry point — walking skeleton for Phase 0 checkpoint.

Reference: Implementation Plan §3 Phase 0 Checkpoint:
"A hard-coded query returns a hard-coded ExecutionReport end-to-end
through the real controller loop (no real tool logic yet, no real LLM calls yet)."
"""

from __future__ import annotations

import json

from src.tools.registry import ToolRegistry
from src.tools.data_loader import data_loader
from src.tools.eda_tool import eda_tool
from src.tools.feature_engineering import feature_engineering
from src.tools.anomaly_detection import anomaly_detection
from src.tools.risk_classification import risk_classification
from src.tools.explanation import explanation
from src.tools.escalation import escalation
from src.agent.controller import AgentController


def build_tool_registry() -> ToolRegistry:
    """Register all available tools.

    Each tool is registered under the name the planner uses to reference it.
    """
    registry = ToolRegistry()
    registry.register("data_loader", data_loader)
    registry.register("eda_tool", eda_tool)
    registry.register("feature_engineering", feature_engineering)
    registry.register("anomaly_detection", anomaly_detection)
    registry.register("risk_classification", risk_classification)
    registry.register("explanation", explanation)
    registry.register("escalation", escalation)
    return registry


def main() -> None:
    """Run the Phase 0 walking skeleton.

    Demonstrates the full round-trip:
    query → QuerySpec → ExecutionPlan → stub tool execution → ExecutionReport
    """
    # Build registry with all stub tools
    registry = build_tool_registry()

    # Create controller in stub mode (no LLM client)
    controller = AgentController(tool_registry=registry, llm_client=None)

    # Reference query from Solution Design §4.4
    query = "Find structuring patterns in the last 30 days"

    print("=" * 70)
    print("AML Suspicious Activity Detection Agent — Phase 0 Walking Skeleton")
    print("=" * 70)
    print(f"\nUser Query: {query}")
    print("-" * 70)

    # Execute the full pipeline
    report = controller.run(user_query=query)

    # Output the structured report as JSON
    report_json = report.model_dump(mode="json")
    print("\nExecutionReport (JSON):")
    print("-" * 70)
    print(json.dumps(report_json, indent=2))
    print("-" * 70)
    print(f"\nPlan reasoning: {report.execution_plan.reasoning}")
    print(f"Tools invoked: {[s.tool for s in report.execution_plan.steps]}")
    print(f"Tools skipped: {[s.tool for s in report.execution_plan.skipped_tools]}")
    print(f"Entities flagged: {report.summary_metrics.entities_flagged}")
    print(f"  High: {report.summary_metrics.high_risk}")
    print(f"  Medium: {report.summary_metrics.medium_risk}")
    print(f"  Low: {report.summary_metrics.low_risk}")
    print("\n✓ Phase 0 checkpoint passed: end-to-end round-trip complete.")


if __name__ == "__main__":
    main()
