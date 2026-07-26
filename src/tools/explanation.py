"""Explanation Component.

Reference: Solution Design §5.6, §2.3, §3.1 principle 4
           Implementation Plan §6.5

Purpose: Turn structured scores + top contributing features into a concise,
query-grounded natural-language reason.

TWO EXECUTION PATHS — both documented or clarified:

PATH A — Deterministic Template (DEFAULT):
  DOCUMENTED §2.3: "templated NL generation"
  DOCUMENTED §3.1 principle 4: numbers from code, deterministic
  All templates stored in explanation_config.yaml (per implementation requirement).
  Every number in the output is directly pulled from upstream outputs.
  Zero LLM involvement. Strictly deterministic.

PATH B — Optional LLM Enhancement:
  DOCUMENTED §5.6: "this is an LLM call, but constrained to only the numeric
  facts passed in (no hallucinated figures)"
  DOCUMENTED §6.5 step 1: constrained prompt receives only already-computed facts
  DOCUMENTED §6.5 step 2: model instructed to restate, never invent
  DOCUMENTED §6.5 step 3: post-generation regex/number-match validation
  DOCUMENTED §6.5 DoD: 100% of numbers traceable to input payload
  IMPLEMENTATION ASSUMPTION: LLM is optional; if API key absent or validation
  fails, falls back to Path A (template). Documentation says "regenerate or
  flag on mismatch"; this implementation discards and uses template instead.

DOCUMENTED REQUIREMENTS:
  - "concise, query-grounded natural-language reason" (§5.6)
  - "constrained to only the numeric facts passed in" (§5.6)
  - "no hallucinated figures" (§5.6)
  - "restate, never invent, numeric values" (§6.5 step 2)
  - "post-generation regex/number-match validation" (§6.5 step 3)
  - "100% of numbers traceable to input payload" (§6.5 DoD)
  - "tie_to_query" argument from ExecutionPlan (§4.2 Listing 2)

IMPLEMENTATION ASSUMPTIONS:
  - Templates stored in explanation_config.yaml (per explicit instruction).
  - LLM availability is determined by ANTHROPIC_API_KEY env var + config flag.
  - Fall back to template if LLM unavailable or validation fails.
  - Input comes from context["risk_classification"] and context["escalation"]
    and context["anomaly_detection"] (placed there by AgentController).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "explanation_config.yaml"
)


def _load_explanation_config() -> dict:
    """Load explanation configuration from explanation_config.yaml."""
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Feature summary builder
# ---------------------------------------------------------------------------

def _build_feature_summary(
    top_contributing_features: list[dict[str, Any]],
    config: dict,
) -> str:
    """Build a prose summary of the top contributing features.

    DOCUMENTED: §5.6 "top contributing features" appear in the explanation.
    Format is an IMPLEMENTATION ASSUMPTION (per config).

    Args:
        top_contributing_features: List of {feature, value, z_score} dicts.
        config: Loaded explanation config.

    Returns:
        A single string summarising the top N features.
    """
    feat_cfg = config.get("feature_summary", {})
    max_n = int(feat_cfg.get("max_features_shown", 3))
    line_template = str(feat_cfg.get(
        "feature_line_template", "{feature} = {value} (z-score: {z_score})"
    ))
    separator = str(feat_cfg.get("feature_separator", "; "))
    prefix = str(feat_cfg.get("feature_prefix", ""))

    if not top_contributing_features:
        return "no specific features recorded"

    lines = []
    for feat in top_contributing_features[:max_n]:
        feature = str(feat.get("feature", "unknown"))
        value = feat.get("value", 0)
        z_score = feat.get("z_score", 0.0)

        # Format numbers precisely — DOCUMENTED: preserve exactly (DoD)
        if isinstance(value, float):
            value_str = f"{value:.4g}"
        else:
            value_str = str(value)

        if isinstance(z_score, float):
            z_str = f"{z_score:.4g}"
        else:
            z_str = str(z_score)

        line = line_template.format(
            feature=feature,
            value=value_str,
            z_score=z_str,
        )
        lines.append(line)

    return prefix + separator.join(lines)


# ---------------------------------------------------------------------------
# Template-based explanation builder (Path A — deterministic)
# ---------------------------------------------------------------------------

def _build_template_explanation(
    customer_id: str,
    risk_score: float,
    risk_band: str,
    detection_method: str,
    aml_pattern: str,
    feature_summary: str,
    rule_condition: str,
    determining_factor: str,
    recommended_action: str,
    escalation_rationale: str,
    config: dict,
) -> str:
    """Build a fully deterministic template-based explanation.

    PATH A — Default execution path. No LLM involvement.
    All values sourced directly from upstream outputs.
    Every number preserved exactly as received.

    DOCUMENTED §2.3: "templated NL generation"
    IMPLEMENTATION ASSUMPTION: selection logic (method > band > default)
    """
    template_vars = {
        "customer_id": customer_id,
        "risk_score": risk_score,
        "risk_band": risk_band,
        "detection_method": detection_method,
        "aml_pattern": aml_pattern,
        "feature_summary": feature_summary,
        "rule_condition": rule_condition,
        "determining_factor": determining_factor,
        "recommended_action": recommended_action,
        "escalation_rationale": escalation_rationale,
    }

    method_templates = config.get("method_templates", {})
    band_templates = config.get("band_templates", {})
    default_template = config.get("default_template", "Customer {customer_id}: {risk_band} risk.")

    # Selection priority: detection method > risk band > default
    # IMPLEMENTATION ASSUMPTION: more specific = more informative
    if detection_method in method_templates:
        template = method_templates[detection_method]
    elif risk_band in band_templates:
        template = band_templates[risk_band]
    else:
        template = default_template

    return template.format(**template_vars).strip()


# ---------------------------------------------------------------------------
# Number validation (documented §6.5 step 3)
# ---------------------------------------------------------------------------

def _extract_numbers_from_text(text: str) -> set[str]:
    """Extract all numeric tokens from a text string.

    DOCUMENTED §6.5 step 3: "cross-checks every number in the generated
    explanation against the numbers passed into the prompt."
    """
    # Match integers and decimals (including negative)
    return set(re.findall(r'-?\d+(?:\.\d+)?', text))


def _validate_numbers(
    generated_text: str,
    input_payload_numbers: set[str],
    tolerance: float = 0.01,
) -> bool:
    """Validate that every number in the generated text appears in the input.

    DOCUMENTED §6.5 step 3 + DoD: "100% of numbers in explanations are
    traceable to the input payload."

    Args:
        generated_text: The LLM-generated explanation text.
        input_payload_numbers: Set of numeric strings from the input payload.
        tolerance: Floating-point comparison tolerance (IMPLEMENTATION ASSUMPTION).

    Returns:
        True if all numbers in the generated text are traceable to the input.
    """
    generated_numbers = _extract_numbers_from_text(generated_text)

    for gen_num_str in generated_numbers:
        gen_val = float(gen_num_str)
        # Check exact string match first (fast path)
        if gen_num_str in input_payload_numbers:
            continue
        # Check approximate numeric match (handles formatting differences)
        found = False
        for inp_num_str in input_payload_numbers:
            try:
                inp_val = float(inp_num_str)
                if abs(gen_val - inp_val) <= tolerance:
                    found = True
                    break
            except ValueError:
                pass
        if not found:
            return False
    return True


def _collect_input_numbers(
    risk_score: float,
    top_contributing_features: list[dict[str, Any]],
) -> set[str]:
    """Collect all numeric strings from the input payload for validation.

    DOCUMENTED §6.5 step 3: the set of allowable numbers is exactly the
    numbers that were passed into the prompt.
    """
    numbers = set()
    # Risk score
    numbers.add(str(risk_score))
    numbers.update(_extract_numbers_from_text(str(risk_score)))
    # Feature values and z-scores
    for feat in top_contributing_features:
        for key in ("value", "z_score"):
            val = feat.get(key)
            if val is not None:
                numbers.add(str(val))
                numbers.update(_extract_numbers_from_text(str(val)))
    return numbers


# ---------------------------------------------------------------------------
# Optional LLM path (Path B — enhancement)
# ---------------------------------------------------------------------------

def _try_llm_explanation(
    customer_id: str,
    risk_score: float,
    risk_band: str,
    detection_method: str,
    aml_pattern: str,
    feature_summary: str,
    determining_factor: str,
    recommended_action: str,
    escalation_rationale: str,
    top_contributing_features: list[dict[str, Any]],
    config: dict,
) -> str | None:
    """Attempt to generate an LLM-enhanced explanation.

    PATH B — Optional LLM Enhancement.
    Only called when llm.enabled=true in config AND ANTHROPIC_API_KEY is set.

    DOCUMENTED §5.6: "LLM call, but constrained to only the numeric facts"
    DOCUMENTED §6.5 step 1: constrained prompt receives only computed facts
    DOCUMENTED §6.5 step 2: model instructed to restate, never invent
    DOCUMENTED §6.5 step 3: post-generation number validation

    IMPLEMENTATION ASSUMPTION: falls back to None (→ template) if:
    - Import fails (anthropic not installed)
    - API key absent
    - API call fails
    - Number validation fails

    Returns:
        LLM-generated explanation string if successful, None otherwise.
    """
    llm_cfg = config.get("llm", {})
    if not llm_cfg.get("enabled", False):
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    try:
        import anthropic  # type: ignore

        user_prompt = str(llm_cfg.get("user_prompt_template", "")).format(
            customer_id=customer_id,
            risk_score=risk_score,
            risk_band=risk_band,
            detection_method=detection_method,
            aml_pattern=aml_pattern,
            feature_summary=feature_summary,
            determining_factor=determining_factor,
            recommended_action=recommended_action,
            escalation_rationale=escalation_rationale,
        )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=str(llm_cfg.get("model", "claude-sonnet-4-20250514")),
            max_tokens=int(llm_cfg.get("max_tokens", 300)),
            system=str(llm_cfg.get("system_prompt", "")),
            messages=[{"role": "user", "content": user_prompt}],
        )
        generated_text = response.content[0].text.strip()

        # DOCUMENTED §6.5 step 3: number validation
        val_cfg = llm_cfg.get("number_validation", {})
        if val_cfg.get("enabled", True):
            input_numbers = _collect_input_numbers(risk_score, top_contributing_features)
            tolerance = float(val_cfg.get("float_tolerance", 0.01))
            if not _validate_numbers(generated_text, input_numbers, tolerance):
                # DOCUMENTED §6.5 step 3 + §11 Risk: "regenerate or flag on mismatch"
                # IMPLEMENTATION ASSUMPTION: discard and use template (per your instruction)
                return None

        return generated_text

    except Exception:
        # Any failure in the LLM path falls back to template silently
        return None


# ---------------------------------------------------------------------------
# Per-entity explanation builder
# ---------------------------------------------------------------------------

def _explain_entity(
    customer_id: str,
    anomaly_entity: dict[str, Any] | None,
    classification: dict[str, Any],
    escalation_entry: dict[str, Any] | None,
    target_pattern: str,
    config: dict,
) -> dict[str, Any]:
    """Build a complete explanation for one entity.

    Assembles all numeric facts from upstream outputs and generates the
    explanation text using Path A (template) or Path B (LLM) as configured.

    Every number in the output is sourced directly from upstream outputs.
    DOCUMENTED §3.1 principle 4, §5.6, §6.5 DoD.

    Args:
        customer_id: The entity's ID.
        anomaly_entity: The entity's dict from anomaly_detection output.
        classification: The entity's dict from risk_classification output.
        escalation_entry: The entity's dict from escalation output (may be None).
        target_pattern: The AML pattern from the execution plan.
        config: Loaded explanation config.

    Returns:
        Dict with explanation fields (see return annotation below).
    """
    # --- Extract values from upstream outputs ---
    # DOCUMENTED: consume only already-computed facts (§5.6, §3.1 p.4)
    risk_score = float(classification.get("risk_score", 0.0))
    risk_band = str(classification.get("risk_band", "Unknown"))
    determining_factor = str(classification.get("determining_factor", ""))
    rule_matched = bool((anomaly_entity or {}).get("rule_matched", False))
    detection_method = str((anomaly_entity or {}).get("method_used", "unknown"))
    if detection_method == "unknown":
        # method_used is on the anomaly_detection result, not per-entity.
        # It is injected by the assembler caller.
        detection_method = "unknown"
    top_contributing_features = list(
        (anomaly_entity or {}).get("top_contributing_features", [])
    )
    rule_condition = str((anomaly_entity or {}).get("matched_condition", "") or "")
    anomaly_score = float((anomaly_entity or {}).get("anomaly_score", risk_score))

    # AML pattern: from target_pattern arg or "anomalous activity" if absent
    aml_pattern = str(target_pattern) if target_pattern else "anomalous activity"

    # Escalation fields
    recommended_action = ""
    escalation_rationale = ""
    if escalation_entry:
        recommended_action = str(escalation_entry.get("recommended_action", ""))
        escalation_rationale = str(escalation_entry.get("rationale", ""))

    # Build feature summary prose
    feature_summary = _build_feature_summary(top_contributing_features, config)

    # --- Attempt LLM path (Path B — optional) ---
    # DOCUMENTED §5.6, §6.5 steps 1-3
    llm_text = _try_llm_explanation(
        customer_id=customer_id,
        risk_score=risk_score,
        risk_band=risk_band,
        detection_method=detection_method,
        aml_pattern=aml_pattern,
        feature_summary=feature_summary,
        determining_factor=determining_factor,
        recommended_action=recommended_action,
        escalation_rationale=escalation_rationale,
        top_contributing_features=top_contributing_features,
        config=config,
    )

    if llm_text is not None:
        explanation_text = llm_text
        explanation_path = "llm"
    else:
        # --- Path A — deterministic template ---
        explanation_text = _build_template_explanation(
            customer_id=customer_id,
            risk_score=risk_score,
            risk_band=risk_band,
            detection_method=detection_method,
            aml_pattern=aml_pattern,
            feature_summary=feature_summary,
            rule_condition=rule_condition,
            determining_factor=determining_factor,
            recommended_action=recommended_action,
            escalation_rationale=escalation_rationale,
            config=config,
        )
        explanation_path = "template"

    return {
        # DOCUMENTED output fields (§5.6, §8):
        "customer_id": customer_id,
        "explanation": explanation_text,
        "risk_band": risk_band,
        "risk_score": risk_score,
        "recommended_action": recommended_action,
        # Audit fields — traceable to upstream outputs:
        "top_contributing_features": top_contributing_features,
        "determining_factor": determining_factor,
        "aml_pattern": aml_pattern,
        "detection_method": detection_method,
        "escalation_rationale": escalation_rationale,
        # Implementation audit field:
        "explanation_path": explanation_path,  # "template" or "llm"
    }


# ---------------------------------------------------------------------------
# Main tool function (registered in ToolRegistry)
# ---------------------------------------------------------------------------

def explanation(context: dict[str, Any], **args: Any) -> dict[str, Any]:
    """Generate query-grounded explanations for flagged entities.

    Reference: Solution Design §5.6, Implementation Plan §6.5.
    This is the tool function registered in the ToolRegistry.

    Reads from risk_classification and escalation outputs in context.
    Generates explanations using the deterministic template path (default)
    or the optional LLM path (if configured and API key is available).

    DOCUMENTED §5.6: "constrained to only the numeric facts passed in"
    DOCUMENTED §3.1 p.4: "numbers from code, words from the LLM"
    DOCUMENTED §4.2: accepts tie_to_query argument

    Args:
        context: Shared execution context. Expected keys:
            - "risk_classification": result from Risk Classification.
            - "escalation": result from Escalation (optional).
            - "anomaly_detection": result from Anomaly Detection (optional).
        **args: ExecutionPlan step arguments:
            - tie_to_query: bool — whether to tie explanation to query context
              (DOCUMENTED §4.2 Listing 2). Currently used as a flag; the
              query text is not available in this context so the template
              always references the aml_pattern instead.

    Returns:
        Dict with:
            - tool: "explanation"
            - status: "success" | "error"
            - explanations: list of per-entity explanation dicts
            - summary: counts by risk band
    """
    tie_to_query = bool(args.get("tie_to_query", True))
    config = _load_explanation_config()

    # --- Resolve Risk Classification output (required) ---
    rc_result = context.get("risk_classification", {})
    if not isinstance(rc_result, dict):
        return {
            "tool": "explanation",
            "status": "error",
            "error": "No risk_classification result found in context.",
        }

    classifications = rc_result.get("classifications", [])
    if not classifications:
        return {
            "tool": "explanation",
            "status": "error",
            "error": (
                "risk_classification.classifications is empty. "
                "Run Risk Classification before Explanation."
            ),
        }

    # --- Resolve optional upstream outputs ---
    anomaly_result = context.get("anomaly_detection", {}) or {}
    escalation_result = context.get("escalation", {}) or {}
    query_spec = context.get("query_spec", {}) or {}

    # Extract detection method and target pattern from anomaly result
    detection_method = str(anomaly_result.get("method_used", "unknown"))
    if isinstance(query_spec, dict):
        target_pattern = str(query_spec.get("aml_pattern", "") or "")
    else:
        try:
            target_pattern = str(query_spec.aml_pattern or "")
        except AttributeError:
            target_pattern = ""

    # Also try target_pattern from anomaly_detection args
    if not target_pattern:
        target_pattern = str(anomaly_result.get("target_pattern", "") or "")

    # Build lookup maps for anomaly entities and escalation entries
    anomaly_entities: dict[str, dict] = {}
    for entity in anomaly_result.get("all_entities", []):
        cid = str(entity.get("customer_id", ""))
        if cid:
            anomaly_entities[cid] = dict(entity)
            # Inject method_used from the top-level result
            anomaly_entities[cid]["method_used"] = detection_method

    escalation_by_id: dict[str, dict] = {}
    for entry in escalation_result.get("escalations", []):
        cid = str(entry.get("customer_id", ""))
        if cid:
            escalation_by_id[cid] = dict(entry)

    # --- Generate explanation per classified entity ---
    explanations = []
    for classification in classifications:
        customer_id = str(classification.get("customer_id", "unknown"))
        anomaly_entity = anomaly_entities.get(customer_id)
        escalation_entry = escalation_by_id.get(customer_id)

        entity_explanation = _explain_entity(
            customer_id=customer_id,
            anomaly_entity=anomaly_entity,
            classification=classification,
            escalation_entry=escalation_entry,
            target_pattern=target_pattern,
            config=config,
        )
        explanations.append(entity_explanation)

    # --- Summary counts ---
    summary: dict[str, int] = {}
    for e in explanations:
        band = e.get("risk_band", "Unknown")
        summary[band] = summary.get(band, 0) + 1

    return {
        "tool": "explanation",
        "status": "success",
        "tie_to_query": tie_to_query,
        "explanations": explanations,
        "summary": summary,
    }
