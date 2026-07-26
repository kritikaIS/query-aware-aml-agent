"""Feature Engineering Tool.

Reference: Solution Design §5.3, Implementation Plan §6.2.

Purpose: Construct AML-relevant, pattern-specific features on demand
rather than one giant fixed feature table.

Architecture:
- Each feature family is an independent function keyed by name.
- The planner requests feature_set="structuring" etc. without computing
  unrelated features.
- This module implements the structuring/smurfing, velocity, layering, and
  amount_deviation families. All documented feature families are complete.

Structuring/Smurfing features (Solution Design §5.3, documented):
- Count of transactions just below reporting threshold (e.g. $10,000)
  per rolling 24h/7d/30d window.
- Ratio of near-threshold transactions to total transactions per customer.

Velocity features (Solution Design §5.3, documented):
- Transaction frequency per customer per time bucket.
- Inter-transaction time deltas.

Documentation compliance notes (audit findings):
1. `reporting_threshold` ($10,000) is a DOCUMENTED value (Solution Design §5.3).
2. `near_threshold_lower_bound_ratio` (defines "just below") is NOT specified
   in the documentation. It is an implementation assumption, externalized to
   src/config/structuring_thresholds.yaml.
3. Velocity time buckets (24h/7d/30d) are NOT explicitly named in the docs.
   They are an implementation assumption, externalized to
   src/config/velocity_config.yaml.
4. Velocity delta statistics (mean/min/max in seconds) are NOT specified in
   the docs — "inter-transaction time deltas" is the only specification.
   These are implementation assumptions, externalized to velocity_config.yaml
   under delta_statistics and delta_unit. Adding/removing a statistic only
   requires a config change, not a code change.
5. "Per rolling window" aggregation (max over all windows) is an interpretation,
   documented explicitly in _rolling_max_count_and_total().
6. Several aggregate features (total_txn_count, total_near_threshold_count,
   near_threshold_ratio_overall) are NOT documented. They are classified as
   enhancements and isolated via ENHANCEMENT_FEATURE_COLUMNS.
7. All rolling-window computation uses pandas time-based .rolling() to avoid
   platform-dependent datetime64 storage unit issues.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_CONFIG_PATH = _CONFIG_DIR / "structuring_thresholds.yaml"
_VELOCITY_CONFIG_PATH = _CONFIG_DIR / "velocity_config.yaml"


def _load_structuring_config() -> dict[str, float]:
    """Load structuring feature thresholds from configuration.

    reporting_threshold: DOCUMENTED (Solution Design §5.3, "e.g. $10,000").
    near_threshold_lower_bound_ratio: IMPLEMENTATION ASSUMPTION, externalized
        here rather than hardcoded, since the documentation does not specify
        a precise quantitative definition of "just below."
    """
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _load_velocity_config() -> dict:
    """Load velocity feature configuration.

    time_buckets: IMPLEMENTATION ASSUMPTION — not named in the docs.
        Documentation says "per time bucket" without specifying which buckets.
    delta_unit: IMPLEMENTATION ASSUMPTION — not specified in the docs.
        Documentation says "inter-transaction time deltas" without naming a unit.
    """
    with open(_VELOCITY_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# Rolling window durations for structuring detection.
# DOCUMENTED: Solution Design §5.3 and Implementation Plan §6.2 explicitly
# specify "rolling 24h/7d/30d window." Expressed as pandas offset-alias
# strings so they can be passed directly to pandas time-based .rolling().
ROLLING_WINDOWS: dict[str, str] = {
    "24h": "24h",
    "7d": "7D",
    "30d": "30D",
}

# Feature columns explicitly documented in Solution Design §5.3 /
# Implementation Plan §6.2 (windowed near-threshold count + ratio).
DOCUMENTED_FEATURE_COLUMNS: list[str] = [
    f"near_threshold_txn_count_{w}" for w in ROLLING_WINDOWS
] + [
    f"near_threshold_txn_ratio_{w}" for w in ROLLING_WINDOWS
]

# Feature columns NOT documented — added as enhancements during initial
# implementation, kept isolated so downstream consumers can distinguish
# documented vs. non-documented output.
ENHANCEMENT_FEATURE_COLUMNS: list[str] = [
    "total_txn_count",
    "total_near_threshold_count",
    "near_threshold_ratio_overall",
]


# ---------------------------------------------------------------------------
# Feature family registry (internal)
# ---------------------------------------------------------------------------

_FEATURE_FAMILIES: dict[str, Any] = {}


def _register_family(name: str):
    """Decorator to register a feature family function by name."""
    def decorator(fn):
        _FEATURE_FAMILIES[name] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Structuring / Smurfing Feature Family
# ---------------------------------------------------------------------------


@_register_family("structuring")
def _compute_structuring_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute structuring/smurfing features per customer.

    Reference: Solution Design §5.3, Implementation Plan §6.2 step 2.

    Documented features computed per customer:
    - near_threshold_txn_count_{window}: max count of near-threshold
      transactions in any rolling window of that duration.
    - near_threshold_txn_ratio_{window}: max_count / total-in-window at
      the same window placement.

    Enhancement features (not in documentation, isolated):
    - total_txn_count, total_near_threshold_count, near_threshold_ratio_overall.

    Args:
        df: Preprocessed transactions DataFrame from Data Loader.
            Must contain: customer_id, timestamp, amount_normalized.

    Returns:
        DataFrame with one row per customer_id and the engineered feature columns.
    """
    required_cols = ["customer_id", "timestamp", "amount_normalized"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns for structuring features: {missing}"
        )

    config = _load_structuring_config()
    threshold = config["reporting_threshold"]
    lower_bound_ratio = config["near_threshold_lower_bound_ratio"]
    lower_bound = threshold * lower_bound_ratio

    df = df.copy()
    df["_is_near_threshold"] = (
        (df["amount_normalized"] >= lower_bound)
        & (df["amount_normalized"] < threshold)
    ).astype(int)

    df = df.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)

    grouped = df.groupby("customer_id")

    results = []
    for customer_id, group in grouped:
        row: dict[str, Any] = {"customer_id": customer_id}

        # --- Enhancement features (NOT documented, isolated) ---
        total_txn_count = len(group)
        total_near_threshold = int(group["_is_near_threshold"].sum())
        row["total_txn_count"] = total_txn_count
        row["total_near_threshold_count"] = total_near_threshold
        row["near_threshold_ratio_overall"] = (
            total_near_threshold / total_txn_count
            if total_txn_count > 0
            else 0.0
        )

        # --- Documented features: rolling window count + ratio ---
        for window_name, window_alias in ROLLING_WINDOWS.items():
            max_count, max_total = _rolling_max_count_and_total(
                group, window_alias
            )
            max_ratio = (max_count / max_total) if max_total > 0 else 0.0

            row[f"near_threshold_txn_count_{window_name}"] = max_count
            row[f"near_threshold_txn_ratio_{window_name}"] = round(max_ratio, 4)

        results.append(row)

    if not results:
        return pd.DataFrame(
            columns=["customer_id"] + ENHANCEMENT_FEATURE_COLUMNS + DOCUMENTED_FEATURE_COLUMNS
        )

    return pd.DataFrame(results)


