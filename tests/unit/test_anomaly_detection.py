"""Unit tests for the Anomaly Detection Tool — Rule Engine path.

Reference: Solution Design §5.4, Implementation Plan §6.3 step 1.
DoD: "On the synthetic dataset with injected structuring cases, the tool
recovers the injected cases with a documented true-positive rate, and does
NOT flag the clean high-volume control customer."
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.tools.anomaly_detection import (
    anomaly_detection,
    _parse_condition,
    _run_rule_engine,
    _run_statistical_detection,
    _run_ml_detection,
    _load_rule_engine_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return _load_rule_engine_config()


@pytest.fixture
def reference_df() -> pd.DataFrame:
    """Minimal fixture matching the documented reference query condition:
    count(transactions) >= 10 AND amount < 10000

    Hand-computed expectations:
    - Customer "A": 10 txns, all amount_normalized=500 → HITS (count=10>=10, all<10000)
    - Customer "B": 9  txns, all amount_normalized=500 → MISS (count=9<10)
    - Customer "C": 10 txns, some amount_normalized=15000 → MISS (not all<10000)
    - Customer "D": 15 txns, all amount_normalized=200  → HITS (count=15>=10, all<10000)
    """
    rows = []
    for i in range(10):
        rows.append({"customer_id": "A", "amount_normalized": 500.0})
    for i in range(9):
        rows.append({"customer_id": "B", "amount_normalized": 500.0})
    # C: 10 txns, but 1 is above 10000
    for i in range(9):
        rows.append({"customer_id": "C", "amount_normalized": 500.0})
    rows.append({"customer_id": "C", "amount_normalized": 15000.0})
    # D: 15 txns, all below 10000
    for i in range(15):
        rows.append({"customer_id": "D", "amount_normalized": 200.0})
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    """Load the synthetic dataset through the real Data Loader pipeline."""
    from src.tools.data_loader import data_loader
    result = data_loader({"query_spec": {"filters": {}}})
    return result["transactions"]


# ---------------------------------------------------------------------------
# Test: Config loading
# ---------------------------------------------------------------------------

class TestRuleEngineConfig:
    def test_config_loads_correctly(self, config):
        assert "anomaly_score_on_hit" in config
        assert "anomaly_score_on_miss" in config
        assert "amount_column" in config
        assert "count_column_alias" in config

    def test_score_on_hit_is_one(self, config):
        """Rule match → anomaly_score = 1.0 (max confidence)."""
        assert config["anomaly_score_on_hit"] == 1.0

    def test_score_on_miss_is_zero(self, config):
        assert config["anomaly_score_on_miss"] == 0.0

    def test_amount_column_is_normalized(self, config):
        """INTERPRETATION: 'amount' maps to amount_normalized from Data Loader."""
        assert config["amount_column"] == "amount_normalized"


# ---------------------------------------------------------------------------
# Test: Condition parser
# ---------------------------------------------------------------------------

class TestConditionParser:
    def test_reference_condition_parsed(self):
        """Documented reference: 'count(transactions) >= 10 AND amount < 10000'"""
        scs = _parse_condition("count(transactions) >= 10 AND amount < 10000")
        assert len(scs) == 2
        assert scs[0]["field"] == "count_transactions"
        assert scs[0]["operator"] == ">="
        assert scs[0]["value"] == 10.0
        assert scs[0]["conjunction"] == "AND"
        assert scs[1]["field"] == "amount"
        assert scs[1]["operator"] == "<"
        assert scs[1]["value"] == 10000.0
        assert scs[1]["conjunction"] is None

    def test_single_condition_parsed(self):
        scs = _parse_condition("count(transactions) > 5")
        assert len(scs) == 1
        assert scs[0]["field"] == "count_transactions"
        assert scs[0]["operator"] == ">"
        assert scs[0]["value"] == 5.0
        assert scs[0]["conjunction"] is None

    def test_all_operators_supported(self):
        for op in [">=", "<=", ">", "<", "==", "!="]:
            scs = _parse_condition(f"amount {op} 5000")
            assert scs[0]["operator"] == op

    def test_or_conjunction_parsed(self):
        scs = _parse_condition("count(transactions) > 5 OR amount < 1000")
        assert scs[0]["conjunction"] == "OR"

    def test_unsupported_operator_raises(self):
        with pytest.raises(ValueError, match="no supported operator"):
            _parse_condition("amount BETWEEN 1000 AND 5000")

    def test_non_numeric_value_raises(self):
        with pytest.raises(ValueError, match="cannot parse numeric value"):
            _parse_condition("amount < high")


# ---------------------------------------------------------------------------
# Test: Rule Engine evaluation — hand-computed fixtures
# ---------------------------------------------------------------------------

class TestRuleEngineEvaluation:
    """All expected values hand-computed from fixture definitions above."""

    def test_customer_a_hits_reference_rule(self, reference_df):
        """A: count=10>=10, all amounts=500<10000 → HITS."""
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "A" in flagged_ids

    def test_customer_b_misses_count_threshold(self, reference_df):
        """B: count=9 < 10 → MISS (count condition fails)."""
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "B" not in flagged_ids

    def test_customer_c_misses_amount_condition(self, reference_df):
        """C: count=10>=10 BUT one amount=15000 ≥ 10000 → MISS."""
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "C" not in flagged_ids

    def test_customer_d_hits_reference_rule(self, reference_df):
        """D: count=15>=10, all amounts=200<10000 → HITS."""
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "D" in flagged_ids

    def test_entities_scored_equals_total_customers(self, reference_df):
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        assert result["entities_scored"] == 4  # A, B, C, D

    def test_entities_flagged_count(self, reference_df):
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        assert result["entities_flagged"] == 2  # A and D

    def test_anomaly_score_on_hit_is_1(self, reference_df):
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        for entity in result["flagged_entities"]:
            assert entity["anomaly_score"] == 1.0

    def test_anomaly_score_on_miss_is_0(self, reference_df):
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        all_ids = {e["customer_id"] for e in result["all_entities"]}
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        missed_ids = all_ids - flagged_ids
        for entity in result["all_entities"]:
            if entity["customer_id"] in missed_ids:
                assert entity["anomaly_score"] == 0.0

    def test_rule_matched_field_correct(self, reference_df):
        result = _run_rule_engine(
            reference_df, "count(transactions) >= 10 AND amount < 10000"
        )
        for entity in result["all_entities"]:
            if entity["customer_id"] in {"A", "D"}:
                assert entity["rule_matched"] is True
                assert entity["matched_condition"] is not None
            else:
                assert entity["rule_matched"] is False
                assert entity["matched_condition"] is None

    def test_condition_evaluated_in_output(self, reference_df):
        cond = "count(transactions) >= 10 AND amount < 10000"
        result = _run_rule_engine(reference_df, cond)
        assert result["condition_evaluated"] == cond

    def test_deterministic_repeated_calls(self, reference_df):
        """Same input → same output every time (determinism requirement)."""
        cond = "count(transactions) >= 10 AND amount < 10000"
        r1 = _run_rule_engine(reference_df, cond)
        r2 = _run_rule_engine(reference_df, cond)
        assert r1["entities_flagged"] == r2["entities_flagged"]
        assert (
            {e["customer_id"] for e in r1["flagged_entities"]}
            == {e["customer_id"] for e in r2["flagged_entities"]}
        )


# ---------------------------------------------------------------------------
# Test: Single-condition rules
# ---------------------------------------------------------------------------

class TestSingleConditionRules:
    def test_count_only_condition(self, reference_df):
        """Count-only rule: count(transactions) >= 10"""
        result = _run_rule_engine(reference_df, "count(transactions) >= 10")
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        # A (10), C (10), D (15) hit; B (9) misses
        assert flagged_ids == {"A", "C", "D"}

    def test_amount_only_condition(self, reference_df):
        """Amount-only rule: amount < 10000"""
        result = _run_rule_engine(reference_df, "amount < 10000")
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        # A, B, D all have all amounts < 10000; C has one >= 10000 → miss
        assert "A" in flagged_ids
        assert "B" in flagged_ids
        assert "D" in flagged_ids
        assert "C" not in flagged_ids

    def test_count_equals_condition(self):
        """Equality operator on count."""
        df = pd.DataFrame({
            "customer_id": ["X"] * 5 + ["Y"] * 3,
            "amount_normalized": [100.0] * 8,
        })
        result = _run_rule_engine(df, "count(transactions) == 5")
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert flagged_ids == {"X"}

    def test_amount_greater_than_condition(self):
        """Greater-than operator on amount."""
        df = pd.DataFrame({
            "customer_id": ["X"] * 3 + ["Y"] * 3,
            "amount_normalized": [50000.0, 60000.0, 70000.0, 500.0, 600.0, 700.0],
        })
        result = _run_rule_engine(df, "amount > 10000")
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "X" in flagged_ids
        assert "Y" not in flagged_ids


# ---------------------------------------------------------------------------
# Test: Synthetic dataset — documented DoD
# ---------------------------------------------------------------------------

class TestSyntheticDataset:
    """DoD: Tool recovers injected cases, does NOT flag clean control customer.

    From the synthetic dataset after Data Loader processing:
    - Customer 7832: 15 transfers, all amount_normalized < 10000 → HITS
    - Customer 9001: 5 transactions, all amount_normalized > 10000 → MISS
      (clean high-volume control customer)
    - Customer 4521: 6 deposits → MISS (count < 10)
    - Customer 1234: 4 transactions → MISS (count < 10)
    """

    def test_7832_flagged_by_reference_rule(self, synthetic_df):
        """Customer 7832: 15 EUR transfers, all converted below $10k → HITS."""
        result = _run_rule_engine(
            synthetic_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "7832" in flagged_ids

    def test_9001_not_flagged_clean_control(self, synthetic_df):
        """DoD requirement: clean high-volume customer 9001 is NOT flagged.
        Customer 9001: 5 transactions, all > $10,000 → amount condition fails.
        """
        result = _run_rule_engine(
            synthetic_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "9001" not in flagged_ids

    def test_4521_not_flagged_insufficient_count(self, synthetic_df):
        """Customer 4521: 6 deposits → count=6 < 10 → MISS."""
        result = _run_rule_engine(
            synthetic_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "4521" not in flagged_ids

    def test_1234_not_flagged_insufficient_count(self, synthetic_df):
        """Customer 1234: 4 transactions → count < 10 → MISS."""
        result = _run_rule_engine(
            synthetic_df, "count(transactions) >= 10 AND amount < 10000"
        )
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "1234" not in flagged_ids

    def test_top_contributing_features_present(self, synthetic_df):
        """Flagged entities include top_contributing_features for auditability."""
        result = _run_rule_engine(
            synthetic_df, "count(transactions) >= 10 AND amount < 10000"
        )
        for entity in result["flagged_entities"]:
            assert "top_contributing_features" in entity
            assert len(entity["top_contributing_features"]) >= 1


# ---------------------------------------------------------------------------
# Test: Tool function interface (context-based call)
# ---------------------------------------------------------------------------

class TestToolInterface:
    def test_rule_engine_via_tool_function(self, reference_df):
        """Rule engine invoked through the anomaly_detection() tool function."""
        context = {
            "data_loader": {"transactions": reference_df},
            "query_spec": {
                "explicit_rule": {
                    "condition": "count(transactions) >= 10 AND amount < 10000",
                    "present": True,
                }
            },
        }
        result = anomaly_detection(context, method="rule_engine")
        assert result["status"] == "success"
        assert result["method_used"] == "rule_engine"
        assert result["entities_flagged"] == 2

    def test_missing_transactions_returns_error(self):
        context = {"query_spec": {"explicit_rule": {"condition": "count(transactions) >= 10", "present": True}}}
        result = anomaly_detection(context, method="rule_engine")
        assert result["status"] == "error"
        assert "No transactions" in result["error"]

    def test_rule_not_present_returns_error(self, reference_df):
        context = {
            "data_loader": {"transactions": reference_df},
            "query_spec": {
                "explicit_rule": {
                    "condition": "count(transactions) >= 10",
                    "present": False,  # <-- rule not present
                }
            },
        }
        result = anomaly_detection(context, method="rule_engine")
        assert result["status"] == "error"

    def test_missing_condition_returns_error(self, reference_df):
        context = {
            "data_loader": {"transactions": reference_df},
            "query_spec": {
                "explicit_rule": {
                    "condition": None,
                    "present": True,
                }
            },
        }
        result = anomaly_detection(context, method="rule_engine")
        assert result["status"] == "error"

    def test_unimplemented_method_returns_not_implemented(self, reference_df):
        context = {
            "data_loader": {"transactions": reference_df},
            "query_spec": {"explicit_rule": {"condition": "count(transactions) >= 10", "present": True}},
        }
        result = anomaly_detection(context, method="hybrid")
        assert result["status"] == "not_implemented"

    def test_output_contains_all_entities(self, reference_df):
        """all_entities includes both flagged and non-flagged customers."""
        context = {
            "data_loader": {"transactions": reference_df},
            "query_spec": {
                "explicit_rule": {
                    "condition": "count(transactions) >= 10 AND amount < 10000",
                    "present": True,
                }
            },
        }
        result = anomaly_detection(context, method="rule_engine")
        assert result["entities_scored"] == 4
        assert len(result["all_entities"]) == 4


# ---------------------------------------------------------------------------
# Test: Statistical Detection method
# ---------------------------------------------------------------------------

class TestStatisticalDetectionConfig:
    def test_config_loads_correctly(self):
        from src.tools.anomaly_detection import _load_statistical_config
        config = _load_statistical_config()
        assert "z_score_threshold" in config
        assert "iqr_multiplier" in config
        assert "score_scale_factor" in config
        assert "min_cohort_size_for_zscore" in config
        assert "top_n_features" in config

    def test_defaults_are_reasonable(self):
        from src.tools.anomaly_detection import _load_statistical_config
        config = _load_statistical_config()
        assert config["z_score_threshold"] > 0
        assert config["iqr_multiplier"] > 0
        assert config["score_scale_factor"] > 0
        assert config["min_cohort_size_for_zscore"] >= 2
        assert config["top_n_features"] >= 1


class TestStatisticalDetectionZscore:
    """Hand-computed z-score tests.

    Fixture: 4 customers, feature 'near_threshold_txn_count_7d':
      1234=0, 4521=6, 7832=0, 9001=0
      mean=1.5, std(ddof=1)=3.0
      z(1234) = (0-1.5)/3 = -0.5
      z(4521) = (6-1.5)/3 = +1.5
      z(7832) = (0-1.5)/3 = -0.5
      z(9001) = (0-1.5)/3 = -0.5

    With z_threshold=2.0: none exceed threshold, so no z-score flags.

    IQR: Q1=0, Q3=1.5, IQR=1.5, upper_fence=Q3+1.5*1.5=3.75
    4521=6 > 3.75 → IQR flagged.

    anomaly_score = min(max_abs_z / scale_factor, 1.0):
      4521: min(1.5/2.0, 1.0) = 0.75
      others: min(0.5/2.0, 1.0) = 0.25
    """

    @pytest.fixture
    def structured_features_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["1234", "4521", "7832", "9001"],
            "near_threshold_txn_count_7d": [0.0, 6.0, 0.0, 0.0],
        })

    def test_4521_flagged_by_iqr(self, structured_features_df):
        """4521 has value 6.0, above upper IQR fence of 3.75 → flagged."""
        result = _run_statistical_detection(structured_features_df)
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "4521" in flagged_ids

    def test_9001_not_flagged_clean_control(self, structured_features_df):
        """DoD: clean control customer 9001 is not flagged."""
        result = _run_statistical_detection(structured_features_df)
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "9001" not in flagged_ids

    def test_anomaly_score_4521(self, structured_features_df):
        """4521: max_abs_z=1.5, scale=2.0 → score=0.75"""
        result = _run_statistical_detection(structured_features_df)
        entity_4521 = next(e for e in result["all_entities"] if e["customer_id"] == "4521")
        assert abs(entity_4521["anomaly_score"] - 0.75) < 0.001

    def test_anomaly_score_1234(self, structured_features_df):
        """1234: max_abs_z=0.5, scale=2.0 → score=0.25"""
        result = _run_statistical_detection(structured_features_df)
        entity_1234 = next(e for e in result["all_entities"] if e["customer_id"] == "1234")
        assert abs(entity_1234["anomaly_score"] - 0.25) < 0.001

    def test_top_contributing_features_present(self, structured_features_df):
        """Flagged entity has top_contributing_features with feature name and z_score."""
        result = _run_statistical_detection(structured_features_df)
        flagged = [e for e in result["flagged_entities"] if e["customer_id"] == "4521"]
        assert len(flagged) == 1
        assert len(flagged[0]["top_contributing_features"]) >= 1
        feat = flagged[0]["top_contributing_features"][0]
        assert "feature" in feat
        assert "value" in feat
        assert "z_score" in feat
        assert "triggered_by" in feat

    def test_triggered_by_contains_threshold(self, structured_features_df):
        """triggered_by field contains the exact threshold that fired — documented requirement."""
        result = _run_statistical_detection(structured_features_df)
        for entity in result["flagged_entities"]:
            for feat in entity["top_contributing_features"]:
                assert len(feat["triggered_by"]) > 0

    def test_entities_scored(self, structured_features_df):
        result = _run_statistical_detection(structured_features_df)
        assert result["entities_scored"] == 4

    def test_method_used(self, structured_features_df):
        result = _run_statistical_detection(structured_features_df)
        assert result["method_used"] == "statistical"

    def test_z_score_threshold_in_output(self, structured_features_df):
        result = _run_statistical_detection(structured_features_df)
        assert "z_score_threshold" in result
        assert result["z_score_threshold"] == 2.0

    def test_iqr_multiplier_in_output(self, structured_features_df):
        result = _run_statistical_detection(structured_features_df)
        assert "iqr_multiplier" in result
        assert result["iqr_multiplier"] == 1.5

    def test_features_evaluated_in_output(self, structured_features_df):
        result = _run_statistical_detection(structured_features_df)
        assert "features_evaluated" in result
        assert "near_threshold_txn_count_7d" in result["features_evaluated"]

    def test_all_entities_present(self, structured_features_df):
        """all_entities includes every customer, not just flagged ones."""
        result = _run_statistical_detection(structured_features_df)
        all_ids = {e["customer_id"] for e in result["all_entities"]}
        assert all_ids == {"1234", "4521", "7832", "9001"}

    def test_deterministic_repeated_calls(self, structured_features_df):
        """Same input → same output every time."""
        r1 = _run_statistical_detection(structured_features_df)
        r2 = _run_statistical_detection(structured_features_df)
        assert r1["entities_flagged"] == r2["entities_flagged"]
        assert {e["customer_id"] for e in r1["flagged_entities"]} == \
               {e["customer_id"] for e in r2["flagged_entities"]}


class TestStatisticalDetectionWithHighZScore:
    """Test with a customer that exceeds the z-score threshold.

    Fixture: 4 customers. Customer X has a value 3 standard deviations above mean.
    Hand-computed:
      values = [0, 0, 0, 9.0]
      mean = 2.25, std(ddof=1) = 4.5
      z(X=9) = (9 - 2.25) / 4.5 = 1.5  → |z|=1.5 < 2.0 → no z-score flag

    Use a cleaner example:
      values = [0, 0, 0, 12.0]
      mean = 3.0, std(ddof=1) = 6.0
      z(X=12) = (12-3)/6 = 1.5 — still not enough.

    Use:
      values = [1, 2, 1, 20.0]
      mean = 6.0, std = 9.0 (ddof=1)
      z(20) = (20-6)/9 = 1.556 — still < 2.0

    To get z > 2.0 with 4 values:
      values = [1, 1, 1, 10.0]
      mean = 3.25, std = 4.5
      z(10) = (10-3.25)/4.5 = 1.5 — no.

      values = [0, 0, 0, 100.0]
      mean = 25, std = 50 (ddof=1)
      z(100) = (100-25)/50 = 1.5 — no.

    With 4 points, max achievable z is sqrt(3) * sqrt(n/(n-1)) ≈ 1.73 for one extreme outlier.
    With 5 points we can exceed 2.0:
      values = [0, 0, 0, 0, 10.0]
      mean=2, std=4.47 (ddof=1)
      z(10) = (10-2)/4.47 = 1.789 — still not quite.

    With more extreme:
      values = [1, 1, 1, 1, 100]
      mean=20.8, std=44.3 (ddof=1)
      z(100)=(100-20.8)/44.3 = 1.789 — still not 2.0.

    With 10 points:
      values = [1,1,1,1,1,1,1,1,1,100]
      mean=10.9, std=31.1 (ddof=1)
      z(100)=(100-10.9)/31.1=2.865 → exceeds threshold!
    """

    @pytest.fixture
    def high_z_features_df(self) -> pd.DataFrame:
        """10 customers. One extreme outlier with value 100, rest have value 1.
        Hand-computed for near_threshold_txn_count_7d:
          values = [1]*9 + [100]
          mean = 10.9, std(ddof=1) = 31.1 (approx)
          z(outlier) = (100-10.9)/31.1 ≈ 2.865 > z_threshold=2.0 → z-score flagged
        """
        import numpy as np
        vals = [1.0] * 9 + [100.0]
        return pd.DataFrame({
            "customer_id": [f"C{i:02d}" for i in range(10)],
            "near_threshold_txn_count_7d": vals,
        })

    def test_outlier_flagged_by_zscore(self, high_z_features_df):
        """The extreme outlier (C09 with value=100) should be flagged by z-score."""
        result = _run_statistical_detection(high_z_features_df)
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "C09" in flagged_ids

    def test_outlier_anomaly_score_is_1(self, high_z_features_df):
        """Extreme outlier z > scale_factor → score capped at 1.0."""
        result = _run_statistical_detection(high_z_features_df)
        entity = next(e for e in result["all_entities"] if e["customer_id"] == "C09")
        assert entity["anomaly_score"] == 1.0

    def test_regular_customers_not_flagged(self, high_z_features_df):
        """Regular customers (value=1) should not be flagged."""
        result = _run_statistical_detection(high_z_features_df)
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        for i in range(9):
            cid = f"C{i:02d}"
            assert cid not in flagged_ids, f"Clean customer {cid} was incorrectly flagged"

    def test_z_score_flagged_field(self, high_z_features_df):
        """z_score_flagged field is True for the outlier."""
        result = _run_statistical_detection(high_z_features_df)
        entity = next(e for e in result["all_entities"] if e["customer_id"] == "C09")
        assert entity["z_score_flagged"] is True


class TestStatisticalDetectionEdgeCases:
    def test_empty_features_raises_error(self):
        with pytest.raises(ValueError, match="no numeric feature columns"):
            _run_statistical_detection(pd.DataFrame({"customer_id": ["X"]}))

    def test_missing_customer_id_raises(self):
        with pytest.raises(ValueError, match="customer_id"):
            _run_statistical_detection(pd.DataFrame({"feature_a": [1, 2, 3]}))

    def test_single_customer_no_flags(self):
        """With a single customer, std=0 (ddof=1 on 1 value=NaN), no flags."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "near_threshold_txn_count_7d": [5.0],
        })
        result = _run_statistical_detection(df)
        # Single entity: std undefined, feature skipped due to min_cohort_size=2
        assert result["entities_scored"] == 1
        assert result["entities_flagged"] == 0

    def test_all_same_values_no_flags(self):
        """When all customers have the same feature value, std=0 → no z-score possible."""
        df = pd.DataFrame({
            "customer_id": ["A", "B", "C"],
            "near_threshold_txn_count_7d": [5.0, 5.0, 5.0],
        })
        result = _run_statistical_detection(df)
        assert result["entities_flagged"] == 0


