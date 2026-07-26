"""ExecutionPlan schema — produced by the Dynamic Execution Planner.

Reference: Solution Design §4.2, Listing 2.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """A single step in the execution plan."""

    tool: str = Field(
        description="Name of the registered tool to invoke.",
    )
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool.",
    )


class SkippedTool(BaseModel):
    """A tool that was explicitly skipped by the planner, with a reason."""

    tool: str = Field(
        description="Name of the skipped tool.",
    )
    reason: str = Field(
        description="Natural language explanation of why this tool was skipped.",
    )


class ExecutionPlan(BaseModel):
    """Ordered execution plan produced by the LLM planner.

    Contains the sequence of tool invocations, reasoning for the plan,
    and an explicit list of skipped tools with justifications.
    """

    plan_id: str = Field(
        description="Unique identifier for this plan.",
    )
    reasoning: str = Field(
        description="Natural language explanation of why this plan was chosen.",
    )
    steps: list[PlanStep] = Field(
        description="Ordered list of tool invocations to execute.",
    )
    skipped_tools: list[SkippedTool] = Field(
        default_factory=list,
        description="Tools that were intentionally not included, with reasons.",
    )
