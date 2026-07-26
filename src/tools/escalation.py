"""Escalation Policy Layer.

Reference: Solution Design §5.7, Implementation Plan §6.6.

Purpose: Deterministic mapping from risk band → recommended action.
This step is never left to LLM judgment.

DOCUMENTED behaviour (Solution Design §5.7):
  Low    → Monitor          (no further action; keep in rolling watch list)
  Medium → Flag for review  (analyst review within SLA, e.g. 3 business days)
  High   → Report (SAR draft) (auto-draft SAR for compliance sign-off)

DOCUMENTED implementation requirements (Implementation Plan §6.6):
  1. Implement as a pure lookup table — no LLM involvement at all.
  2. Attach the human-readable rationale string alongside the action.
  3. Table-driven: adding a new band/action requires a one-line config change.

IMPLEMENTATION ASSUMPTIONS:
  - Tool name: "escalation" registered in the ToolRegistry (consistent with
    all other tools; not explicitly named in the documentation).
  - Output field names: recommended_action, rationale, risk_band (not
    explicitly specified in docs; semantics are documented).
  - Input: reads from context["risk_classification"]["classifications"],
    which is the output of the Risk Classification Tool. The documentation
    places Escalation immediately after Risk Classification in the pipeline.
  - Unknown risk bands: return an error rather than silently ignoring them,
    to prevent undetected misconfiguration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "escalation_config.yaml"
)


def _load_escalation_config() -> dict:
    """Load the escalation policy from escalation_config.yaml.

    DOCUMENTED: "Table-driven; adding a new band/action requires a one-line
    config change" — Implementation Plan §6.6 DoD.
    """
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Core lookup function
# ---------------------------------------------------------------------------

def _escalate_band(
    risk_band: str,
    policy: dict[str, dict[str, str]],
) -> tuple[str, str]:
    """Look up the escalation action and rationale for a given risk band.

    DOCUMENTED: pure lookup table mapping risk band → recommended action
    (§5.7, §6.6 step 1).

    Args:
        risk_band: One of the documented bands: Low, Medium, High.
        policy: The loaded policy dict mapping band → {action, rationale}.

    Returns:
        Tuple of (recommended_action, rationale).

    Raises:
        ValueError: If risk_band is not present in the policy table.
            This surfaces misconfiguration rather than silently falling through.
    """
    if risk_band not in policy:
        known = list(policy.keys())
        raise ValueError(
            f"Escalation: unknown risk band '{risk_band}'. "
            f"Configured bands: {known}. "
            f"Add an entry to escalation_config.yaml to support this band."
        )
    entry = policy[risk_band]
    return str(entry["recommended_action"]), str(entry["rationale"])


# ---------------------------------------------------------------------------
# Main tool function (registered in ToolRegistry)
# ---------------------------------------------------------------------------

def escalation(context: dict[str, Any], **args: Any) -> dict[str, Any]:
    """Apply the escalation policy to Risk Classification outputs.

    Reference: Solution Design §5.7, Implementation Plan §6.6.
    This is the tool function registered in the ToolRegistry.

    Reads the risk classification result from context and applies a
    deterministic lookup to produce the recommended action per entity.
    No LLM involvement. Pure function.

    Args:
        context: Shared execution context. Expected keys:
            - "risk_classification": result dict from Risk Classification
              containing "classifications" list.
        **args: Arguments from the ExecutionPlan step (currently unused;
                present for AgentController contract compatibility).

    Returns:
        Dict with:
            - tool: "escalation"
            - status: "success" | "error"
            - escalations: list of per-entity dicts containing:
                - customer_id
                - risk_band        (passed through from Risk Classification)
                - risk_score       (passed through for auditability)
                - recommended_action (DOCUMENTED: §5.7 action column)
                - rationale          (DOCUMENTED: §5.7 rationale column)
            - summary: count of entities per recommended action
    """
    # --- Load policy (documented: table-driven, config-only) ---
    config = _load_escalation_config()
    policy = config.get("policy", {})

    # --- Resolve Risk Classification output from context ---
    rc_result = context.get("risk_classification", {})
    if not isinstance(rc_result, dict):
        return {
            "tool": "escalation",
            "status": "error",
            "error": "No risk_classification result found in context.",
        }

    classifications = rc_result.get("classifications", [])
    if not classifications:
        return {
            "tool": "escalation",
            "status": "error",
            "error": (
                "risk_classification.classifications is empty. "
                "Run Risk Classification before Escalation."
            ),
        }

    # --- Apply deterministic lookup per entity (DOCUMENTED: §5.7, §6.6) ---
    escalations = []
    for classification in classifications:
        customer_id = str(classification.get("customer_id", "unknown"))
        risk_band = str(classification.get("risk_band", ""))
        risk_score = classification.get("risk_score", 0.0)

        try:
            recommended_action, rationale = _escalate_band(risk_band, policy)
        except ValueError as e:
            return {
                "tool": "escalation",
                "status": "error",
                "error": str(e),
            }

        escalations.append({
            "customer_id": customer_id,
            "risk_band": risk_band,
            "risk_score": risk_score,
            "recommended_action": recommended_action,
            "rationale": rationale,
        })

    # --- Summary counts per recommended action ---
    summary: dict[str, int] = {}
    for e in escalations:
        action = e["recommended_action"]
        summary[action] = summary.get(action, 0) + 1

    return {
        "tool": "escalation",
        "status": "success",
        "escalations": escalations,
        "summary": summary,
    }