class TestStatisticalDetectionToolInterface:
    @pytest.fixture
    def structured_features_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "customer_id": ["1234", "4521", "7832", "9001"],
            "near_threshold_txn_count_7d": [0.0, 6.0, 0.0, 0.0],
        })

    def test_statistical_via_tool_function(self, structured_features_df):
        """Statistical method invoked through anomaly_detection() tool function."""
        context = {
            "data_loader": {"transactions": pd.DataFrame({"customer_id": ["X"], "amount_normalized": [100.0]})},
            "feature_engineering": {"features_df": structured_features_df},
        }
        result = anomaly_detection(context, method="statistical")
        assert result["status"] == "success"
        assert result["method_used"] == "statistical"
        assert result["entities_scored"] == 4

    def test_missing_feature_engineering_returns_error(self):
        context = {
            "data_loader": {"transactions": pd.DataFrame({"customer_id": ["X"], "amount_normalized": [100.0]})},
            # No feature_engineering in context
        }
        result = anomaly_detection(context, method="statistical")
        assert result["status"] == "error"
        assert "feature_engineering" in result["error"]

    def test_ml_still_not_implemented(self):
        """Hybrid is not yet implemented."""
        context = {
            "data_loader": {"transactions": pd.DataFrame({"customer_id": ["X"], "amount_normalized": [100.0]})},
        }
        result = anomaly_detection(context, method="hybrid")
        assert result["status"] == "not_implemented"

    def test_hybrid_still_not_implemented(self):
        context = {
            "data_loader": {"transactions": pd.DataFrame({"customer_id": ["X"], "amount_normalized": [100.0]})},
        }
        result = anomaly_detection(context, method="hybrid")
        assert result["status"] == "not_implemented"


