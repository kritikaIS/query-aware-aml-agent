"""Tool Registry — maps tool names to callables.

Reference: Solution Design §3.1, Implementation Plan §3 Phase 0.
The registry enforces the contract that every tool is a pure function
taking (context, **args) and returning structured output.
"""

from __future__ import annotations

from typing import Any, Callable

# Type alias for a tool function: takes context dict + keyword args, returns dict.
ToolFunction = Callable[..., dict[str, Any]]


class ToolRegistry:
    """Registry mapping tool names to their callable implementations.

    Enforces:
    - Each tool lives in its own module with a single registration call.
    - Tools can be registered/deregistered without touching the controller.
    - The planner can only reference tools that exist in this registry.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolFunction] = {}

    def register(self, name: str, fn: ToolFunction) -> None:
        """Register a tool function under the given name.

        Args:
            name: Unique tool name (must match the names used in ExecutionPlan.steps).
            fn: Callable that implements the tool logic.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if name in self._tools:
            raise ValueError(
                f"Tool '{name}' is already registered. "
                "Each tool name must be unique."
            )
        self._tools[name] = fn

    def get(self, name: str) -> ToolFunction:
        """Retrieve a registered tool by name.

        Args:
            name: The tool name.

        Returns:
            The tool callable.

        Raises:
            KeyError: If the tool is not registered.
        """
        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' is not registered. "
                f"Available tools: {list(self._tools.keys())}"
            )
        return self._tools[name]

    def list_tools(self) -> list[str]:
        """Return list of all registered tool names.

        Used by the planner to constrain tool selection.
        """
        return list(self._tools.keys())

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def __len__(self) -> int:
        return len(self._tools)
