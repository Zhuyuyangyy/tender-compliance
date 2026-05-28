"""Smoke tests for tender-compliance system.

Tests cover:
- Core module imports
- TenderParser: parsing, risk detection, coordinate generation
- RuleEngine: semantic operator chain, risk detection
- TenderRiskScorer: risk entropy calculation, coupling effects
- SimilarityAnalyzer: bid similarity, price curves, entity connections
- ReportGenerator: report generation, export formats
- Pydantic schemas: model validation
"""
import importlib
import pytest


# ─── Module Import Tests ───────────────────────────────────────────

class TestImports:
    """Verify all core modules can be imported."""

    def test_import_tender_parser(self):
        from backend.app.services.tender_parser import TenderParser
        assert TenderParser is not None

    def test_import_rule_engine(self):
        from backend.app.services.rule_engine import RuleEngine, SemanticOperator
        assert RuleEngine is not None
        assert SemanticOperator is not None

    def test_import_risk_scorer(self):
        from backend.app.services.tender_risk_scorer import TenderRiskScorer
        assert TenderRiskScorer is not None

    def test_import_similarity_analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        assert SimilarityAnalyzer is not None

    def test_import_report_generator(self):
        from backend.app.services.report_generator import ReportGenerator
        assert ReportGenerator is not None

    def test_import_schemas(self):
        from backend.app.models.schemas import (
            RiskItem, ClauseLocation, TenderAnalysisResult,
            BidSimilarityResult, RiskReport, HealthResponse
        )
        assert all(cls is not None for cls in [
            RiskItem, ClauseLocation, TenderAnalysisResult,
            BidSimilarityResult, RiskReport, HealthResponse
        ])


# ─── TenderParser Tests ────────────────────────────────────────────

class TestTenderParser:
    """Test tender document parsing and risk detection."""

    @pytest.fixture
    def parser(self):
        from backend.app.services.tender_parser import TenderParser
        return TenderParser()

    @pytest.fixture
    def sample_tender(self):
        return """
第一章 招标公告
本次招标项目为某市政府信息化建设项目

第二章 投标人资格要求
投标人必须具有计算机系统集成一级资质
投标人应当具备ISO9001质量管理体系认证

第三章 评标办法
本项目采用综合评分法
评标委员会由5名专家组成
技术标占60%，商务标占40%

第四章 技术规格要求
服务器必须采用华为品牌
存储设备必须是EMC或IBM品牌

第五章 合同条款
付款方式：按进度付款
履约保证金：合同金额的10%
"""

    def test_parse_tender_returns_structure(self, parser, sample_tender):
        result = parser.parse_tender(sample_tender)
        assert isinstance(result, dict)
        assert "raw_content" in result
        assert "chapters" in result
        assert "clauses" in result
        assert "coordinates" in result

    def test_parse_tender_detects_chapters(self, parser, sample_tender):
        result = parser.parse_tender(sample_tender)
        assert len(result["chapters"]) >= 4

    def test_parse_tender_classifies_chapters(self, parser, sample_tender):
        result = parser.parse_tender(sample_tender)
        chapter_types = [c["type"] for c in result["chapters"]]
        assert "qualification" in chapter_types
        assert "scoring" in chapter_types
        assert "technical" in chapter_types

    def test_parse_tender_generates_coordinates(self, parser, sample_tender):
        result = parser.parse_tender(sample_tender)
        assert len(result["coordinates"]) > 0
        coord = result["coordinates"][0]["coordinate"]
        assert "x" in coord
        assert "y" in coord

    def test_detect_risks_finds_brand_restriction(self, parser, sample_tender):
        risks = parser.detect_risks(sample_tender)
        brand_risks = [r for r in risks if r.rule_type == "exclusive_brand"]
        assert len(brand_risks) >= 1
        assert brand_risks[0].severity == "high"

    def test_detect_risks_finds_qualification_exclusive(self, parser):
        content = "第二章 资格要求\n投标人必须具有甲级资质\n仅限一级企业参与"
        risks = parser.detect_risks(content)
        qual_risks = [r for r in risks if r.rule_type == "exclusive_qualification"]
        assert len(qual_risks) >= 1

    def test_detect_risks_empty_content(self, parser):
        risks = parser.detect_risks("")
        assert risks == []

    def test_detect_risks_clean_document(self, parser):
        content = "第一章 总则\n本项目采用公开招标方式\n欢迎符合条件的供应商参与"
        risks = parser.detect_risks(content)
        assert len(risks) == 0