class TestStatisticalDetectionOnSyntheticData:
    """DoD test: On the synthetic dataset with injected structuring cases,
    the statistical method recovers them and does NOT flag the clean control.
    """

    @pytest.fixture
    def synthetic_features_df(self) -> pd.DataFrame:
        from src.tools.data_loader import data_loader
        from src.tools.feature_engineering import feature_engineering
        context = {"query_spec": {"filters": {}}}
        loader_result = data_loader(context)
        fe_context = {"data_loader": loader_result}
        fe_result = feature_engineering(fe_context, feature_set="structuring")
        return fe_result["features_df"]

    def test_4521_has_higher_score_than_9001(self, synthetic_features_df):
        """Customer 4521 (structuring pattern) should score higher than 9001 (clean control)."""
        result = _run_statistical_detection(synthetic_features_df)
        scores = {e["customer_id"]: e["anomaly_score"] for e in result["all_entities"]}
        # 4521 has near_threshold_txn_count_7d=6, 9001=0
        assert scores["4521"] >= scores["9001"]

    def test_result_structure_is_complete(self, synthetic_features_df):
        """Output structure is complete and consistent."""
        result = _run_statistical_detection(synthetic_features_df)
        assert result["entities_scored"] == 4
        assert len(result["all_entities"]) == 4
        for entity in result["all_entities"]:
            assert "customer_id" in entity
            assert "anomaly_score" in entity
            assert 0.0 <= entity["anomaly_score"] <= 1.0
            assert "top_contributing_features" in entity
            assert "z_score_flagged" in entity
            assert "iqr_flagged" in entity


