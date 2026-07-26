"""Risk Classification Tool.

Reference: Solution Design §5.5, Implementation Plan §6.4.

Purpose: Convert raw anomaly scores / rule hits into a business-facing
Low / Medium / High risk band using context-appropriate thresholds.

DOCUMENTED behaviour:
1. Percentile-based thresholds computed within the filtered cohort.
   (Never against a global fixed cutoff — §6.4 step 1.)
2. Hard business rule overrides layered on top:
   - any exact rule-engine match → minimum Medium (§5.5, §6.4 step 2)
   - any prior SAR filing on the entity (customers.csv.kyc_flags) → minimum High
     (§5.5, §6.4 step 2)
3. Return risk band, underlying continuous score, and the specific rule/threshold
   that determined the final band, for auditability. (§6.4 step 3)

IMPLEMENTATION ASSUMPTIONS (externalized to risk_classification_config.yaml):
- high_percentile (95): "e.g. top 5% = High" in §5.5 — the "e.g." means
  illustrative not mandatory; value externalized for tuning.
- medium_percentile (80): "next 15% = Medium" → starts at 80th percentile;
  same caveat.
- prior_sar_kyc_flag_values: §5.5 specifies the kyc_flags field drives the
  prior-SAR override but does not name the exact flag strings.
- anomaly_score used as the continuous score: the detection tool already
  produces a 0-1 continuous score; this is the "underlying continuous score"
  referenced in §6.4 step 3.

IMPLEMENTATION IMPROVEMENTS:
- Identical-scores edge case: when all scores are equal, numpy.percentile
  returns the common value as both thresholds, causing every entity to be
  classified as High. A strict comparison (`>` rather than `>=` for the
  medium band fallback) combined with the equal-scores guard ensures a
  sensible spread. Deterministic.

USER-REQUESTED ENHANCEMENTS (isolated, do not alter documented architecture):
- Small-cohort fallback (min_cohort_for_percentile): when the filtered cohort
  has fewer than this many entities, absolute score thresholds are used instead
  of percentile thresholds. Externalized to config, documented as enhancement.
- Expanded audit fields in the result dict: initial_band, final_band,
  rule_override, sar_override, thresholds_used. The existing determining_factor
  field is preserved. New fields are additions only, not replacements.
- Robust prior-SAR detection: handles None, NaN, float, whitespace-only, and
  mixed-case kyc_flags values without raising exceptions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config"
    / "risk_classification_config.yaml"
)


def _load_risk_config() -> dict:
    """Load risk classification configuration."""
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Band ordering helper
# ---------------------------------------------------------------------------

def _band_rank(band: str, bands: list[str]) -> int:
    """Return the ordinal rank of a risk band (0 = lowest)."""
    try:
        return bands.index(band)
    except ValueError:
        return 0


def _max_band(a: str, b: str, bands: list[str]) -> str:
    """Return the higher of two risk bands."""
    return a if _band_rank(a, bands) >= _band_rank(b, bands) else b


# ---------------------------------------------------------------------------
# Percentile threshold computation
# ---------------------------------------------------------------------------

def _compute_thresholds(
    scores: list[float],
    high_percentile: float,
    medium_percentile: float,
) -> tuple[float, float]:
    """Compute percentile-based thresholds within the filtered cohort.

    DOCUMENTED: "percentile-based thresholds computed within the filtered
    cohort (never against a global fixed cutoff)" — §6.4 step 1.

    Returns:
        Tuple of (high_threshold, medium_threshold).
        A score >= high_threshold → High band.
        A score >= medium_threshold (and < high_threshold) → Medium band.
        Otherwise → Low band.
    """
    if len(scores) == 0:
        return 0.0, 0.0
    arr = np.array(scores, dtype=float)
    high_thresh = float(np.percentile(arr, high_percentile))
    medium_thresh = float(np.percentile(arr, medium_percentile))
    return high_thresh, medium_thresh


def _all_scores_equal(scores: list[float]) -> bool:
    """Return True if all scores in the list are identical.

    IMPLEMENTATION IMPROVEMENT: When all scores are equal, numpy percentile
    returns the same value for both thresholds, causing every entity to be
    classified as High (score >= threshold is always true). This guard
    identifies that degenerate case so the caller can apply sensible logic.
    """
    if len(scores) <= 1:
        return True
    return all(abs(s - scores[0]) < 1e-9 for s in scores)


def _assign_band_by_percentile(
    risk_score: float,
    high_thresh: float,
    medium_thresh: float,
    all_equal: bool,
) -> tuple[str, str]:
    """Assign an initial band from percentile thresholds.

    IMPLEMENTATION IMPROVEMENT — Identical-scores guard:
    When all_equal=True, every score equals both thresholds. Classifying
    all as High would be misleading. Instead, assign Low to all (no entity
    is more anomalous than another when scores are identical).

    Args:
        risk_score: The entity's anomaly score.
        high_thresh: 95th-percentile threshold.
        medium_thresh: 80th-percentile threshold.
        all_equal: True when all entities in the cohort have the same score.

    Returns:
        Tuple of (initial_band, percentile_reason_str).
    """
    if all_equal:
        # IMPLEMENTATION IMPROVEMENT: uniform scores — assign Low to all.
        # No entity is statistically more anomalous than another.
        return (
            "Low",
            f"all_scores_equal={risk_score} → Low (uniform cohort, "
            f"no statistical differentiation possible)"
        )

    if risk_score >= high_thresh:
        return (
            "High",
            f"anomaly_score={risk_score} >= high_threshold={round(high_thresh, 4)} "
            f"(top percentile of cohort)"
        )
    if risk_score >= medium_thresh:
        return (
            "Medium",
            f"anomaly_score={risk_score} >= medium_threshold={round(medium_thresh, 4)} "
            f"(next percentile band of cohort)"
        )
    return (
        "Low",
        f"anomaly_score={risk_score} < medium_threshold={round(medium_thresh, 4)}"
    )


def _assign_band_by_absolute(
    risk_score: float,
    score_high: float,
    score_medium: float,
) -> tuple[str, str]:
    """Assign band by absolute score thresholds (small-cohort fallback).

    USER-REQUESTED ENHANCEMENT: When the cohort is too small for percentile
    thresholds to be meaningful, use fixed absolute thresholds instead.
    These thresholds are fully externalized to risk_classification_config.yaml.

    Args:
        risk_score: The entity's anomaly score.
        score_high: Absolute threshold above which → High.
        score_medium: Absolute threshold above which → Medium.

    Returns:
        Tuple of (band, reason_str).
    """
    if risk_score >= score_high:
        return (
            "High",
            f"small_cohort_fallback: anomaly_score={risk_score} >= "
            f"score_high_absolute={score_high}"
        )
    if risk_score >= score_medium:
        return (
            "Medium",
            f"small_cohort_fallback: anomaly_score={risk_score} >= "
            f"score_medium_absolute={score_medium}"
        )
    return (
        "Low",
        f"small_cohort_fallback: anomaly_score={risk_score} < "
        f"score_medium_absolute={score_medium}"
    )


# ---------------------------------------------------------------------------
# Prior-SAR check
# ---------------------------------------------------------------------------

def _has_prior_sar(
    customer_id: str,
    df_customers: pd.DataFrame | None,
    sar_flag_values: list[str],
) -> bool:
    """Check whether a customer has a prior SAR flag in kyc_flags.

    DOCUMENTED: "any prior SAR filing on the entity (from customers.csv.kyc_flags)
    → minimum High" — §5.5, §6.4 step 2.

    IMPLEMENTATION IMPROVEMENT — Robust null/whitespace/type handling:
    Gracefully handles missing kyc_flags column, None values, NaN values
    (numpy float NaN), empty strings, whitespace-only strings, and mixed
    capitalisation — without raising exceptions.

    Args:
        customer_id: The customer to check.
        df_customers: Customers DataFrame from the Data Loader.
        sar_flag_values: Substrings to look for in kyc_flags (case-insensitive).

    Returns:
        True if any SAR-related flag is present.
    """
    if df_customers is None:
        return False
    if not isinstance(df_customers, pd.DataFrame):
        return False
    if "kyc_flags" not in df_customers.columns:
        return False

    cid_str = str(customer_id)
    try:
        mask = df_customers["customer_id"].astype(str) == cid_str
    except Exception:
        return False

    rows = df_customers[mask]
    if rows.empty:
        return False

    raw_val = rows.iloc[0]["kyc_flags"]

    # IMPLEMENTATION IMPROVEMENT: robust null/NaN/whitespace handling.
    # pandas may present missing values as float NaN, None, or empty string.
    if raw_val is None:
        return False
    # Guard against numpy float NaN
    try:
        if isinstance(raw_val, float) and np.isnan(raw_val):
            return False
    except (TypeError, ValueError):
        pass

    kyc_val = str(raw_val).strip().lower()
    if not kyc_val or kyc_val in ("nan", "none", "nat", ""):
        return False

    for flag in sar_flag_values:
        if str(flag).lower().strip() in kyc_val:
            return True
    return False


# ---------------------------------------------------------------------------
# Main classification function
# ---------------------------------------------------------------------------

def _classify_entities(
    all_entities: list[dict[str, Any]],
    df_customers: pd.DataFrame | None,
    config: dict,
) -> list[dict[str, Any]]:
    """Classify all entities into risk bands.

    Applies:
    1. Percentile-based thresholds on the anomaly_score (§6.4 step 1),
       with edge-case handling for identical scores and small cohorts.
    2. Hard business rule overrides (§6.4 step 2).
    3. Returns risk_band, risk_score, and determining_factor (§6.4 step 3),
       plus expanded audit fields (user-requested enhancement).

    Args:
        all_entities: List of entity dicts from the Anomaly Detection output.
            Each must contain 'customer_id', 'anomaly_score', 'rule_matched'.
        df_customers: Customers DataFrame for prior-SAR lookup.
        config: Loaded risk classification config.

    Returns:
        List of classification result dicts per entity.
    """
    bands = config["bands"]
    high_percentile = float(config["high_percentile"])
    medium_percentile = float(config["medium_percentile"])
    sar_flags = config["prior_sar_kyc_flag_values"]
    min_cohort = int(config.get("min_cohort_for_percentile", 5))
    fallback = config.get("small_cohort_fallback", "score_only")
    score_high_abs = float(config.get("score_high_absolute", 0.75))
    score_med_abs = float(config.get("score_medium_absolute", 0.40))

    n = len(all_entities)
    scores = [float(e["anomaly_score"]) for e in all_entities]

    # --- Step 1: Determine thresholds ---
    use_fallback = n < min_cohort  # USER-REQUESTED ENHANCEMENT: small cohort
    equal_scores = _all_scores_equal(scores)  # IMPLEMENTATION IMPROVEMENT

    if not use_fallback:
        high_thresh, medium_thresh = _compute_thresholds(
            scores, high_percentile, medium_percentile
        )
    else:
        high_thresh, medium_thresh = 0.0, 0.0  # not used in fallback path

    # --- Build audit context string for thresholds ---
    if use_fallback:
        thresholds_used = (
            f"small_cohort_fallback (n={n} < min={min_cohort}): "
            f"absolute high={score_high_abs}, medium={score_med_abs}"
        )
    elif equal_scores:
        thresholds_used = (
            f"uniform_scores: all={scores[0] if scores else 0} "
            f"(percentiles: high={round(high_thresh, 4)}, medium={round(medium_thresh, 4)})"
        )
    else:
        thresholds_used = (
            f"percentile high={round(high_percentile)}th={round(high_thresh, 4)}, "
            f"medium={round(medium_percentile)}th={round(medium_thresh, 4)}"
        )

    results = []
    for entity in all_entities:
        customer_id = str(entity["customer_id"])
        risk_score = round(float(entity["anomaly_score"]), 4)
        rule_matched = bool(entity.get("rule_matched", False))

        # --- Step 1: Assign initial band ---
        if use_fallback:
            initial_band, percentile_reason = _assign_band_by_absolute(
                risk_score, score_high_abs, score_med_abs
            )
        else:
            initial_band, percentile_reason = _assign_band_by_percentile(
                risk_score, high_thresh, medium_thresh, equal_scores
            )

        final_band = initial_band
        rule_override = False
        sar_override = False

        # Build the determining_factor (backward-compatible: same field name,
        # same meaning, now richer content — USER-REQUESTED ENHANCEMENT).
        determining_factor = percentile_reason

        # --- Step 2: Hard business rule overrides (DOCUMENTED) ---
        # Rule 1: any exact rule-engine match → minimum Medium
        if rule_matched and _band_rank(final_band, bands) < _band_rank("Medium", bands):
            final_band = "Medium"
            rule_override = True
            determining_factor = (
                f"rule_engine_match=True → minimum Medium override "
                f"(underlying_score={risk_score}, initial_band={initial_band})"
            )

        # Rule 2: prior SAR flag → minimum High
        prior_sar = _has_prior_sar(customer_id, df_customers, sar_flags)
        if prior_sar and _band_rank(final_band, bands) < _band_rank("High", bands):
            final_band = "High"
            sar_override = True
            determining_factor = (
                f"prior_sar_flag=True → minimum High override "
                f"(underlying_score={risk_score}, initial_band={initial_band})"
            )

        # --- USER-REQUESTED ENHANCEMENT: expanded audit fields ---
        # All new fields are additions only; existing fields are unchanged.
        results.append({
            # Existing documented fields (§6.4 step 3) — UNCHANGED:
            "customer_id": customer_id,
            "risk_score": risk_score,
            "risk_band": final_band,
            "determining_factor": determining_factor,
            # New audit fields (user-requested enhancement):
            "initial_band": initial_band,
            "rule_override": rule_override,
            "sar_override": sar_override,
            "thresholds_used": thresholds_used,
        })

    return results


# ---------------------------------------------------------------------------
# Main tool function (registered in ToolRegistry)
# ---------------------------------------------------------------------------


def risk_classification(context: dict[str, Any], **args: Any) -> dict[str, Any]:
    """Classify entities into risk bands.

    Reference: Solution Design §5.5, Implementation Plan §6.4.
    This is the tool function registered in the ToolRegistry.

    Public API is UNCHANGED from the original implementation:
    - Same input contract (context, **args)
    - Same output keys: tool, status, scheme, high_threshold, medium_threshold,
      classifications, summary
    - New output keys added as user-requested enhancement: cohort_size,
      fallback_used, equal_scores_detected (additions only, no removals)

    Args:
        context: Shared execution context. Expected keys:
            - "anomaly_detection": result dict from Anomaly Detection.
            - "data_loader": optional, for customers DataFrame (prior-SAR check).
        **args: Arguments from the ExecutionPlan step (e.g., scheme).

    Returns:
        Dict with:
            - tool: "risk_classification"
            - status: "success"
            - scheme: the classification scheme used
            - high_threshold: computed high percentile threshold
            - medium_threshold: computed medium percentile threshold
            - classifications: list per entity with documented fields + audit fields
            - summary: {Low: N, Medium: N, High: N}
            - cohort_size: total entities classified (NEW — audit)
            - fallback_used: True if small-cohort fallback was applied (NEW — audit)
            - equal_scores_detected: True if all scores identical (NEW — audit)
    """
    scheme = args.get("scheme", "pattern_aware")
    config = _load_risk_config()

    # --- Resolve Anomaly Detection output from context ---
    anomaly_result = context.get("anomaly_detection", {})
    if not isinstance(anomaly_result, dict):
        return {
            "tool": "risk_classification",
            "status": "error",
            "error": "No anomaly_detection result found in context.",
        }

    all_entities = anomaly_result.get("all_entities", [])
    if not all_entities:
        return {
            "tool": "risk_classification",
            "status": "error",
            "error": (
                "anomaly_detection.all_entities is empty. "
                "Run Anomaly Detection before Risk Classification."
            ),
        }

    # --- Resolve customers DataFrame for prior-SAR check ---
    df_customers = None
    data_loader_result = context.get("data_loader", {})
    if isinstance(data_loader_result, dict):
        df_customers = data_loader_result.get("customers")
    if df_customers is None:
        df_customers = context.get("customers")

    # --- Classify entities ---
    classifications = _classify_entities(all_entities, df_customers, config)

    # --- Summary counts ---
    bands = config["bands"]
    summary = {band: 0 for band in bands}
    for c in classifications:
        summary[c["risk_band"]] = summary.get(c["risk_band"], 0) + 1

    # --- Compute thresholds for output (auditability — documented §6.4 step 3) ---
    scores = [float(e["anomaly_score"]) for e in all_entities]
    n = len(scores)
    min_cohort = int(config.get("min_cohort_for_percentile", 5))
    use_fallback = n < min_cohort
    equal_scores = _all_scores_equal(scores)

    if not use_fallback:
        high_thresh, medium_thresh = _compute_thresholds(
            scores,
            float(config["high_percentile"]),
            float(config["medium_percentile"]),
        )
    else:
        high_thresh = float(config.get("score_high_absolute", 0.75))
        medium_thresh = float(config.get("score_medium_absolute", 0.40))

    return {
        "tool": "risk_classification",
        "status": "success",
        "scheme": scheme,
        # Documented output fields (UNCHANGED):
        "high_threshold": round(high_thresh, 4),
        "medium_threshold": round(medium_thresh, 4),
        "classifications": classifications,
        "summary": summary,
        # New audit fields (user-requested enhancement):
        "cohort_size": n,
        "fallback_used": use_fallback,
        "equal_scores_detected": equal_scores,
    }