# ─── RuleEngine Tests ──────────────────────────────────────────────

class TestRuleEngine:
    """Test semantic operator chain and rule detection."""

    @pytest.fixture
    def engine(self):
        from backend.app.services.rule_engine import RuleEngine
        return RuleEngine()

    @pytest.fixture
    def risky_content(self):
        return """
第一章 总则
第二章 投标人资格要求
投标人必须具有计算机系统集成一级资质
投标人必须是本地注册企业
第三章 评标办法
本项目采用综合评分法
评标委员会由专家组成
第四章 技术规格要求
服务器设备必须是华为品牌
存储设备指定供应商为EMC
第五章 合同条款
"""

    def test_detect_risks_finds_multiple_issues(self, engine, risky_content):
        risks = engine.detect_risks(risky_content)
        assert len(risks) >= 3

    def test_detect_risks_brand_restriction(self, engine, risky_content):
        risks = engine.detect_risks(risky_content)
        brand_risks = [r for r in risks if r.rule_type == "exclusive_brand"]
        assert len(brand_risks) >= 1

    def test_detect_risks_region_limitation(self, engine, risky_content):
        risks = engine.detect_risks(risky_content)
        region_risks = [r for r in risks if r.rule_type == "region_limitation"]
        assert len(region_risks) >= 1

    def test_apply_semantic_chain(self, engine, risky_content):
        results = engine.apply_semantic_chain(risky_content)
        assert len(results) > 0
        for result in results:
            assert "line" in result
            assert "operators" in result
            assert "risk_level" in result

    def test_semantic_chain_detects_p_limit(self, engine):
        content = "服务器必须是华为品牌"
        results = engine.apply_semantic_chain(content)
        assert any("P_LIMIT" in r["operators"] for r in results)

    def test_semantic_chain_detects_p_forbid(self, engine):
        content = "投标人必须具有甲级资质"
        results = engine.apply_semantic_chain(content)
        assert any("P_FORBID" in r["operators"] for r in results)

    def test_get_rule_by_id(self, engine):
        # This may return None if rules file is not loaded, but should not crash
        result = engine.get_rule_by_id("RULE_T_001")
        # Just verify it doesn't crash
        assert result is None or isinstance(result, dict)

    def test_evaluate_rule_compliance_unknown_rule(self, engine):
        result = engine.evaluate_rule_compliance("test content", "UNKNOWN_RULE")
        assert result["status"] == "unknown"

    def test_detect_risks_empty_content(self, engine):
        risks = engine.detect_risks("")
        assert risks == []


# ─── TenderRiskScorer Tests ────────────────────────────────────────

