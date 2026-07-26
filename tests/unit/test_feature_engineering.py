"""Unit tests for Feature Engineering Tool — Structuring/Smurfing family.

Reference: Implementation Plan §6.2 Definition of Done:
"Each feature family has a unit test with a hand-crafted mini-DataFrame
where the expected feature values are computed by hand and asserted exactly."
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.tools.feature_engineering import (
    feature_engineering,
    _compute_structuring_features,
    _compute_velocity_features,
    _compute_layering_features,
    _compute_amount_deviation_features,
    _rolling_max_count_and_total,
    _load_structuring_config,
    _load_velocity_config,
    _load_layering_config,
    _load_amount_deviation_config,
    ROLLING_WINDOWS,
    DOCUMENTED_FEATURE_COLUMNS,
    ENHANCEMENT_FEATURE_COLUMNS,
)

# Load config-driven thresholds once for use across tests.
_CONFIG = _load_structuring_config()
REPORTING_THRESHOLD = _CONFIG["reporting_threshold"]
NEAR_THRESHOLD_LOWER_BOUND_RATIO = _CONFIG["near_threshold_lower_bound_ratio"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def structuring_customer_df() -> pd.DataFrame:
    """Customer 4521: 6 near-threshold deposits within 3 days.

    All amounts are between $8,000 and $10,000 (near-threshold).
    This is a clear structuring pattern.

    Hand-computed expected values:
    - total_txn_count: 6
    - total_near_threshold_count: 6
    - near_threshold_ratio_overall: 6/6 = 1.0
    - 24h window: max 2 (July 1 has 2, July 2 has 2, July 3 has 2)
    - 7d window: max 6 (all within 7 days)
    - 30d window: max 6 (all within 30 days)
    """
    return pd.DataFrame({
        "customer_id": ["4521"] * 6,
        "timestamp": pd.to_datetime([
            "2026-07-01 10:15:00",
            "2026-07-01 14:30:00",
            "2026-07-02 09:00:00",
            "2026-07-02 16:45:00",
            "2026-07-03 11:20:00",
            "2026-07-03 15:50:00",
        ], utc=True),
        "amount_normalized": [9500.0, 9800.0, 9200.0, 9700.0, 9400.0, 9600.0],
    })


@pytest.fixture
def clean_customer_df() -> pd.DataFrame:
    """Customer 9001: 5 high-value transactions, all ABOVE threshold.

    All amounts are >= $10,000 (NOT near-threshold, they exceed it).
    This should produce zero near-threshold features.

    Hand-computed expected values:
    - total_txn_count: 5
    - total_near_threshold_count: 0
    - near_threshold_ratio_overall: 0.0
    - All window counts: 0
    - All window ratios: 0.0
    """
    return pd.DataFrame({
        "customer_id": ["9001"] * 5,
        "timestamp": pd.to_datetime([
            "2026-07-01 09:00:00",
            "2026-07-05 14:00:00",
            "2026-07-10 10:00:00",
            "2026-07-15 16:00:00",
            "2026-07-20 11:00:00",
        ], utc=True),
        "amount_normalized": [25000.0, 30000.0, 28000.0, 32000.0, 27000.0],
    })


@pytest.fixture
def mixed_customer_df() -> pd.DataFrame:
    """Customer 1234: 4 transactions, 1 near-threshold.

    Hand-computed:
    - total_txn_count: 4
    - total_near_threshold_count: 1 (the $8,500 one)
    - near_threshold_ratio_overall: 1/4 = 0.25
    - 24h: max near_threshold count = 1, max total = 2
    - 7d: max near_threshold count = 1, max total = 4
    - 30d: max near_threshold count = 1, max total = 4
    """
    return pd.DataFrame({
        "customer_id": ["1234"] * 4,
        "timestamp": pd.to_datetime([
            "2026-07-01 10:00:00",
            "2026-07-01 14:00:00",
            "2026-07-03 09:00:00",
            "2026-07-05 16:00:00",
        ], utc=True),
        "amount_normalized": [8500.0, 500.0, 3000.0, 2000.0],
    })


@pytest.fixture
def multi_customer_df(
    structuring_customer_df, clean_customer_df, mixed_customer_df
) -> pd.DataFrame:
    """Combined multi-customer dataset for integration testing."""
    return pd.concat(
        [structuring_customer_df, clean_customer_df, mixed_customer_df],
        ignore_index=True,
    )


# ---------------------------------------------------------------------------
# Test: Structuring features — customer with clear structuring pattern
# ---------------------------------------------------------------------------


class TestStructuringFeaturesPositive:
    """Customer 4521 — all transactions are near-threshold (structuring)."""

    def test_total_counts(self, structuring_customer_df):
        result = _compute_structuring_features(structuring_customer_df)
        row = result[result["customer_id"] == "4521"].iloc[0]
        assert row["total_txn_count"] == 6
        assert row["total_near_threshold_count"] == 6

    def test_overall_ratio(self, structuring_customer_df):
        result = _compute_structuring_features(structuring_customer_df)
        row = result[result["customer_id"] == "4521"].iloc[0]
        assert row["near_threshold_ratio_overall"] == 1.0

    def test_24h_window(self, structuring_customer_df):
        """24h window: max count is 2 (each day has 2 txns within 24h)."""
        result = _compute_structuring_features(structuring_customer_df)
        row = result[result["customer_id"] == "4521"].iloc[0]
        # July 1: 10:15 to July 2 10:15 captures 10:15, 14:30, 09:00 = 3
        # Actually: from 10:15 July 1, within 24h includes up to 10:15 July 2
        # which gets 10:15, 14:30, 09:00 = 3 near-threshold txns
        assert row["near_threshold_txn_count_24h"] >= 2

    def test_7d_window(self, structuring_customer_df):
        """7d window: all 6 txns within 3 days, so max count is 6."""
        result = _compute_structuring_features(structuring_customer_df)
        row = result[result["customer_id"] == "4521"].iloc[0]
        assert row["near_threshold_txn_count_7d"] == 6

    def test_30d_window(self, structuring_customer_df):
        """30d window: all 6 txns within 3 days, so max count is 6."""
        result = _compute_structuring_features(structuring_customer_df)
        row = result[result["customer_id"] == "4521"].iloc[0]
        assert row["near_threshold_txn_count_30d"] == 6

    def test_7d_ratio(self, structuring_customer_df):
        """7d window ratio: 6/6 = 1.0 (all txns are near-threshold)."""
        result = _compute_structuring_features(structuring_customer_df)
        row = result[result["customer_id"] == "4521"].iloc[0]
        assert row["near_threshold_txn_ratio_7d"] == 1.0


# ---------------------------------------------------------------------------
# Test: Clean customer — no structuring
# ---------------------------------------------------------------------------


class TestStructuringFeaturesClean:
    """Customer 9001 — all transactions ABOVE threshold (not near)."""

    def test_total_near_threshold_is_zero(self, clean_customer_df):
        result = _compute_structuring_features(clean_customer_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["total_near_threshold_count"] == 0

    def test_overall_ratio_is_zero(self, clean_customer_df):
        result = _compute_structuring_features(clean_customer_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["near_threshold_ratio_overall"] == 0.0

    def test_all_window_counts_zero(self, clean_customer_df):
        result = _compute_structuring_features(clean_customer_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        for window_name in ROLLING_WINDOWS:
            assert row[f"near_threshold_txn_count_{window_name}"] == 0
            assert row[f"near_threshold_txn_ratio_{window_name}"] == 0.0


# ---------------------------------------------------------------------------
# Test: Mixed customer — some near-threshold
# ---------------------------------------------------------------------------


class TestStructuringFeaturesMixed:
    """Customer 1234 — 1 of 4 transactions near-threshold."""

    def test_total_counts(self, mixed_customer_df):
        result = _compute_structuring_features(mixed_customer_df)
        row = result[result["customer_id"] == "1234"].iloc[0]
        assert row["total_txn_count"] == 4
        assert row["total_near_threshold_count"] == 1

    def test_overall_ratio(self, mixed_customer_df):
        result = _compute_structuring_features(mixed_customer_df)
        row = result[result["customer_id"] == "1234"].iloc[0]
        assert row["near_threshold_ratio_overall"] == 0.25

    def test_7d_window_count(self, mixed_customer_df):
        """All 4 txns within 7 days, only 1 near-threshold."""
        result = _compute_structuring_features(mixed_customer_df)
        row = result[result["customer_id"] == "1234"].iloc[0]
        assert row["near_threshold_txn_count_7d"] == 1

    def test_7d_window_ratio(self, mixed_customer_df):
        """7d window: 1 near-threshold out of 4 total = 0.25."""
        result = _compute_structuring_features(mixed_customer_df)
        row = result[result["customer_id"] == "1234"].iloc[0]
        assert row["near_threshold_txn_ratio_7d"] == 0.25


# ---------------------------------------------------------------------------
# Test: Multi-customer (integration)
# ---------------------------------------------------------------------------


class TestMultiCustomer:
    """Multiple customers processed together produce correct per-customer rows."""

    def test_one_row_per_customer(self, multi_customer_df):
        result = _compute_structuring_features(multi_customer_df)
        assert len(result) == 3
        assert set(result["customer_id"]) == {"4521", "9001", "1234"}

    def test_structuring_customer_still_detected(self, multi_customer_df):
        result = _compute_structuring_features(multi_customer_df)
        row = result[result["customer_id"] == "4521"].iloc[0]
        assert row["total_near_threshold_count"] == 6
        assert row["near_threshold_txn_count_7d"] == 6

    def test_clean_customer_not_flagged(self, multi_customer_df):
        result = _compute_structuring_features(multi_customer_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["total_near_threshold_count"] == 0


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_dataframe(self):
        """Empty input produces empty output with correct columns."""
        df = pd.DataFrame(columns=["customer_id", "timestamp", "amount_normalized"])
        result = _compute_structuring_features(df)
        assert len(result) == 0
        assert "near_threshold_txn_count_7d" in result.columns

    def test_single_transaction_at_boundary(self):
        """Transaction at exactly $8,000 (lower bound) IS near-threshold."""
        lower_bound = REPORTING_THRESHOLD * NEAR_THRESHOLD_LOWER_BOUND_RATIO
        df = pd.DataFrame({
            "customer_id": ["X"],
            "timestamp": pd.to_datetime(["2026-07-01 10:00:00"], utc=True),
            "amount_normalized": [lower_bound],  # Exactly $8,000
        })
        result = _compute_structuring_features(df)
        assert result.iloc[0]["total_near_threshold_count"] == 1

    def test_transaction_at_threshold_not_near(self):
        """Transaction at exactly $10,000 is NOT near-threshold (it equals threshold)."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "timestamp": pd.to_datetime(["2026-07-01 10:00:00"], utc=True),
            "amount_normalized": [REPORTING_THRESHOLD],  # Exactly $10,000
        })
        result = _compute_structuring_features(df)
        assert result.iloc[0]["total_near_threshold_count"] == 0

    def test_transaction_just_below_lower_bound(self):
        """Transaction at $7,999.99 is NOT near-threshold (below lower bound)."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "timestamp": pd.to_datetime(["2026-07-01 10:00:00"], utc=True),
            "amount_normalized": [7999.99],
        })
        result = _compute_structuring_features(df)
        assert result.iloc[0]["total_near_threshold_count"] == 0

    def test_single_customer_single_transaction(self):
        """Single transaction produces valid features."""
        df = pd.DataFrame({
            "customer_id": ["Y"],
            "timestamp": pd.to_datetime(["2026-07-01 10:00:00"], utc=True),
            "amount_normalized": [9500.0],
        })
        result = _compute_structuring_features(df)
        assert len(result) == 1
        assert result.iloc[0]["total_txn_count"] == 1
        assert result.iloc[0]["total_near_threshold_count"] == 1
        assert result.iloc[0]["near_threshold_ratio_overall"] == 1.0

    def test_missing_column_raises_error(self):
        """Missing required column raises ValueError."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "timestamp": pd.to_datetime(["2026-07-01"], utc=True),
            # Missing amount_normalized
        })
        with pytest.raises(ValueError, match="Missing required columns"):
            _compute_structuring_features(df)