def _rolling_max_count_and_total(
    group: pd.DataFrame,
    window_alias: str,
) -> tuple[int, int]:
    """Find the maximum near-threshold count and total count in any
    rolling window of the given duration, using pandas time-based rolling.

    INTERPRETATION NOTE (not an explicit documented requirement):
    The documentation ("rolling-window count... per window") does not state
    how to aggregate across all possible window placements in a customer's
    transaction history. This implementation takes the MAXIMUM count/ratio
    found in any window of the given duration — i.e., the worst-case burst.
    Rationale: for AML burst detection, averaging would dilute a genuine
    structuring burst with quiet periods; the maximum surfaces the most
    suspicious interval, consistent with standard transaction-monitoring
    practice for burst/velocity detection.

    Implementation note: uses pandas time-based `.rolling(window_alias)`
    on a DatetimeIndex, which internally handles datetime64 unit conversion
    (us/ns/ms) safely. This avoids manual int64 arithmetic that depends on
    the platform/numpy-version-specific storage resolution of datetime64
    arrays (a class of bug previously encountered and fixed in this project).

    pandas time-based rolling windows are right-closed and backward-looking
    by default: for each row at time t, the window covers (t - window, t].
    Sliding this window's right edge across every transaction timestamp is
    equivalent to sliding a forward-looking window's left edge across every
    timestamp, for the purpose of finding the maximum count in any window
    of fixed duration (the window can always be shifted to align its edge
    with a data point without changing the maximum achievable count).

    Args:
        group: Transactions for a single customer, sorted by timestamp,
            containing at least "timestamp" and "_is_near_threshold" columns.
        window_alias: pandas offset alias string (e.g. "24h", "7D", "30D").

    Returns:
        Tuple of (max_near_threshold_count, max_total_count) across all
        rolling window placements.
    """
    if len(group) == 0:
        return 0, 0

    indexed = group.set_index("timestamp")

    rolling_near_threshold_sum = indexed["_is_near_threshold"].rolling(
        window_alias
    ).sum()
    rolling_total_count = indexed["_is_near_threshold"].rolling(
        window_alias
    ).count()

    max_count = int(rolling_near_threshold_sum.max())
    max_total = int(rolling_total_count.max())

    return max_count, max_total