class TestTenderRiskScorer:
    """Test risk entropy calculation and coupling effects."""

    @pytest.fixture
    def scorer(self):
        from backend.app.services.tender_risk_scorer import TenderRiskScorer
        return TenderRiskScorer()

    @pytest.fixture
    def sample_risk_items(self):
        from backend.app.models.schemas import RiskItem, ClauseLocation
        return [
            RiskItem(
                rule_id="RULE_T_001",
                rule_type="exclusive_brand",
                risk_name="限定品牌",
                severity="high",
                location=ClauseLocation(line_start=10, line_end=10, raw_text="服务器必须是华为品牌"),
                evidence="检测到限定品牌",
                suggestion="改为同等档次品牌"
            ),
            RiskItem(
                rule_id="RULE_T_002",
                rule_type="exclusive_qualification",
                risk_name="排他资质",
                severity="critical",
                location=ClauseLocation(line_start=20, line_end=20, raw_text="投标人必须具有一级资质"),
                evidence="检测到排他资质",
                suggestion="调整为满足资质要求"
            )
        ]

    def test_empty_risk_items(self, scorer):
        result = scorer.calculate_tender_risk([])
        assert result["risk_score"] == 0.0
        assert result["risk_level"] == "green"

    def test_calculate_tender_risk(self, scorer, sample_risk_items):
        result = scorer.calculate_tender_risk(sample_risk_items)
        assert result["risk_score"] > 0
        assert result["risk_level"] in ["green", "yellow", "red"]
        assert "factor_scores" in result
        assert "coupling_alerts" in result

    def test_coupling_effect(self, scorer, sample_risk_items):
        result = scorer.calculate_tender_risk(sample_risk_items)
        # brand + qualification should trigger coupling
        assert result["coupling_multiplier"] > 1.0
        assert len(result["coupling_alerts"]) > 0

    def test_severity_to_score_mapping(self, scorer):
        assert scorer._severity_to_score("critical") == 1.0
        assert scorer._severity_to_score("high") == 0.75
        assert scorer._severity_to_score("medium") == 0.5
        assert scorer._severity_to_score("low") == 0.25

    def test_score_to_level_boundaries(self, scorer):
        assert scorer._score_to_level(0.1) == "green"
        assert scorer._score_to_level(0.4) == "yellow"
        assert scorer._score_to_level(0.7) == "red"

    def test_bid_similarity_risk(self, scorer):
        result = scorer.calculate_bid_similarity_risk(
            similarity_pairs=[{"bid1": "A", "bid2": "B", "similarity": 0.92, "risk_flag": True}],
            price_analysis={"price_deviation": 0.2, "curve_correlation": 0.95},
            entity_connections=[{"type": "ip", "entities": ["A", "C"]}]
        )
        assert result["risk_score"] > 0
        assert result["risk_level"] in ["green", "yellow", "red"]
        assert "components" in result


# ─── SimilarityAnalyzer Tests ──────────────────────────────────────

