"""Data Loader & Preprocessing Tool.

Reference: Solution Design §5.1, §6.1; Implementation Plan §6.1.

Responsibilities:
1. Load raw transaction/customer CSV data.
2. Apply column mapping from column_mapping.yaml to normalize arbitrary
   source column names to the internal schema.
3. Type coercion: timestamps to UTC, amounts to float64.
4. Currency normalization: convert all amounts to base currency (USD)
   using a static FX lookup table.
5. Apply filters from QuerySpec (date_range, customer_id, segment,
   country, transaction_type) at load time so downstream tools only
   see the minimal relevant slice.
6. Deduplication of identical rows.
7. Null handling (drop rows with critical nulls, impute non-critical).
8. Emit a preprocessing_log for auditability.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yaml


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_yaml(path: Path) -> dict:
    """Load a YAML config file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _load_column_mapping() -> dict[str, dict[str, list[str]]]:
    """Load column_mapping.yaml."""
    return _load_yaml(_CONFIG_DIR / "column_mapping.yaml")


def _load_fx_rates() -> tuple[str, dict[str, float]]:
    """Load static FX rates from fx_rates.yaml.

    Returns:
        Tuple of (base_currency, {currency_code: rate_to_base}).
    """
    config = _load_yaml(_CONFIG_DIR / "fx_rates.yaml")
    return config["base_currency"], config["rates"]


def _apply_column_mapping(
    df: pd.DataFrame, mapping: dict[str, list[str]]
) -> pd.DataFrame:
    """Rename DataFrame columns using the column mapping config.

    For each internal field name, find the first source column name
    that exists in the DataFrame and rename it.

    Args:
        df: Raw DataFrame with arbitrary column names.
        mapping: Dict of {internal_name: [possible_source_names]}.

    Returns:
        DataFrame with columns renamed to internal schema.
    """
    rename_map: dict[str, str] = {}
    existing_cols = set(df.columns)

    for internal_name, source_names in mapping.items():
        for source_name in source_names:
            if source_name in existing_cols and source_name not in rename_map:
                if source_name != internal_name:
                    rename_map[source_name] = internal_name
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def _normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Convert timestamp column to UTC datetime.

    Reference: Implementation Plan §6.1 step 1 — "timestamps to UTC".
    """
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def _normalize_currency(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize amounts to the base currency (USD) using static FX rates.

    Reference: Implementation Plan §6.1 step 2 — "currency normalization
    to a base currency using a static/lookup FX table for the demo."

    Preserves original columns untouched and adds normalization columns:
    - amount_original: original amount (unchanged copy of source 'amount').
    - currency_original: original currency code (unchanged copy of source 'currency').
    - fx_rate_used: the exchange rate applied from fx_rates.yaml.
    - amount_normalized: amount converted to base currency (amount × fx_rate_used).
    - base_currency: the base currency code (e.g., 'USD').

    The source 'amount' and 'currency' columns remain as-is.
    Downstream tools can fully trace the normalization:
      amount_normalized == amount × fx_rate_used
    """
    if "amount" not in df.columns or "currency" not in df.columns:
        return df

    base_currency, rates = _load_fx_rates()

    # Preserve originals explicitly
    df["amount_original"] = df["amount"].copy()
    df["currency_original"] = df["currency"].copy()

    # Look up the FX rate for each row's currency
    df["fx_rate_used"] = df["currency"].map(rates).fillna(1.0)

    # Compute normalized amount in base currency
    df["amount_normalized"] = (df["amount"] * df["fx_rate_used"]).round(2)
    df["base_currency"] = base_currency

    return df


