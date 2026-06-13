"""
Tests for TenderRiskScorer (backend/app/services/tender_risk_scorer.py).
Covers risk entropy calculation, coupling effects, severity mapping,
bid similarity risk scoring.
"""
import pytest


class TestTenderRiskCalculation:
    """Test calculate_tender_risk method."""

    @pytest.fixture
    def scorer(self):
        from backend.app.services.tender_risk_scorer import TenderRiskScorer
        return TenderRiskScorer()

    def test_empty_risk_items(self, scorer):
        result = scorer.calculate_tender_risk([])
        assert result["risk_score"] == 0.0
        assert result["risk_level"] == "green"
        assert result["factor_scores"] == {}
        assert result["coupling_alerts"] == []

    def test_single_risk_item(self, scorer, sample_risk_items):
        single = [sample_risk_items[0]]
        result = scorer.calculate_tender_risk(single)
        assert result["risk_score"] > 0
        assert result["risk_level"] in ["green", "yellow", "red"]
        assert "exclusive_brand" in result["factor_scores"]

    def test_multiple_risk_items(self, scorer, sample_risk_items):
        result = scorer.calculate_tender_risk(sample_risk_items)
        assert result["risk_score"] > 0
        assert len(result["factor_scores"]) >= 2

    def test_coupling_effect_brand_qualification(self, scorer, sample_risk_items):
        """brand + qualification should trigger coupling amplification."""
        result = scorer.calculate_tender_risk(sample_risk_items)
        assert result["coupling_multiplier"] > 1.0
        assert len(result["coupling_alerts"]) > 0

    def test_score_capped_at_one(self, scorer):
        from backend.app.models.schemas import RiskItem, ClauseLocation
        # Create many critical risks to test cap
        items = [
            RiskItem(
                rule_id=f"R{i}", rule_type=t, risk_name=f"Risk {i}",
                severity="critical",
                location=ClauseLocation(raw_text=f"text {i}"),
                evidence="e", suggestion="s"
            )
            for i, t in enumerate([
                "exclusive_brand", "exclusive_qualification",
                "bid_similarity", "entity_connection", "price_anomaly"
            ])
        ]
        result = scorer.calculate_tender_risk(items)
        assert result["risk_score"] <= 1.0

    def test_result_has_all_fields(self, scorer, sample_risk_items):
        result = scorer.calculate_tender_risk(sample_risk_items)
        assert "risk_score" in result
        assert "risk_level" in result
        assert "factor_scores" in result
        assert "coupling_multiplier" in result
        assert "coupling_alerts" in result


class TestBidSimilarityRisk:
    """Test calculate_bid_similarity_risk method."""

    @pytest.fixture
    def scorer(self):
        from backend.app.services.tender_risk_scorer import TenderRiskScorer
        return TenderRiskScorer()

    def test_no_data(self, scorer):
        result = scorer.calculate_bid_similarity_risk([], {}, [])
        assert result["risk_score"] == 0.0
        assert result["risk_level"] == "green"

    def test_high_similarity_pair(self, scorer):
        pairs = [{"bid1": "A", "bid2": "B", "similarity": 0.92, "risk_flag": True}]
        result = scorer.calculate_bid_similarity_risk(pairs, {}, [])
        assert result["risk_score"] > 0
        assert result["components"]["similarity_risk"] > 0

    def test_multiple_high_similarity_pairs(self, scorer):
        pairs = [
            {"bid1": "A", "bid2": "B", "similarity": 0.90, "risk_flag": True},
            {"bid1": "A", "bid2": "C", "similarity": 0.88, "risk_flag": True}
        ]
        result = scorer.calculate_bid_similarity_risk(pairs, {}, [])
        assert result["high_similarity_pairs"] == 2
        assert result["components"]["similarity_risk"] > 0.8

    def test_price_anomaly(self, scorer):
        price = {"price_deviation": 0.25, "curve_correlation": 0.95}
        result = scorer.calculate_bid_similarity_risk([], price, [])
        assert result["components"]["price_risk"] > 0

    def test_entity_connections(self, scorer):
        connections = [
            {"type": "ip", "entities": ["A", "B"]},
            {"type": "contact", "entities": ["A", "C"]}
        ]
        result = scorer.calculate_bid_similarity_risk([], {}, connections)
        assert result["components"]["entity_risk"] > 0
        assert result["entity_connection_count"] == 2

    def test_nonlinear_fuse_high_similarity_and_entity(self, scorer):
        pairs = [{"bid1": "A", "bid2": "B", "similarity": 0.92, "risk_flag": True}]
        connections = [{"type": "ip", "entities": ["A", "B"]}]
        result = scorer.calculate_bid_similarity_risk(pairs, {}, connections)
        # Should trigger nonlinear fuse
        assert result["risk_score"] > 0.3

    def test_score_capped_at_one(self, scorer):
        pairs = [
            {"bid1": "A", "bid2": "B", "similarity": 0.99, "risk_flag": True},
            {"bid1": "A", "bid2": "C", "similarity": 0.98, "risk_flag": True},
            {"bid1": "B", "bid2": "C", "similarity": 0.97, "risk_flag": True}
        ]
        price = {"price_deviation": 0.5, "curve_correlation": 0.99}
        connections = [
            {"type": "ip", "entities": ["A", "B"]},
            {"type": "contact", "entities": ["A", "C"]},
            {"type": "address", "entities": ["B", "C"]}
        ]
        result = scorer.calculate_bid_similarity_risk(pairs, price, connections)
        assert result["risk_score"] <= 1.0


class TestSeverityMapping:
    """Test severity-to-score conversion."""

    @pytest.fixture
    def scorer(self):
        from backend.app.services.tender_risk_scorer import TenderRiskScorer
        return TenderRiskScorer()

    def test_critical(self, scorer):
        assert scorer._severity_to_score("critical") == 1.0

    def test_high(self, scorer):
        assert scorer._severity_to_score("high") == 0.75

    def test_medium(self, scorer):
        assert scorer._severity_to_score("medium") == 0.5

    def test_low(self, scorer):
        assert scorer._severity_to_score("low") == 0.25

    def test_info(self, scorer):
        assert scorer._severity_to_score("info") == 0.1

    def test_unknown_defaults(self, scorer):
        assert scorer._severity_to_score("unknown") == 0.3

    def test_case_insensitive(self, scorer):
        assert scorer._severity_to_score("HIGH") == 0.75
        assert scorer._severity_to_score("Critical") == 1.0


class TestScoreToLevel:
    """Test score-to-level conversion."""

    @pytest.fixture
    def scorer(self):
        from backend.app.services.tender_risk_scorer import TenderRiskScorer
        return TenderRiskScorer()

    def test_green_low(self, scorer):
        assert scorer._score_to_level(0.0) == "green"

    def test_green_boundary(self, scorer):
        assert scorer._score_to_level(0.29) == "green"

    def test_yellow(self, scorer):
        assert scorer._score_to_level(0.3) == "yellow"
        assert scorer._score_to_level(0.59) == "yellow"

    def test_red(self, scorer):
        assert scorer._score_to_level(0.6) == "red"
        assert scorer._score_to_level(1.0) == "red"