# ---------------------------------------------------------------------------
# Velocity Feature Family
# ---------------------------------------------------------------------------

# DOCUMENTED velocity feature columns (Solution Design §5.3):
#   txn_frequency_{bucket}: transaction count in the max window of that duration
#   inter_txn_delta_{stat}_seconds: statistics of consecutive transaction gaps
#
# IMPLEMENTATION ASSUMPTIONS (externalized to velocity_config.yaml):
#   - Bucket labels: 24h, 7d, 30d (not named in documentation)
#   - Delta statistics: mean, min, max (documentation says "deltas", plural)
#   - Delta unit: seconds (documentation does not specify)


@_register_family("velocity")
def _compute_velocity_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute velocity features per customer.

    Reference: Solution Design §5.3, Implementation Plan §6.2 step 3.

    DOCUMENTED features:
    - txn_frequency_{bucket}: maximum number of transactions observed for this
      customer within any single window of the given duration.
      "Transaction frequency per customer per time bucket." (§5.3)
    - inter_txn_delta_mean_seconds: mean of consecutive-transaction gaps in
      seconds.
    - inter_txn_delta_min_seconds: minimum gap (fastest back-to-back pair).
    - inter_txn_delta_max_seconds: maximum gap (longest dormant period).
      "Inter-transaction time deltas." (§5.3)

    IMPLEMENTATION ASSUMPTIONS (externalized to velocity_config.yaml):
    - Time buckets are 24h, 7d, 30d (consistent with structuring windows).
    - "Frequency per time bucket" is interpreted as the maximum count in any
      rolling window of that duration (same max-burst interpretation as
      structuring, documented as an interpretation, not a doc requirement).
    - Delta statistics are mean, min, max because "deltas" (plural) implies
      more than one statistic; these three are the most informative for AML.
    - Unit is seconds; externalized to config.

    Why these detect suspicious velocity:
    - High txn_frequency_24h → burst of transactions in a single day,
      characteristic of layering, smurfing, or coordinated rapid cash-out.
    - Low inter_txn_delta_min_seconds → two consecutive transactions nearly
      simultaneous; human behavior rarely produces sub-minute transaction pairs,
      suggesting automated or coordinated activity.
    - Low inter_txn_delta_mean_seconds → overall unusually rapid pacing,
      inconsistent with legitimate retail banking patterns.

    Args:
        df: Preprocessed transactions DataFrame from Data Loader.
            Must contain: customer_id, timestamp.

    Returns:
        DataFrame with one row per customer_id and velocity feature columns.
    """
    required_cols = ["customer_id", "timestamp"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns for velocity features: {missing}"
        )

    config = _load_velocity_config()
    buckets = config["time_buckets"]

    df = df.copy()
    df = df.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)

    grouped = df.groupby("customer_id")
    bucket_labels = [b["label"] for b in buckets]

    results = []
    for customer_id, group in grouped:
        row: dict[str, Any] = {"customer_id": customer_id}

        # --- Documented: transaction frequency per time bucket ---
        # Uses pandas time-based rolling on the DatetimeIndex.
        # For each bucket window, compute the maximum number of transactions
        # in any single window of that duration (worst-case burst).
        for bucket in buckets:
            label = bucket["label"]
            hours = bucket["hours"]
            window_alias = f"{hours}h"

            indexed = group.set_index("timestamp")
            # Rolling count: each row i counts how many transactions fall
            # within [timestamp_i - window, timestamp_i]
            rolling_counts = (
                indexed["customer_id"].rolling(window_alias).count()
            )
            max_freq = int(rolling_counts.max()) if len(rolling_counts) > 0 else 0
            row[f"txn_frequency_{label}"] = max_freq

        # --- Documented: inter-transaction time deltas ---
        # Uses pandas Timedelta arithmetic — platform-independent.
        # Which statistics are computed is driven by delta_statistics in config.
        timestamps = group["timestamp"].sort_values().reset_index(drop=True)
        if len(timestamps) >= 2:
            deltas_seconds = timestamps.diff().dropna().dt.total_seconds()
            stat_fns = {
                "mean": lambda s: round(float(s.mean()), 2),
                "min":  lambda s: round(float(s.min()), 2),
                "max":  lambda s: round(float(s.max()), 2),
            }
            for stat in config["delta_statistics"]:
                if stat in stat_fns:
                    row[f"inter_txn_delta_{stat}_seconds"] = stat_fns[stat](deltas_seconds)
                else:
                    raise ValueError(
                        f"Unsupported delta statistic '{stat}' in velocity_config.yaml. "
                        f"Supported: {list(stat_fns.keys())}"
                    )
        else:
            # Single transaction: no consecutive pair exists; delta is undefined.
            for stat in config["delta_statistics"]:
                row[f"inter_txn_delta_{stat}_seconds"] = None

        results.append(row)

    expected_cols = (
        ["customer_id"]
        + [f"txn_frequency_{lbl}" for lbl in bucket_labels]
        + [f"inter_txn_delta_{stat}_seconds" for stat in config["delta_statistics"]]
    )

    if not results:
        return pd.DataFrame(columns=expected_cols)

    return pd.DataFrame(results)


# Velocity documented and enhancement columns (for the tool return dict).
# Populated here after the family function is defined so the column names
# match bucket labels from config.
def _velocity_documented_columns() -> list[str]:
    """Return documented velocity feature column names, driven by config."""
    config = _load_velocity_config()
    buckets = config["time_buckets"]
    delta_stats = config["delta_statistics"]
    return (
        [f"txn_frequency_{b['label']}" for b in buckets]
        + [f"inter_txn_delta_{stat}_seconds" for stat in delta_stats]
    )


# ---------------------------------------------------------------------------
# Layering Feature Family
# ---------------------------------------------------------------------------


def _load_layering_config() -> dict:
    """Load layering feature configuration from layering_config.yaml.

    All keys are IMPLEMENTATION ASSUMPTIONS not specified in the documentation.
    See layering_config.yaml for full rationale per key.
    """
    config_path = _CONFIG_DIR / "layering_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@_register_family("layering")
def _compute_layering_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute layering features per customer.

    Reference: Solution Design §5.3, Implementation Plan §6.2 step 4.
    Library: networkx (documented in Impl Plan §6.2 "Libraries: networkx").

    DOCUMENTED features:
    - direct_counterparty_count: approximation of "counterparty network depth /
      hop count" (Solution Design §5.3) and "counterparty network hop-count"
      (Impl Plan §6.2 step 4). Named direct_counterparty_count because the
      schema provides only 1-hop data; the column counts distinct direct
      counterparties rather than shortest-path depth. Full rationale in
      layering_config.yaml under hop_count_interpretation.
    - fan_in_ratio: "fan-in / fan-out ratios" (Solution Design §5.3,
      Impl Plan §6.2 step 4). Fan-in = fraction of transactions where
      the customer receives funds.
    - fan_out_ratio: "fan-in / fan-out ratios" (Solution Design §5.3,
      Impl Plan §6.2 step 4). Fan-out = fraction of transactions where
      the customer sends funds.
    - passthrough_ratio: "rapid pass-through balance (funds in ≈ funds out
      within short window)" (Solution Design §5.3). Continuous value in [0, 1];
      a value close to 1.0 indicates near-equal in/out within the window.

    IMPLEMENTATION ASSUMPTIONS (externalized to layering_config.yaml):
    - "hop count" is implemented as the count of distinct direct counterparties.
      The transaction schema provides only counterparty_id (one hop depth);
      multi-hop traversal requires counterparty-to-counterparty data not in
      this schema. Documented in layering_config.yaml under
      hop_count_interpretation.
    - "rapid" window for pass-through = passthrough_window_hours from config.
    - "≈" for funds in ≈ funds out = passthrough_tolerance from config.
      Implemented as min(in, out) / max(in, out) >= tolerance within window.
    - incoming_transaction_types and outgoing_transaction_types define which
      transaction_type values count as funds-in vs. funds-out; externalized
      to config.

    Why these detect layering:
    - High direct_counterparty_count: laundering moves funds through many
      intermediate accounts. Many distinct counterparties = wide network
      exposure, characteristic of layering.
    - High fan_out_ratio: a customer who sends to many recipients rapidly
      is distributing funds, a core layering behaviour.
    - High fan_in_ratio: a customer who receives from many sources acts as
      an aggregator in the layering chain.
    - passthrough_ratio near 1.0: the customer is a mere conduit —
      money arrives and leaves at roughly equal amounts within a short
      window, not consistent with legitimate accumulation.

    The counterparty graph is built with networkx per documented library
    requirement (Impl Plan §6.2), then graph metrics are extracted
    deterministically.

    Args:
        df: Preprocessed transactions DataFrame from Data Loader.
            Must contain: customer_id, transaction_type, counterparty_id,
            timestamp, amount_normalized.

    Returns:
        DataFrame with one row per customer_id and layering feature columns.
    """
    import networkx as nx

    required_cols = ["customer_id", "transaction_type", "counterparty_id",
                     "timestamp", "amount_normalized"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns for layering features: {missing}"
        )

    config = _load_layering_config()
    incoming_types = set(t.lower() for t in config["incoming_transaction_types"])
    outgoing_types = set(t.lower() for t in config["outgoing_transaction_types"])
    passthrough_window = pd.Timedelta(hours=config["passthrough_window_hours"])
    passthrough_tolerance = config["passthrough_tolerance"]

    df = df.copy()
    df["_txn_type_lower"] = df["transaction_type"].str.lower().fillna("unknown")
    df = df.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)

    grouped = df.groupby("customer_id")

    results = []
    for customer_id, group in grouped:
        row: dict[str, Any] = {"customer_id": customer_id}

        # --- Documented: direct_counterparty_count ---
        # Build directed graph with networkx (documented library).
        # Nodes: customer + counterparties. Edges: direction of each transaction.
        #
        # NAMING INTERPRETATION NOTE:
        # Solution Design §5.3 says "counterparty network depth / hop count"
        # and Impl Plan §6.2 says "counterparty network hop-count."
        # A true "hop count" (shortest-path depth) requires counterparty-to-
        # counterparty edge data, which the transaction schema does not provide.
        # The schema only exposes one hop: customer → direct counterparty.
        # Therefore this feature is computed as the count of distinct DIRECT
        # counterparties (1-hop neighbors in the graph), which is the closest
        # measurable approximation given the available data.
        # The column is named direct_counterparty_count to be technically
        # accurate rather than misrepresenting it as a multi-hop depth measure.
        # This interpretation is documented in layering_config.yaml under
        # hop_count_interpretation.
        G = nx.DiGraph()
        G.add_node(str(customer_id))

        for _, txn in group.iterrows():
            cp = str(txn["counterparty_id"])
            if cp and cp.lower() not in ("unknown", "nan", "none", ""):
                G.add_node(cp)
                txn_type = txn["_txn_type_lower"]
                if txn_type in outgoing_types:
                    G.add_edge(str(customer_id), cp)
                elif txn_type in incoming_types:
                    G.add_edge(cp, str(customer_id))

        # Distinct direct counterparties = neighbors in either direction
        out_neighbors = set(G.successors(str(customer_id)))
        in_neighbors = set(G.predecessors(str(customer_id)))
        distinct_counterparties = out_neighbors | in_neighbors
        row["direct_counterparty_count"] = len(distinct_counterparties)

        # --- Documented: fan_in_ratio and fan_out_ratio ---
        total_txns = len(group)
        incoming_count = int(
            (group["_txn_type_lower"].isin(incoming_types)).sum()
        )
        outgoing_count = int(
            (group["_txn_type_lower"].isin(outgoing_types)).sum()
        )

        row["fan_in_ratio"] = (
            round(incoming_count / total_txns, 4) if total_txns > 0 else 0.0
        )
        row["fan_out_ratio"] = (
            round(outgoing_count / total_txns, 4) if total_txns > 0 else 0.0
        )

        # --- Documented: passthrough_ratio ---
        # For each transaction as a window start, sum incoming and outgoing
        # amounts within [t, t + window]. Compute min/max ratio.
        # Report the maximum passthrough_ratio found across all windows.
        row["passthrough_ratio"] = _max_passthrough_ratio(
            group, passthrough_window, incoming_types, outgoing_types
        )

        results.append(row)

    expected_cols = [
        "customer_id",
        "direct_counterparty_count",
        "fan_in_ratio",
        "fan_out_ratio",
        "passthrough_ratio",
    ]

    if not results:
        return pd.DataFrame(columns=expected_cols)

    return pd.DataFrame(results)


