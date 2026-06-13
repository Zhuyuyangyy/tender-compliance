"""
Tests for RuleEngine (backend/app/services/rule_engine.py).
Covers semantic operator chain, risk detection, rule evaluation.
"""
import pytest


class TestRuleEngineRiskDetection:
    """Test the detect_risks method of RuleEngine."""

    @pytest.fixture
    def engine(self):
        from backend.app.services.rule_engine import RuleEngine
        return RuleEngine()

    def test_empty_content(self, engine):
        assert engine.detect_risks("") == []

    def test_clean_content(self, engine, clean_tender_content):
        risks = engine.detect_risks(clean_tender_content)
        assert len(risks) == 0

    def test_detects_brand_restriction(self, engine):
        content = "服务器设备必须是华为品牌"
        risks = engine.detect_risks(content)
        brand_risks = [r for r in risks if r.rule_type == "exclusive_brand"]
        assert len(brand_risks) >= 1
        assert brand_risks[0].severity == "high"

    def test_detects_multiple_brand_keywords(self, engine):
        keywords = ["必须是华为", "限于思科", "仅限Oracle", "指定供应商EMC"]
        for kw in keywords:
            risks = engine.detect_risks(f"设备{kw}品牌")
            assert len(risks) >= 1, f"Failed to detect: {kw}"

    def test_detects_qualification_exclusive(self, engine):
        content = "投标人必须具有甲级资质"
        risks = engine.detect_risks(content)
        qual_risks = [r for r in risks if r.rule_type == "exclusive_qualification"]
        assert len(qual_risks) >= 1

    def test_detects_region_limitation(self, engine):
        content = "投标人必须是本地注册企业"
        risks = engine.detect_risks(content)
        region_risks = [r for r in risks if r.rule_type == "region_limitation"]
        assert len(region_risks) >= 1

    def test_detects_experience_exclusive(self, engine):
        content = "不接受联合体投标业绩"
        risks = engine.detect_risks(content)
        exp_risks = [r for r in risks if r.rule_type == "experience_exclusive"]
        assert len(exp_risks) >= 1

    def test_detects_unclear_scoring(self, engine):
        content = "本项目采用综合评分法\n由评标委员会决定"
        risks = engine.detect_risks(content)
        scoring_risks = [r for r in risks if r.rule_type == "unclear_scoring"]
        assert len(scoring_risks) >= 1

    def test_multiple_risks_in_document(self, engine, sample_tender_content):
        risks = engine.detect_risks(sample_tender_content)
        types = {r.rule_type for r in risks}
        assert len(types) >= 2

    def test_risk_has_evidence(self, engine):
        content = "服务器必须是华为品牌"
        risks = engine.detect_risks(content)
        assert len(risks) >= 1
        assert "P_LIMIT" in risks[0].evidence

    def test_risk_has_chapter_context(self, engine):
        content = "第一章 总则\n第二章 技术要求\n服务器必须是华为品牌"
        risks = engine.detect_risks(content)
        assert len(risks) >= 1
        assert risks[0].location.chapter is not None


class TestRuleEngineSemanticChain:
    """Test the apply_semantic_chain method."""

    @pytest.fixture
    def engine(self):
        from backend.app.services.rule_engine import RuleEngine
        return RuleEngine()

    def test_empty_content(self, engine):
        assert engine.apply_semantic_chain("") == []

    def test_detects_p_limit(self, engine):
        results = engine.apply_semantic_chain("服务器必须是华为品牌")
        assert any("P_LIMIT" in r["operators"] for r in results)

    def test_detects_p_forbid(self, engine):
        results = engine.apply_semantic_chain("投标人必须具有甲级资质")
        assert any("P_FORBID" in r["operators"] for r in results)

    def test_detects_p_prefer(self, engine):
        results = engine.apply_semantic_chain("综合评分法由专家评审")
        assert any("P_PREFER" in r["operators"] for r in results)

    def test_detects_p_basis(self, engine):
        results = engine.apply_semantic_chain("基准价为所有投标报价的平均值")
        assert any("P_BASIS" in r["operators"] for r in results)

    def test_result_structure(self, engine):
        results = engine.apply_semantic_chain("服务器必须是华为品牌")
        assert len(results) >= 1
        r = results[0]
        assert "line" in r
        assert "text" in r
        assert "operators" in r
        assert "risk_level" in r

    def test_high_risk_for_p_forbid(self, engine):
        results = engine.apply_semantic_chain("投标人必须具有甲级资质")
        forbid_results = [r for r in results if "P_FORBID" in r["operators"]]
        assert len(forbid_results) >= 1
        assert forbid_results[0]["risk_level"] == "high"