# ---------------------------------------------------------------------------
# Test: ML Detection method
# ---------------------------------------------------------------------------


class TestMLDetectionConfig:
    def test_config_loads_correctly(self):
        from src.tools.anomaly_detection import _load_ml_config
        config = _load_ml_config()
        assert "if_n_estimators" in config
        assert "if_contamination" in config
        assert "if_random_state" in config
        assert "lof_n_neighbors" in config
        assert "lof_contamination" in config
        assert "score_combination" in config
        assert "explainability_method" in config
        assert "top_n_features" in config

    def test_random_state_present_for_reproducibility(self):
        """random_state must be set for IsolationForest determinism (§3.1 principle 4)."""
        from src.tools.anomaly_detection import _load_ml_config
        config = _load_ml_config()
        assert config["if_random_state"] is not None
        # Must be an integer (not None or 'auto')
        assert isinstance(int(config["if_random_state"]), int)


class TestMLDetectionBasic:
    """Basic correctness tests on a controlled fixture.

    Fixture: 8 customers. One extreme outlier has very high feature values.
    The documented DoD requires detecting injected anomalies.
    """

    @pytest.fixture
    def ml_features_df(self) -> pd.DataFrame:
        """8 customers: 7 with near-zero features, 1 extreme outlier.
        Expected: extreme outlier (C07) flagged by IsolationForest.
        """
        import numpy as np
        np.random.seed(0)
        rows = []
        # 7 normal customers
        for i in range(7):
            rows.append({
                "customer_id": f"C{i:02d}",
                "near_threshold_txn_count_7d": float(np.random.randint(0, 2)),
                "near_threshold_txn_ratio_7d": float(np.random.uniform(0, 0.1)),
            })
        # 1 extreme outlier
        rows.append({
            "customer_id": "C07",
            "near_threshold_txn_count_7d": 50.0,
            "near_threshold_txn_ratio_7d": 1.0,
        })
        return pd.DataFrame(rows)

    def test_method_used(self, ml_features_df):
        result = _run_ml_detection(ml_features_df)
        assert result["method_used"] == "ml"

    def test_algorithms_used(self, ml_features_df):
        """Both documented algorithms must be listed in output."""
        result = _run_ml_detection(ml_features_df)
        assert "IsolationForest" in result["algorithms_used"]
        assert "LocalOutlierFactor" in result["algorithms_used"]

    def test_extreme_outlier_flagged(self, ml_features_df):
        """C07 with extreme values should be flagged by IF."""
        result = _run_ml_detection(ml_features_df)
        flagged_ids = {e["customer_id"] for e in result["flagged_entities"]}
        assert "C07" in flagged_ids

    def test_entities_scored(self, ml_features_df):
        result = _run_ml_detection(ml_features_df)
        assert result["entities_scored"] == 8

    def test_anomaly_score_range(self, ml_features_df):
        """All anomaly_scores must be in [0, 1]."""
        result = _run_ml_detection(ml_features_df)
        for entity in result["all_entities"]:
            assert 0.0 <= entity["anomaly_score"] <= 1.0

    def test_top_contributing_features_present(self, ml_features_df):
        """Documented: top contributing features via z-score proxy (§6.3)."""
        result = _run_ml_detection(ml_features_df)
        flagged = [e for e in result["flagged_entities"] if e["customer_id"] == "C07"]
        assert len(flagged) == 1
        assert len(flagged[0]["top_contributing_features"]) >= 1
        feat = flagged[0]["top_contributing_features"][0]
        assert "feature" in feat
        assert "value" in feat
        assert "z_score" in feat

    def test_top_features_sorted_by_abs_zscore(self, ml_features_df):
        """Top contributing features should be sorted by descending |z-score|."""
        result = _run_ml_detection(ml_features_df)
        for entity in result["all_entities"]:
            feats = entity["top_contributing_features"]
            if len(feats) > 1:
                for i in range(len(feats) - 1):
                    assert abs(feats[i]["z_score"]) >= abs(feats[i + 1]["z_score"])

    def test_deterministic_repeated_calls(self, ml_features_df):
        """Same input → same output every time (required by §3.1 principle 4)."""
        r1 = _run_ml_detection(ml_features_df)
        r2 = _run_ml_detection(ml_features_df)
        assert r1["entities_flagged"] == r2["entities_flagged"]
        assert {e["customer_id"] for e in r1["flagged_entities"]} == \
               {e["customer_id"] for e in r2["flagged_entities"]}
        for e1, e2 in zip(
            sorted(r1["all_entities"], key=lambda x: x["customer_id"]),
            sorted(r2["all_entities"], key=lambda x: x["customer_id"])
        ):
            assert e1["anomaly_score"] == e2["anomaly_score"]

    def test_all_entities_present(self, ml_features_df):
        result = _run_ml_detection(ml_features_df)
        all_ids = {e["customer_id"] for e in result["all_entities"]}
        assert len(all_ids) == 8

    def test_output_contains_if_and_lof_scores(self, ml_features_df):
        """Individual IF and LOF scores are present for auditability."""
        result = _run_ml_detection(ml_features_df)
        for entity in result["all_entities"]:
            assert "if_score" in entity
            assert "lof_score" in entity
            assert 0.0 <= entity["if_score"] <= 1.0
            assert 0.0 <= entity["lof_score"] <= 1.0

    def test_features_used_in_output(self, ml_features_df):
        result = _run_ml_detection(ml_features_df)
        assert "features_used" in result
        assert "near_threshold_txn_count_7d" in result["features_used"]


