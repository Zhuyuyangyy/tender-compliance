"""
Tests for ReportGenerator (backend/app/services/report_generator.py).
Covers tender reports, bid reports, comprehensive reports, export formats.
"""
import json
import pytest


class TestTenderReport:
    """Test tender compliance report generation."""

    @pytest.fixture
    def generator(self):
        from backend.app.services.report_generator import ReportGenerator
        return ReportGenerator()

    def test_generate_tender_report_structure(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1,
            tender_name="Test Project",
            analysis_result={"risk_score": 0.65, "risk_level": "yellow", "risk_count": 1},
            risk_items=sample_risk_items
        )
        assert report["report_type"] == "tender_compliance"
        assert report["tender_id"] == 1
        assert report["tender_name"] == "Test Project"
        assert "generated_at" in report
        assert "summary" in report
        assert "risk_distribution" in report
        assert "chapter_analysis" in report
        assert "detail_items" in report
        assert "suggestions" in report
        assert "audit_trail" in report

    def test_summary_text_by_level(self, generator, sample_risk_items):
        for level, expected_keyword in [("green", "良好"), ("yellow", "一定风险"), ("red", "严重")]:
            report = generator.generate_tender_report(
                tender_id=1, tender_name="t",
                analysis_result={"risk_score": 0.5, "risk_level": level},
                risk_items=sample_risk_items
            )
            assert expected_keyword in report["summary"]["summary_text"]

    def test_risk_distribution_by_severity(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        dist = report["risk_distribution"]["by_severity"]
        assert dist["high"] >= 2  # brand + qualification
        assert dist["medium"] >= 1  # region_limitation

    def test_risk_distribution_by_type(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        types = report["risk_distribution"]["by_type"]
        assert "exclusive_brand" in types

    def test_chapter_analysis(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        chapters = report["chapter_analysis"]
        assert len(chapters) >= 1
        for ch in chapters:
            assert "chapter" in ch
            assert "risk_count" in ch

    def test_detail_items_formatted(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        items = report["detail_items"]
        assert len(items) == len(sample_risk_items)
        for item in items:
            assert "rule_id" in item
            assert "risk_name" in item
            assert "severity" in item
            assert "evidence" in item
            assert "suggestion" in item

    def test_suggestions_generated(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        suggestions = report["suggestions"]
        assert len(suggestions) >= 1
        for s in suggestions:
            assert "priority" in s
            assert "suggestion" in s

    def test_audit_trail_present(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        trail = report["audit_trail"]
        assert trail["action"] == "tender_analysis"
        assert trail["target_id"] == 1
        assert "timestamp" in trail

    def test_empty_risk_items(self, generator):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0, "risk_level": "green"},
            risk_items=[]
        )
        assert report["detail_items"] == []
        assert report["suggestions"] == []


class TestBidSimilarityReport:
    """Test bid similarity report generation."""

    @pytest.fixture
    def generator(self):
        from backend.app.services.report_generator import ReportGenerator
        return ReportGenerator()

    def test_generate_bid_report(self, generator):
        sim_result = {
            "bids": [{"id": 1}, {"id": 2}],
            "similarity_pairs": [{"bid1": "A", "bid2": "B", "risk_flag": True}],
            "risk_summary": {}
        }
        price = {"anomaly_detected": True}
        connections = [{"type": "ip", "risk_level": "high", "entities": ["A", "B"]}]

        report = generator.generate_bid_similarity_report(
            tender_id=1, tender_name="t",
            similarity_result=sim_result,
            price_analysis=price,
            entity_connections=connections
        )
        assert report["report_type"] == "bid_similarity"
        assert report["tender_id"] == 1
        assert "summary" in report
        assert "suggestions" in report

    def test_bid_suggestions_with_high_similarity(self, generator):
        sim_result = {
            "bids": [],
            "similarity_pairs": [{"bid1": "A", "bid2": "B", "risk_flag": True}],
            "price_analysis": {}
        }
        report = generator.generate_bid_similarity_report(
            tender_id=1, tender_name="t",
            similarity_result=sim_result,
            price_analysis={},
            entity_connections=[]
        )
        suggestions = report["suggestions"]
        assert any(s["type"] == "similarity" for s in suggestions)


class TestComprehensiveReport:
    """Test comprehensive report generation."""

    @pytest.fixture
    def generator(self):
        from backend.app.services.report_generator import ReportGenerator
        return ReportGenerator()

    def test_generate_comprehensive_report(self, generator, sample_risk_items):
        tender_analysis = {
            "risk_score": 0.6,
            "risk_level": "yellow",
            "risk_items": sample_risk_items,
            "risk_count": len(sample_risk_items),
            "summary": "Found risks"
        }
        bid_analysis = {
            "total_bids": 3,
            "similarity_pairs": [],
            "price_analysis": {},
            "entity_connections": [],
            "overall_risk": 0.3,
            "risk_level": "green"
        }

        report = generator.generate_comprehensive_report(
            tender_id=1, tender_name="t",
            tender_analysis=tender_analysis,
            bid_analysis=bid_analysis
        )
        assert report.tender_id == 1
        assert report.final_risk_score > 0
        assert report.final_risk_level in ["green", "yellow", "red"]

    def test_final_risk_weighted(self, generator):
        # tender risk 0.6 * 0.6 + bid risk 0.4 * 0.4 = 0.52
        score = generator._calculate_final_risk(0.6, 0.4)
        assert abs(score - 0.52) < 0.01

    def test_final_risk_coupling(self, generator):
        # Both high should trigger coupling
        score = generator._calculate_final_risk(0.6, 0.5)
        # 0.6*0.6 + 0.5*0.4 = 0.56, then * 1.3 = 0.728
        assert score > 0.56

    def test_score_to_level(self, generator):
        assert generator._score_to_level(0.1) == "green"
        assert generator._score_to_level(0.4) == "yellow"
        assert generator._score_to_level(0.7) == "red"


class TestExportFormats:
    """Test report export methods."""

    @pytest.fixture
    def generator(self):
        from backend.app.services.report_generator import ReportGenerator
        return ReportGenerator()

    def test_export_json(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        json_str = generator.export_report_json(report)
        parsed = json.loads(json_str)
        assert parsed["report_type"] == "tender_compliance"

    def test_export_markdown(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        md = generator.export_report_markdown(report)
        assert "# tender_compliance Report" in md
        assert "Risk Level" in md
        assert "Risk Details" in md

    def test_export_markdown_with_items(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="t",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        md = generator.export_report_markdown(report)
        for item in sample_risk_items:
            assert item.risk_name in md


class TestAuditTrail:
    """Test audit trail generation."""

    @pytest.fixture
    def generator(self):
        from backend.app.services.report_generator import ReportGenerator
        return ReportGenerator()

    def test_audit_trail_fields(self, generator):
        trail = generator._generate_audit_trail("test_action", 42, {"key": "value"})
        assert trail["action"] == "test_action"
        assert trail["target_id"] == 42
        assert trail["operator"] == "system"
        assert "timestamp" in trail
        assert "data_snapshot" in trail

    def test_audit_trail_data_truncated(self, generator):
        large_data = {"content": "x" * 5000}
        trail = generator._generate_audit_trail("test", 1, large_data)
        assert len(trail["data_snapshot"]) <= 1000