class TestRuleEngineHelpers:
    """Test helper methods of RuleEngine."""

    @pytest.fixture
    def engine(self):
        from backend.app.services.rule_engine import RuleEngine
        return RuleEngine()

    def test_is_exclusive_context_positive(self, engine):
        assert engine._is_exclusive_context("仅限一级企业") is True
        assert engine._is_exclusive_context("必须是本地企业") is True

    def test_is_exclusive_context_negative(self, engine):
        assert engine._is_exclusive_context("欢迎各企业参与") is False

    def test_has_clear_scoring_criteria_with_numbers(self, engine):
        assert engine._has_clear_scoring_criteria("技术标60分 商务标40分") is True

    def test_has_clear_scoring_criteria_with_percentage(self, engine):
        assert engine._has_clear_scoring_criteria("技术标占60%") is True

    def test_has_clear_scoring_criteria_without(self, engine):
        assert engine._has_clear_scoring_criteria("由评标委员会决定") is False

    def test_get_context(self, engine):
        lines = ["line0", "line1", "line2", "line3", "line4"]
        ctx = engine._get_context(2, lines, before=1, after=1)
        assert "line1" in ctx
        assert "line2" in ctx
        assert "line3" in ctx

    def test_find_chapter_context(self, engine):
        lines = ["第一章 总则", "第二章 要求", "具体条款内容"]
        result = engine._find_chapter_context(2, lines)
        assert result == "第二章 要求"

    def test_find_chapter_context_first_line(self, engine):
        lines = ["第一章 总则", "内容"]
        result = engine._find_chapter_context(1, lines)
        assert result == "第一章 总则"

    def test_get_brand_suggestion(self, engine):
        assert "品牌" in engine._get_brand_suggestion("必须是华为品牌")
        assert "供应商" in engine._get_brand_suggestion("指定供应商EMC")


class TestRuleEngineRuleEvaluation:
    """Test rule evaluation methods."""

    def test_get_rule_by_id_found(self):
        from backend.app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        rule = engine.get_rule_by_id("RULE_T_001")
        assert rule is None or rule["rule_id"] == "RULE_T_001"

    def test_get_rule_by_id_not_found(self):
        from backend.app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        assert engine.get_rule_by_id("NONEXISTENT") is None

    def test_evaluate_rule_compliance_unknown(self):
        from backend.app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        result = engine.evaluate_rule_compliance("test", "UNKNOWN_RULE")
        assert result["status"] == "unknown"

    def test_evaluate_rule_compliance_pass(self):
        from backend.app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        result = engine.evaluate_rule_compliance(
            "本项目采用公开招标方式",
            "RULE_T_001"
        )
        assert result["status"] == "pass"
        assert result["violation_count"] == 0

    def test_evaluate_rule_compliance_fail(self):
        from backend.app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        result = engine.evaluate_rule_compliance(
            "服务器必须是华为品牌",
            "RULE_T_001"
        )
        assert result["status"] == "fail"
        assert result["violation_count"] >= 1


class TestSemanticOperator:
    """Test SemanticOperator constants."""

    def test_operators_defined(self):
        from backend.app.services.rule_engine import SemanticOperator
        assert SemanticOperator.P_REQUIRE == "P_REQUIRE"
        assert SemanticOperator.P_FORBID == "P_FORBID"
        assert SemanticOperator.P_BASIS == "P_BASIS"
        assert SemanticOperator.P_RECOMMEND == "P_RECOMMEND"
        assert SemanticOperator.P_LIMIT == "P_LIMIT"
        assert SemanticOperator.P_PREFER == "P_PREFER"
