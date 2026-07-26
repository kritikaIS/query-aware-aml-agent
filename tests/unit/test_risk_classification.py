"""Unit tests for Risk Classification Tool.

Reference: Solution Design §5.5, Implementation Plan §6.4.
DoD: Band assignment is deterministic and reproducible given the same score
distribution; business-rule overrides are unit-tested independently of the
percentile logic.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from src.tools.risk_classification import (
    risk_classification,
    _classify_entities,
    _compute_thresholds,
    _has_prior_sar,
    _load_risk_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return _load_risk_config()


@pytest.fixture
def basic_entities():
    """10 entities with varied anomaly scores for percentile testing.

    Scores: [0.95, 0.90, 0.85, 0.70, 0.65, 0.60, 0.55, 0.40, 0.20, 0.10]
    95th percentile = 0.9275 → scores >= 0.9275 → High (only 0.95)
    80th percentile = 0.8600 → scores >= 0.86 → Medium (0.90)
    Below 0.86 → Low (all others)
    """
    scores = [0.95, 0.90, 0.85, 0.70, 0.65, 0.60, 0.55, 0.40, 0.20, 0.10]
    return [
        {
            "customer_id": f"C{i:02d}",
            "anomaly_score": s,
            "rule_matched": False,
        }
        for i, s in enumerate(scores)
    ]


@pytest.fixture
def rule_matched_entity():
    """Entity with rule_matched=True and low anomaly_score."""
    return [{
        "customer_id": "RULE01",
        "anomaly_score": 0.05,
        "rule_matched": True,
    }]


@pytest.fixture
def prior_sar_customers():
    """Customers DataFrame where C00 has a prior SAR flag."""
    return pd.DataFrame({
        "customer_id": ["C00", "C01"],
        "kyc_flags": ["prior_sar", ""],
    })


# ---------------------------------------------------------------------------
# Test: Config loading
# ---------------------------------------------------------------------------

class TestRiskConfig:
    def test_config_loads(self, config):
        assert "high_percentile" in config
        assert "medium_percentile" in config
        assert "prior_sar_kyc_flag_values" in config
        assert "bands" in config

    def test_three_bands_defined(self, config):
        """DOCUMENTED: Low, Medium, High bands (§5.5, §5.7)."""
        assert "Low" in config["bands"]
        assert "Medium" in config["bands"]
        assert "High" in config["bands"]

    def test_high_percentile_reasonable(self, config):
        assert 50 < config["high_percentile"] < 100

    def test_medium_percentile_below_high(self, config):
        assert config["medium_percentile"] < config["high_percentile"]


# ---------------------------------------------------------------------------
# Test: Percentile threshold computation
# ---------------------------------------------------------------------------

class TestThresholds:
    def test_high_threshold_at_95th(self):
        """DOCUMENTED: 'e.g. top 5% = High' → 95th percentile."""
        scores = [0.95, 0.90, 0.85, 0.70, 0.65, 0.60, 0.55, 0.40, 0.20, 0.10]
        high, medium = _compute_thresholds(scores, 95, 80)
        assert abs(high - np.percentile(scores, 95)) < 0.0001

    def test_medium_threshold_at_80th(self):
        scores = [0.95, 0.90, 0.85, 0.70, 0.65, 0.60, 0.55, 0.40, 0.20, 0.10]
        high, medium = _compute_thresholds(scores, 95, 80)
        assert abs(medium - np.percentile(scores, 80)) < 0.0001

    def test_computed_within_cohort(self):
        """DOCUMENTED: 'within the filtered cohort' — §6.4 step 1.
        Two different cohorts should produce two different thresholds."""
        cohort_a = [0.9, 0.8, 0.7, 0.6]  # high-score cohort
        cohort_b = [0.3, 0.2, 0.1, 0.05]  # low-score cohort
        high_a, _ = _compute_thresholds(cohort_a, 95, 80)
        high_b, _ = _compute_thresholds(cohort_b, 95, 80)
        assert high_a > high_b

    def test_empty_cohort_returns_zeros(self):
        high, medium = _compute_thresholds([], 95, 80)
        assert high == 0.0
        assert medium == 0.0


# ---------------------------------------------------------------------------
# Test: Percentile-based band assignment (documented DoD)
# ---------------------------------------------------------------------------

class TestPercentileBandAssignment:
    """Hand-computed expected values from 10-customer fixture.

    Scores: [0.95, 0.90, 0.85, 0.70, 0.65, 0.60, 0.55, 0.40, 0.20, 0.10]
    np.percentile(scores, 95) = 0.9275
    np.percentile(scores, 80) = 0.8600
    C00 (0.95) >= 0.9275 → High
    C01 (0.90) is < 0.9275 but >= 0.8600 → Medium
    C02-C09 → Low
    """

    def test_top_entity_is_high(self, basic_entities, config):
        results = _classify_entities(basic_entities, None, config)
        top = next(r for r in results if r["customer_id"] == "C00")
        assert top["risk_band"] == "High"

    def test_second_entity_is_medium(self, basic_entities, config):
        results = _classify_entities(basic_entities, None, config)
        second = next(r for r in results if r["customer_id"] == "C01")
        assert second["risk_band"] == "Medium"

    def test_low_score_entity_is_low(self, basic_entities, config):
        results = _classify_entities(basic_entities, None, config)
        last = next(r for r in results if r["customer_id"] == "C09")
        assert last["risk_band"] == "Low"

    def test_all_entities_have_band(self, basic_entities, config):
        results = _classify_entities(basic_entities, None, config)
        assert len(results) == 10
        for r in results:
            assert r["risk_band"] in ["Low", "Medium", "High"]

    def test_risk_score_unchanged(self, basic_entities, config):
        """DOCUMENTED: return the underlying continuous score (§6.4 step 3)."""
        results = _classify_entities(basic_entities, None, config)
        for original, classified in zip(basic_entities, results):
            assert abs(classified["risk_score"] - original["anomaly_score"]) < 0.0001

    def test_determining_factor_present(self, basic_entities, config):
        """DOCUMENTED: return the specific rule/threshold that determined the band (§6.4 step 3)."""
        results = _classify_entities(basic_entities, None, config)
        for r in results:
            assert "determining_factor" in r
            assert len(r["determining_factor"]) > 0

    def test_deterministic_repeated_calls(self, basic_entities, config):
        """DoD: deterministic and reproducible given the same score distribution."""
        r1 = _classify_entities(basic_entities, None, config)
        r2 = _classify_entities(basic_entities, None, config)
        for a, b in zip(r1, r2):
            assert a["risk_band"] == b["risk_band"]
            assert a["risk_score"] == b["risk_score"]


# ---------------------------------------------------------------------------
# Test: Rule-engine match → minimum Medium override (DOCUMENTED)
# ---------------------------------------------------------------------------

class TestRuleEngineOverride:
    """DOCUMENTED: any exact rule-engine match → minimum Medium (§5.5, §6.4 step 2)."""

    def test_low_score_with_rule_match_becomes_medium(self, config):
        """Customer with anomaly_score=0.0 and rule_matched=True → Medium."""
        entities = [
            {"customer_id": "X", "anomaly_score": 0.0, "rule_matched": True},
            {"customer_id": "Y", "anomaly_score": 0.9, "rule_matched": False},
        ]
        results = _classify_entities(entities, None, config)
        x = next(r for r in results if r["customer_id"] == "X")
        assert x["risk_band"] == "Medium"
        assert "rule_engine_match" in x["determining_factor"].lower()

    def test_high_score_with_rule_match_stays_high(self, config):
        """If percentile already assigns High, rule match does not lower it."""
        entities = [
            {"customer_id": "X", "anomaly_score": 1.0, "rule_matched": True},
            {"customer_id": "Y", "anomaly_score": 0.0, "rule_matched": False},
        ]
        results = _classify_entities(entities, None, config)
        x = next(r for r in results if r["customer_id"] == "X")
        assert x["risk_band"] == "High"

    def test_medium_score_with_rule_match_stays_medium(self, config):
        """If percentile already assigns Medium, rule match keeps it Medium."""
        scores = [1.0, 0.8, 0.6, 0.3]  # 95th=0.97, 80th=0.87 → 0.8 is Medium
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": s, "rule_matched": (i == 1)}
            for i, s in enumerate(scores)
        ]
        results = _classify_entities(entities, None, config)
        c1 = next(r for r in results if r["customer_id"] == "C1")
        assert c1["risk_band"] in ("Medium", "High")  # at least Medium


# ---------------------------------------------------------------------------
# Test: Prior-SAR override (DOCUMENTED)
# ---------------------------------------------------------------------------

class TestPriorSAROverride:
    """DOCUMENTED: prior SAR filing (kyc_flags) → minimum High (§5.5, §6.4 step 2)."""

    def test_prior_sar_flag_overrides_to_high(self, config):
        """Customer with low score but prior_sar flag → High."""
        entities = [
            {"customer_id": "C00", "anomaly_score": 0.05, "rule_matched": False},
            {"customer_id": "C01", "anomaly_score": 0.90, "rule_matched": False},
        ]
        df_customers = pd.DataFrame({
            "customer_id": ["C00", "C01"],
            "kyc_flags": ["prior_sar", ""],
        })
        results = _classify_entities(entities, df_customers, config)
        c00 = next(r for r in results if r["customer_id"] == "C00")
        assert c00["risk_band"] == "High"
        assert "prior_sar" in c00["determining_factor"].lower()

    def test_no_sar_flag_no_override(self, config):
        """Customer with empty kyc_flags gets normal percentile band.
        With a single entity, score=0.05 equals both thresholds (N=1 edge case),
        so it will be classified as High by percentile — no SAR override needed.
        Test that empty kyc_flags does NOT trigger the SAR override specifically.
        """
        entities = [
            {"customer_id": "X", "anomaly_score": 0.05, "rule_matched": False},
            {"customer_id": "Y", "anomaly_score": 0.90, "rule_matched": False},
        ]
        df_customers = pd.DataFrame({
            "customer_id": ["X", "Y"],
            "kyc_flags": ["", ""],
        })
        results = _classify_entities(entities, df_customers, config)
        x = next(r for r in results if r["customer_id"] == "X")
        # No SAR override: determining_factor must NOT mention prior_sar
        assert "prior_sar" not in x["determining_factor"].lower()

    def test_no_customers_df_no_sar_override(self, config):
        """If no customers DataFrame provided, SAR override is NOT applied.
        Test this by verifying the determining_factor does not mention prior_sar.
        """
        entities = [
            {"customer_id": "X", "anomaly_score": 0.05, "rule_matched": False},
        ]
        results = _classify_entities(entities, None, config)
        x = results[0]
        # No prior-SAR logic triggered since no customers df
        assert "prior_sar" not in x["determining_factor"].lower()

    def test_sar_override_takes_precedence_over_rule_override(self, config):
        """prior_sar overrides to High, which is higher than rule's Medium."""
        entities = [
            {"customer_id": "X", "anomaly_score": 0.05, "rule_matched": True},
        ]
        df_customers = pd.DataFrame({
            "customer_id": ["X"],
            "kyc_flags": ["prior_sar"],
        })
        results = _classify_entities(entities, df_customers, config)
        assert results[0]["risk_band"] == "High"