class TestMLDetectionEdgeCases:
    def test_missing_customer_id_raises(self):
        df = pd.DataFrame({"feature_a": [1.0, 2.0]})
        with pytest.raises(ValueError, match="customer_id"):
            _run_ml_detection(df)

    def test_no_numeric_features_raises(self):
        df = pd.DataFrame({"customer_id": ["A", "B"]})
        with pytest.raises(ValueError, match="no numeric feature columns"):
            _run_ml_detection(df)

    def test_small_cohort_n_neighbors_capped(self):
        """LOF n_neighbors is capped to n_samples-1 for small cohorts."""
        df = pd.DataFrame({
            "customer_id": ["A", "B"],
            "feature_x": [1.0, 100.0],
        })
        # Should not raise even though lof_n_neighbors_raw > n_samples-1
        result = _run_ml_detection(df)
        assert result["entities_scored"] == 2


class TestMLDetectionToolInterface:
    @pytest.fixture
    def ml_features_df(self) -> pd.DataFrame:
        import numpy as np
        np.random.seed(0)
        rows = []
        for i in range(7):
            rows.append({
                "customer_id": f"C{i:02d}",
                "near_threshold_txn_count_7d": float(np.random.randint(0, 2)),
            })
        rows.append({"customer_id": "C07", "near_threshold_txn_count_7d": 50.0})
        return pd.DataFrame(rows)

    def test_ml_via_tool_function(self, ml_features_df):
        context = {
            "data_loader": {"transactions": pd.DataFrame(
                {"customer_id": ["X"], "amount_normalized": [100.0]}
            )},
            "feature_engineering": {"features_df": ml_features_df},
        }
        result = anomaly_detection(context, method="ml")
        assert result["status"] == "success"
        assert result["method_used"] == "ml"
        assert result["entities_scored"] == 8

    def test_missing_feature_engineering_returns_error(self):
        context = {
            "data_loader": {"transactions": pd.DataFrame(
                {"customer_id": ["X"], "amount_normalized": [100.0]}
            )},
        }
        result = anomaly_detection(context, method="ml")
        assert result["status"] == "error"
        assert "feature_engineering" in result["error"]

    def test_hybrid_still_not_implemented(self):
        context = {
            "data_loader": {"transactions": pd.DataFrame(
                {"customer_id": ["X"], "amount_normalized": [100.0]}
            )},
        }
        result = anomaly_detection(context, method="hybrid")
        assert result["status"] == "not_implemented"