def _apply_filters(
    df: pd.DataFrame, filters: dict[str, Any]
) -> pd.DataFrame:
    """Apply QuerySpec filters to scope the DataFrame.

    Reference: Implementation Plan §6.1 step 3 — "Implement filter
    application (date range, customer_id, segment, country,
    transaction_type) directly at load time."

    Args:
        df: Normalized DataFrame.
        filters: Dict from QuerySpec.filters (may contain nulls).

    Returns:
        Filtered DataFrame.
    """
    # Date range filter
    # Dates are interpreted as full days: start includes from 00:00:00,
    # end includes through 23:59:59.999999 (end-of-day).
    # Reference: Solution Design §4.1 — date_range uses YYYY-MM-DD granularity.
    date_range = filters.get("date_range")
    if date_range and "timestamp" in df.columns:
        start = date_range.get("start")
        end = date_range.get("end")
        if start:
            start_dt = pd.Timestamp(start, tz="UTC")
            df = df[df["timestamp"] >= start_dt]
        if end:
            # End of day: include all transactions on the end date
            end_dt = (
                pd.Timestamp(end, tz="UTC")
                + pd.Timedelta(days=1)
                - pd.Timedelta(microseconds=1)
            )
            df = df[df["timestamp"] <= end_dt]

    # Customer ID filter
    customer_id = filters.get("customer_id")
    if customer_id and "customer_id" in df.columns:
        df = df[df["customer_id"].astype(str) == str(customer_id)]

    # Segment filter (requires join with customers — applied post-join)
    # Handled separately when customers are loaded.

    # Country filter (on transaction's counterparty_country)
    country = filters.get("country")
    if country and "counterparty_country" in df.columns:
        df = df[df["counterparty_country"].str.upper() == country.upper()]

    # Transaction type filter
    transaction_type = filters.get("transaction_type")
    if transaction_type and "transaction_type" in df.columns:
        df = df[
            df["transaction_type"].str.lower() == transaction_type.lower()
        ]

    return df


def _deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove duplicate rows.

    Reference: Implementation Plan §6.1 — "dedup".

    Returns:
        Tuple of (deduplicated DataFrame, count of duplicates removed).
    """
    before = len(df)
    df = df.drop_duplicates()
    dedup_count = before - len(df)
    return df, dedup_count


def _handle_nulls(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Handle null values.

    Strategy:
    - Critical columns (transaction_id, customer_id, timestamp, amount):
      drop rows where these are null.
    - Non-critical columns (counterparty_id, counterparty_country, channel):
      impute with 'unknown'.

    Returns:
        Tuple of (cleaned DataFrame, rows_dropped, nulls_imputed).
    """
    critical_cols = ["transaction_id", "customer_id", "timestamp", "amount"]
    existing_critical = [c for c in critical_cols if c in df.columns]

    rows_before = len(df)
    df = df.dropna(subset=existing_critical)
    rows_dropped = rows_before - len(df)

    # Impute non-critical columns
    non_critical = ["counterparty_id", "counterparty_country", "channel"]
    nulls_imputed = 0
    for col in non_critical:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                df[col] = df[col].fillna("unknown")
                nulls_imputed += null_count

    return df, rows_dropped, int(nulls_imputed)


def _apply_segment_filter(
    df_transactions: pd.DataFrame,
    df_customers: pd.DataFrame,
    segment: str,
) -> pd.DataFrame:
    """Filter transactions by customer segment (requires customer data).

    Joins on customer_id, filters by segment, then drops the join column.
    """
    if "customer_id" not in df_customers.columns:
        return df_transactions

    # Get customer IDs matching the segment
    matching_customers = df_customers[
        df_customers["segment"].str.lower() == segment.lower()
    ]["customer_id"].astype(str)

    df_transactions = df_transactions[
        df_transactions["customer_id"].astype(str).isin(matching_customers)
    ]
    return df_transactions


# ---------------------------------------------------------------------------
# Main tool function
# ---------------------------------------------------------------------------


