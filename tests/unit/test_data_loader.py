"""Unit tests for Data Loader & Preprocessing Tool.

Reference: Implementation Plan §6.1 Definition of Done:
"Given the same raw CSV, three different QuerySpec.filters produce
three correctly-scoped DataFrames verified against expected row counts
in unit tests."
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.tools.data_loader import (
    data_loader,
    _apply_column_mapping,
    _normalize_timestamps,
    _normalize_currency,
    _deduplicate,
    _handle_nulls,
    _apply_filters,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_transactions() -> pd.DataFrame:
    """Hand-crafted micro-fixture with known properties.

    31 rows total in the CSV (1 duplicate of TXN030).
    After dedup: 30 unique rows.
    Customer 4521: 6 transactions (all July 2026, USD, deposits)
    Customer 7832: 15 transactions (all July 1 2026, EUR, transfers)
    Customer 9001: 5 transactions (July 2026, USD, mixed)
    Customer 1234: 4 transactions (June 2026, GBP, mixed)
    """
    return pd.read_csv("data/synthetic/transactions.csv")


@pytest.fixture
def sample_customers() -> pd.DataFrame:
    return pd.read_csv("data/synthetic/customers.csv")


# ---------------------------------------------------------------------------
# Test: Column mapping
# ---------------------------------------------------------------------------


class TestColumnMapping:
    def test_already_correct_columns_unchanged(self, sample_transactions):
        """If columns already match internal schema, no rename needed."""
        mapping = {
            "transaction_id": ["transaction_id", "txn_id"],
            "customer_id": ["customer_id", "cust_id"],
            "timestamp": ["timestamp", "date"],
            "amount": ["amount", "transaction_amount"],
        }
        result = _apply_column_mapping(sample_transactions, mapping)
        assert "transaction_id" in result.columns
        assert "customer_id" in result.columns

    def test_alternate_column_names_mapped(self):
        """Source columns with non-standard names get mapped correctly."""
        df = pd.DataFrame({
            "txn_id": ["T1"],
            "cust_id": ["C1"],
            "date": ["2026-07-01"],
            "transaction_amount": [100.0],
        })
        mapping = {
            "transaction_id": ["transaction_id", "txn_id"],
            "customer_id": ["customer_id", "cust_id"],
            "timestamp": ["timestamp", "date"],
            "amount": ["amount", "transaction_amount"],
        }
        result = _apply_column_mapping(df, mapping)
        assert "transaction_id" in result.columns
        assert "customer_id" in result.columns
        assert "timestamp" in result.columns
        assert "amount" in result.columns


# ---------------------------------------------------------------------------
# Test: Timestamp normalization
# ---------------------------------------------------------------------------


class TestTimestampNormalization:
    def test_timestamps_converted_to_utc(self, sample_transactions):
        result = _normalize_timestamps(sample_transactions)
        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])
        # All timestamps should have UTC timezone
        assert result["timestamp"].dt.tz is not None
        assert str(result["timestamp"].dt.tz) == "UTC"


# ---------------------------------------------------------------------------
# Test: Currency normalization
# ---------------------------------------------------------------------------


class TestCurrencyNormalization:
    def test_usd_unchanged(self):
        """USD amounts: original preserved, fx_rate_used=1.0, normalized equals original."""
        df = pd.DataFrame({
            "amount": [9500.00],
            "currency": ["USD"],
        })
        result = _normalize_currency(df)
        # Original columns untouched
        assert result["amount"].iloc[0] == 9500.00
        assert result["currency"].iloc[0] == "USD"
        # Explicit original copies
        assert result["amount_original"].iloc[0] == 9500.00
        assert result["currency_original"].iloc[0] == "USD"
        # FX rate
        assert result["fx_rate_used"].iloc[0] == 1.0
        # Normalized column
        assert result["amount_normalized"].iloc[0] == 9500.00
        assert result["base_currency"].iloc[0] == "USD"
        # Traceability: amount_normalized == amount * fx_rate_used
        assert result["amount_normalized"].iloc[0] == result["amount"].iloc[0] * result["fx_rate_used"].iloc[0]

    def test_eur_converted(self):
        """EUR amounts: original preserved, fx_rate_used=1.08, normalized correctly."""
        df = pd.DataFrame({
            "amount": [1000.00],
            "currency": ["EUR"],
        })
        result = _normalize_currency(df)
        # Original stays as EUR
        assert result["amount"].iloc[0] == 1000.00
        assert result["currency"].iloc[0] == "EUR"
        assert result["amount_original"].iloc[0] == 1000.00
        assert result["currency_original"].iloc[0] == "EUR"
        # FX rate matches fx_rates.yaml
        assert result["fx_rate_used"].iloc[0] == 1.08
        # Normalized to USD
        assert result["amount_normalized"].iloc[0] == 1080.00  # 1000 * 1.08
        assert result["base_currency"].iloc[0] == "USD"
        # Traceability
        assert result["amount_normalized"].iloc[0] == result["amount"].iloc[0] * result["fx_rate_used"].iloc[0]

    def test_gbp_converted(self):
        """GBP amounts: original preserved, fx_rate_used=1.27, normalized correctly."""
        df = pd.DataFrame({
            "amount": [500.00],
            "currency": ["GBP"],
        })
        result = _normalize_currency(df)
        # Original stays as GBP
        assert result["amount"].iloc[0] == 500.00
        assert result["currency"].iloc[0] == "GBP"
        # FX rate matches fx_rates.yaml
        assert result["fx_rate_used"].iloc[0] == 1.27
        # Normalized to USD
        assert result["amount_normalized"].iloc[0] == 635.00  # 500 * 1.27
        assert result["base_currency"].iloc[0] == "USD"
        # Traceability
        assert result["amount_normalized"].iloc[0] == result["amount"].iloc[0] * result["fx_rate_used"].iloc[0]

    def test_fx_rate_matches_yaml(self):
        """All fx_rate_used values must match what is loaded from fx_rates.yaml."""
        from src.tools.data_loader import _load_fx_rates

        _, rates = _load_fx_rates()
        df = pd.DataFrame({
            "amount": [1000.00, 2000.00, 3000.00],
            "currency": ["USD", "EUR", "GBP"],
        })
        result = _normalize_currency(df)
        assert result["fx_rate_used"].iloc[0] == rates["USD"]
        assert result["fx_rate_used"].iloc[1] == rates["EUR"]
        assert result["fx_rate_used"].iloc[2] == rates["GBP"]

    def test_normalization_traceability(self):
        """amount_normalized == amount * fx_rate_used for all rows."""
        df = pd.DataFrame({
            "amount": [1000.00, 2000.00, 500.00, 750.00],
            "currency": ["USD", "EUR", "GBP", "CAD"],
        })
        result = _normalize_currency(df)
        expected = (result["amount"] * result["fx_rate_used"]).round(2)
        assert (result["amount_normalized"] == expected).all()


# ---------------------------------------------------------------------------
# Test: Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_duplicates_removed(self, sample_transactions):
        """The sample data has 1 exact duplicate (TXN030 appears twice)."""
        result, dedup_count = _deduplicate(sample_transactions)
        assert dedup_count == 1
        assert len(result) == 30  # 31 - 1 duplicate

    def test_no_duplicates_leaves_data_unchanged(self):
        df = pd.DataFrame({
            "transaction_id": ["T1", "T2", "T3"],
            "amount": [100, 200, 300],
        })
        result, dedup_count = _deduplicate(df)
        assert dedup_count == 0
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Test: Null handling
# ---------------------------------------------------------------------------


class TestNullHandling:
    def test_critical_null_rows_dropped(self):
        """Rows with null in critical columns are dropped."""
        df = pd.DataFrame({
            "transaction_id": ["T1", None, "T3"],
            "customer_id": ["C1", "C2", "C3"],
            "timestamp": ["2026-07-01", "2026-07-02", "2026-07-03"],
            "amount": [100.0, 200.0, 300.0],
            "counterparty_id": ["CP1", None, "CP3"],
        })
        result, rows_dropped, nulls_imputed = _handle_nulls(df)
        assert rows_dropped == 1  # Row with null transaction_id dropped
        assert len(result) == 2

    def test_non_critical_nulls_imputed(self):
        """Non-critical null values are filled with 'unknown'."""
        df = pd.DataFrame({
            "transaction_id": ["T1", "T2"],
            "customer_id": ["C1", "C2"],
            "timestamp": ["2026-07-01", "2026-07-02"],
            "amount": [100.0, 200.0],
            "counterparty_id": [None, "CP2"],
            "channel": ["online", None],
        })
        result, rows_dropped, nulls_imputed = _handle_nulls(df)
        assert rows_dropped == 0
        assert nulls_imputed == 2
        assert result["counterparty_id"].iloc[0] == "unknown"
        assert result["channel"].iloc[1] == "unknown"


# ---------------------------------------------------------------------------
# Test: Filter application (DoD — three different filters, three results)
# ---------------------------------------------------------------------------


class TestFilterApplication:
    """Definition of Done: 'Given the same raw CSV, three different
    QuerySpec.filters produce three correctly-scoped DataFrames
    verified against expected row counts.'
    """

    def test_filter_by_date_range_july(self, sample_transactions):
        """Filter to July 2026 only — should exclude June transactions."""
        df = _normalize_timestamps(sample_transactions.drop_duplicates())
        filters = {
            "date_range": {"start": "2026-07-01", "end": "2026-07-31"}
        }
        result = _apply_filters(df, filters)
        # June transactions (customer 1234): 4 rows excluded
        # July transactions: 26 rows remain
        assert len(result) == 26

    def test_filter_by_customer_id(self, sample_transactions):
        """Filter to customer 4521 only."""
        df = sample_transactions.drop_duplicates()
        filters = {"customer_id": "4521"}
        result = _apply_filters(df, filters)
        assert len(result) == 6
        assert all(result["customer_id"].astype(str) == "4521")

    def test_filter_by_transaction_type(self, sample_transactions):
        """Filter to deposits only."""
        df = sample_transactions.drop_duplicates()
        filters = {"transaction_type": "deposit"}
        result = _apply_filters(df, filters)
        # Customer 4521: 6 deposits + Customer 9001: 2 deposits +
        # Customer 1234: 1 deposit = 9
        assert len(result) == 9
        assert all(result["transaction_type"].str.lower() == "deposit")

    def test_combined_filters(self, sample_transactions):
        """Date range + customer ID combined."""
        df = _normalize_timestamps(sample_transactions.drop_duplicates())
        filters = {
            "date_range": {"start": "2026-07-01", "end": "2026-07-03"},
            "customer_id": "4521",
        }
        result = _apply_filters(df, filters)
        # Customer 4521 has 6 txns on July 1-3.
        # End date "2026-07-03" includes the full day (through 23:59:59),
        # so all 6 transactions are within range.
        assert len(result) == 6


# ---------------------------------------------------------------------------
# Test: Full data_loader integration
# ---------------------------------------------------------------------------


class TestDataLoaderIntegration:
    def test_full_pipeline_no_filters(self):
        """Full pipeline with no filters applied."""
        context = {"query_spec": {"filters": {}}}
        result = data_loader(context)
        assert result["status"] == "success"
        assert result["rows_loaded"] == 31  # Raw CSV has 31 rows
        assert result["preprocessing_log"]["dedup_count"] == 1
        assert result["rows_after_filter"] == 30  # After dedup

    def test_full_pipeline_with_date_filter(self):
        """Full pipeline filtering to July only."""
        context = {
            "query_spec": {
                "filters": {
                    "date_range": {"start": "2026-07-01", "end": "2026-07-31"}
                }
            }
        }
        result = data_loader(context, date_range=["2026-07-01", "2026-07-31"])
        assert result["status"] == "success"
        assert result["rows_after_filter"] == 26

    def test_full_pipeline_single_customer(self):
        """Full pipeline filtering to a single customer."""
        context = {"query_spec": {"filters": {}}}
        result = data_loader(context, customer_id="7832")
        assert result["status"] == "success"
        assert result["rows_after_filter"] == 15

    def test_preprocessing_log_present(self):
        """Preprocessing log is always returned."""
        context = {"query_spec": {"filters": {}}}
        result = data_loader(context)
        log = result["preprocessing_log"]
        assert "rows_dropped" in log
        assert "nulls_imputed" in log
        assert "dedup_count" in log

    def test_returns_dataframes_in_result(self):
        """Result includes pandas DataFrames for downstream tools."""
        context = {"query_spec": {"filters": {}}}
        result = data_loader(context)
        assert isinstance(result["transactions"], pd.DataFrame)
        assert isinstance(result["customers"], pd.DataFrame)