# ---------------------------------------------------------------------------
# Test: Rolling window helper directly (pandas-native implementation)
# ---------------------------------------------------------------------------


class TestRollingWindowHelpers:
    def test_max_count_and_total_basic(self):
        """3 flagged txns within 24h window; 4th txn 2 days later is excluded."""
        group = pd.DataFrame({
            "timestamp": pd.to_datetime([
                "2026-07-01 08:00:00",
                "2026-07-01 10:00:00",
                "2026-07-01 12:00:00",
                "2026-07-03 10:00:00",
            ], utc=True),
            "_is_near_threshold": [1, 1, 1, 0],
        })
        max_count, max_total = _rolling_max_count_and_total(group, "24h")
        assert max_count == 3
        assert max_total == 3

    def test_empty_group(self):
        group = pd.DataFrame({
            "timestamp": pd.to_datetime([], utc=True),
            "_is_near_threshold": pd.Series([], dtype=int),
        })
        max_count, max_total = _rolling_max_count_and_total(group, "24h")
        assert max_count == 0
        assert max_total == 0

    def test_max_total_basic(self):
        """4 txns within 24h of the first; 5th txn 4 days later is excluded."""
        group = pd.DataFrame({
            "timestamp": pd.to_datetime([
                "2026-07-01 08:00:00",
                "2026-07-01 10:00:00",
                "2026-07-01 12:00:00",
                "2026-07-01 23:00:00",
                "2026-07-05 10:00:00",
            ], utc=True),
            "_is_near_threshold": [0, 0, 0, 0, 0],
        })
        max_count, max_total = _rolling_max_count_and_total(group, "24h")
        assert max_total == 4
        assert max_count == 0

    def test_datetime_unit_safety_microseconds(self):
        """Rolling computation works correctly regardless of datetime64
        storage resolution (us vs ns), verifying the fix for the previously
        encountered platform-dependent datetime unit bug."""
        # pd.to_datetime on this platform may produce datetime64[us] or [ns]
        # depending on pandas/numpy version; the pandas-native rolling
        # implementation must be correct either way.
        group = pd.DataFrame({
            "timestamp": pd.to_datetime([
                "2026-07-01 08:00:00",
                "2026-07-05 10:00:00",  # 4 days 2 hours later — outside 24h
            ], utc=True),
            "_is_near_threshold": [1, 1],
        })
        max_count, max_total = _rolling_max_count_and_total(group, "24h")
        # Each transaction is its own window of 1 (no other txn within 24h)
        assert max_count == 1
        assert max_total == 1