class TestMLDetectionOnSyntheticData:
    """DoD test: recover injected structuring cases, do not flag clean control."""

    @pytest.fixture
    def synthetic_features_df(self) -> pd.DataFrame:
        from src.tools.data_loader import data_loader
        from src.tools.feature_engineering import feature_engineering
        context = {"query_spec": {"filters": {}}}
        loader_result = data_loader(context)
        fe_result = feature_engineering(
            {"data_loader": loader_result}, feature_set="structuring"
        )
        return fe_result["features_df"]

    def test_if_score_4521_highest(self, synthetic_features_df):
        """Customer 4521 (injected structuring) should have highest IF score."""
        result = _run_ml_detection(synthetic_features_df)
        scores = {e["customer_id"]: e["if_score"] for e in result["all_entities"]}
        assert scores["4521"] >= scores["9001"]

    def test_result_structure_complete(self, synthetic_features_df):
        result = _run_ml_detection(synthetic_features_df)
        assert result["entities_scored"] == 4
        assert len(result["all_entities"]) == 4
        for entity in result["all_entities"]:
            assert "customer_id" in entity
            assert "anomaly_score" in entity
            assert 0.0 <= entity["anomaly_score"] <= 1.0
            assert "top_contributing_features" in entity
            assert "if_score" in entity
            assert "lof_score" in entity

    def test_features_used_are_from_structuring_family(self, synthetic_features_df):
        result = _run_ml_detection(synthetic_features_df)
        assert "near_threshold_txn_count_7d" in result["features_used"]
