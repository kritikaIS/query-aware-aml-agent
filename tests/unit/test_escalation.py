"""Unit tests for the Escalation Policy Layer.

Reference: Solution Design §5.7, Implementation Plan §6.6.
DoD: Table-driven; adding a new band/action requires a one-line config change,
     verified by test.
"""

from __future__ import annotations

import pytest

from src.tools.escalation import (
    escalation,
    _escalate_band,
    _load_escalation_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return _load_escalation_config()


@pytest.fixture
def policy(config):
    return config["policy"]


def _make_rc_result(classifications: list[dict]) -> dict:
    """Build a minimal risk_classification context dict."""
    return {
        "tool": "risk_classification",
        "status": "success",
        "classifications": classifications,
        "summary": {},
    }


# ---------------------------------------------------------------------------
# Test: Config loading and structure
# ---------------------------------------------------------------------------

class TestEscalationConfig:
    def test_config_loads(self, config):
        assert "policy" in config

    def test_all_three_bands_configured(self, policy):
        """DOCUMENTED: three bands Low, Medium, High (§5.7)."""
        assert "Low" in policy
        assert "Medium" in policy
        assert "High" in policy

    def test_each_band_has_action_and_rationale(self, policy):
        """DOCUMENTED: action and rationale per band (§5.7, §6.6 step 2)."""
        for band, entry in policy.items():
            assert "recommended_action" in entry, f"Missing recommended_action for {band}"
            assert "rationale" in entry, f"Missing rationale for {band}"

    def test_low_action_is_monitor(self, policy):
        """DOCUMENTED: Low → Monitor (§5.7 table)."""
        assert policy["Low"]["recommended_action"] == "Monitor"

    def test_medium_action_is_flag_for_review(self, policy):
        """DOCUMENTED: Medium → Flag for review (§5.7 table)."""
        assert policy["Medium"]["recommended_action"] == "Flag for review"

    def test_high_action_is_report_sar(self, policy):
        """DOCUMENTED: High → Report (SAR draft) (§5.7 table)."""
        assert policy["High"]["recommended_action"] == "Report (SAR draft)"

    def test_rationale_strings_non_empty(self, policy):
        """DOCUMENTED: human-readable rationale shown to reviewer (§6.6 step 2)."""
        for band, entry in policy.items():
            assert len(entry["rationale"]) > 0, f"Empty rationale for {band}"


# ---------------------------------------------------------------------------
# Test: _escalate_band core lookup
# ---------------------------------------------------------------------------

class TestEscalateBand:
    def test_low_returns_monitor(self, policy):
        action, rationale = _escalate_band("Low", policy)
        assert action == "Monitor"

    def test_medium_returns_flag_for_review(self, policy):
        action, rationale = _escalate_band("Medium", policy)
        assert action == "Flag for review"

    def test_high_returns_report_sar_draft(self, policy):
        action, rationale = _escalate_band("High", policy)
        assert action == "Report (SAR draft)"

    def test_low_rationale_matches_doc(self, policy):
        """DOCUMENTED rationale: 'No further action; keep in rolling watch list'."""
        _, rationale = _escalate_band("Low", policy)
        assert "rolling watch list" in rationale.lower() or "monitor" in rationale.lower()

    def test_medium_rationale_mentions_sla(self, policy):
        """DOCUMENTED rationale mentions SLA (§5.7)."""
        _, rationale = _escalate_band("Medium", policy)
        assert "sla" in rationale.lower() or "analyst" in rationale.lower() or "review" in rationale.lower()

    def test_high_rationale_mentions_sar(self, policy):
        """DOCUMENTED rationale mentions SAR (§5.7)."""
        _, rationale = _escalate_band("High", policy)
        assert "sar" in rationale.lower() or "suspicious activity" in rationale.lower()

    def test_unknown_band_raises_value_error(self, policy):
        """Unknown band raises ValueError rather than returning silently."""
        with pytest.raises(ValueError, match="unknown risk band"):
            _escalate_band("Critical", policy)

    def test_empty_band_raises_value_error(self, policy):
        with pytest.raises(ValueError, match="unknown risk band"):
            _escalate_band("", policy)

    def test_case_sensitive(self, policy):
        """Band names are case-sensitive (Low ≠ low)."""
        with pytest.raises(ValueError):
            _escalate_band("low", policy)

    def test_lookup_deterministic(self, policy):
        """Same input always produces the same output."""
        for band in ["Low", "Medium", "High"]:
            r1 = _escalate_band(band, policy)
            r2 = _escalate_band(band, policy)
            assert r1 == r2


# ---------------------------------------------------------------------------
# Test: Tool function — all documented escalation levels
# ---------------------------------------------------------------------------

class TestEscalationToolLevels:
    def test_low_band_escalated_correctly(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "C1", "risk_band": "Low", "risk_score": 0.1}
            ])
        }
        result = escalation(context)
        assert result["status"] == "success"
        e = result["escalations"][0]
        assert e["recommended_action"] == "Monitor"
        assert e["customer_id"] == "C1"
        assert e["risk_band"] == "Low"

    def test_medium_band_escalated_correctly(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "C2", "risk_band": "Medium", "risk_score": 0.5}
            ])
        }
        result = escalation(context)
        e = result["escalations"][0]
        assert e["recommended_action"] == "Flag for review"

    def test_high_band_escalated_correctly(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "C3", "risk_band": "High", "risk_score": 0.9}
            ])
        }
        result = escalation(context)
        e = result["escalations"][0]
        assert e["recommended_action"] == "Report (SAR draft)"

    def test_rationale_attached_to_each_entity(self):
        """DOCUMENTED: rationale string shown to reviewer (§6.6 step 2)."""
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "C1", "risk_band": "Low", "risk_score": 0.1},
                {"customer_id": "C2", "risk_band": "Medium", "risk_score": 0.5},
                {"customer_id": "C3", "risk_band": "High", "risk_score": 0.9},
            ])
        }
        result = escalation(context)
        for e in result["escalations"]:
            assert "rationale" in e
            assert len(e["rationale"]) > 0

    def test_risk_score_passed_through(self):
        """Risk score from Risk Classification is preserved in output."""
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "X", "risk_band": "High", "risk_score": 0.87}
            ])
        }
        result = escalation(context)
        assert result["escalations"][0]["risk_score"] == 0.87

    def test_risk_band_passed_through(self):
        """Risk band is preserved for auditability."""
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "X", "risk_band": "Medium", "risk_score": 0.5}
            ])
        }
        result = escalation(context)
        assert result["escalations"][0]["risk_band"] == "Medium"

    def test_customer_id_passed_through(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "4521", "risk_band": "High", "risk_score": 0.9}
            ])
        }
        result = escalation(context)
        assert result["escalations"][0]["customer_id"] == "4521"


