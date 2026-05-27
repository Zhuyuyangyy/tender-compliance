"""
规则引擎
检测"限定品牌"、"排他性资质"、"倾向性评分"等隐性风险
语义算子链：P_REQUIRE/P_FORBID/P_BASIS 等
"""
import re
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from ..models.schemas import RiskItem, ClauseLocation


class SemanticOperator:
    """语义算子定义"""
    # P_REQUIRE: 必须满足的要求
    P_REQUIRE = "P_REQUIRE"
    # P_FORBID: 禁止性条款
    P_FORBID = "P_FORBID"
    # P_BASIS: 评标基准
    P_BASIS = "P_BASIS"
    # P_RECOMMEND: 推荐性条款
    P_RECOMMEND = "P_RECOMMEND"
    # P_LIMIT: 限制性条款
    P_LIMIT = "P_LIMIT"
    # P_PREFER: 倾向性条款
    P_PREFER = "P_PREFER"


class RuleEngine:
    """招投标规则引擎"""

    def __init__(self, rules_path: Optional[str] = None):
        if rules_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            rules_path = str(base_dir / "rules" / "tender_rules.json")

        self.rules = self._load_rules(rules_path)
        self.semantic_patterns = self._init_semantic_patterns()

    def _load_rules(self, rules_path: str) -> Dict[str, Any]:
        """加载规则库"""
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[RuleEngine] 规则文件未找到: {rules_path}")
            return {"rules": [], "patterns": {}}

    def _init_semantic_patterns(self) -> Dict[str, List[str]]:
        """初始化语义模式库"""
        return {
            # 限定性语义算子
            "brand_restriction": [
                "必须是", "只能是", "限于", "仅限于", "仅限",
                "指定品牌", "指定供应商", "独家供应",
                "必须是以下品牌", "优先选用", "推荐品牌"
            ],
            "qualification_exclusive": [
                "必须具有", "应当具备", "需要具备",
                "仅限", "排斥", "排除", "不包括",
                "具有甲级", "具有乙级", "特级资质", "一级资质"
            ],
            "scoring_preference": [
                "综合评分", "专家评审", "评标委员会",
                "具有以下条件", "优先考虑", "加分",
                "同等条件下", "可以选择"
            ],
            "price_control": [
                "最低价", "最高限价", "报价不得低于",
                "价格分", "报价权重", "价格得分"
            ]
        }

    def detect_risks(self, content: str) -> List[RiskItem]:
        """
        使用规则引擎检测招标文件风险
        返回风险项列表
        """
        risks = []
        lines = content.split('\n')

        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 1. 检测限定品牌（P_LIMIT 算子）
            brand_risk = self._detect_brand_restriction(line_stripped, idx, lines)
            if brand_risk:
                risks.append(brand_risk)

            # 2. 检测排他性资质（P_FORBID 算子）
            qual_risk = self._detect_qualification_exclusive(line_stripped, idx, lines)
            if qual_risk:
                risks.append(qual_risk)

            # 3. 检测倾向性评分（P_PREFER 算子）
            scoring_risk = self._detect_scoring_preference(line_stripped, idx, lines)
            if scoring_risk:
                risks.append(scoring_risk)

            # 4. 检测限制性条款（P_REQUIRE 算子）
            limit_risk = self._detect_limitation(line_stripped, idx, lines)
            if limit_risk:
                risks.append(limit_risk)

        return risks

    def _detect_brand_restriction(self, line: str, line_num: int, all_lines: List[str]) -> Optional[RiskItem]:
        """检测限定品牌风险"""
        patterns = self.semantic_patterns.get("brand_restriction", [])

        for pattern in patterns:
            if pattern in line:
                # 获取上下文
                context = self._get_context(line_num, all_lines, before=2, after=2)

                return RiskItem(
                    rule_id="RULE_T_001",
                    rule_type="exclusive_brand",
                    risk_name="限定品牌或供应商（歧视性条款）",
                    severity="high",
                    location=ClauseLocation(
                        chapter=self._find_chapter_context(line_num, all_lines),
                        paragraph=self._get_paragraph(line_num, all_lines),
                        line_start=line_num,
                        line_end=line_num,
                        raw_text=line
                    ),
                    evidence=f"语义算子P_LIMIT激活: 检测到限定性表述 '{pattern}'\n上下文: {context}",
                    suggestion=self._get_brand_suggestion(line)
                )
        return None

    def _detect_qualification_exclusive(self, line: str, line_num: int, all_lines: List[str]) -> Optional[RiskItem]:
        """检测排他性资质风险"""
        patterns = self.semantic_patterns.get("qualification_exclusive", [])

        for pattern in patterns:
            if pattern in line:
                # 判断是否为排他性描述
                if self._is_exclusive_context(line):
                    context = self._get_context(line_num, all_lines)

                    return RiskItem(
                        rule_id="RULE_T_002",
                        rule_type="exclusive_qualification",
                        risk_name="排他性资质要求",
                        severity="high",
                        location=ClauseLocation(
                            chapter=self._find_chapter_context(line_num, all_lines),
                            paragraph=self._get_paragraph(line_num, all_lines),
                            line_start=line_num,
                            line_end=line_num,
                            raw_text=line
                        ),
                        evidence=f"语义算子P_FORBID激活: 检测到排他性资质描述 '{pattern}'\n上下文: {context}",
                        suggestion="调整为通用资质描述，如'具有相应资质'或'满足招标文件要求'"
                    )
        return None

    def _detect_scoring_preference(self, line: str, line_num: int, all_lines: List[str]) -> Optional[RiskItem]:
        """检测倾向性评分风险"""
        patterns = self.semantic_patterns.get("scoring_preference", [])

        for pattern in patterns:
            if pattern in line:
                # 检查周围是否有明确的评分标准
                context_lines = all_lines[max(0, line_num):min(len(all_lines), line_num + 20)]
                context_text = '\n'.join(context_lines)

                # 缺少明确标准时触发风险
                if not self._has_clear_scoring_criteria(context_text):
                    return RiskItem(
                        rule_id="RULE_T_003",
                        rule_type="unclear_scoring",
                        risk_name="评分标准不透明",
                        severity="medium",
                        location=ClauseLocation(
                            chapter=self._find_chapter_context(line_num, all_lines),
                            paragraph=self._get_paragraph(line_num, all_lines),
                            line_start=line_num,
                            line_end=min(line_num + 20, len(all_lines) - 1),
                            raw_text=line
                        ),
                        evidence=f"语义算子P_PREFER激活: 评标方式缺乏透明度\n检测到关键词: '{pattern}'",
                        suggestion="明确评分指标、权重分配和计算方法，确保评标过程公平透明"
                    )
        return None

    def _detect_limitation(self, line: str, line_num: int, all_lines: List[str]) -> Optional[RiskItem]:
        """检测其他限制性条款"""
        # 检测地域限制
        region_patterns = [
            r'仅限本省', r'仅限本市', r'必须是本地企业',
            r'仅限本地', r'本省企业', r'本市企业',
            r'在[XX]市注册', r'注册地在'
        ]

        for pattern in region_patterns:
            if re.search(pattern, line):
                return RiskItem(
                    rule_id="RULE_T_008",
                    rule_type="region_limitation",
                    risk_name="地域限制条款",
                    severity="medium",
                    location=ClauseLocation(
                        chapter=self._find_chapter_context(line_num, all_lines),
                        paragraph=self._get_paragraph(line_num, all_lines),
                        line_start=line_num,
                        line_end=line_num,
                        raw_text=line
                    ),
                    evidence=f"检测到地域限制表述: {line}",
                    suggestion="删除地域限制，确保公平竞争"
                )

        # 检测业绩排斥
        if re.search(r'不接受|不包含|不包括.*业绩', line):
            return RiskItem(
                rule_id="RULE_T_009",
                rule_type="experience_exclusive",
                risk_name="业绩排斥条款",
                severity="medium",
                location=ClauseLocation(
                    chapter=self._find_chapter_context(line_num, all_lines),
                    paragraph=self._get_paragraph(line_num, all_lines),
                    line_start=line_num,
                    line_end=line_num,
                    raw_text=line
                ),
                evidence=f"检测到业绩排斥表述: {line}",
                suggestion="调整为'具有类似项目经验'的正面描述"
            )

        return None

    def _is_exclusive_context(self, line: str) -> bool:
        """判断是否为排他性上下文"""
        exclusive_markers = [
            "仅限", "只能是", "必须是", "仅限于",
            "排除", "排斥", "不包括", "不包括以下"
        ]
        return any(marker in line for marker in exclusive_markers)

    def _has_clear_scoring_criteria(self, text: str) -> bool:
        """检查是否有明确的评分标准"""
        clear_markers = [
            r'\d+分', r'\d+%',
            r'权重', r'分值',
            r'评分标准', r'评分办法',
            r'各项.*分', r'技术.*\d+分',
            r'商务.*\d+分'
        ]

        for marker in clear_markers:
            if re.search(marker, text):
                return True
        return False

    def _get_context(self, line_num: int, all_lines: List[str], before: int = 2, after: int = 2) -> str:
        """获取上下文"""
        start = max(0, line_num - before)
        end = min(len(all_lines), line_num + after + 1)
        return '\n'.join(all_lines[start:end])

    def _get_paragraph(self, line_num: int, all_lines: List[str]) -> str:
        """获取段落（当前行前后各5行）"""
        return self._get_context(line_num, all_lines, before=5, after=5)

    def _find_chapter_context(self, line_num: int, all_lines: List[str]) -> Optional[str]:
        """查找章节上下文"""
        for i in range(line_num, -1, -1):
            line = all_lines[i].strip()
            if re.match(r'^第[一二三四五六七八九十\d]+[章节篇]', line):
                return line
            if re.match(r'^第[一二三四五六七八九十\d]+条', line):
                return line
        return None

    def _get_brand_suggestion(self, line: str) -> str:
        """获取品牌限制的整改建议"""
        if "品牌" in line:
            return "删除指定品牌，改为'同等档次品牌'或'满足技术要求的品牌'"
        if "供应商" in line:
            return "删除指定供应商，改为'满足资质要求的供应商'"
        return "检查并删除限制性描述，确保公平竞争"

    def apply_semantic_chain(self, text: str) -> List[Dict[str, Any]]:
        """
        应用语义算子链
        识别文本中的语义结构
        """
        results = []
        lines = text.split('\n')

        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 分析每个语义算子的激活情况
            activated_operators = []

            if any(p in line for p in self.semantic_patterns.get("brand_restriction", [])):
                activated_operators.append(SemanticOperator.P_LIMIT)

            if any(p in line for p in self.semantic_patterns.get("qualification_exclusive", [])):
                activated_operators.append(SemanticOperator.P_FORBID)

            if any(p in line for p in self.semantic_patterns.get("scoring_preference", [])):
                activated_operators.append(SemanticOperator.P_PREFER)

            if any(p in line for p in self.semantic_patterns.get("price_control", [])):
                activated_operators.append(SemanticOperator.P_BASIS)

            if activated_operators:
                results.append({
                    "line": idx,
                    "text": line,
                    "operators": activated_operators,
                    "risk_level": "high" if SemanticOperator.P_FORBID in activated_operators else "medium"
                })

        return results

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """根据规则ID获取规则详情"""
        for rule in self.rules.get("rules", []):
            if rule.get("rule_id") == rule_id:
                return rule
        return None

    def evaluate_rule_compliance(self, content: str, rule_id: str) -> Dict[str, Any]:
        """
        评估特定规则的合规性
        """
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            return {"status": "unknown", "details": f"规则 {rule_id} 未找到"}

        # 应用规则检测
        violations = []
        lines = content.split('\n')

        rule_patterns = rule.get("patterns", [])
        for idx, line in enumerate(lines):
            for pattern in rule_patterns:
                if re.search(pattern, line):
                    violations.append({
                        "line": idx,
                        "text": line,
                        "pattern": pattern
                    })

        return {
            "rule_id": rule_id,
            "rule_type": rule.get("rule_type"),
            "status": "fail" if violations else "pass",
            "violations": violations,
            "violation_count": len(violations)
        }


if __name__ == "__main__":
    engine = RuleEngine()

    test_content = """
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

    print("=== 语义算子链分析 ===")
    chain_results = engine.apply_semantic_chain(test_content)
    for result in chain_results:
        print(f"行{result['line']}: {result['operators']} - {result['text'][:50]}...")

    print("\n=== 风险检测 ===")
    risks = engine.detect_risks(test_content)
    print(f"检测到 {len(risks)} 个风险项:")
    for risk in risks:
        print(f"  [{risk.severity}] {risk.risk_name} - {risk.evidence[:50]}...")