# ---------------------------------------------------------------------------
# Test: _has_prior_sar directly
# ---------------------------------------------------------------------------

class TestHasPriorSar:
    def test_matches_prior_sar_substring(self, config):
        df = pd.DataFrame({"customer_id": ["X"], "kyc_flags": ["prior_sar"]})
        assert _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"]) is True

    def test_case_insensitive(self, config):
        df = pd.DataFrame({"customer_id": ["X"], "kyc_flags": ["PRIOR_SAR"]})
        assert _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"]) is True

    def test_empty_flag_returns_false(self, config):
        df = pd.DataFrame({"customer_id": ["X"], "kyc_flags": [""]})
        assert _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"]) is False

    def test_unknown_customer_returns_false(self, config):
        df = pd.DataFrame({"customer_id": ["Y"], "kyc_flags": ["prior_sar"]})
        assert _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"]) is False

    def test_no_customers_df_returns_false(self, config):
        assert _has_prior_sar("X", None, config["prior_sar_kyc_flag_values"]) is False


# ---------------------------------------------------------------------------
# Test: Tool function interface
# ---------------------------------------------------------------------------

class TestRiskClassificationToolInterface:
    @pytest.fixture
    def anomaly_result_with_entities(self):
        return {
            "tool": "anomaly_detection",
            "status": "success",
            "method_used": "rule_engine",
            "all_entities": [
                {"customer_id": "4521", "anomaly_score": 0.87, "rule_matched": True},
                {"customer_id": "7832", "anomaly_score": 0.72, "rule_matched": False},
                {"customer_id": "9001", "anomaly_score": 0.10, "rule_matched": False},
            ]
        }

    def test_success_response(self, anomaly_result_with_entities):
        context = {"anomaly_detection": anomaly_result_with_entities}
        result = risk_classification(context, scheme="pattern_aware")
        assert result["status"] == "success"
        assert result["tool"] == "risk_classification"

    def test_classifications_present(self, anomaly_result_with_entities):
        context = {"anomaly_detection": anomaly_result_with_entities}
        result = risk_classification(context)
        assert "classifications" in result
        assert len(result["classifications"]) == 3

    def test_summary_counts_correct(self, anomaly_result_with_entities):
        context = {"anomaly_detection": anomaly_result_with_entities}
        result = risk_classification(context)
        total = sum(result["summary"].values())
        assert total == 3

    def test_thresholds_in_output(self, anomaly_result_with_entities):
        """DOCUMENTED: return the threshold for auditability (§6.4 step 3)."""
        context = {"anomaly_detection": anomaly_result_with_entities}
        result = risk_classification(context)
        assert "high_threshold" in result
        assert "medium_threshold" in result

    def test_missing_anomaly_detection_returns_error(self):
        context = {}
        result = risk_classification(context)
        assert result["status"] == "error"

    def test_empty_all_entities_returns_error(self):
        context = {
            "anomaly_detection": {"all_entities": []}
        }
        result = risk_classification(context)
        assert result["status"] == "error"

    def test_rule_match_customer_gets_at_least_medium(self, anomaly_result_with_entities):
        """DOCUMENTED: rule_matched=True → minimum Medium."""
        context = {"anomaly_detection": anomaly_result_with_entities}
        result = risk_classification(context)
        c4521 = next(
            c for c in result["classifications"] if c["customer_id"] == "4521"
        )
        bands = ["Low", "Medium", "High"]
        assert bands.index(c4521["risk_band"]) >= bands.index("Medium")

    def test_prior_sar_customer_is_high(self):
        """DOCUMENTED: prior SAR flag → minimum High."""
        context = {
            "anomaly_detection": {
                "all_entities": [
                    {"customer_id": "A", "anomaly_score": 0.05, "rule_matched": False},
                    {"customer_id": "B", "anomaly_score": 0.95, "rule_matched": False},
                ]
            },
            "data_loader": {
                "customers": pd.DataFrame({
                    "customer_id": ["A", "B"],
                    "kyc_flags": ["prior_sar", ""],
                })
            }
        }
        result = risk_classification(context)
        a = next(c for c in result["classifications"] if c["customer_id"] == "A")
        assert a["risk_band"] == "High"

    def test_business_rules_independent_of_percentile(self):
        """DoD: business-rule overrides are unit-tested independently of percentile logic.
        C00 has prior_sar → High regardless of cohort percentile logic.
        To isolate business rule from percentile: give C00 a meaningfully lower
        score than C01, and verify C00 still ends up High due to prior_sar.
        """
        entities = [
            {"customer_id": "C00", "anomaly_score": 0.01, "rule_matched": False},
            {"customer_id": "C01", "anomaly_score": 0.99, "rule_matched": False},
        ]
        context = {
            "anomaly_detection": {"all_entities": entities},
            "data_loader": {
                "customers": pd.DataFrame({
                    "customer_id": ["C00", "C01"],
                    "kyc_flags": ["prior_sar", ""],
                })
            }
        }
        result = risk_classification(context)
        c00 = next(c for c in result["classifications"] if c["customer_id"] == "C00")
        # C00 has prior_sar → must be High despite low anomaly_score
        assert c00["risk_band"] == "High"
        assert "prior_sar" in c00["determining_factor"].lower()