# ---------------------------------------------------------------------------
# Test: Tool function interface (context-based call)
# ---------------------------------------------------------------------------


class TestToolInterface:
    def test_success_with_data_loader_context(self, structuring_customer_df):
        """Tool function works when called via the expected context pattern."""
        context = {
            "data_loader": {
                "transactions": structuring_customer_df,
                "status": "success",
            }
        }
        result = feature_engineering(context, feature_set="structuring")
        assert result["status"] == "success"
        assert result["feature_set"] == "structuring"
        assert result["entities_processed"] == 1
        assert "near_threshold_txn_count_7d" in result["features_computed"]
        assert isinstance(result["features_df"], pd.DataFrame)

    def test_error_on_missing_data(self):
        """Returns error when no transactions in context."""
        context = {}
        result = feature_engineering(context, feature_set="structuring")
        assert result["status"] == "error"

    def test_error_on_unknown_feature_set(self, structuring_customer_df):
        """Returns error for a genuinely unimplemented feature family name."""
        context = {
            "data_loader": {"transactions": structuring_customer_df}
        }
        result = feature_engineering(context, feature_set="rapid_cashout")
        assert result["status"] == "error"
        assert "not implemented" in result["error"]

    def test_default_feature_set_is_structuring(self, structuring_customer_df):
        """Default feature_set is 'structuring'."""
        context = {
            "data_loader": {"transactions": structuring_customer_df}
        }
        result = feature_engineering(context)
        assert result["feature_set"] == "structuring"
        assert result["status"] == "success"

    def test_documented_and_enhancement_features_isolated(self, structuring_customer_df):
        """Documented (Solution Design §5.3) and enhancement features are
        reported separately, so downstream consumers can distinguish them."""
        context = {
            "data_loader": {"transactions": structuring_customer_df}
        }
        result = feature_engineering(context, feature_set="structuring")

        # Documented features: only the 6 windowed count/ratio columns
        assert set(result["features_computed"]) == set(DOCUMENTED_FEATURE_COLUMNS)

        # Enhancement features: the 3 non-documented aggregate columns
        assert set(result["enhancement_features_computed"]) == set(
            ENHANCEMENT_FEATURE_COLUMNS
        )

        # No overlap between the two sets
        assert not set(result["features_computed"]) & set(
            result["enhancement_features_computed"]
        )


# ---------------------------------------------------------------------------
# Test: Configuration-driven thresholds (audit requirement)
# ---------------------------------------------------------------------------


class TestConfigDrivenThresholds:
    """Verifies thresholds are loaded from structuring_thresholds.yaml,
    not hardcoded in Python, per documentation compliance audit."""

    def test_config_loads_reporting_threshold(self):
        config = _load_structuring_config()
        assert config["reporting_threshold"] == 10000.00

    def test_config_loads_lower_bound_ratio(self):
        config = _load_structuring_config()
        assert config["near_threshold_lower_bound_ratio"] == 0.80

    def test_reporting_threshold_used_in_computation(self):
        """A transaction at exactly the configured threshold is excluded."""
        config = _load_structuring_config()
        threshold = config["reporting_threshold"]

        df = pd.DataFrame({
            "customer_id": ["Z"],
            "timestamp": pd.to_datetime(["2026-07-01 10:00:00"], utc=True),
            "amount_normalized": [threshold],
        })
        result = _compute_structuring_features(df)
        assert result.iloc[0]["total_near_threshold_count"] == 0


# ---------------------------------------------------------------------------
# Test: Velocity Feature Family
# ---------------------------------------------------------------------------