def _max_passthrough_ratio(
    group: pd.DataFrame,
    window: pd.Timedelta,
    incoming_types: set,
    outgoing_types: set,
) -> float:
    """Compute the maximum pass-through ratio over all rolling windows.

    For each transaction as the start of a window, sums the incoming and
    outgoing amounts within [t, t + window]. The pass-through ratio for
    that window is:
        min(amount_in, amount_out) / max(amount_in, amount_out)

    Returns the maximum ratio found across all window placements.
    A value near 1.0 means the customer consistently receives and
    immediately sends nearly the same amount — a conduit / pass-through.
    A value of 0.0 is returned if no window has both incoming and outgoing
    transactions, or if the group is empty.

    INTERPRETATION NOTE: "rapid pass-through balance (funds in ≈ funds out
    within short window)" does not specify whether to report the maximum,
    average, or a per-window value. Maximum is chosen to surface the most
    suspicious window (same rationale as structuring and velocity families).
    This is an implementation interpretation, not a documented requirement.

    Uses pandas Timedelta arithmetic — platform-independent and safe across
    numpy datetime64 storage resolutions (us/ns/ms).
    """
    if len(group) == 0:
        return 0.0

    sorted_group = group.sort_values("timestamp").reset_index(drop=True)
    timestamps = sorted_group["timestamp"]
    amounts = sorted_group["amount_normalized"]
    types = sorted_group["_txn_type_lower"]

    max_ratio = 0.0

    for i in range(len(sorted_group)):
        t_start = timestamps.iloc[i]
        t_end = t_start + window

        mask = (timestamps >= t_start) & (timestamps <= t_end)
        window_types = types[mask]
        window_amounts = amounts[mask]

        amount_in = float(
            window_amounts[window_types.isin(incoming_types)].sum()
        )
        amount_out = float(
            window_amounts[window_types.isin(outgoing_types)].sum()
        )

        if amount_in > 0 and amount_out > 0:
            ratio = min(amount_in, amount_out) / max(amount_in, amount_out)
            if ratio > max_ratio:
                max_ratio = ratio

    return round(max_ratio, 4)