# ---------------------------------------------------------------------------
# Test: Documented DoD assertions
# ---------------------------------------------------------------------------

class TestDefinitionOfDone:
    def test_deterministic_same_scores_same_bands(self):
        """DoD: band assignment is deterministic and reproducible."""
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": s, "rule_matched": False}
            for i, s in enumerate([0.9, 0.7, 0.5, 0.3, 0.1])
        ]
        config = _load_risk_config()
        r1 = _classify_entities(entities, None, config)
        r2 = _classify_entities(entities, None, config)
        for a, b in zip(r1, r2):
            assert a["risk_band"] == b["risk_band"]

    def test_rule_override_independent_of_score_distribution(self):
        """DoD: business-rule override is independent of cohort percentile."""
        # Rule match should produce at least Medium regardless of score distribution
        for score in [0.0, 0.01, 0.05]:
            entities = [
                {"customer_id": "X", "anomaly_score": score, "rule_matched": True},
                {"customer_id": "Y", "anomaly_score": 0.99, "rule_matched": False},
            ]
            config = _load_risk_config()
            results = _classify_entities(entities, None, config)
            x = next(r for r in results if r["customer_id"] == "X")
            bands = config["bands"]
            assert bands.index(x["risk_band"]) >= bands.index("Medium"), (
                f"score={score} with rule_matched=True should be at least Medium, "
                f"got {x['risk_band']}"
            )

    def test_prior_sar_override_independent_of_score(self):
        """DoD: prior SAR override is independent of anomaly score."""
        for score in [0.0, 0.01, 0.99]:
            entities = [
                {"customer_id": "X", "anomaly_score": score, "rule_matched": False},
                {"customer_id": "Y", "anomaly_score": 0.99, "rule_matched": False},
            ]
            df_customers = pd.DataFrame({
                "customer_id": ["X", "Y"],
                "kyc_flags": ["prior_sar", ""],
            })
            config = _load_risk_config()
            results = _classify_entities(entities, df_customers, config)
            x = next(r for r in results if r["customer_id"] == "X")
            assert x["risk_band"] == "High", (
                f"score={score} with prior_sar should be High, got {x['risk_band']}"
            )