class TestSimilarityAnalyzer:
    """Test bid similarity analysis."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    @pytest.fixture
    def sample_bids(self):
        return [
            {
                "id": 1, "bidder_name": "公司A",
                "content": "投标文件 联系人：张三 电话：010-12345678 地址：北京市海淀区中关村大街1号 投标报价：150万元"
            },
            {
                "id": 2, "bidder_name": "公司B",
                "content": "投标文件 联系人：李四 电话：010-87654321 地址：北京市海淀区中关村大街1号 投标报价：148万元"
            },
            {
                "id": 3, "bidder_name": "公司C",
                "content": "投标文件 联系人：王五 电话：010-55555555 地址：北京市朝阳区建国路100号 投标报价：200万元"
            }
        ]

    def test_analyze_bids_with_two_bids(self, analyzer, sample_bids):
        result = analyzer.analyze_bids(sample_bids)
        assert "similarity_pairs" in result
        assert "price_analysis" in result
        assert "entity_connections" in result
        assert "overall_risk" in result
        assert "risk_level" in result

    def test_analyze_bids_single_bid(self, analyzer):
        bids = [{"id": 1, "bidder_name": "A", "content": "test"}]
        result = analyzer.analyze_bids(bids)
        assert result["similarity_pairs"] == []
        assert result["risk_level"] == "green"

    def test_cosine_similarity_identical(self, analyzer):
        vec = {0: 1.0, 1: 2.0, 2: 3.0}
        sim = analyzer._cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self, analyzer):
        vec1 = {0: 1.0, 1: 0.0}
        vec2 = {0: 0.0, 1: 1.0}
        sim = analyzer._cosine_similarity(vec1, vec2)
        assert abs(sim) < 0.001

    def test_cosine_similarity_empty(self, analyzer):
        sim = analyzer._cosine_similarity({}, {})
        assert sim == 0.0

    def test_extract_price(self, analyzer):
        assert analyzer._extract_price("投标报价：150万元") == 150.0
        assert analyzer._extract_price("总价为200万元") == 200.0

    def test_extract_contact_info(self, analyzer):
        info = analyzer._extract_contact_info("联系人：张三 电话：010-12345678")
        assert "张三" in info["names"]

    def test_entity_connections_shared_address(self, analyzer, sample_bids):
        result = analyzer.analyze_bids(sample_bids)
        # Company A and B share the same address
        address_connections = [c for c in result["entity_connections"] if c["type"] == "address"]
        assert len(address_connections) >= 1

    def test_build_similarity_graph(self, analyzer):
        pairs = [
            {"bid1_name": "A", "bid2_name": "B", "similarity": 0.9, "risk_flag": True},
            {"bid1_name": "A", "bid2_name": "C", "similarity": 0.3, "risk_flag": False}
        ]
        graph = analyzer.build_similarity_graph(pairs)
        assert "nodes" in graph
        assert "edges" in graph
        # Only high similarity edges should be included
        assert len(graph["edges"]) == 1


# ─── ReportGenerator Tests ─────────────────────────────────────────

class TestReportGenerator:
    """Test report generation and export."""

    @pytest.fixture
    def generator(self):
        from backend.app.services.report_generator import ReportGenerator
        return ReportGenerator()

    @pytest.fixture
    def sample_risk_items(self):
        from backend.app.models.schemas import RiskItem, ClauseLocation
        return [
            RiskItem(
                rule_id="RULE_T_001",
                rule_type="exclusive_brand",
                risk_name="限定品牌",
                severity="high",
                location=ClauseLocation(chapter="第四章", line_start=10, line_end=10, raw_text="必须是华为品牌"),
                evidence="检测到限定品牌",
                suggestion="改为同等档次品牌"
            )
        ]

    def test_generate_tender_report(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1,
            tender_name="测试项目",
            analysis_result={"risk_score": 0.65, "risk_level": "yellow", "risk_count": 1},
            risk_items=sample_risk_items
        )
        assert report["report_type"] == "tender_compliance"
        assert report["tender_id"] == 1
        assert "summary" in report
        assert "risk_distribution" in report
        assert "suggestions" in report

    def test_export_report_json(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="test",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        json_str = generator.export_report_json(report)
        assert isinstance(json_str, str)
        assert "tender_compliance" in json_str

    def test_export_report_markdown(self, generator, sample_risk_items):
        report = generator.generate_tender_report(
            tender_id=1, tender_name="test",
            analysis_result={"risk_score": 0.5, "risk_level": "yellow"},
            risk_items=sample_risk_items
        )
        md = generator.export_report_markdown(report)
        assert isinstance(md, str)
        assert "# tender_compliance Report" in md

    def test_calculate_final_risk(self, generator):
        score = generator._calculate_final_risk(0.6, 0.5)
        assert 0 <= score <= 1
        # Should be weighted: 0.6 * 0.6 + 0.5 * 0.4 = 0.56
        assert abs(score - 0.56) < 0.01

    def test_calculate_final_risk_coupling(self, generator):
        score = generator._calculate_final_risk(0.6, 0.5)
        # Both high, should trigger coupling
        assert score > 0.5


# ─── Schema Validation Tests ───────────────────────────────────────

class TestSchemas:
    """Test Pydantic model validation."""

    def test_clause_location(self):
        from backend.app.models.schemas import ClauseLocation
        loc = ClauseLocation(line_start=10, line_end=10, raw_text="test")
        assert loc.line_start == 10
        assert loc.raw_text == "test"

    def test_risk_item(self):
        from backend.app.models.schemas import RiskItem, ClauseLocation
        item = RiskItem(
            rule_id="RULE_T_001",
            rule_type="exclusive_brand",
            risk_name="test",
            severity="high",
            location=ClauseLocation(line_start=1, line_end=1, raw_text="test"),
            evidence="test",
            suggestion="test"
        )
        assert item.rule_id == "RULE_T_001"

    def test_health_response(self):
        from backend.app.models.schemas import HealthResponse
        from datetime import datetime
        resp = HealthResponse(status="ok", version="1.0", timestamp=datetime.now())
        assert resp.status == "ok"

    def test_upload_response(self):
        from backend.app.models.schemas import UploadResponse
        resp = UploadResponse(success=True, message="ok", id=1)
        assert resp.success is True