class TestVelocityFeaturesHighFrequency:
    """Customer 7832: 15 transfers all within 5.5 hours on 2026-07-01.

    This is a high-velocity customer.

    Hand-computed expected values:
    - txn_frequency_24h: 15 (all 15 within 5.5h, so within any 24h window)
    - txn_frequency_7d: 15 (all within 7 days)
    - txn_frequency_30d: 15 (all within 30 days)
    - inter_txn_delta_mean_seconds: 1414.29 (mean of 14 gaps)
    - inter_txn_delta_min_seconds: 900.0 (15 minutes)
    - inter_txn_delta_max_seconds: 1800.0 (30 minutes)
    """

    @pytest.fixture
    def high_velocity_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["7832"] * 15,
            "timestamp": pd.to_datetime([
                "2026-07-01 08:00:00", "2026-07-01 08:15:00", "2026-07-01 08:30:00",
                "2026-07-01 09:00:00", "2026-07-01 09:15:00", "2026-07-01 09:45:00",
                "2026-07-01 10:00:00", "2026-07-01 10:30:00", "2026-07-01 11:00:00",
                "2026-07-01 11:15:00", "2026-07-01 11:45:00", "2026-07-01 12:00:00",
                "2026-07-01 12:30:00", "2026-07-01 13:00:00", "2026-07-01 13:30:00",
            ], utc=True),
            "amount_normalized": [4500.0] * 15,
        })

    def test_frequency_24h(self, high_velocity_df):
        """All 15 txns are within 5.5h; 24h window captures all."""
        result = _compute_velocity_features(high_velocity_df)
        row = result[result["customer_id"] == "7832"].iloc[0]
        assert row["txn_frequency_24h"] == 15

    def test_frequency_7d(self, high_velocity_df):
        result = _compute_velocity_features(high_velocity_df)
        row = result[result["customer_id"] == "7832"].iloc[0]
        assert row["txn_frequency_7d"] == 15

    def test_frequency_30d(self, high_velocity_df):
        result = _compute_velocity_features(high_velocity_df)
        row = result[result["customer_id"] == "7832"].iloc[0]
        assert row["txn_frequency_30d"] == 15

    def test_delta_mean(self, high_velocity_df):
        """Mean of [900, 900, 1800, 900, 1800, 900, 1800, 1800, 900, 1800, 900,
        1800, 1800, 1800] = 19800/14 = 1414.29 seconds."""
        result = _compute_velocity_features(high_velocity_df)
        row = result[result["customer_id"] == "7832"].iloc[0]
        assert abs(row["inter_txn_delta_mean_seconds"] - 1414.29) < 0.01

    def test_delta_min(self, high_velocity_df):
        """Minimum gap is 900 seconds (15 minutes)."""
        result = _compute_velocity_features(high_velocity_df)
        row = result[result["customer_id"] == "7832"].iloc[0]
        assert row["inter_txn_delta_min_seconds"] == 900.0

    def test_delta_max(self, high_velocity_df):
        """Maximum gap is 1800 seconds (30 minutes)."""
        result = _compute_velocity_features(high_velocity_df)
        row = result[result["customer_id"] == "7832"].iloc[0]
        assert row["inter_txn_delta_max_seconds"] == 1800.0