# ---------------------------------------------------------------------------
# Test: Identical-score edge case (IMPLEMENTATION IMPROVEMENT)
# ---------------------------------------------------------------------------

class TestIdenticalScores:
    """When all anomaly scores are identical, classifying all as High is
    misleading (they are equally anomalous relative to each other = not at all).
    The implementation improvement assigns all to Low in this case.
    """

    def test_all_equal_scores_not_all_high(self):
        """IMPLEMENTATION IMPROVEMENT: identical scores → no entity is High
        due to percentile threshold alone."""
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": 0.5, "rule_matched": False}
            for i in range(10)
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        # No entity should be classified High by percentile alone
        for r in results:
            assert r["risk_band"] == "Low", (
                f"All equal scores should produce Low, got {r['risk_band']} "
                f"for {r['customer_id']}"
            )

    def test_all_equal_scores_determining_factor_mentions_uniform(self):
        """Audit trail must record that uniform-score logic was applied.
        Uses 6 entities (>= min_cohort=5) to avoid the small-cohort fallback.
        """
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": 0.8, "rule_matched": False}
            for i in range(6)
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        for r in results:
            factor = r["determining_factor"].lower()
            assert "uniform" in factor or "equal" in factor, (
                f"Expected 'uniform' or 'equal' in determining_factor, got: {r['determining_factor']}"
            )

    def test_equal_scores_with_rule_override_still_becomes_medium(self):
        """Rule override applies on top of the equal-scores fallback.
        Uses 6 entities (>= min_cohort=5) to activate equal-scores logic, not small-cohort fallback.
        """
        entities = [
            {"customer_id": "A", "anomaly_score": 0.5, "rule_matched": True},
        ] + [
            {"customer_id": f"C{i}", "anomaly_score": 0.5, "rule_matched": False}
            for i in range(5)
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        a = next(r for r in results if r["customer_id"] == "A")
        others = [r for r in results if r["customer_id"] != "A"]
        assert a["risk_band"] == "Medium"  # rule override kicks in
        # Others with equal scores and no rule match → Low
        for other in others:
            assert other["risk_band"] == "Low"

    def test_equal_scores_deterministic(self):
        """Identical scores produce identical results on repeated calls."""
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": 0.6, "rule_matched": False}
            for i in range(5)
        ]
        config = _load_risk_config()
        r1 = _classify_entities(entities, None, config)
        r2 = _classify_entities(entities, None, config)
        for a, b in zip(r1, r2):
            assert a["risk_band"] == b["risk_band"]

    def test_tool_output_reports_equal_scores_detected(self):
        """Tool-level output includes equal_scores_detected audit flag."""
        context = {
            "anomaly_detection": {
                "all_entities": [
                    {"customer_id": "A", "anomaly_score": 0.5, "rule_matched": False},
                    {"customer_id": "B", "anomaly_score": 0.5, "rule_matched": False},
                    {"customer_id": "C", "anomaly_score": 0.5, "rule_matched": False},
                    {"customer_id": "D", "anomaly_score": 0.5, "rule_matched": False},
                    {"customer_id": "E", "anomaly_score": 0.5, "rule_matched": False},
                ]
            }
        }
        result = risk_classification(context)
        assert result["equal_scores_detected"] is True


