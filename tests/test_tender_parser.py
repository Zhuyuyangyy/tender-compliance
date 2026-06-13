"""
Tests for TenderParser (backend/app/services/tender_parser.py).
Covers document parsing, chapter classification, coordinate generation,
zone extraction, and risk detection.
"""
import pytest


class TestTenderParserParsing:
    """Test the parse_tender method."""

    @pytest.fixture
    def parser(self):
        from backend.app.services.tender_parser import TenderParser
        return TenderParser()

    def test_returns_dict_structure(self, parser, sample_tender_content):
        result = parser.parse_tender(sample_tender_content)
        assert isinstance(result, dict)
        for key in ["raw_content", "total_lines", "chapters", "clauses", "coordinates"]:
            assert key in result

    def test_raw_content_preserved(self, parser, sample_tender_content):
        result = parser.parse_tender(sample_tender_content)
        assert result["raw_content"] == sample_tender_content

    def test_total_lines_counted(self, parser, sample_tender_content):
        result = parser.parse_tender(sample_tender_content)
        assert result["total_lines"] == len(sample_tender_content.split("\n"))

    def test_chapters_detected(self, parser, sample_tender_content):
        result = parser.parse_tender(sample_tender_content)
        assert len(result["chapters"]) >= 4
        chapter_titles = [c["title"] for c in result["chapters"]]
        assert any("招标公告" in t for t in chapter_titles)
        assert any("资格要求" in t for t in chapter_titles)

    def test_chapter_types_classified(self, parser, sample_tender_content):
        result = parser.parse_tender(sample_tender_content)
        types = {c["type"] for c in result["chapters"]}
        assert "qualification" in types
        assert "scoring" in types
        assert "technical" in types

    def test_coordinates_generated(self, parser, sample_tender_content):
        result = parser.parse_tender(sample_tender_content)
        assert len(result["coordinates"]) > 0
        coord = result["coordinates"][0]["coordinate"]
        assert "x" in coord and "y" in coord and "z" in coord
        assert 0 <= coord["x"] <= 1
        assert 0 <= coord["y"] <= 1

    def test_zones_extracted(self, parser, sample_tender_content):
        result = parser.parse_tender(sample_tender_content)
        assert "qualification_zone" in result
        assert "scoring_zone" in result
        assert "technical_zone" in result
        assert "contract_zone" in result

    def test_empty_content(self, parser):
        result = parser.parse_tender("")
        assert result["chapters"] == []
        assert result["total_lines"] == 1  # empty string has one split element

    def test_single_line(self, parser):
        result = parser.parse_tender("第一章 总则")
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["type"] == "general"


class TestTenderParserClassification:
    """Test chapter and clause classification."""

    @pytest.fixture
    def parser(self):
        from backend.app.services.tender_parser import TenderParser
        return TenderParser()

    def test_classify_chapter_qualification(self, parser):
        assert parser._classify_chapter("第二章 投标人资格要求") == "qualification"
        assert parser._classify_chapter("资质条件") == "qualification"

    def test_classify_chapter_scoring(self, parser):
        assert parser._classify_chapter("第三章 评标办法") == "scoring"
        assert parser._classify_chapter("评分标准") == "scoring"

    def test_classify_chapter_technical(self, parser):
        assert parser._classify_chapter("第四章 技术规格要求") == "technical"

    def test_classify_chapter_commercial(self, parser):
        assert parser._classify_chapter("商务报价要求") == "commercial"

    def test_classify_chapter_contract(self, parser):
        assert parser._classify_chapter("合同协议条款") == "contract"

    def test_classify_chapter_general(self, parser):
        assert parser._classify_chapter("附录") == "general"

    def test_classify_clause_brand(self, parser):
        assert parser._classify_clause("必须是华为品牌服务器") == "brand_restriction"

    def test_classify_clause_qualification(self, parser):
        assert parser._classify_clause("仅限一级资质企业") == "qualification_exclusive"

    def test_classify_clause_normal(self, parser):
        assert parser._classify_clause("本项目采用公开招标") == "normal"