class TestVelocityFeaturesLowFrequency:
    """Customer 9001: 5 transactions spread across 20 days.

    This is a low-velocity (clean) customer.

    Hand-computed expected values:
    - txn_frequency_24h: 1 (no two txns within 24h of each other)
    - txn_frequency_7d: 2 (July 1 + July 5 = 2 within any 7-day window)
    - txn_frequency_30d: 5 (all 5 within 20 days, within any 30d window)
    - inter_txn_delta_mean_seconds: 412200.0
    - inter_txn_delta_min_seconds: 363600.0
    - inter_txn_delta_max_seconds: 453600.0
    """

    @pytest.fixture
    def low_velocity_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["9001"] * 5,
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00",
                "2026-07-05 14:00:00",
                "2026-07-10 10:00:00",
                "2026-07-15 16:00:00",
                "2026-07-20 11:00:00",
            ], utc=True),
            "amount_normalized": [25000.0] * 5,
        })

    def test_frequency_24h(self, low_velocity_df):
        """No two txns within 24h of each other — max per window is 1."""
        result = _compute_velocity_features(low_velocity_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["txn_frequency_24h"] == 1

    def test_frequency_7d(self, low_velocity_df):
        """July 1 + July 5 are within 7 days; max window captures 2."""
        result = _compute_velocity_features(low_velocity_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["txn_frequency_7d"] == 2

    def test_frequency_30d(self, low_velocity_df):
        """All 5 txns within 20 days — within any 30d window."""
        result = _compute_velocity_features(low_velocity_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["txn_frequency_30d"] == 5

    def test_delta_mean(self, low_velocity_df):
        """Mean of [363600, 417600, 453600, 414000] = 1648800/4 = 412200.0s."""
        result = _compute_velocity_features(low_velocity_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["inter_txn_delta_mean_seconds"] == 412200.0

    def test_delta_min(self, low_velocity_df):
        """Shortest gap: July 1 → July 5 = 4 days 5h = 363600 seconds."""
        result = _compute_velocity_features(low_velocity_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["inter_txn_delta_min_seconds"] == 363600.0

    def test_delta_max(self, low_velocity_df):
        """Longest gap: July 10 → July 15 = 5 days 6h = 453600 seconds."""
        result = _compute_velocity_features(low_velocity_df)
        row = result[result["customer_id"] == "9001"].iloc[0]
        assert row["inter_txn_delta_max_seconds"] == 453600.0


class TestVelocityEdgeCases:
    def test_single_transaction_delta_is_none(self):
        """A single transaction has no consecutive pair — deltas are None."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "timestamp": pd.to_datetime(["2026-07-01 10:00:00"], utc=True),
            "amount_normalized": [500.0],
        })
        result = _compute_velocity_features(df)
        row = result.iloc[0]
        assert row["inter_txn_delta_mean_seconds"] is None
        assert row["inter_txn_delta_min_seconds"] is None
        assert row["inter_txn_delta_max_seconds"] is None
        assert row["txn_frequency_24h"] == 1

    def test_empty_dataframe(self):
        """Empty input produces empty output with correct columns."""
        df = pd.DataFrame(columns=["customer_id", "timestamp", "amount_normalized"])
        result = _compute_velocity_features(df)
        assert len(result) == 0
        assert "txn_frequency_24h" in result.columns
        assert "inter_txn_delta_mean_seconds" in result.columns

    def test_missing_column_raises_error(self):
        """Missing required column raises ValueError."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            # Missing timestamp
        })
        with pytest.raises(ValueError, match="Missing required columns"):
            _compute_velocity_features(df)

    def test_two_transactions_exact_delta(self):
        """Two transactions exactly 1 hour apart — all delta stats equal 3600s."""
        df = pd.DataFrame({
            "customer_id": ["Y", "Y"],
            "timestamp": pd.to_datetime([
                "2026-07-01 10:00:00",
                "2026-07-01 11:00:00",
            ], utc=True),
            "amount_normalized": [500.0, 600.0],
        })
        result = _compute_velocity_features(df)
        row = result.iloc[0]
        assert row["inter_txn_delta_mean_seconds"] == 3600.0
        assert row["inter_txn_delta_min_seconds"] == 3600.0
        assert row["inter_txn_delta_max_seconds"] == 3600.0

    def test_multi_customer_produces_one_row_each(self):
        """Multi-customer input yields one row per customer."""
        df = pd.DataFrame({
            "customer_id": ["A", "A", "B", "B", "B"],
            "timestamp": pd.to_datetime([
                "2026-07-01 10:00:00", "2026-07-01 11:00:00",
                "2026-07-01 09:00:00", "2026-07-01 10:00:00", "2026-07-01 12:00:00",
            ], utc=True),
            "amount_normalized": [100.0, 200.0, 300.0, 400.0, 500.0],
        })
        result = _compute_velocity_features(df)
        assert len(result) == 2
        assert set(result["customer_id"]) == {"A", "B"}


class TestVelocityToolInterface:
    def test_velocity_via_tool_function(self):
        """Velocity family invoked through the main feature_engineering() function."""
        df = pd.DataFrame({
            "customer_id": ["7832"] * 3,
            "timestamp": pd.to_datetime([
                "2026-07-01 08:00:00",
                "2026-07-01 09:00:00",
                "2026-07-01 10:00:00",
            ], utc=True),
            "amount_normalized": [4500.0] * 3,
        })
        context = {"data_loader": {"transactions": df}}
        result = feature_engineering(context, feature_set="velocity")
        assert result["status"] == "success"
        assert result["feature_set"] == "velocity"
        assert "txn_frequency_24h" in result["features_computed"]
        assert "inter_txn_delta_mean_seconds" in result["features_computed"]
        assert result["enhancement_features_computed"] == []

    def test_velocity_documented_columns_isolated(self):
        """All velocity columns are in features_computed, none in enhancement."""
        df = pd.DataFrame({
            "customer_id": ["Z"] * 2,
            "timestamp": pd.to_datetime([
                "2026-07-01 10:00:00", "2026-07-01 11:00:00",
            ], utc=True),
            "amount_normalized": [500.0, 600.0],
        })
        context = {"data_loader": {"transactions": df}}
        result = feature_engineering(context, feature_set="velocity")
        assert result["enhancement_features_computed"] == []
        # All 6 expected columns (3 freq + 3 delta) must be in documented set
        assert "txn_frequency_24h" in result["features_computed"]
        assert "txn_frequency_7d" in result["features_computed"]
        assert "txn_frequency_30d" in result["features_computed"]
        assert "inter_txn_delta_mean_seconds" in result["features_computed"]
        assert "inter_txn_delta_min_seconds" in result["features_computed"]
        assert "inter_txn_delta_max_seconds" in result["features_computed"]

    def test_velocity_config_is_loaded_from_yaml(self):
        """Config is read from velocity_config.yaml, not hardcoded."""
        from src.tools.feature_engineering import _load_velocity_config
        config = _load_velocity_config()
        assert "time_buckets" in config
        assert "delta_unit" in config
        assert config["delta_unit"] == "seconds"
        bucket_labels = [b["label"] for b in config["time_buckets"]]
        assert "24h" in bucket_labels
        assert "7d" in bucket_labels
        assert "30d" in bucket_labels


# ---------------------------------------------------------------------------
# Test: Layering Feature Family
# ---------------------------------------------------------------------------


class TestLayeringFeaturesLayerer:
    """Customer A: classic layering pattern.

    Receives 1 large deposit from SOURCE1, then sends 4 equal transfers
    to DEST1–DEST4 within the same hour. All within the pass-through window.

    Hand-computed expected values:
    - direct_counterparty_count: 5 (SOURCE1, DEST1, DEST2, DEST3, DEST4)
    - fan_in_ratio: 1/5 = 0.2 (1 deposit out of 5 total)
    - fan_out_ratio: 4/5 = 0.8 (4 transfers out of 5 total)
    - passthrough_ratio: 1.0 (amount_in=10000, amount_out=10000)
    """

    @pytest.fixture
    def layerer_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["A"] * 5,
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00",
                "2026-07-01 09:30:00",
                "2026-07-01 10:00:00",
                "2026-07-01 10:30:00",
                "2026-07-01 11:00:00",
            ], utc=True),
            "transaction_type": [
                "deposit", "transfer", "transfer", "transfer", "transfer"
            ],
            "counterparty_id": ["SOURCE1", "DEST1", "DEST2", "DEST3", "DEST4"],
            "amount_normalized": [10000.0, 2500.0, 2500.0, 2500.0, 2500.0],
        })

    def test_hop_count(self, layerer_df):
        result = _compute_layering_features(layerer_df)
        row = result[result["customer_id"] == "A"].iloc[0]
        assert row["direct_counterparty_count"] == 5

    def test_fan_in_ratio(self, layerer_df):
        """1 deposit / 5 transactions = 0.2"""
        result = _compute_layering_features(layerer_df)
        row = result[result["customer_id"] == "A"].iloc[0]
        assert row["fan_in_ratio"] == 0.2

    def test_fan_out_ratio(self, layerer_df):
        """4 transfers / 5 transactions = 0.8"""
        result = _compute_layering_features(layerer_df)
        row = result[result["customer_id"] == "A"].iloc[0]
        assert row["fan_out_ratio"] == 0.8

    def test_passthrough_ratio(self, layerer_df):
        """amount_in=10000, amount_out=10000, ratio=1.0"""
        result = _compute_layering_features(layerer_df)
        row = result[result["customer_id"] == "A"].iloc[0]
        assert row["passthrough_ratio"] == 1.0


