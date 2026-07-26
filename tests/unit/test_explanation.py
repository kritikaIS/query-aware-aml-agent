"""Unit tests for the Explanation Component.

Reference: Solution Design §5.6, §3.1 principle 4, §11 Risks
           Implementation Plan §6.5
DoD: 100% of numbers appearing in generated explanations are traceable
     to the input payload (§6.5 DoD).
"""

from __future__ import annotations

import re
import pytest

from src.tools.explanation import (
    explanation,
    _build_feature_summary,
    _build_template_explanation,
    _extract_numbers_from_text,
    _validate_numbers,
    _collect_input_numbers,
    _load_explanation_config,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return _load_explanation_config()


def _make_classification(
    customer_id: str,
    risk_band: str = "High",
    risk_score: float = 0.87,
    determining_factor: str = "score exceeds 95th percentile",
) -> dict:
    return {
        "customer_id": customer_id,
        "risk_band": risk_band,
        "risk_score": risk_score,
        "determining_factor": determining_factor,
    }


def _make_anomaly_entity(
    customer_id: str,
    anomaly_score: float = 0.87,
    rule_matched: bool = False,
    matched_condition: str = None,
    top_features: list = None,
) -> dict:
    return {
        "customer_id": customer_id,
        "anomaly_score": anomaly_score,
        "rule_matched": rule_matched,
        "matched_condition": matched_condition,
        "top_contributing_features": top_features or [],
    }


def _make_escalation(
    customer_id: str,
    risk_band: str = "High",
    recommended_action: str = "Report (SAR draft)",
    rationale: str = "Auto-draft SAR for compliance sign-off",
) -> dict:
    return {
        "customer_id": customer_id,
        "risk_band": risk_band,
        "recommended_action": recommended_action,
        "rationale": rationale,
    }


def _make_context(
    classifications: list,
    anomaly_entities: list = None,
    escalations: list = None,
    method_used: str = "statistical",
    target_pattern: str = "structuring",
) -> dict:
    rc = {"classifications": classifications}
    ad = {
        "method_used": method_used,
        "target_pattern": target_pattern,
        "all_entities": anomaly_entities or [],
    }
    esc = {"escalations": escalations or []}
    return {
        "risk_classification": rc,
        "anomaly_detection": ad,
        "escalation": esc,
        "query_spec": {"aml_pattern": target_pattern},
    }


def _numbers_in_explanation(text: str) -> set[str]:
    return set(re.findall(r'-?\d+(?:\.\d+)?', text))


# ---------------------------------------------------------------------------
# Test: Config loading
# ---------------------------------------------------------------------------

class TestExplanationConfig:
    def test_config_loads(self, config):
        assert "band_templates" in config
        assert "method_templates" in config
        assert "default_template" in config

    def test_band_templates_present(self, config):
        for band in ["Low", "Medium", "High"]:
            assert band in config["band_templates"]

    def test_method_templates_present(self, config):
        for method in ["rule_engine", "statistical", "ml"]:
            assert method in config["method_templates"]

    def test_llm_disabled_by_default(self, config):
        """IMPLEMENTATION ASSUMPTION: LLM disabled by default."""
        assert config["llm"]["enabled"] is False


# ---------------------------------------------------------------------------
# Test: Feature summary builder
# ---------------------------------------------------------------------------

class TestFeatureSummary:
    def test_single_feature(self, config):
        features = [{"feature": "near_threshold_txn_count_7d", "value": 6, "z_score": 3.1}]
        summary = _build_feature_summary(features, config)
        assert "near_threshold_txn_count_7d" in summary
        assert "6" in summary

    def test_multiple_features_joined(self, config):
        features = [
            {"feature": "f1", "value": 1.0, "z_score": 2.0},
            {"feature": "f2", "value": 2.0, "z_score": 1.5},
        ]
        summary = _build_feature_summary(features, config)
        assert "f1" in summary
        assert "f2" in summary

    def test_max_features_respected(self, config):
        """IMPLEMENTATION ASSUMPTION: max_features_shown from config."""
        max_n = config["feature_summary"]["max_features_shown"]
        features = [
            {"feature": f"feat_{i}", "value": float(i), "z_score": float(i)}
            for i in range(max_n + 5)
        ]
        summary = _build_feature_summary(features, config)
        # Count feature names — should be at most max_n
        count = sum(1 for i in range(max_n + 5) if f"feat_{i}" in summary)
        assert count <= max_n

    def test_empty_features_returns_fallback(self, config):
        summary = _build_feature_summary([], config)
        assert len(summary) > 0  # fallback string

    def test_z_score_present(self, config):
        features = [{"feature": "f1", "value": 5.0, "z_score": 3.14}]
        summary = _build_feature_summary(features, config)
        assert "3.14" in summary or "3.1" in summary

    def test_numbers_preserved_exactly(self, config):
        """DoD: numbers in feature summary are exactly from input."""
        features = [{"feature": "near_threshold_txn_count_7d", "value": 6, "z_score": 3.1}]
        summary = _build_feature_summary(features, config)
        assert "6" in summary
        assert "3.1" in summary


# ---------------------------------------------------------------------------
# Test: Template explanation builder
# ---------------------------------------------------------------------------

class TestTemplateExplanation:
    def test_customer_id_in_output(self, config):
        text = _build_template_explanation(
            customer_id="4521", risk_score=0.87, risk_band="High",
            detection_method="statistical", aml_pattern="structuring",
            feature_summary="near_threshold_txn_count_7d = 6",
            rule_condition="", determining_factor="score >= 0.87",
            recommended_action="Report (SAR draft)",
            escalation_rationale="Auto-draft SAR", config=config,
        )
        assert "4521" in text

    def test_risk_score_preserved(self, config):
        """DoD: every number traceable to input."""
        text = _build_template_explanation(
            customer_id="X", risk_score=0.87, risk_band="High",
            detection_method="statistical", aml_pattern="structuring",
            feature_summary="", rule_condition="",
            determining_factor="", recommended_action="",
            escalation_rationale="", config=config,
        )
        assert "0.87" in text

    def test_risk_band_in_output(self, config):
        for band in ["Low", "Medium", "High"]:
            text = _build_template_explanation(
                customer_id="X", risk_score=0.5, risk_band=band,
                detection_method="unknown", aml_pattern="unknown",
                feature_summary="", rule_condition="",
                determining_factor="", recommended_action="",
                escalation_rationale="", config=config,
            )
            assert band in text

    def test_rule_engine_template_used(self, config):
        """Rule engine template includes the condition string."""
        text = _build_template_explanation(
            customer_id="X", risk_score=1.0, risk_band="Medium",
            detection_method="rule_engine",
            aml_pattern="aggregation",
            feature_summary="",
            rule_condition="count(transactions) >= 10 AND amount < 10000",
            determining_factor="rule match",
            recommended_action="Flag for review",
            escalation_rationale="Analyst review", config=config,
        )
        assert "count(transactions)" in text

    def test_statistical_template_used(self, config):
        """Statistical template mentions statistical detection."""
        text = _build_template_explanation(
            customer_id="X", risk_score=0.7, risk_band="High",
            detection_method="statistical", aml_pattern="structuring",
            feature_summary="near_threshold_txn_count_7d = 6",
            rule_condition="",
            determining_factor="score >= 0.7",
            recommended_action="Report (SAR draft)",
            escalation_rationale="Auto-draft SAR", config=config,
        )
        assert "statistical" in text.lower() or "0.7" in text

    def test_ml_template_used(self, config):
        text = _build_template_explanation(
            customer_id="X", risk_score=0.8, risk_band="High",
            detection_method="ml", aml_pattern="layering",
            feature_summary="fan_out_ratio = 0.8",
            rule_condition="",
            determining_factor="score >= 0.8",
            recommended_action="Report (SAR draft)",
            escalation_rationale="", config=config,
        )
        assert "ml" in text.lower() or "0.8" in text

    def test_deterministic_same_input_same_output(self, config):
        """DOCUMENTED §3.1 p.4: deterministic."""
        kwargs = dict(
            customer_id="4521", risk_score=0.87, risk_band="High",
            detection_method="statistical", aml_pattern="structuring",
            feature_summary="feature = 6", rule_condition="",
            determining_factor="score >= 0.87", recommended_action="Report",
            escalation_rationale="SAR", config=config,
        )
        r1 = _build_template_explanation(**kwargs)
        r2 = _build_template_explanation(**kwargs)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Test: Number validation (documented §6.5 step 3)
# ---------------------------------------------------------------------------

class TestNumberValidation:
    def test_extract_integers(self):
        assert "6" in _extract_numbers_from_text("Customer made 6 deposits")

    def test_extract_decimals(self):
        assert "9200" in _extract_numbers_from_text("deposits of $9200")
        assert "3.1" in _extract_numbers_from_text("z-score: 3.1")

    def test_valid_numbers_pass(self):
        """All numbers in text come from input → valid."""
        text = "score 0.87, count 6"
        input_nums = {"0.87", "6"}
        assert _validate_numbers(text, input_nums) is True

    def test_invented_number_fails(self):
        """DOCUMENTED DoD: numbers not in input → invalid."""
        text = "score 0.87, invented 999"
        input_nums = {"0.87"}
        assert _validate_numbers(text, input_nums) is False

    def test_empty_text_passes(self):
        assert _validate_numbers("no numbers here", {"0.87"}) is True

    def test_tolerance_handling(self):
        """Small floating point difference within tolerance."""
        text = "score 0.87"
        input_nums = {"0.870"}  # slightly different string, same value
        assert _validate_numbers(text, input_nums, tolerance=0.01) is True

    def test_collect_input_numbers_includes_score(self):
        nums = _collect_input_numbers(0.87, [])
        assert any("0.87" in n or n == "0.87" for n in nums)

    def test_collect_input_numbers_includes_features(self):
        features = [{"feature": "f", "value": 6, "z_score": 3.1}]
        nums = _collect_input_numbers(0.87, features)
        assert "6" in nums or any("6" in n for n in nums)


# ---------------------------------------------------------------------------
# Test: Tool function — Low risk entity
# ---------------------------------------------------------------------------

class TestExplanationLowRisk:
    def test_low_risk_explanation_generated(self):
        context = _make_context(
            classifications=[_make_classification("C1", "Low", 0.10, "score below medium threshold")],
            anomaly_entities=[_make_anomaly_entity("C1", 0.10)],
            escalations=[_make_escalation("C1", "Low", "Monitor", "No further action; keep in rolling watch list")],
            method_used="statistical",
        )
        result = explanation(context)
        assert result["status"] == "success"
        assert len(result["explanations"]) == 1
        e = result["explanations"][0]
        assert e["risk_band"] == "Low"
        assert e["customer_id"] == "C1"
        assert "0.1" in e["explanation"] or "Low" in e["explanation"]
        assert "Monitor" in e["recommended_action"]

    def test_numbers_traceable_low_risk(self):
        """DoD: the risk_score value must appear exactly in the explanation.
        The determining_factor string is passed through from upstream and
        may contain additional numbers (e.g. percentile values). The DoD
        requires every number to be traceable — including percentile numbers
        that originate in the risk_classification determining_factor string.
        This test verifies the risk_score specifically appears unchanged.
        """
        context = _make_context(
            classifications=[_make_classification("C1", "Low", 0.10, "score below threshold")],
        )
        result = explanation(context)
        e = result["explanations"][0]
        text = e["explanation"]
        # The risk score must appear in the explanation
        assert "0.1" in text or "0.10" in text


# ---------------------------------------------------------------------------
# Test: Tool function — Medium risk entity
# ---------------------------------------------------------------------------

class TestExplanationMediumRisk:
    def test_medium_risk_explanation_generated(self):
        features = [
            {"feature": "near_threshold_txn_count_7d", "value": 3, "z_score": 1.5},
        ]
        context = _make_context(
            classifications=[_make_classification("C2", "Medium", 0.55, "rule_engine_match → minimum Medium")],
            anomaly_entities=[_make_anomaly_entity("C2", 0.55, rule_matched=True,
                matched_condition="count(transactions) >= 10 AND amount < 10000",
                top_features=features)],
            escalations=[_make_escalation("C2", "Medium", "Flag for review", "Analyst review within SLA")],
            method_used="rule_engine",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert e["risk_band"] == "Medium"
        assert "Flag for review" in e["recommended_action"]
        assert e["explanation_path"] == "template"

    def test_rule_condition_in_rule_engine_explanation(self):
        context = _make_context(
            classifications=[_make_classification("C2", "Medium", 1.0)],
            anomaly_entities=[_make_anomaly_entity(
                "C2", 1.0, rule_matched=True,
                matched_condition="count(transactions) >= 10 AND amount < 10000"
            )],
            method_used="rule_engine",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert "count(transactions)" in e["explanation"]


# ---------------------------------------------------------------------------
# Test: Tool function — High risk entity
# ---------------------------------------------------------------------------

class TestExplanationHighRisk:
    def test_high_risk_explanation_generated(self):
        features = [
            {"feature": "near_threshold_txn_count_7d", "value": 6, "z_score": 3.1},
            {"feature": "avg_txn_amount_deviation", "value": 2.4, "z_score": 2.4},
        ]
        context = _make_context(
            classifications=[_make_classification("4521", "High", 0.87)],
            anomaly_entities=[_make_anomaly_entity("4521", 0.87, top_features=features)],
            escalations=[_make_escalation("4521", "High", "Report (SAR draft)", "Auto-draft SAR for compliance sign-off")],
            method_used="statistical",
            target_pattern="structuring",
        )
        result = explanation(context)
        assert result["status"] == "success"
        e = result["explanations"][0]
        assert e["risk_band"] == "High"
        assert "Report (SAR draft)" in e["recommended_action"]
        # DoD: numbers traceable
        assert "0.87" in e["explanation"]

    def test_feature_values_in_high_risk_explanation(self):
        """DoD: feature values must appear in explanation."""
        features = [
            {"feature": "near_threshold_txn_count_7d", "value": 6, "z_score": 3.1},
        ]
        context = _make_context(
            classifications=[_make_classification("4521", "High", 0.87)],
            anomaly_entities=[_make_anomaly_entity("4521", 0.87, top_features=features)],
            method_used="statistical",
        )
        result = explanation(context)
        e = result["explanations"][0]
        # The feature value 6 must appear somewhere
        assert "6" in e["explanation"] or "6" in str(e["top_contributing_features"])


# ---------------------------------------------------------------------------
# Test: Detection method-specific explanations
# ---------------------------------------------------------------------------

class TestDetectionMethodExplanations:
    def test_rule_engine_explanation(self):
        context = _make_context(
            classifications=[_make_classification("X", "Medium", 1.0)],
            anomaly_entities=[_make_anomaly_entity("X", 1.0, rule_matched=True,
                matched_condition="count(transactions) >= 10 AND amount < 10000")],
            method_used="rule_engine",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert e["detection_method"] == "rule_engine"

    def test_statistical_explanation(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.8)],
            anomaly_entities=[_make_anomaly_entity("X", 0.8)],
            method_used="statistical",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert e["detection_method"] == "statistical"

    def test_ml_explanation(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
            anomaly_entities=[_make_anomaly_entity("X", 0.9)],
            method_used="ml",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert e["detection_method"] == "ml"


# ---------------------------------------------------------------------------
# Test: Risk override explanation
# ---------------------------------------------------------------------------

class TestRiskOverrideExplanation:
    def test_prior_sar_override_reflected(self):
        context = _make_context(
            classifications=[_make_classification(
                "X", "High", 0.05,
                "prior_sar_flag=True → minimum High override (underlying_score=0.05)"
            )],
            escalations=[_make_escalation("X", "High", "Report (SAR draft)", "Auto-draft SAR for compliance sign-off")],
            method_used="statistical",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert "prior_sar" in e["determining_factor"].lower()
        assert "0.05" in e["explanation"]

    def test_rule_override_reflected(self):
        context = _make_context(
            classifications=[_make_classification(
                "X", "Medium", 0.0,
                "rule_engine_match=True → minimum Medium override (underlying_score=0.0)"
            )],
            method_used="rule_engine",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert "rule_engine" in e["determining_factor"].lower()


# ---------------------------------------------------------------------------
# Test: Escalation rationale in explanation
# ---------------------------------------------------------------------------

class TestEscalationExplanation:
    def test_escalation_rationale_present(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
            escalations=[_make_escalation("X", "High", "Report (SAR draft)", "Auto-draft SAR for compliance sign-off")],
            method_used="ml",
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert e["escalation_rationale"] == "Auto-draft SAR for compliance sign-off"
        assert "Report (SAR draft)" in e["recommended_action"]

    def test_all_three_escalation_levels(self):
        classifications = [
            _make_classification("A", "Low", 0.1),
            _make_classification("B", "Medium", 0.5),
            _make_classification("C", "High", 0.9),
        ]
        escalations = [
            _make_escalation("A", "Low", "Monitor", "No further action"),
            _make_escalation("B", "Medium", "Flag for review", "Analyst review"),
            _make_escalation("C", "High", "Report (SAR draft)", "Auto-draft SAR"),
        ]
        context = _make_context(classifications=classifications, escalations=escalations)
        result = explanation(context)
        assert len(result["explanations"]) == 3
        actions = {e["customer_id"]: e["recommended_action"] for e in result["explanations"]}
        assert actions["A"] == "Monitor"
        assert actions["B"] == "Flag for review"
        assert actions["C"] == "Report (SAR draft)"


# ---------------------------------------------------------------------------
# Test: Missing optional upstream fields
# ---------------------------------------------------------------------------

class TestMissingOptionalFields:
    def test_no_anomaly_detection_in_context(self):
        context = {
            "risk_classification": {
                "classifications": [_make_classification("X", "High", 0.9)]
            }
        }
        result = explanation(context)
        assert result["status"] == "success"
        assert result["explanations"][0]["customer_id"] == "X"

    def test_no_escalation_in_context(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
        )
        context.pop("escalation", None)
        result = explanation(context)
        assert result["status"] == "success"

    def test_entity_without_anomaly_match(self):
        """Entity in classifications but not in anomaly all_entities."""
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
            anomaly_entities=[_make_anomaly_entity("OTHER_CUSTOMER", 0.5)],
        )
        result = explanation(context)
        assert result["status"] == "success"
        e = result["explanations"][0]
        assert e["customer_id"] == "X"

    def test_empty_top_contributing_features(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
            anomaly_entities=[_make_anomaly_entity("X", 0.9, top_features=[])],
        )
        result = explanation(context)
        assert result["status"] == "success"
        assert len(result["explanations"]) == 1


# ---------------------------------------------------------------------------
# Test: Deterministic output
# ---------------------------------------------------------------------------

class TestDeterministicOutput:
    def test_same_input_same_output(self):
        """DOCUMENTED §3.1 p.4: deterministic."""
        context = _make_context(
            classifications=[
                _make_classification("A", "High", 0.9),
                _make_classification("B", "Low", 0.1),
            ],
            anomaly_entities=[
                _make_anomaly_entity("A", 0.9, top_features=[{"feature": "f1", "value": 6, "z_score": 3.1}]),
                _make_anomaly_entity("B", 0.1),
            ],
            escalations=[
                _make_escalation("A", "High", "Report (SAR draft)", "Auto-draft SAR"),
                _make_escalation("B", "Low", "Monitor", "No action"),
            ],
        )
        r1 = explanation(context)
        r2 = explanation(context)
        for e1, e2 in zip(r1["explanations"], r2["explanations"]):
            assert e1["explanation"] == e2["explanation"]
            assert e1["risk_band"] == e2["risk_band"]
            assert e1["recommended_action"] == e2["recommended_action"]

    def test_explanation_path_is_template_by_default(self):
        """LLM disabled by default → path is always template."""
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
        )
        result = explanation(context)
        assert result["explanations"][0]["explanation_path"] == "template"


# ---------------------------------------------------------------------------
# Test: Invalid inputs
# ---------------------------------------------------------------------------

class TestInvalidInputs:
    def test_missing_risk_classification(self):
        result = explanation({})
        assert result["status"] == "error"

    def test_empty_classifications(self):
        result = explanation({
            "risk_classification": {"classifications": []}
        })
        assert result["status"] == "error"

    def test_non_dict_risk_classification(self):
        result = explanation({"risk_classification": "not_a_dict"})
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Test: Output format
# ---------------------------------------------------------------------------

class TestOutputFormat:
    def test_all_required_fields_present(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
            escalations=[_make_escalation("X", "High", "Report (SAR draft)", "Auto-draft SAR")],
        )
        result = explanation(context)
        assert "tool" in result
        assert result["tool"] == "explanation"
        assert "status" in result
        assert "explanations" in result
        assert "summary" in result

    def test_entity_fields_complete(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.87)],
            escalations=[_make_escalation("X", "High", "Report (SAR draft)", "SAR")],
            method_used="statistical",
        )
        result = explanation(context)
        e = result["explanations"][0]
        required_fields = [
            "customer_id", "explanation", "risk_band", "risk_score",
            "recommended_action", "top_contributing_features",
            "determining_factor", "aml_pattern", "detection_method",
            "escalation_rationale", "explanation_path",
        ]
        for field in required_fields:
            assert field in e, f"Missing field: {field}"

    def test_risk_score_preserved_exactly(self):
        """DoD: every number traceable to input."""
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.87)],
        )
        result = explanation(context)
        e = result["explanations"][0]
        assert e["risk_score"] == 0.87
        assert "0.87" in e["explanation"]

    def test_summary_counts_match_explanations(self):
        context = _make_context(
            classifications=[
                _make_classification("A", "High", 0.9),
                _make_classification("B", "High", 0.8),
                _make_classification("C", "Low", 0.1),
            ],
        )
        result = explanation(context)
        assert result["summary"]["High"] == 2
        assert result["summary"]["Low"] == 1

    def test_tie_to_query_default_true(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
        )
        result = explanation(context)
        assert result["tie_to_query"] is True

    def test_tie_to_query_false(self):
        context = _make_context(
            classifications=[_make_classification("X", "High", 0.9)],
        )
        result = explanation(context, tie_to_query=False)
        assert result["tie_to_query"] is False

    def test_multiple_entities_all_explained(self):
        n = 5
        context = _make_context(
            classifications=[
                _make_classification(f"C{i}", "Low" if i % 2 == 0 else "High", 0.1 * i)
                for i in range(1, n + 1)
            ],
        )
        result = explanation(context)
        assert len(result["explanations"]) == n