def _layering_documented_columns() -> list[str]:
    """Return documented layering feature column names.

    direct_counterparty_count: approximation of the documented "counterparty
    network depth / hop count" (Solution Design §5.3). Named accurately to
    reflect that it counts 1-hop neighbors rather than multi-hop depth.
    See layering_config.yaml → hop_count_interpretation for rationale.
    """
    return [
        "direct_counterparty_count",
        "fan_in_ratio",
        "fan_out_ratio",
        "passthrough_ratio",
    ]


# ---------------------------------------------------------------------------
# Amount Deviation Feature Family
# ---------------------------------------------------------------------------


def _load_amount_deviation_config() -> dict:
    """Load amount deviation feature configuration from amount_deviation_config.yaml.

    All keys are IMPLEMENTATION ASSUMPTIONS not specified in the documentation.
    See amount_deviation_config.yaml for full rationale per key.
    """
    config_path = _CONFIG_DIR / "amount_deviation_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@_register_family("amount_deviation")
def _compute_amount_deviation_features(
    df_transactions: pd.DataFrame,
    df_customers: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute amount deviation features per customer.

    Reference: Solution Design §5.3, Implementation Plan §6.2 step 5.
    Libraries: pandas, numpy (documented in Impl Plan §6.2).

    DOCUMENTED features:
    - customer_amount_zscore_{agg}: z-score of each transaction amount
      vs. that customer's own historical mean/std, summarised per customer.
      "z-score of transaction amount vs. that customer's historical mean/std"
      (Solution Design §5.3, Impl Plan §6.2 step 5).
    - segment_amount_zscore_{agg}: z-score of each transaction amount
      vs. the customer's segment peer-group mean/std, summarised per customer.
      "deviation from peer-group (segment) norms"
      (Solution Design §5.3, Impl Plan §6.2 step 5).

    IMPLEMENTATION ASSUMPTIONS (externalized to amount_deviation_config.yaml):
    - "historical" means all transactions in the filtered dataset passed to
      this function (consistent with how all other families operate on the
      already-filtered Data Loader output).
    - Per-transaction z-scores are summarised per customer using aggregations
      from config (zscore_aggregations: mean, max). Adding/removing an
      aggregation changes the feature columns.
    - use_absolute_zscore: True means |z| is aggregated; False preserves sign.
    - min_transactions_for_customer_zscore: minimum transactions for a customer
      to have non-zero std; below this threshold, 0.0 is returned.
    - min_transactions_for_segment_zscore: same for segment-level std.

    Why these features detect AML:
    - High customer_amount_zscore_max: one transaction is dramatically different
      from this customer's own pattern — sudden large amount inconsistent with
      account history, a classic money-placement signal.
    - High segment_amount_zscore_max: transaction is dramatically different from
      the customer's peer group — "wrong profile" transactions (e.g. a student
      making a $100,000 wire transfer) that blend-in at the individual level
      but stand out vs. peers.

    Args:
        df_transactions: Preprocessed transactions DataFrame from Data Loader.
            Must contain: customer_id, amount_normalized.
        df_customers: Optional customers DataFrame for segment join.
            Must contain: customer_id, segment if provided.
            If None, segment z-scores cannot be computed and will be 0.0.

    Returns:
        DataFrame with one row per customer_id and amount deviation columns.
    """
    import numpy as np

    required_cols = ["customer_id", "amount_normalized"]
    missing = [c for c in required_cols if c not in df_transactions.columns]
    if missing:
        raise ValueError(
            f"Missing required columns for amount deviation features: {missing}"
        )

    config = _load_amount_deviation_config()
    min_cust_txns = config["min_transactions_for_customer_zscore"]
    min_seg_txns = config["min_transactions_for_segment_zscore"]
    aggregations = config["zscore_aggregations"]
    use_abs = config["use_absolute_zscore"]

    df = df_transactions.copy()

    # --- Documented: per-customer z-score ---
    # For each customer, compute z-score of each transaction amount vs.
    # that customer's mean and std across all their transactions.
    customer_stats = (
        df.groupby("customer_id")["amount_normalized"]
        .agg(["mean", "std", "count"])
        .rename(columns={"mean": "_cust_mean", "std": "_cust_std",
                         "count": "_cust_count"})
    )
    df = df.merge(customer_stats, on="customer_id", how="left")

    # Compute per-transaction customer z-score
    # std = NaN when count = 1; treat as 0 deviation.
    df["_cust_zscore"] = 0.0
    mask = (
        (df["_cust_count"] >= min_cust_txns)
        & (df["_cust_std"].notna())
        & (df["_cust_std"] > 0)
    )
    df.loc[mask, "_cust_zscore"] = (
        (df.loc[mask, "amount_normalized"] - df.loc[mask, "_cust_mean"])
        / df.loc[mask, "_cust_std"]
    )
    if use_abs:
        df["_cust_zscore"] = df["_cust_zscore"].abs()

    # --- Documented: per-segment z-score ---
    # Join transactions with customers to get segment, then compute z-score
    # vs. segment (peer-group) mean and std.
    df["_segment"] = "unknown"

    if df_customers is not None and "segment" in df_customers.columns:
        seg_map = (
            df_customers[["customer_id", "segment"]]
            .drop_duplicates("customer_id")
            .set_index("customer_id")["segment"]
        )
        df["_segment"] = (
            df["customer_id"].map(seg_map).fillna("unknown")
        )

    segment_stats = (
        df.groupby("_segment")["amount_normalized"]
        .agg(["mean", "std", "count"])
        .rename(columns={"mean": "_seg_mean", "std": "_seg_std",
                         "count": "_seg_count"})
    )
    df = df.merge(segment_stats, on="_segment", how="left")

    df["_seg_zscore"] = 0.0
    seg_mask = (
        (df["_seg_count"] >= min_seg_txns)
        & (df["_seg_std"].notna())
        & (df["_seg_std"] > 0)
    )
    df.loc[seg_mask, "_seg_zscore"] = (
        (df.loc[seg_mask, "amount_normalized"] - df.loc[seg_mask, "_seg_mean"])
        / df.loc[seg_mask, "_seg_std"]
    )
    if use_abs:
        df["_seg_zscore"] = df["_seg_zscore"].abs()

    # --- Aggregate per customer ---
    agg_fns = {
        "mean": lambda s: round(float(s.mean()), 4),
        "max":  lambda s: round(float(s.max()), 4),
    }

    results = []
    for customer_id, group in df.groupby("customer_id"):
        row: dict[str, Any] = {"customer_id": customer_id}
        for agg in aggregations:
            if agg in agg_fns:
                row[f"customer_amount_zscore_{agg}"] = agg_fns[agg](
                    group["_cust_zscore"]
                )
                row[f"segment_amount_zscore_{agg}"] = agg_fns[agg](
                    group["_seg_zscore"]
                )
            else:
                raise ValueError(
                    f"Unsupported zscore aggregation '{agg}' in "
                    f"amount_deviation_config.yaml. Supported: {list(agg_fns.keys())}"
                )
        results.append(row)

    agg_cols = [f"customer_amount_zscore_{a}" for a in aggregations] + [
        f"segment_amount_zscore_{a}" for a in aggregations
    ]
    expected_cols = ["customer_id"] + agg_cols

    if not results:
        return pd.DataFrame(columns=expected_cols)

    return pd.DataFrame(results)


def _amount_deviation_documented_columns() -> list[str]:
    """Return documented amount deviation feature column names, driven by config."""
    config = _load_amount_deviation_config()
    aggregations = config["zscore_aggregations"]
    return (
        [f"customer_amount_zscore_{a}" for a in aggregations]
        + [f"segment_amount_zscore_{a}" for a in aggregations]
    )


# ---------------------------------------------------------------------------
# Main tool function (registered in ToolRegistry)
# ---------------------------------------------------------------------------


def feature_engineering(context: dict[str, Any], **args: Any) -> dict[str, Any]:
    """Generate pattern-specific AML features.

    This is the tool function registered in the ToolRegistry.
    It dispatches to the appropriate feature family function based on
    the 'feature_set' argument from the ExecutionPlan.

    Args:
        context: Shared execution context. Expected keys:
            - "data_loader" or "transactions": DataFrame from Data Loader output.
        **args: Arguments from the ExecutionPlan step:
            - feature_set: str — which feature family to compute
              (currently only "structuring" is implemented).

    Returns:
        Dict with:
            - tool: "feature_engineering"
            - status: "success"
            - feature_set: which family was computed
            - features_computed: documented feature column names
            - enhancement_features_computed: non-documented feature column
              names, kept isolated from the documented feature set
            - features_df: DataFrame with all engineered features per customer
            - entities_processed: number of unique customers
    """
    feature_set = args.get("feature_set", "structuring")

    if feature_set not in _FEATURE_FAMILIES:
        available = list(_FEATURE_FAMILIES.keys())
        return {
            "tool": "feature_engineering",
            "status": "error",
            "error": (
                f"Feature set '{feature_set}' is not implemented. "
                f"Available: {available}"
            ),
        }

    # The Data Loader places its output under the "data_loader" key,
    # which contains a "transactions" sub-key with the DataFrame.
    data_loader_result = context.get("data_loader", {})
    if isinstance(data_loader_result, dict) and "transactions" in data_loader_result:
        df = data_loader_result["transactions"]
    else:
        df = context.get("transactions")

    if df is None or not isinstance(df, pd.DataFrame):
        return {
            "tool": "feature_engineering",
            "status": "error",
            "error": "No transactions DataFrame found in context.",
        }

    family_fn = _FEATURE_FAMILIES[feature_set]

    # amount_deviation requires both transactions and customers DataFrames
    # (for segment join). All other families receive transactions only.
    if feature_set == "amount_deviation":
        # Resolve customers DataFrame from context
        data_loader_result = context.get("data_loader", {})
        if isinstance(data_loader_result, dict) and "customers" in data_loader_result:
            df_customers = data_loader_result["customers"]
        else:
            df_customers = context.get("customers")
        features_df = family_fn(df, df_customers)
    else:
        features_df = family_fn(df)

    all_feature_columns = [c for c in features_df.columns if c != "customer_id"]

    if feature_set == "structuring":
        documented = [c for c in all_feature_columns if c in DOCUMENTED_FEATURE_COLUMNS]
        enhancements = [c for c in all_feature_columns if c in ENHANCEMENT_FEATURE_COLUMNS]
    elif feature_set == "velocity":
        vel_doc_cols = _velocity_documented_columns()
        documented = [c for c in all_feature_columns if c in vel_doc_cols]
        enhancements = []
    elif feature_set == "layering":
        lay_doc_cols = _layering_documented_columns()
        documented = [c for c in all_feature_columns if c in lay_doc_cols]
        enhancements = []
    elif feature_set == "amount_deviation":
        dev_doc_cols = _amount_deviation_documented_columns()
        documented = [c for c in all_feature_columns if c in dev_doc_cols]
        enhancements = []
    else:
        # Future families: all columns classified as documented by default.
        documented = all_feature_columns
        enhancements = []

    return {
        "tool": "feature_engineering",
        "status": "success",
        "feature_set": feature_set,
        "features_computed": documented,
        "enhancement_features_computed": enhancements,
        "features_df": features_df,
        "entities_processed": len(features_df),
    }