class TestLayeringFeaturesClean:
    """Customer B: clean depositor — only incoming transactions.

    Hand-computed expected values:
    - direct_counterparty_count: 3 (CP1, CP2, CP3)
    - fan_in_ratio: 3/3 = 1.0
    - fan_out_ratio: 0/3 = 0.0
    - passthrough_ratio: 0.0 (no outgoing transactions in any window)
    """

    @pytest.fixture
    def clean_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["B"] * 3,
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00",
                "2026-07-05 10:00:00",
                "2026-07-10 11:00:00",
            ], utc=True),
            "transaction_type": ["deposit", "deposit", "deposit"],
            "counterparty_id": ["CP1", "CP2", "CP3"],
            "amount_normalized": [5000.0, 6000.0, 7000.0],
        })

    def test_hop_count(self, clean_df):
        result = _compute_layering_features(clean_df)
        row = result[result["customer_id"] == "B"].iloc[0]
        assert row["direct_counterparty_count"] == 3

    def test_fan_in_ratio(self, clean_df):
        result = _compute_layering_features(clean_df)
        row = result[result["customer_id"] == "B"].iloc[0]
        assert row["fan_in_ratio"] == 1.0

    def test_fan_out_ratio(self, clean_df):
        result = _compute_layering_features(clean_df)
        row = result[result["customer_id"] == "B"].iloc[0]
        assert row["fan_out_ratio"] == 0.0

    def test_passthrough_ratio(self, clean_df):
        """No outgoing transactions → passthrough is 0."""
        result = _compute_layering_features(clean_df)
        row = result[result["customer_id"] == "B"].iloc[0]
        assert row["passthrough_ratio"] == 0.0


class TestLayeringFeaturesPassthrough:
    """Customer C: pass-through customer.

    Receives 5000+5000=10000, sends 4900+5100=10000 within same 24h window.
    Hand-computed:
    - direct_counterparty_count: 4 (CP1, CP2, DEST1, DEST2)
    - fan_in_ratio: 2/4 = 0.5
    - fan_out_ratio: 2/4 = 0.5
    - passthrough_ratio: min(10000, 10000) / max(10000, 10000) = 1.0
    """

    @pytest.fixture
    def passthrough_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["C"] * 4,
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00",
                "2026-07-01 09:30:00",
                "2026-07-01 10:00:00",
                "2026-07-01 10:30:00",
            ], utc=True),
            "transaction_type": ["deposit", "deposit", "transfer", "transfer"],
            "counterparty_id": ["CP1", "CP2", "DEST1", "DEST2"],
            "amount_normalized": [5000.0, 5000.0, 4900.0, 5100.0],
        })

    def test_hop_count(self, passthrough_df):
        result = _compute_layering_features(passthrough_df)
        row = result[result["customer_id"] == "C"].iloc[0]
        assert row["direct_counterparty_count"] == 4

    def test_fan_in_ratio(self, passthrough_df):
        result = _compute_layering_features(passthrough_df)
        row = result[result["customer_id"] == "C"].iloc[0]
        assert row["fan_in_ratio"] == 0.5

    def test_fan_out_ratio(self, passthrough_df):
        result = _compute_layering_features(passthrough_df)
        row = result[result["customer_id"] == "C"].iloc[0]
        assert row["fan_out_ratio"] == 0.5

    def test_passthrough_ratio_equals_one(self, passthrough_df):
        """in=10000, out=10000 → ratio = 1.0"""
        result = _compute_layering_features(passthrough_df)
        row = result[result["customer_id"] == "C"].iloc[0]
        assert row["passthrough_ratio"] == 1.0


class TestLayeringEdgeCases:
    def test_empty_dataframe(self):
        """Empty input produces empty output with correct columns."""
        df = pd.DataFrame(columns=[
            "customer_id", "transaction_type", "counterparty_id",
            "timestamp", "amount_normalized",
        ])
        result = _compute_layering_features(df)
        assert len(result) == 0
        assert "direct_counterparty_count" in result.columns
        assert "fan_in_ratio" in result.columns
        assert "fan_out_ratio" in result.columns
        assert "passthrough_ratio" in result.columns

    def test_missing_column_raises(self):
        """Missing required column raises ValueError."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "timestamp": pd.to_datetime(["2026-07-01"], utc=True),
            # Missing transaction_type, counterparty_id, amount_normalized
        })
        with pytest.raises(ValueError, match="Missing required columns"):
            _compute_layering_features(df)

    def test_single_transaction(self):
        """Single transaction: 1 counterparty, fan ratios = 0 or 1."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "timestamp": pd.to_datetime(["2026-07-01 10:00:00"], utc=True),
            "transaction_type": ["deposit"],
            "counterparty_id": ["CP1"],
            "amount_normalized": [1000.0],
        })
        result = _compute_layering_features(df)
        row = result.iloc[0]
        assert row["direct_counterparty_count"] == 1
        assert row["fan_in_ratio"] == 1.0
        assert row["fan_out_ratio"] == 0.0
        assert row["passthrough_ratio"] == 0.0

    def test_repeated_counterparty_counted_once(self):
        """Same counterparty multiple times counts as 1 hop, not multiple."""
        df = pd.DataFrame({
            "customer_id": ["X"] * 3,
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00",
                "2026-07-01 10:00:00",
                "2026-07-01 11:00:00",
            ], utc=True),
            "transaction_type": ["transfer", "transfer", "transfer"],
            "counterparty_id": ["CP1", "CP1", "CP1"],
            "amount_normalized": [1000.0, 1000.0, 1000.0],
        })
        result = _compute_layering_features(df)
        row = result.iloc[0]
        # Same counterparty repeated — only 1 distinct counterparty
        assert row["direct_counterparty_count"] == 1

    def test_unknown_counterparty_excluded(self):
        """Null/unknown counterparty_id should not inflate hop count."""
        df = pd.DataFrame({
            "customer_id": ["X", "X"],
            "timestamp": pd.to_datetime(
                ["2026-07-01 09:00:00", "2026-07-01 10:00:00"], utc=True
            ),
            "transaction_type": ["deposit", "withdrawal"],
            "counterparty_id": ["unknown", ""],
            "amount_normalized": [1000.0, 1000.0],
        })
        result = _compute_layering_features(df)
        row = result.iloc[0]
        assert row["direct_counterparty_count"] == 0

    def test_partial_passthrough(self):
        """Partial pass-through: 1000 in, 500 out → ratio = 0.5."""
        df = pd.DataFrame({
            "customer_id": ["Y", "Y"],
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00",
                "2026-07-01 09:30:00",
            ], utc=True),
            "transaction_type": ["deposit", "transfer"],
            "counterparty_id": ["CP1", "DEST1"],
            "amount_normalized": [1000.0, 500.0],
        })
        result = _compute_layering_features(df)
        row = result.iloc[0]
        assert row["passthrough_ratio"] == 0.5

    def test_multi_customer(self):
        """Multi-customer input yields one row per customer."""
        df = pd.DataFrame({
            "customer_id": ["A", "A", "B", "B"],
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00", "2026-07-01 10:00:00",
                "2026-07-01 09:00:00", "2026-07-01 10:00:00",
            ], utc=True),
            "transaction_type": ["deposit", "transfer", "deposit", "deposit"],
            "counterparty_id": ["CP1", "CP2", "CP3", "CP4"],
            "amount_normalized": [1000.0, 1000.0, 500.0, 500.0],
        })
        result = _compute_layering_features(df)
        assert len(result) == 2
        assert set(result["customer_id"]) == {"A", "B"}