class TestTenderParserRiskDetection:
    """Test the detect_risks method."""

    @pytest.fixture
    def parser(self):
        from backend.app.services.tender_parser import TenderParser
        return TenderParser()

    def test_detects_brand_restriction(self, parser, sample_tender_content):
        risks = parser.detect_risks(sample_tender_content)
        brand_risks = [r for r in risks if r.rule_type == "exclusive_brand"]
        assert len(brand_risks) >= 2  # 华为 + EMC/IBM
        for r in brand_risks:
            assert r.severity == "high"
            assert r.rule_id == "RULE_T_001"

    def test_detects_qualification_exclusive(self, parser):
        content = "第二章 资格\n投标人必须具有甲级资质"
        risks = parser.detect_risks(content)
        qual_risks = [r for r in risks if r.rule_type == "exclusive_qualification"]
        assert len(qual_risks) >= 1

    def test_detects_unclear_scoring(self, parser):
        content = "第三章 评标\n本项目采用综合评分法\n由评标委员会决定"
        risks = parser.detect_risks(content)
        scoring_risks = [r for r in risks if r.rule_type == "unclear_scoring"]
        assert len(scoring_risks) >= 1
        assert scoring_risks[0].severity == "medium"

    def test_empty_content_no_risks(self, parser):
        assert parser.detect_risks("") == []

    def test_clean_document_no_risks(self, parser, clean_tender_content):
        risks = parser.detect_risks(clean_tender_content)
        assert len(risks) == 0

    def test_risk_has_location(self, parser):
        content = "服务器必须是华为品牌"
        risks = parser.detect_risks(content)
        assert len(risks) >= 1
        assert risks[0].location.raw_text != ""

    def test_risk_has_suggestion(self, parser):
        content = "服务器必须是华为品牌"
        risks = parser.detect_risks(content)
        assert len(risks) >= 1
        assert len(risks[0].suggestion) > 0

    def test_multiple_risk_types(self, parser, sample_tender_content):
        risks = parser.detect_risks(sample_tender_content)
        types = {r.rule_type for r in risks}
        assert "exclusive_brand" in types


class TestTenderParserCoordinateGeneration:
    """Test virtual coordinate generation."""

    @pytest.fixture
    def parser(self):
        from backend.app.services.tender_parser import TenderParser
        return TenderParser()

    def test_coordinate_has_xyz(self, parser):
        coord = parser._generate_coordinate("qualification", 10, 100)
        assert "x" in coord and "y" in coord and "z" in coord

    def test_coordinate_x_proportional(self, parser):
        coord = parser._generate_coordinate("qualification", 50, 100)
        assert abs(coord["x"] - 0.5) < 0.01

    def test_coordinate_y_based_on_type(self, parser):
        coord_qual = parser._generate_coordinate("qualification", 10, 100)
        coord_score = parser._generate_coordinate("scoring", 10, 100)
        assert coord_qual["y"] != coord_score["y"]


class TestTenderParserZoneExtraction:
    """Test zone extraction methods."""

    @pytest.fixture
    def parser(self):
        from backend.app.services.tender_parser import TenderParser
        return TenderParser()

    def test_extract_zone_finds_keywords(self, parser):
        content = "第一行\n必须具有甲级资质\n第三行"
        results = parser._extract_zone(content, ["必须具有"])
        assert len(results) >= 1
        assert results[0]["keyword"] == "必须具有"

    def test_extract_zone_no_match(self, parser):
        results = parser._extract_zone("普通文本内容", ["不存在的关键词"])
        assert results == []

    def test_extract_zone_includes_context(self, parser):
        content = "行1\n行2\n必须具有资质\n行4\n行5"
        results = parser._extract_zone(content, ["必须具有"])
        assert len(results) >= 1
        assert "context" in results[0]
        assert len(results[0]["context"]) >= 1
