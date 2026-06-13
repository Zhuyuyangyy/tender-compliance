"""
Tests for Pydantic data models (backend/app/models/schemas.py).
Covers all model instantiation, validation, defaults, and Config.
"""
import pytest
from datetime import datetime


class TestClauseLocation:
    """Tests for ClauseLocation model."""

    def test_minimal(self):
        from backend.app.models.schemas import ClauseLocation
        loc = ClauseLocation(raw_text="test clause")
        assert loc.raw_text == "test clause"
        assert loc.chapter is None
        assert loc.line_start is None

    def test_full_fields(self):
        from backend.app.models.schemas import ClauseLocation
        loc = ClauseLocation(
            chapter="第一章",
            section="1.1",
            paragraph="para text",
            line_start=5,
            line_end=10,
            raw_text="full clause text"
        )
        assert loc.chapter == "第一章"
        assert loc.section == "1.1"
        assert loc.line_start == 5
        assert loc.line_end == 10

    def test_optional_fields_default_none(self):
        from backend.app.models.schemas import ClauseLocation
        loc = ClauseLocation(raw_text="x")
        assert loc.paragraph is None
        assert loc.line_start is None
        assert loc.line_end is None


class TestRiskItem:
    """Tests for RiskItem model."""

    def test_creation(self):
        from backend.app.models.schemas import RiskItem, ClauseLocation
        item = RiskItem(
            rule_id="R001",
            rule_type="exclusive_brand",
            risk_name="Test Risk",
            severity="high",
            location=ClauseLocation(raw_text="test"),
            evidence="found issue",
            suggestion="fix it"
        )
        assert item.rule_id == "R001"
        assert item.severity == "high"

    def test_all_severity_levels(self):
        from backend.app.models.schemas import RiskItem, ClauseLocation
        for level in ["critical", "high", "medium", "low", "info"]:
            item = RiskItem(
                rule_id="R001", rule_type="test", risk_name="t",
                severity=level,
                location=ClauseLocation(raw_text="x"),
                evidence="e", suggestion="s"
            )
            assert item.severity == level


class TestTenderAnalysisResult:
    """Tests for TenderAnalysisResult model."""

    def test_creation(self):
        from backend.app.models.schemas import TenderAnalysisResult
        result = TenderAnalysisResult(
            tender_id=1,
            risk_score=0.65,
            risk_level="yellow",
            risk_items=[],
            summary="1 risk found"
        )
        assert result.tender_id == 1
        assert result.risk_score == 0.65
        assert result.risk_level == "yellow"


class TestBidSimilarityResult:
    """Tests for BidSimilarityResult model."""

    def test_creation(self):
        from backend.app.models.schemas import BidSimilarityResult
        result = BidSimilarityResult(
            tender_id=1,
            total_bids=3,
            similarity_pairs=[{"pair": "A-B"}],
            price_curve_analysis={"deviation": 0.1},
            entity_connections=[],
            overall_risk_score=0.45,
            risk_level="yellow"
        )
        assert result.total_bids == 3
        assert len(result.similarity_pairs) == 1


class TestRiskReport:
    """Tests for RiskReport model."""

    def test_creation_with_defaults(self):
        from backend.app.models.schemas import (
            RiskReport, TenderAnalysisResult, BidSimilarityResult
        )
        report = RiskReport(
            tender_id=1,
            tender_analysis=TenderAnalysisResult(
                tender_id=1, risk_score=0.3, risk_level="green",
                risk_items=[], summary="ok"
            ),
            bid_analysis=BidSimilarityResult(
                tender_id=1, total_bids=2, similarity_pairs=[],
                price_curve_analysis={}, entity_connections=[],
                overall_risk_score=0.2, risk_level="green"
            ),
            final_risk_score=0.25,
            final_risk_level="green"
        )
        assert isinstance(report.generated_at, datetime)
        assert report.final_risk_level == "green"


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_creation(self):
        from backend.app.models.schemas import HealthResponse
        resp = HealthResponse(status="healthy", version="1.0.0", timestamp=datetime.now())
        assert resp.status == "healthy"
        assert resp.version == "1.0.0"


class TestUploadResponse:
    """Tests for UploadResponse model."""

    def test_success(self):
        from backend.app.models.schemas import UploadResponse
        resp = UploadResponse(success=True, message="ok", id=42)
        assert resp.success is True
        assert resp.id == 42

    def test_failure(self):
        from backend.app.models.schemas import UploadResponse
        resp = UploadResponse(success=False, message="error")
        assert resp.success is False
        assert resp.id is None


class TestRuleModels:
    """Tests for Rule-related models."""

    def test_rule_base(self):
        from backend.app.models.schemas import RuleBase
        rule = RuleBase(
            rule_id="R001",
            rule_type="exclusive_brand",
            description="test rule",
            severity="high"
        )
        assert rule.rule_id == "R001"
        assert rule.penalty is None

    def test_rule_create(self):
        from backend.app.models.schemas import RuleCreate
        rule = RuleCreate(
            rule_id="R002",
            rule_type="test",
            description="desc",
            severity="medium",
            penalty="fix"
        )
        assert rule.penalty == "fix"


class TestBidModels:
    """Tests for Bid-related models."""

    def test_bid_create(self):
        from backend.app.models.schemas import BidCreate
        bid = BidCreate(
            tender_id=1,
            bidder_name="Company A",
            content="bid content here"
        )
        assert bid.tender_id == 1
        assert bid.bidder_name == "Company A"


class TestAuditLogEntry:
    """Tests for AuditLogEntry model."""

    def test_creation(self):
        from backend.app.models.schemas import AuditLogEntry
        entry = AuditLogEntry(
            id=1,
            action="upload_tender",
            target_type="tender",
            target_id=10,
            details="uploaded file",
            created_at=datetime.now()
        )
        assert entry.action == "upload_tender"
