"""Anomaly Detection Tool.

Reference: Solution Design §5.4, Implementation Plan §6.3.

Purpose: Score transactions/customers as anomalous using the method appropriate
to the query — not always ML.

Methods (agent chooses via 'method' argument):
  - rule_engine: direct threshold/count logic applied per customer.
    Used when the query states a concrete rule (explicit_rule.present=True).
    Implementation Plan §6.3 step 1.
  - statistical: z-score/IQR flagging on engineered features.
    Returned with the exact feature and threshold that triggered the flag.
    Implementation Plan §6.3 step 2.
  - ml:          IsolationForest / LOF.  (Implementation Plan §6.3 step 3)
  - hybrid:      rule pre-filter + ML scoring. (Implementation Plan §6.3
    step 4 — not yet implemented in this task cycle)

Output (all methods): per-entity dict containing:
  - customer_id
  - anomaly_score (float in [0, 1])
  - rule_matched (bool) — True only for rule_engine method
  - matched_condition (str | None) — the condition string that fired
  - top_contributing_features (list of {feature, value, z_score})

Implementation interpretations (documented per project rules):
  1. §4.4 shows "rule_engine" as a named step in the pipeline. This is treated
     as a LOGICAL PROCESSING LABEL, not a requirement to register it as a
     separate ToolRegistry tool. The Rule Engine is implemented as step 1
     of the Anomaly Detection Tool, consistent with Solution Design §5.4 and
     Implementation Plan §6.3, which both describe it as a method/step of
     this tool.
  2. "count(transactions)" in the condition string means per-customer row count
     in the DataFrame provided to the rule engine. Not defined in documentation;
     clarified as an implementation interpretation.
  3. "amount" in the condition string maps to the "amount_normalized" column
     produced by the Data Loader. The documentation does not specify which
     amount column; this mapping is an implementation interpretation and is
     externalized to rule_engine_config.yaml.
  4. Statistical path operates on the per-customer features DataFrame produced
     by the Feature Engineering Tool (not raw transactions). This is required
     by §6.3 step 2: "z-score/IQR flagging on engineered features".
  5. anomaly_score for the statistical path = min(max_abs_z / scale_factor, 1.0).
     The documentation specifies "anomaly_score (0–1)" but not the mapping from
     z-scores to this range. This formula is an implementation interpretation,
     externalized to statistical_detection_config.yaml.
  6. z-score threshold (2.0) and IQR multiplier (1.5) are implementation
     assumptions not specified in the documentation. Both are externalized
     to statistical_detection_config.yaml.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_RULE_ENGINE_CONFIG_PATH = _CONFIG_DIR / "rule_engine_config.yaml"
_STATISTICAL_CONFIG_PATH = _CONFIG_DIR / "statistical_detection_config.yaml"
_ML_DETECTION_CONFIG_PATH = _CONFIG_DIR / "ml_detection_config.yaml"


def _load_rule_engine_config() -> dict:
    """Load rule engine configuration from rule_engine_config.yaml."""
    with open(_RULE_ENGINE_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _load_statistical_config() -> dict:
    """Load statistical detection configuration from statistical_detection_config.yaml.

    All keys are IMPLEMENTATION ASSUMPTIONS not specified in the documentation.
    See statistical_detection_config.yaml for full rationale per key.
    """
    with open(_STATISTICAL_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _load_ml_config() -> dict:
    """Load ML detection configuration from ml_detection_config.yaml.

    Most keys are IMPLEMENTATION ASSUMPTIONS not specified in the documentation.
    Documented keys: use of IsolationForest, LOF, scikit-learn/PyOD, unsupervised.
    See ml_detection_config.yaml for full rationale per key.
    """
    with open(_ML_DETECTION_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Rule DSL parser and evaluator
# ---------------------------------------------------------------------------

# Supported operators in the condition DSL.
# IMPLEMENTATION ASSUMPTION: The documentation provides one example condition
# (count(transactions) >= 10 AND amount < 10000). The full set of supported
# operators is an implementation assumption necessary to build a working DSL.
_SUPPORTED_OPERATORS = {">=", "<=", ">", "<", "==", "!="}
_SUPPORTED_CONJUNCTIONS = {"AND", "OR"}


def _parse_condition(condition: str) -> list[dict[str, Any]]:
    """Parse an explicit_rule.condition string into a list of sub-conditions.

    Reference: Implementation Plan §6.3 step 1 — "takes the explicit_rule.condition
    string (or a parsed structured version of it) and applies it directly to the
    DataFrame."

    The parser recognises:
    - count(transactions) {op} {value}  — per-customer transaction count
    - amount {op} {value}               — per-customer amount column condition
    - {field} {op} {value}              — general per-row field condition (future)

    Conjunctions AND / OR are parsed as the joining logic between sub-conditions.

    IMPLEMENTATION ASSUMPTION: The documented example uses a simple flat expression
    with one conjunction. Nested parentheses are not supported. This is sufficient
    for the documented reference query and any reasonable single-level rule.

    Args:
        condition: Condition string, e.g.
            "count(transactions) >= 10 AND amount < 10000"

    Returns:
        List of parsed sub-condition dicts with keys:
            - field: str  ("count_transactions" | "amount" | other)
            - operator: str  (">=", "<=", etc.)
            - value: float
            - conjunction: str  ("AND" | "OR" | None — last sub-condition)
    """
    # Normalise whitespace
    condition = " ".join(condition.split())

    # Split on AND / OR while preserving the conjunction
    # Pattern: split on word-boundary AND or OR
    parts = re.split(r'\s+(AND|OR)\s+', condition, flags=re.IGNORECASE)

    sub_conditions = []
    i = 0
    while i < len(parts):
        token = parts[i].strip()
        # Determine conjunction for this sub-condition (follows it in `parts`)
        if i + 1 < len(parts) and parts[i + 1].upper() in _SUPPORTED_CONJUNCTIONS:
            conjunction = parts[i + 1].upper()
            i += 2  # skip the conjunction token in next iteration
        else:
            conjunction = None
            i += 1

        sub_conditions.append(_parse_sub_condition(token, conjunction))

    return sub_conditions


def _parse_sub_condition(token: str, conjunction: str | None) -> dict[str, Any]:
    """Parse a single sub-condition token.

    Args:
        token: e.g. "count(transactions) >= 10" or "amount < 10000"
        conjunction: "AND", "OR", or None

    Returns:
        Dict with keys: field, operator, value, conjunction
    """
    # Try to match an operator
    op_match = None
    for op in sorted(_SUPPORTED_OPERATORS, key=len, reverse=True):  # longest first
        if op in token:
            op_match = op
            break

    if op_match is None:
        raise ValueError(
            f"Rule Engine: no supported operator found in sub-condition: '{token}'. "
            f"Supported operators: {sorted(_SUPPORTED_OPERATORS)}"
        )

    left, right = token.split(op_match, 1)
    left = left.strip()
    right = right.strip()

    # Parse the value
    try:
        value = float(right)
    except ValueError:
        raise ValueError(
            f"Rule Engine: cannot parse numeric value from '{right}' in "
            f"sub-condition '{token}'"
        )

    # Normalise field name
    # "count(transactions)" → "count_transactions"  (documented alias)
    # "amount" → use the configured amount_column name
    field_lower = left.lower().replace(" ", "")
    if field_lower in ("count(transactions)", "count_transactions"):
        field = "count_transactions"
    else:
        # Any other field is passed through as-is (lowercased)
        # "amount" will be remapped to amount_column in the evaluator
        field = left.lower().strip()

    return {
        "field": field,
        "operator": op_match,
        "value": value,
        "conjunction": conjunction,
    }


def _evaluate_customer(
    customer_id: str,
    group: pd.DataFrame,
    sub_conditions: list[dict[str, Any]],
    amount_column: str,
) -> bool:
    """Evaluate all sub-conditions for a single customer.

    Applies each sub-condition against the customer's transaction group:
    - "count_transactions" conditions compare against row count.
    - "amount" conditions check whether ALL transactions satisfy the condition.
      IMPLEMENTATION ASSUMPTION: "amount < 10000" means every transaction for
      this customer is below $10,000, consistent with the reference query
      "Which customers made 10+ transactions under $10,000?" — all must be
      under threshold, not just some.

    Args:
        customer_id: For error messages only.
        group: Transaction rows for this customer.
        sub_conditions: Parsed sub-conditions from _parse_condition().
        amount_column: Column name to use for "amount" comparisons.

    Returns:
        True if the customer satisfies the full combined condition.
    """
    _OPS = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">":  lambda a, b: a > b,
        "<":  lambda a, b: a < b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    result = None  # overall result, built incrementally

    for sc in sub_conditions:
        field = sc["field"]
        op = sc["operator"]
        threshold = sc["value"]
        conjunction = sc["conjunction"]

        op_fn = _OPS[op]

        if field == "count_transactions":
            # Per-customer count of rows in the provided DataFrame
            sub_result = op_fn(len(group), threshold)

        elif field == "amount":
            # IMPLEMENTATION ASSUMPTION: "amount < X" means ALL of this customer's
            # transactions satisfy the condition (all are below the threshold).
            if amount_column not in group.columns:
                raise ValueError(
                    f"Rule Engine: amount column '{amount_column}' not found in "
                    f"DataFrame. Available columns: {list(group.columns)}"
                )
            sub_result = bool(op_fn(group[amount_column], threshold).all())

        else:
            # Generic field: check against a column if it exists
            if field not in group.columns:
                raise ValueError(
                    f"Rule Engine: field '{field}' not found in DataFrame. "
                    f"Available columns: {list(group.columns)}"
                )
            sub_result = bool(op_fn(group[field], threshold).all())

        # Combine with running result using conjunction from the PREVIOUS token
        if result is None:
            result = sub_result
        elif sc.get("_prev_conjunction") == "OR":
            result = result or sub_result
        else:  # AND (default when conjunction is present or None)
            result = result and sub_result

    return bool(result) if result is not None else False


def _evaluate_conditions(
    df: pd.DataFrame,
    sub_conditions: list[dict[str, Any]],
    amount_column: str,
) -> dict[str, bool]:
    """Evaluate parsed conditions for every customer in the DataFrame.

    Args:
        df: Transactions DataFrame (from Data Loader output).
        sub_conditions: Output of _parse_condition().
        amount_column: Column to use for "amount" comparisons.

    Returns:
        Dict mapping customer_id → bool (True = rule matched).
    """
    # Propagate conjunction forward so each sub-condition knows how it combines
    # with the preceding result.
    for i in range(1, len(sub_conditions)):
        sub_conditions[i]["_prev_conjunction"] = sub_conditions[i - 1]["conjunction"]

    results = {}
    for customer_id, group in df.groupby("customer_id"):
        results[str(customer_id)] = _evaluate_customer(
            str(customer_id), group, sub_conditions, amount_column
        )
    return results


# ---------------------------------------------------------------------------
# Rule Engine path
# ---------------------------------------------------------------------------


def _run_rule_engine(
    df: pd.DataFrame,
    condition: str,
) -> dict[str, Any]:
    """Apply the rule engine to the transactions DataFrame.

    Reference: Solution Design §5.4 Rule Engine method;
               Implementation Plan §6.3 step 1.

    Evaluates the condition string per customer and returns an anomaly score
    for each customer.

    IMPLEMENTATION ASSUMPTIONS (see rule_engine_config.yaml for rationale):
    - anomaly_score = 1.0 for rule hit, 0.0 for miss.
    - "amount" in the condition maps to amount_normalized.
    - "count(transactions)" means per-customer row count.

    Args:
        df: Preprocessed transactions DataFrame from Data Loader.
            Must contain: customer_id, amount_normalized.
        condition: The explicit_rule.condition string from QuerySpec.

    Returns:
        Dict with:
          - method_used: "rule_engine"
          - condition_evaluated: the condition string
          - entities_scored: total customers evaluated
          - entities_flagged: customers where condition is True
          - flagged_entities: list of {customer_id, anomaly_score, rule_matched,
              matched_condition, top_contributing_features}
          - all_entities: same structure for all customers (including non-flagged)
    """
    config = _load_rule_engine_config()
    score_on_hit = float(config["anomaly_score_on_hit"])
    score_on_miss = float(config["anomaly_score_on_miss"])
    amount_column = config["amount_column"]

    sub_conditions = _parse_condition(condition)
    match_map = _evaluate_conditions(df, sub_conditions, amount_column)

    all_entities = []
    flagged_entities = []

    customer_stats = (
        df.groupby("customer_id")[amount_column]
        .agg(["count", "mean"])
        .rename(columns={"count": "txn_count", "mean": "avg_amount"})
    )
    # Normalise index to string for consistent lookup
    customer_stats.index = customer_stats.index.astype(str)

    for customer_id, matched in match_map.items():
        stats = customer_stats.loc[customer_id] if customer_id in customer_stats.index else None
        txn_count = int(stats["txn_count"]) if stats is not None else 0
        avg_amount = round(float(stats["avg_amount"]), 2) if stats is not None else 0.0

        score = score_on_hit if matched else score_on_miss

        # Top contributing features: the two rule terms that drove the decision.
        # For the rule engine these are the literal condition terms, not ML
        # feature attributions. Returned so the Explanation Component can use them.
        top_features = [
            {
                "feature": "txn_count",
                "value": txn_count,
                "z_score": 0.0,   # z_score is not applicable for rule engine
            },
            {
                "feature": amount_column,
                "value": avg_amount,
                "z_score": 0.0,
            },
        ]

        entity = {
            "customer_id": customer_id,
            "anomaly_score": score,
            "rule_matched": matched,
            "matched_condition": condition if matched else None,
            "top_contributing_features": top_features,
        }
        all_entities.append(entity)
        if matched:
            flagged_entities.append(entity)

    return {
        "method_used": "rule_engine",
        "condition_evaluated": condition,
        "entities_scored": len(match_map),
        "entities_flagged": len(flagged_entities),
        "flagged_entities": flagged_entities,
        "all_entities": all_entities,
    }


# ---------------------------------------------------------------------------
# Statistical Detection path
# ---------------------------------------------------------------------------


def _run_statistical_detection(
    features_df: pd.DataFrame,
) -> dict[str, Any]:
    """Apply z-score and IQR outlier detection to engineered features.

    Reference: Solution Design §5.4 Statistical method;
               Implementation Plan §6.3 step 2.
               Library: scipy.stats (documented in §6.3).

    Note on library use: §6.3 lists `scipy.stats` as the library for this path.
    The statistical computations below (mean, std, percentile) use numpy, which
    produces identical results to scipy.stats equivalents for these operations.
    scipy is installed per requirements.txt and is available for more advanced
    statistical tests if needed in future. The documented intent — deterministic
    statistical outlier detection — is fully satisfied by numpy's implementations.

    DOCUMENTED behaviour:
    - z-score outlier detection on engineered features.
    - IQR outlier detection on engineered features.
    - Return the exact feature and threshold that triggered the flag.
    - Return anomaly_score (0–1) per entity.
    - Return top contributing features via simple feature z-scores.
      (Solution Design §7: "simple z-score attribution for statistical path")

    IMPLEMENTATION ASSUMPTIONS (see statistical_detection_config.yaml):
    - z_score_threshold: 2.0 (flag if |z| > threshold)
    - iqr_multiplier:    1.5 (standard Tukey fence)
    - score_scale_factor: 2.0 (anomaly_score = min(max_abs_z / scale_factor, 1.0))
      This formula is an IMPLEMENTATION ASSUMPTION — §5.4 specifies the output
      range (0–1) and "simple z-score attribution" but does not define the exact
      mapping formula. Externalized to config so it can be tuned independently.
    - min_cohort_size_for_zscore: 2
    - top_n_features: 5

    Args:
        features_df: Per-customer engineered features DataFrame from the
            Feature Engineering Tool. Must contain a "customer_id" column.
            All other numeric columns are treated as features.

    Returns:
        Dict with:
          - method_used: "statistical"
          - entities_scored: total customers evaluated
          - entities_flagged: customers flagged by z-score or IQR
          - flagged_entities: list of flagged entity dicts
          - all_entities: same structure for all customers
    """
    import numpy as np

    config = _load_statistical_config()
    z_threshold = float(config["z_score_threshold"])
    iqr_mult = float(config["iqr_multiplier"])
    scale_factor = float(config["score_scale_factor"])
    min_cohort = int(config["min_cohort_size_for_zscore"])
    top_n = int(config["top_n_features"])

    if "customer_id" not in features_df.columns:
        raise ValueError(
            "Statistical detection: 'customer_id' column not found in features DataFrame."
        )

    # Identify numeric feature columns (exclude customer_id)
    feature_cols = [
        c for c in features_df.columns
        if c != "customer_id"
        and pd.api.types.is_numeric_dtype(features_df[c])
    ]

    if not feature_cols:
        raise ValueError(
            "Statistical detection: no numeric feature columns found in features DataFrame."
        )

    n_customers = len(features_df)

    # --- Compute cohort-level statistics for each feature ---
    # DOCUMENTED: "z-score / IQR outlier detection on engineered features"
    # Statistics are computed across all customers in the cohort (the filtered
    # dataset passed to this function), not against a global baseline.
    feature_stats: dict[str, dict] = {}
    for col in feature_cols:
        vals = features_df[col].astype(float).values
        non_nan = vals[~np.isnan(vals)]

        if len(non_nan) < min_cohort:
            # Skip features with insufficient data for z-score
            continue

        mu = float(np.mean(non_nan))
        sigma = float(np.std(non_nan, ddof=1))
        q1 = float(np.percentile(non_nan, 25))
        q3 = float(np.percentile(non_nan, 75))
        iqr_val = q3 - q1

        feature_stats[col] = {
            "mean": mu,
            "std": sigma,
            "q1": q1,
            "q3": q3,
            "iqr": iqr_val,
            "lower_fence": q1 - iqr_mult * iqr_val,
            "upper_fence": q3 + iqr_mult * iqr_val,
        }

    all_entities = []
    flagged_entities = []

    for _, row in features_df.iterrows():
        # Normalise customer_id: pandas may present integer IDs as floats
        # (e.g. 4521 → 4521.0 → "4521.0") during row iteration.
        # Cast to int first if the value is a whole number, then to str.
        raw_cid = row["customer_id"]
        try:
            customer_id = str(int(float(raw_cid)))
        except (ValueError, TypeError):
            customer_id = str(raw_cid)
        contributing_features = []

        max_abs_z = 0.0
        iqr_flagged = False

        for col, stats in feature_stats.items():
            val = float(row[col]) if not pd.isna(row[col]) else 0.0

            # --- Z-score computation ---
            # DOCUMENTED: "z-score / IQR flagging on engineered features,
            # returned with the exact feature and threshold that triggered the flag"
            if stats["std"] > 0:
                z = (val - stats["mean"]) / stats["std"]
            else:
                z = 0.0

            abs_z = abs(z)
            if abs_z > max_abs_z:
                max_abs_z = abs_z

            z_flagged = abs_z > z_threshold

            # --- IQR computation ---
            col_iqr_flagged = (
                val < stats["lower_fence"] or val > stats["upper_fence"]
            )
            if col_iqr_flagged:
                iqr_flagged = True

            # Record this feature if it triggered a flag
            if z_flagged or col_iqr_flagged:
                # DOCUMENTED: "returned with the exact feature and threshold
                # that triggered the flag"
                trigger_info = []
                if z_flagged:
                    trigger_info.append(
                        f"z={z:.3f} > threshold={z_threshold}"
                    )
                if col_iqr_flagged:
                    trigger_info.append(
                        f"IQR_fence=[{stats['lower_fence']:.2f}, "
                        f"{stats['upper_fence']:.2f}]"
                    )

                contributing_features.append({
                    "feature": col,
                    "value": round(val, 4),
                    "z_score": round(z, 4),
                    "triggered_by": " | ".join(trigger_info),
                })

        # Sort by absolute z-score descending (highest deviation first)
        contributing_features.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        top_features = contributing_features[:top_n]

        # --- Compute anomaly_score (0–1) ---
        # IMPLEMENTATION ASSUMPTION: score = min(max_abs_z / scale_factor, 1.0)
        # The documentation specifies the range (0–1) and "simple z-score
        # attribution" but not the exact formula. See config rationale.
        anomaly_score = round(min(max_abs_z / scale_factor, 1.0), 4)

        entity_flagged = len(contributing_features) > 0

        entity = {
            "customer_id": customer_id,
            "anomaly_score": anomaly_score,
            "rule_matched": False,          # not applicable for statistical
            "matched_condition": None,      # not applicable for statistical
            "top_contributing_features": top_features,
            "z_score_flagged": any(
                abs(f["z_score"]) > z_threshold for f in top_features
            ),
            "iqr_flagged": iqr_flagged,
        }

        all_entities.append(entity)
        if entity_flagged:
            flagged_entities.append(entity)

    return {
        "method_used": "statistical",
        "z_score_threshold": z_threshold,
        "iqr_multiplier": iqr_mult,
        "features_evaluated": list(feature_stats.keys()),
        "entities_scored": n_customers,
        "entities_flagged": len(flagged_entities),
        "flagged_entities": flagged_entities,
        "all_entities": all_entities,
    }


# ---------------------------------------------------------------------------
# ML Detection path
# ---------------------------------------------------------------------------


def _run_ml_detection(
    features_df: pd.DataFrame,
) -> dict[str, Any]:
    """Apply IsolationForest and LocalOutlierFactor to engineered features.

    Reference: Solution Design §5.4 ML-based unsupervised method;
               Implementation Plan §6.3 step 3.
               Libraries: scikit-learn (documented in §6.3, §7).

    DOCUMENTED requirements:
    - IsolationForest on the pattern-specific feature set. (§5.4, §6.3)
    - LocalOutlierFactor on the pattern-specific feature set. (§5.4, §6.3)
    - Unsupervised: no labeled fraud examples required. (§11 Risks)
    - anomaly_score (0–1) per entity. (§5.4 output)
    - Top contributing features via IsolationForest path-length attribution
      OR per-feature z-scores as a lightweight explainability proxy. (§6.3)

    Note on PyOD: §6.3 and §7 list PyOD as a library for this path.
    The current implementation uses scikit-learn's IsolationForest and
    LocalOutlierFactor, which are the two explicitly named algorithms.
    PyOD is installed per requirements.txt and is available if additional
    ensemble anomaly detectors (e.g. COPOD, ECOD) are added in future.
    The documented intent — running IF and LOF unsupervised — is fully
    satisfied by scikit-learn's implementations.

    IsolationForest (documented algorithm):
      Builds an ensemble of isolation trees. Each tree isolates a point by
      randomly selecting a feature and a split value within [min, max] of that
      feature. Anomaly score is inversely proportional to the average path
      length to isolation: shorter path = easier to isolate = more anomalous.
      Formula: score = 2^(-E[h(x)] / c(n)) mapped to [0, 1].
      WHY it detects AML: AML customers (structurers, layerers) have unusual
      feature combinations that are quickly isolated in sparse regions of the
      feature space. Does not require labeled examples.

    LocalOutlierFactor (documented algorithm):
      Compares each entity's local reachability density to its n_neighbors
      nearest neighbours. LOF > 1.0 = lower density than neighbours = outlier.
      WHY it detects AML: catches local density anomalies — a customer with an
      unusual combination relative to similar customers, even if not globally
      extreme. Complements IF's global isolation approach.

    Explainability (documented):
      §6.3: "per-feature z-scores as a lightweight explainability proxy."
      §5.4: "IsolationForest path-length attribution OR simple feature z-scores."
      Implementation uses per-feature z-scores (zscore_proxy) as they are
      deterministic and auditable without requiring tree internals.

    IMPLEMENTATION ASSUMPTIONS (externalized to ml_detection_config.yaml):
    - IF hyperparameters: n_estimators, contamination, random_state (for
      deterministic outputs as required by §3.1 principle 4).
    - LOF hyperparameters: n_neighbors, contamination.
    - Score combination method: "mean" of normalised IF and LOF scores.
    - Normalisation: min-max normalisation of raw scores to [0, 1]; then flip
      so high = anomalous. This is an implementation interpretation since §5.4
      specifies "0–1" range but not the normalisation formula.

    Args:
        features_df: Per-customer engineered features DataFrame from the
            Feature Engineering Tool. Must contain a "customer_id" column.
            All other numeric columns are treated as features.

    Returns:
        Dict with:
          - method_used: "ml"
          - algorithms_used: list of algorithm names
          - entities_scored: total customers evaluated
          - entities_flagged: customers flagged by combined score > threshold
          - flagged_entities: list of flagged entity dicts
          - all_entities: same structure for all customers
    """
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.neighbors import LocalOutlierFactor

    config = _load_ml_config()
    top_n = int(config["top_n_features"])
    score_combination = config["score_combination"]

    # IsolationForest config
    if_n_estimators = int(config["if_n_estimators"])
    if_contamination = config["if_contamination"]
    if_random_state = int(config["if_random_state"])

    # LOF config
    lof_contamination = config["lof_contamination"]

    if "customer_id" not in features_df.columns:
        raise ValueError(
            "ML detection: 'customer_id' column not found in features DataFrame."
        )

    feature_cols = [
        c for c in features_df.columns
        if c != "customer_id"
        and pd.api.types.is_numeric_dtype(features_df[c])
    ]

    if not feature_cols:
        raise ValueError(
            "ML detection: no numeric feature columns found in features DataFrame."
        )

    n_customers = len(features_df)

    # Normalise customer_id (same logic as statistical path)
    customer_ids = []
    for raw_cid in features_df["customer_id"]:
        try:
            customer_ids.append(str(int(float(raw_cid))))
        except (ValueError, TypeError):
            customer_ids.append(str(raw_cid))

    # Build feature matrix (fill NaN with 0)
    X = features_df[feature_cols].fillna(0).values.astype(float)

    # --- Cohort-level statistics for z-score proxy explainability ---
    # DOCUMENTED: "per-feature z-scores as a lightweight explainability proxy"
    feature_means = X.mean(axis=0)
    feature_stds = X.std(axis=0, ddof=1)
    # Avoid division by zero: features with zero std contribute no variation
    feature_stds_safe = np.where(feature_stds == 0, 1.0, feature_stds)

    # --- IsolationForest (documented algorithm) ---
    # random_state is required for deterministic outputs (§3.1 principle 4).
    clf_if = IsolationForest(
        n_estimators=if_n_estimators,
        contamination=if_contamination,
        random_state=if_random_state,
    )
    clf_if.fit(X)
    if_scores_raw = clf_if.decision_function(X)  # lower = more anomalous

    # Normalise to [0, 1] and flip: high = anomalous
    if_range = if_scores_raw.max() - if_scores_raw.min()
    if if_range > 1e-9:
        if_scores = 1.0 - (if_scores_raw - if_scores_raw.min()) / if_range
    else:
        if_scores = np.zeros(n_customers)

    # --- LocalOutlierFactor (documented algorithm) ---
    # n_neighbors must be < n_samples; cap at n_customers - 1 for small cohorts.
    # IMPLEMENTATION ASSUMPTION: externalized to config, capped here for safety.
    lof_n_neighbors_raw = int(config["lof_n_neighbors"])
    lof_n_neighbors = max(1, min(lof_n_neighbors_raw, n_customers - 1))

    clf_lof = LocalOutlierFactor(
        n_neighbors=lof_n_neighbors,
        contamination=lof_contamination,
        novelty=False,
    )
    clf_lof.fit_predict(X)
    lof_scores_raw = clf_lof.negative_outlier_factor_  # more negative = more anomalous

    # Normalise to [0, 1] and flip: high = anomalous
    lof_range = lof_scores_raw.max() - lof_scores_raw.min()
    if lof_range > 1e-9:
        lof_scores = 1.0 - (lof_scores_raw - lof_scores_raw.min()) / lof_range
    else:
        lof_scores = np.zeros(n_customers)

    # --- Combine scores (IMPLEMENTATION ASSUMPTION: see config) ---
    if score_combination == "mean":
        combined_scores = (if_scores + lof_scores) / 2.0
    elif score_combination == "max":
        combined_scores = np.maximum(if_scores, lof_scores)
    elif score_combination == "if_only":
        combined_scores = if_scores
    elif score_combination == "lof_only":
        combined_scores = lof_scores
    else:
        combined_scores = (if_scores + lof_scores) / 2.0

    # Determine flagged entities using IF's predict for consistency.
    # IMPLEMENTATION INTERPRETATION: IF's predict() uses the contamination
    # parameter to calibrate its own threshold (returning -1 for anomalies,
    # 1 for normal). Using IF's own calibrated threshold is more principled
    # than applying an arbitrary cutoff to the combined anomaly_score.
    # This means a customer's flagged status is driven by IF's threshold,
    # while the anomaly_score is the combined metric (for ranking severity).
    # This interpretation is not specified in the documentation.
    if_predictions = clf_if.predict(X)  # -1 = anomaly, 1 = normal

    all_entities = []
    flagged_entities = []

    for idx, customer_id in enumerate(customer_ids):
        score = round(float(combined_scores[idx]), 4)
        # An entity is flagged if IF labels it as an anomaly (predict=-1)
        is_flagged = int(if_predictions[idx]) == -1

        # --- Per-feature z-score explainability proxy (DOCUMENTED) ---
        # §6.3: "per-feature z-scores as a lightweight explainability proxy"
        feature_zscores = (X[idx] - feature_means) / feature_stds_safe
        top_feature_indices = np.argsort(np.abs(feature_zscores))[::-1][:top_n]
        top_features = [
            {
                "feature": feature_cols[i],
                "value": round(float(X[idx][i]), 4),
                "z_score": round(float(feature_zscores[i]), 4),
            }
            for i in top_feature_indices
            if abs(feature_zscores[i]) > 0  # only include features with variation
        ]

        entity = {
            "customer_id": customer_id,
            "anomaly_score": score,
            "rule_matched": False,       # not applicable for ML
            "matched_condition": None,   # not applicable for ML
            "top_contributing_features": top_features,
            "if_score": round(float(if_scores[idx]), 4),
            "lof_score": round(float(lof_scores[idx]), 4),
            "if_flagged": is_flagged,
        }

        all_entities.append(entity)
        if is_flagged:
            flagged_entities.append(entity)

    return {
        "method_used": "ml",
        "algorithms_used": ["IsolationForest", "LocalOutlierFactor"],
        "features_used": feature_cols,
        "score_combination": score_combination,
        "entities_scored": n_customers,
        "entities_flagged": len(flagged_entities),
        "flagged_entities": flagged_entities,
        "all_entities": all_entities,
    }


# ---------------------------------------------------------------------------
# Main tool function (registered in ToolRegistry)
# ---------------------------------------------------------------------------


def anomaly_detection(context: dict[str, Any], **args: Any) -> dict[str, Any]:
    """Detect suspicious patterns using the specified method.

    Reference: Solution Design §5.4, Implementation Plan §6.3.

    This is the tool function registered in the ToolRegistry.

    Args:
        context: Shared execution context. Expected keys:
            - "data_loader": result dict from Data Loader containing
              "transactions" DataFrame.
            - "query_spec": dict with explicit_rule sub-dict.
        **args: Arguments from the ExecutionPlan step:
            - method: str — detection method to use.
              "rule_engine": deterministic threshold/count logic.
              "statistical", "ml", "hybrid": not yet implemented.
            - target_pattern: str — AML pattern being targeted (for logging).

    Returns:
        Dict with:
            - tool: "anomaly_detection"
            - status: "success"
            - method_used: which method was applied
            - condition_evaluated: condition string (rule_engine only)
            - entities_scored: total entities evaluated
            - entities_flagged: entities above threshold
            - flagged_entities: list of flagged entity dicts
            - all_entities: list of all entity dicts (flagged + clean)
    """
    method = args.get("method", "rule_engine")
    target_pattern = args.get("target_pattern", None)

    # Resolve transactions DataFrame from context
    data_loader_result = context.get("data_loader", {})
    if isinstance(data_loader_result, dict) and "transactions" in data_loader_result:
        df = data_loader_result["transactions"]
    else:
        df = context.get("transactions")

    if df is None or not isinstance(df, pd.DataFrame):
        return {
            "tool": "anomaly_detection",
            "status": "error",
            "error": "No transactions DataFrame found in context.",
        }

    if method == "rule_engine":
        # Resolve the condition from the QuerySpec
        query_spec = context.get("query_spec", {})
        if isinstance(query_spec, dict):
            explicit_rule = query_spec.get("explicit_rule", {})
        else:
            # QuerySpec may be a Pydantic model if coming from the controller
            try:
                explicit_rule = query_spec.explicit_rule.model_dump()
            except AttributeError:
                explicit_rule = {}

        condition = explicit_rule.get("condition") if isinstance(explicit_rule, dict) else None
        rule_present = explicit_rule.get("present", False) if isinstance(explicit_rule, dict) else False

        if not rule_present or not condition:
            return {
                "tool": "anomaly_detection",
                "status": "error",
                "error": (
                    "Rule engine called but explicit_rule.present is False or "
                    "explicit_rule.condition is missing in QuerySpec."
                ),
            }

        result = _run_rule_engine(df, condition)
        return {
            "tool": "anomaly_detection",
            "status": "success",
            "target_pattern": target_pattern,
            **result,
        }

    elif method == "statistical":
        # The statistical path operates on the per-customer features DataFrame
        # from the Feature Engineering Tool, not on raw transactions.
        # Implementation interpretation #4 (see module docstring).
        fe_result = context.get("feature_engineering", {})
        if isinstance(fe_result, dict) and "features_df" in fe_result:
            features_df = fe_result["features_df"]
        else:
            return {
                "tool": "anomaly_detection",
                "status": "error",
                "error": (
                    "Statistical detection requires feature_engineering output "
                    "in context (features_df). Run the Feature Engineering Tool "
                    "before the Statistical Anomaly Detection method."
                ),
            }

        if not isinstance(features_df, pd.DataFrame) or features_df.empty:
            return {
                "tool": "anomaly_detection",
                "status": "error",
                "error": "features_df is empty or not a DataFrame.",
            }

        result = _run_statistical_detection(features_df)
        return {
            "tool": "anomaly_detection",
            "status": "success",
            "target_pattern": target_pattern,
            **result,
        }

    elif method == "ml":
        # The ML path operates on the per-customer features DataFrame
        # from the Feature Engineering Tool, not on raw transactions.
        fe_result = context.get("feature_engineering", {})
        if isinstance(fe_result, dict) and "features_df" in fe_result:
            features_df = fe_result["features_df"]
        else:
            return {
                "tool": "anomaly_detection",
                "status": "error",
                "error": (
                    "ML detection requires feature_engineering output in context "
                    "(features_df). Run the Feature Engineering Tool before the "
                    "ML Anomaly Detection method."
                ),
            }

        if not isinstance(features_df, pd.DataFrame) or features_df.empty:
            return {
                "tool": "anomaly_detection",
                "status": "error",
                "error": "features_df is empty or not a DataFrame.",
            }

        result = _run_ml_detection(features_df)
        return {
            "tool": "anomaly_detection",
            "status": "success",
            "target_pattern": target_pattern,
            **result,
        }

    else:
        # Hybrid path — not yet implemented in this task cycle
        return {
            "tool": "anomaly_detection",
            "status": "not_implemented",
            "method_used": method,
            "target_pattern": target_pattern,
            "error": (
                f"Method '{method}' is not yet implemented. "
                "Implemented methods: rule_engine, statistical, ml"
            ),
        }