def data_loader(context: dict[str, Any], **args: Any) -> dict[str, Any]:
    """Load and preprocess transaction/customer data.

    This is the tool function registered in the ToolRegistry.

    Args:
        context: Shared execution context. May contain:
            - "transactions": pre-loaded DataFrame (or None to load from disk)
            - "customers": pre-loaded DataFrame (or None to load from disk)
            - "query_spec": dict with filters
        **args: Arguments from the ExecutionPlan step, e.g.:
            - date_range: list [start, end] or dict {start, end}
            - customer_id: str
            - segment: str
            - country: str
            - transaction_type: str

    Returns:
        Dict with:
            - tool: "data_loader"
            - status: "success"
            - transactions: filtered DataFrame (added to context)
            - customers: normalized customer DataFrame (added to context)
            - rows_loaded: total rows in raw data
            - rows_after_filter: rows after all filtering
            - preprocessing_log: {rows_dropped, nulls_imputed, dedup_count}
            - filters_applied: which filters were active
    """
    # Load column mapping
    col_mapping = _load_column_mapping()

    # --- Load transactions ---
    df_transactions = context.get("transactions")
    if df_transactions is None or not isinstance(df_transactions, pd.DataFrame):
        data_dir = os.getenv("DATA_DIR", "data/synthetic")
        txn_path = Path(data_dir) / "transactions.csv"
        df_transactions = pd.read_csv(txn_path)

    # --- Load customers ---
    df_customers = context.get("customers")
    if df_customers is None or not isinstance(df_customers, pd.DataFrame):
        data_dir = os.getenv("DATA_DIR", "data/synthetic")
        cust_path = Path(data_dir) / "customers.csv"
        df_customers = pd.read_csv(cust_path)

    rows_loaded = len(df_transactions)

    # Step 1: Apply column mapping
    df_transactions = _apply_column_mapping(
        df_transactions, col_mapping["transactions"]
    )
    df_customers = _apply_column_mapping(
        df_customers, col_mapping["customers"]
    )

    # Step 2: Type coercion — amounts to float64
    if "amount" in df_transactions.columns:
        df_transactions["amount"] = df_transactions["amount"].astype("float64")

    # Step 3: Timestamp normalization (to UTC)
    df_transactions = _normalize_timestamps(df_transactions)

    # Step 4: Currency normalization (to base currency via static FX table)
    df_transactions = _normalize_currency(df_transactions)

    # Step 5: Deduplication
    df_transactions, dedup_count = _deduplicate(df_transactions)

    # Step 6: Null handling
    df_transactions, rows_dropped, nulls_imputed = _handle_nulls(df_transactions)

    # Step 7: Build filters from args + context query_spec
    filters = _build_filters(context, args)

    # Step 8: Apply filters
    df_transactions = _apply_filters(df_transactions, filters)

    # Step 8b: Segment filter (requires customer data)
    segment = filters.get("segment")
    if segment:
        df_transactions = _apply_segment_filter(
            df_transactions, df_customers, segment
        )

    rows_after_filter = len(df_transactions)

    # Build preprocessing log
    preprocessing_log = {
        "rows_dropped": rows_dropped,
        "nulls_imputed": nulls_imputed,
        "dedup_count": dedup_count,
    }

    return {
        "tool": "data_loader",
        "status": "success",
        "transactions": df_transactions,
        "customers": df_customers,
        "rows_loaded": rows_loaded,
        "rows_after_filter": rows_after_filter,
        "preprocessing_log": preprocessing_log,
        "filters_applied": filters,
    }


def _build_filters(context: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    """Merge filters from QuerySpec and plan step args.

    Plan step args take precedence over QuerySpec filters.
    Handles date_range as either list [start, end] or dict {start, end}.
    """
    # Start with QuerySpec filters if available
    query_spec = context.get("query_spec", {})
    spec_filters = query_spec.get("filters", {}) if isinstance(query_spec, dict) else {}

    filters: dict[str, Any] = {}

    # Merge: args override spec_filters
    for key in ["customer_id", "segment", "country", "transaction_type"]:
        value = args.get(key) or spec_filters.get(key)
        if value:
            filters[key] = value

    # Handle date_range (can be list or dict)
    date_range = args.get("date_range") or spec_filters.get("date_range")
    if date_range:
        if isinstance(date_range, list) and len(date_range) == 2:
            filters["date_range"] = {"start": date_range[0], "end": date_range[1]}
        elif isinstance(date_range, dict):
            filters["date_range"] = date_range

    return filters
