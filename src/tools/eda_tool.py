"""EDA Tool — STUB implementation for Phase 0.

Reference: Solution Design §5.2.
Broad exploratory profiling invoked only when intent = broad_exploration.
Returns hard-coded valid JSON matching the expected output contract.
Real implementation in Phase 1.
"""

from __future__ import annotations

from typing import Any


def eda_tool(context: dict[str, Any], **args: Any) -> dict[str, Any]:
    """Perform exploratory data analysis on the loaded dataset.

    In Phase 0, returns a hard-coded stub response.

    Args:
        context: Shared execution context.
        **args: Arguments from the execution plan.

    Returns:
        Dict with summary statistics and profiling results.
    """
    return {
        "tool": "eda_tool",
        "status": "success",
        "summary_stats": {
            "total_transactions": 1000,
            "unique_customers": 85,
            "date_range": {"start": "2026-06-01", "end": "2026-07-01"},
            "amount_stats": {
                "mean": 5420.50,
                "median": 3200.00,
                "std": 4100.75,
                "min": 10.00,
                "max": 49500.00,
            },
        },
        "outlier_flags": {
            "z_score_outliers": 12,
            "iqr_outliers": 8,
        },
    }