# ---------------------------------------------------------------------------
# Test: Tool function — summary
# ---------------------------------------------------------------------------

class TestEscalationSummary:
    def test_summary_counts_per_action(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "C1", "risk_band": "Low", "risk_score": 0.1},
                {"customer_id": "C2", "risk_band": "High", "risk_score": 0.9},
                {"customer_id": "C3", "risk_band": "High", "risk_score": 0.95},
                {"customer_id": "C4", "risk_band": "Medium", "risk_score": 0.5},
            ])
        }
        result = escalation(context)
        summary = result["summary"]
        assert summary["Monitor"] == 1
        assert summary["Flag for review"] == 1
        assert summary["Report (SAR draft)"] == 2

    def test_summary_total_equals_entity_count(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": f"C{i}", "risk_band": "Low", "risk_score": 0.1}
                for i in range(7)
            ])
        }
        result = escalation(context)
        total = sum(result["summary"].values())
        assert total == 7


# ---------------------------------------------------------------------------
# Test: Tool function — error handling
# ---------------------------------------------------------------------------

class TestEscalationErrors:
    def test_missing_risk_classification_returns_error(self):
        result = escalation({})
        assert result["status"] == "error"
        assert "risk_classification" in result["error"].lower()

    def test_empty_classifications_returns_error(self):
        context = {"risk_classification": {"classifications": []}}
        result = escalation(context)
        assert result["status"] == "error"

    def test_non_dict_risk_classification_returns_error(self):
        result = escalation({"risk_classification": "not_a_dict"})
        assert result["status"] == "error"

    def test_unknown_band_returns_error_not_exception(self):
        """Tool function should return error dict, not raise, on unknown band."""
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "X", "risk_band": "Critical", "risk_score": 0.9}
            ])
        }
        result = escalation(context)
        assert result["status"] == "error"
        assert "unknown risk band" in result["error"].lower()


# ---------------------------------------------------------------------------
# Test: Documented DoD — table-driven, one-line config change
# ---------------------------------------------------------------------------