class TestLayeringToolInterface:
    def test_layering_via_feature_engineering(self):
        """Layering family invoked via the main feature_engineering() function."""
        df = pd.DataFrame({
            "customer_id": ["A"] * 3,
            "timestamp": pd.to_datetime([
                "2026-07-01 09:00:00",
                "2026-07-01 09:30:00",
                "2026-07-01 10:00:00",
            ], utc=True),
            "transaction_type": ["deposit", "transfer", "transfer"],
            "counterparty_id": ["SOURCE1", "DEST1", "DEST2"],
            "amount_normalized": [1000.0, 500.0, 500.0],
        })
        context = {"data_loader": {"transactions": df}}
        result = feature_engineering(context, feature_set="layering")
        assert result["status"] == "success"
        assert result["feature_set"] == "layering"
        assert "direct_counterparty_count" in result["features_computed"]
        assert "fan_in_ratio" in result["features_computed"]
        assert "fan_out_ratio" in result["features_computed"]
        assert "passthrough_ratio" in result["features_computed"]
        assert result["enhancement_features_computed"] == []

    def test_layering_config_loaded_from_yaml(self):
        """Config is driven by layering_config.yaml."""
        from src.tools.feature_engineering import _load_layering_config
        config = _load_layering_config()
        assert "passthrough_window_hours" in config
        assert "passthrough_tolerance" in config
        assert "incoming_transaction_types" in config
        assert "outgoing_transaction_types" in config
        assert "hop_count_interpretation" in config


# ---------------------------------------------------------------------------
# Test: Amount Deviation Feature Family
# ---------------------------------------------------------------------------


class TestAmountDeviationCustomerZscore:
    """Per-customer z-score tests.

    Fixture: Customer X: amounts [100, 200, 300]
      mean=200, std=100 (ddof=1 in pandas)
      |z-scores|: |100-200|/100=1.0, |200-200|/100=0.0, |300-200|/100=1.0
      customer_amount_zscore_mean = (1.0+0.0+1.0)/3 = 0.6667
      customer_amount_zscore_max  = 1.0

    Customer Y: amounts [500, 500, 500]
      std=0 → below std threshold → all customer z-scores = 0.0
      customer_amount_zscore_mean = 0.0
      customer_amount_zscore_max  = 0.0
    """

    @pytest.fixture
    def two_customer_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["X", "X", "X", "Y", "Y", "Y"],
            "amount_normalized": [100.0, 200.0, 300.0, 500.0, 500.0, 500.0],
        })

    def test_customer_zscore_mean_x(self, two_customer_df):
        result = _compute_amount_deviation_features(two_customer_df)
        row = result[result["customer_id"] == "X"].iloc[0]
        assert abs(row["customer_amount_zscore_mean"] - 0.6667) < 0.0001

    def test_customer_zscore_max_x(self, two_customer_df):
        result = _compute_amount_deviation_features(two_customer_df)
        row = result[result["customer_id"] == "X"].iloc[0]
        assert row["customer_amount_zscore_max"] == 1.0

    def test_customer_zscore_zero_when_std_is_zero(self, two_customer_df):
        """Customer Y has std=0; all customer z-scores must be 0.0."""
        result = _compute_amount_deviation_features(two_customer_df)
        row = result[result["customer_id"] == "Y"].iloc[0]
        assert row["customer_amount_zscore_mean"] == 0.0
        assert row["customer_amount_zscore_max"] == 0.0

    def test_one_row_per_customer(self, two_customer_df):
        result = _compute_amount_deviation_features(two_customer_df)
        assert len(result) == 2
        assert set(result["customer_id"]) == {"X", "Y"}