# ---------------------------------------------------------------------------
# Test: Small-cohort fallback (USER-REQUESTED ENHANCEMENT)
# ---------------------------------------------------------------------------

class TestSmallCohortFallback:
    """When cohort < min_cohort_for_percentile (default 5), absolute score
    thresholds are used instead of percentile thresholds.
    """

    def test_small_cohort_uses_absolute_thresholds(self):
        """With 2 entities, fallback applies. Score=0.9 >= 0.75 (absolute High)."""
        entities = [
            {"customer_id": "A", "anomaly_score": 0.9, "rule_matched": False},
            {"customer_id": "B", "anomaly_score": 0.1, "rule_matched": False},
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        a = next(r for r in results if r["customer_id"] == "A")
        b = next(r for r in results if r["customer_id"] == "B")
        assert a["risk_band"] == "High"
        assert b["risk_band"] == "Low"

    def test_small_cohort_medium_band_absolute(self):
        """Score=0.5 falls between medium (0.40) and high (0.75) → Medium."""
        entities = [
            {"customer_id": "X", "anomaly_score": 0.5, "rule_matched": False},
            {"customer_id": "Y", "anomaly_score": 0.1, "rule_matched": False},
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        x = next(r for r in results if r["customer_id"] == "X")
        assert x["risk_band"] == "Medium"

    def test_small_cohort_determining_factor_mentions_fallback(self):
        """Audit trail must mention fallback when it applies."""
        entities = [
            {"customer_id": "X", "anomaly_score": 0.9, "rule_matched": False},
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        assert "fallback" in results[0]["determining_factor"].lower()

    def test_tool_output_reports_fallback_used(self):
        """Tool-level output includes fallback_used audit flag."""
        context = {
            "anomaly_detection": {
                "all_entities": [
                    {"customer_id": "X", "anomaly_score": 0.9, "rule_matched": False},
                    {"customer_id": "Y", "anomaly_score": 0.1, "rule_matched": False},
                ]
            }
        }
        result = risk_classification(context)
        assert result["fallback_used"] is True

    def test_full_cohort_does_not_use_fallback(self):
        """With 10 entities (>= min_cohort=5), fallback is not used."""
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": i * 0.1, "rule_matched": False}
            for i in range(10)
        ]
        context = {"anomaly_detection": {"all_entities": entities}}
        result = risk_classification(context)
        assert result["fallback_used"] is False


# ---------------------------------------------------------------------------
# Test: Robust prior-SAR detection (IMPLEMENTATION IMPROVEMENT)
# ---------------------------------------------------------------------------

class TestRobustPriorSAR:
    """Robust handling of NULL, NaN, whitespace, mixed case in kyc_flags."""

    def test_nan_kyc_flag_no_exception(self, config):
        """NaN value in kyc_flags column must not raise an exception."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "kyc_flags": [float("nan")],
        })
        result = _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"])
        assert result is False

    def test_none_kyc_flag_no_exception(self, config):
        """None value in kyc_flags must not raise an exception."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "kyc_flags": [None],
        })
        result = _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"])
        assert result is False

    def test_whitespace_only_kyc_flag(self, config):
        """Whitespace-only string is not a SAR flag."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "kyc_flags": ["   "],
        })
        result = _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"])
        assert result is False

    def test_mixed_case_sar_flag(self, config):
        """PRIOR_SAR in upper case should still match."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "kyc_flags": ["PRIOR_SAR"],
        })
        result = _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"])
        assert result is True

    def test_mixed_case_flag_value(self, config):
        """prior_Sar in mixed case should still match."""
        df = pd.DataFrame({
            "customer_id": ["X"],
            "kyc_flags": ["prior_Sar"],
        })
        result = _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"])
        assert result is True

    def test_missing_kyc_flags_column(self, config):
        """DataFrame without kyc_flags column returns False gracefully."""
        df = pd.DataFrame({"customer_id": ["X"], "segment": ["retail"]})
        result = _has_prior_sar("X", df, config["prior_sar_kyc_flag_values"])
        assert result is False

    def test_non_dataframe_customers_returns_false(self, config):
        """Passing a non-DataFrame (e.g. dict or None) returns False."""
        result = _has_prior_sar("X", {"customer_id": ["X"], "kyc_flags": ["prior_sar"]},
                                config["prior_sar_kyc_flag_values"])
        assert result is False