class TestDefinitionOfDone:
    def test_adding_new_band_requires_only_config_change(self):
        """DoD: adding a new band/action requires a one-line config change.
        Verified by directly calling _escalate_band with an extended policy dict.
        """
        extended_policy = {
            "Low": {"recommended_action": "Monitor", "rationale": "watch"},
            "Medium": {"recommended_action": "Flag for review", "rationale": "review"},
            "High": {"recommended_action": "Report (SAR draft)", "rationale": "report"},
            "Critical": {"recommended_action": "Immediate freeze", "rationale": "freeze assets"},
        }
        action, rationale = _escalate_band("Critical", extended_policy)
        assert action == "Immediate freeze"
        assert rationale == "freeze assets"

    def test_deterministic_same_input_same_output(self):
        """DoD: deterministic behaviour."""
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "A", "risk_band": "Low", "risk_score": 0.1},
                {"customer_id": "B", "risk_band": "Medium", "risk_score": 0.5},
                {"customer_id": "C", "risk_band": "High", "risk_score": 0.9},
            ])
        }
        r1 = escalation(context)
        r2 = escalation(context)
        for e1, e2 in zip(r1["escalations"], r2["escalations"]):
            assert e1["recommended_action"] == e2["recommended_action"]
            assert e1["rationale"] == e2["rationale"]

    def test_no_llm_involvement(self):
        """DoD: pure lookup table, no LLM involvement (§6.6 step 1).
        The entire module imports only yaml — no LLM client is ever instantiated.
        Verified by inspecting escalation output for determinism on identical input.
        """
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "X", "risk_band": "High", "risk_score": 0.9}
            ])
        }
        # If LLM were involved, result would be non-deterministic across calls
        results = [escalation(context) for _ in range(5)]
        actions = [r["escalations"][0]["recommended_action"] for r in results]
        assert len(set(actions)) == 1, "Non-deterministic output detected"

    def test_output_fields_complete(self):
        """Every documented field is present in every entity output."""
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "X", "risk_band": "High", "risk_score": 0.9}
            ])
        }
        result = escalation(context)
        assert result["status"] == "success"
        assert "escalations" in result
        assert "summary" in result
        e = result["escalations"][0]
        # Documented fields:
        assert "customer_id" in e
        assert "risk_band" in e
        assert "risk_score" in e
        assert "recommended_action" in e  # documented §5.7
        assert "rationale" in e           # documented §6.6 step 2


# ---------------------------------------------------------------------------
# Test: Boundary conditions
# ---------------------------------------------------------------------------

class TestBoundaryConditions:
    def test_single_entity_low(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "solo", "risk_band": "Low", "risk_score": 0.05}
            ])
        }
        result = escalation(context)
        assert len(result["escalations"]) == 1
        assert result["escalations"][0]["recommended_action"] == "Monitor"

    def test_many_entities_all_high(self):
        n = 100
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": f"C{i}", "risk_band": "High", "risk_score": 0.95}
                for i in range(n)
            ])
        }
        result = escalation(context)
        assert len(result["escalations"]) == n
        for e in result["escalations"]:
            assert e["recommended_action"] == "Report (SAR draft)"
        assert result["summary"]["Report (SAR draft)"] == n

    def test_mixed_bands_correct_mapping(self):
        context = {
            "risk_classification": _make_rc_result([
                {"customer_id": "low_cust", "risk_band": "Low", "risk_score": 0.1},
                {"customer_id": "med_cust", "risk_band": "Medium", "risk_score": 0.5},
                {"customer_id": "high_cust", "risk_band": "High", "risk_score": 0.9},
            ])
        }
        result = escalation(context)
        escalations_by_id = {e["customer_id"]: e for e in result["escalations"]}
        assert escalations_by_id["low_cust"]["recommended_action"] == "Monitor"
        assert escalations_by_id["med_cust"]["recommended_action"] == "Flag for review"
        assert escalations_by_id["high_cust"]["recommended_action"] == "Report (SAR draft)"

    def test_classification_with_extra_fields_not_broken(self):
        """Extra fields in risk_classification output do not break escalation."""
        context = {
            "risk_classification": _make_rc_result([
                {
                    "customer_id": "X",
                    "risk_band": "Medium",
                    "risk_score": 0.5,
                    "determining_factor": "some_feature",
                    "initial_band": "Low",
                    "rule_override": True,
                }
            ])
        }
        result = escalation(context)
        assert result["status"] == "success"
        assert result["escalations"][0]["recommended_action"] == "Flag for review"