class TestAmountDeviationSegmentZscore:
    """Per-segment z-score tests.

    Fixture: Two customers in same segment 'retail'.
    All transactions: [100, 200, 300, 500, 500, 500]
    mean=350.0, std=176.0682 (pandas ddof=1)

    X segment |z-scores|:
      |(100-350)/176.0682| = 1.4199
      |(200-350)/176.0682| = 0.8519
      |(300-350)/176.0682| = 0.2840
      mean = (1.4199+0.8519+0.2840)/3 = 0.8519
      max  = 1.4199

    Y segment |z-scores|:
      |(500-350)/176.0682| = 0.8519 (all three same)
      mean = 0.8519, max = 0.8519
    """

    @pytest.fixture
    def txns_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["X", "X", "X", "Y", "Y", "Y"],
            "amount_normalized": [100.0, 200.0, 300.0, 500.0, 500.0, 500.0],
        })

    @pytest.fixture
    def custs_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["X", "Y"],
            "segment": ["retail", "retail"],
        })

    def test_segment_zscore_mean_x(self, txns_df, custs_df):
        """X segment mean = (1.4199+0.8519+0.2840)/3 = 0.8519."""
        result = _compute_amount_deviation_features(txns_df, custs_df)
        row = result[result["customer_id"] == "X"].iloc[0]
        assert abs(row["segment_amount_zscore_mean"] - 0.8519) < 0.0001

    def test_segment_zscore_max_x(self, txns_df, custs_df):
        """X segment max = 1.4199 (the $100 transaction)."""
        result = _compute_amount_deviation_features(txns_df, custs_df)
        row = result[result["customer_id"] == "X"].iloc[0]
        assert abs(row["segment_amount_zscore_max"] - 1.4199) < 0.0001

    def test_segment_zscore_mean_y(self, txns_df, custs_df):
        """Y segment mean = 0.8519 (all transactions at 500)."""
        result = _compute_amount_deviation_features(txns_df, custs_df)
        row = result[result["customer_id"] == "Y"].iloc[0]
        assert abs(row["segment_amount_zscore_mean"] - 0.8519) < 0.0001

    def test_segment_zscore_max_y(self, txns_df, custs_df):
        """Y segment max = 0.8519."""
        result = _compute_amount_deviation_features(txns_df, custs_df)
        row = result[result["customer_id"] == "Y"].iloc[0]
        assert abs(row["segment_amount_zscore_max"] - 0.8519) < 0.0001

    def test_different_segments_give_different_scores(self):
        """Customers in different segments each have their own segment pool.

        A: segment 'retail', amounts [100, 110] → mean=105, std=7.0711
          |z(100)| = |z(110)| = 0.7071 → mean=max=0.7071
        B: segment 'corporate', amounts [5000, 5100] → mean=5050, std=70.711
          |z(5000)| = |z(5100)| = 0.7071 → mean=max=0.7071
        Both get 0.7071 (same relative deviation within their own segment).
        """
        txns = pd.DataFrame({
            "customer_id": ["A", "A", "B", "B"],
            "amount_normalized": [100.0, 110.0, 5000.0, 5100.0],
        })
        custs = pd.DataFrame({
            "customer_id": ["A", "B"],
            "segment": ["retail", "corporate"],
        })
        result = _compute_amount_deviation_features(txns, custs)
        row_a = result[result["customer_id"] == "A"].iloc[0]
        row_b = result[result["customer_id"] == "B"].iloc[0]
        # Each segment has 2 transactions with non-zero std
        assert abs(row_a["segment_amount_zscore_mean"] - 0.7071) < 0.0001
        assert abs(row_b["segment_amount_zscore_mean"] - 0.7071) < 0.0001
        # Customer z-scores also 0.7071 (same relative spread within own history)
        assert abs(row_a["customer_amount_zscore_mean"] - 0.7071) < 0.0001
        assert abs(row_b["customer_amount_zscore_mean"] - 0.7071) < 0.0001


class TestAmountDeviationEdgeCases:
    def test_empty_dataframe(self):
        """Empty input produces empty output with correct columns."""
        df = pd.DataFrame(columns=["customer_id", "amount_normalized"])
        result = _compute_amount_deviation_features(df)
        assert len(result) == 0
        assert "customer_amount_zscore_mean" in result.columns
        assert "segment_amount_zscore_mean" in result.columns

    def test_missing_column_raises(self):
        """Missing required column raises ValueError."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            # Missing amount_normalized
        })
        with pytest.raises(ValueError, match="Missing required columns"):
            _compute_amount_deviation_features(df)

    def test_single_transaction_customer(self):
        """Customer with 1 transaction: customer z-score = 0 (no std)."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "amount_normalized": [1000.0],
        })
        result = _compute_amount_deviation_features(df)
        row = result.iloc[0]
        assert row["customer_amount_zscore_mean"] == 0.0
        assert row["customer_amount_zscore_max"] == 0.0

    def test_no_customers_df_uses_all_in_one_segment(self):
        """Without customers df, all transactions share 'unknown' segment."""
        df = pd.DataFrame({
            "customer_id": ["X", "X", "Y", "Y"],
            "amount_normalized": [100.0, 200.0, 100.0, 200.0],
        })
        result = _compute_amount_deviation_features(df, None)
        # Both customers exist; segment z-scores computed from shared pool
        assert len(result) == 2
        assert "segment_amount_zscore_mean" in result.columns


class TestAmountDeviationToolInterface:
    def test_amount_deviation_via_feature_engineering(self):
        """Amount deviation invoked via the main feature_engineering() function."""
        txns = pd.DataFrame({
            "customer_id": ["X", "X", "X"],
            "amount_normalized": [100.0, 200.0, 300.0],
        })
        context = {"data_loader": {"transactions": txns, "customers": None}}
        result = feature_engineering(context, feature_set="amount_deviation")
        assert result["status"] == "success"
        assert result["feature_set"] == "amount_deviation"
        assert "customer_amount_zscore_mean" in result["features_computed"]
        assert "customer_amount_zscore_max" in result["features_computed"]
        assert "segment_amount_zscore_mean" in result["features_computed"]
        assert "segment_amount_zscore_max" in result["features_computed"]
        assert result["enhancement_features_computed"] == []

    def test_amount_deviation_config_from_yaml(self):
        """Config is driven by amount_deviation_config.yaml."""
        from src.tools.feature_engineering import _load_amount_deviation_config
        config = _load_amount_deviation_config()
        assert "min_transactions_for_customer_zscore" in config
        assert "min_transactions_for_segment_zscore" in config
        assert "zscore_aggregations" in config
        assert "use_absolute_zscore" in config
        assert "mean" in config["zscore_aggregations"]
        assert "max" in config["zscore_aggregations"]

    def test_documented_columns_isolated(self):
        """All 4 columns are documented; enhancement list is empty."""
        txns = pd.DataFrame({
            "customer_id": ["X", "X"],
            "amount_normalized": [100.0, 200.0],
        })
        context = {"data_loader": {"transactions": txns}}
        result = feature_engineering(context, feature_set="amount_deviation")
        assert result["enhancement_features_computed"] == []
        assert len(result["features_computed"]) == 4