# ---------------------------------------------------------------------------
# Test: Expanded audit information (USER-REQUESTED ENHANCEMENT)
# ---------------------------------------------------------------------------

class TestAuditFields:
    """The new audit fields must be present and contain accurate information."""

    def test_initial_band_present(self):
        entities = [
            {"customer_id": "X", "anomaly_score": 0.9, "rule_matched": False},
            {"customer_id": "Y", "anomaly_score": 0.1, "rule_matched": False},
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        for r in results:
            assert "initial_band" in r
            assert r["initial_band"] in ["Low", "Medium", "High"]

    def test_rule_override_flag_true_when_override_occurred(self):
        entities = [
            {"customer_id": "X", "anomaly_score": 0.0, "rule_matched": True},
            {"customer_id": "Y", "anomaly_score": 0.9, "rule_matched": False},
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        x = next(r for r in results if r["customer_id"] == "X")
        assert x["rule_override"] is True
        y = next(r for r in results if r["customer_id"] == "Y")
        assert y["rule_override"] is False

    def test_sar_override_flag_true_when_override_occurred(self):
        entities = [
            {"customer_id": "X", "anomaly_score": 0.0, "rule_matched": False},
            {"customer_id": "Y", "anomaly_score": 0.9, "rule_matched": False},
        ]
        df_customers = pd.DataFrame({
            "customer_id": ["X", "Y"],
            "kyc_flags": ["prior_sar", ""],
        })
        config = _load_risk_config()
        results = _classify_entities(entities, df_customers, config)
        x = next(r for r in results if r["customer_id"] == "X")
        assert x["sar_override"] is True
        y = next(r for r in results if r["customer_id"] == "Y")
        assert y["sar_override"] is False

    def test_thresholds_used_always_present(self):
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": i * 0.1, "rule_matched": False}
            for i in range(10)
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        for r in results:
            assert "thresholds_used" in r
            assert len(r["thresholds_used"]) > 0

    def test_existing_fields_still_present(self):
        """Public API fields must not be removed."""
        entities = [
            {"customer_id": "X", "anomaly_score": 0.8, "rule_matched": False},
            {"customer_id": "Y", "anomaly_score": 0.2, "rule_matched": False},
        ]
        context = {"anomaly_detection": {"all_entities": entities}}
        result = risk_classification(context)
        # All original documented output fields must still be present
        assert "tool" in result
        assert "status" in result
        assert "scheme" in result
        assert "high_threshold" in result
        assert "medium_threshold" in result
        assert "classifications" in result
        assert "summary" in result
        for c in result["classifications"]:
            assert "customer_id" in c
            assert "risk_score" in c
            assert "risk_band" in c
            assert "determining_factor" in c

    def test_initial_band_equals_final_when_no_overrides(self):
        """When no overrides occur, initial_band equals final risk_band."""
        entities = [
            {"customer_id": f"C{i}", "anomaly_score": i * 0.1, "rule_matched": False}
            for i in range(10)
        ]
        config = _load_risk_config()
        results = _classify_entities(entities, None, config)
        for r in results:
            # No override triggered
            if not r["rule_override"] and not r["sar_override"]:
                assert r["initial_band"] == r["risk_band"]
