"""
招标文件结构解析服务
虚拟条款坐标映射 + 隐性风险检测
"""
import re
import jieba
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from ..models.schemas import ClauseLocation, RiskItem


# 关键词库
BRAND_KEYWORDS = [
    "指定品牌", "限于", "仅限", "必须是", "只能采用",
    "品牌型号", "著名品牌", "知名品牌", "一线品牌",
    "必须是以下品牌", "指定供应商", "独家供应",
    "仅限以下", "优先选用", "推荐品牌"
]

QUALIFICATION_KEYWORDS = [
    "必须具有", "应当具备", "需要具备", "持有",
    "具有甲级", "具有乙级", "特级资质", "一级资质",
    "注册资金", "注册资本", "成立年限", "行业排名",
    "特定对象", "仅限于", "排斥", "排除"
]

SCORING_KEYWORDS = [
    "综合评分", "专家评审", "评标委员会",
    "主观分", "印象分", "资信分",
    "加分项", "扣分项", "分值分配",
    "权重", "系数", "参考"
]

CONTRACT_KEYWORDS = [
    "合同条款", "付款方式", "违约责任",
    "履约保证金", "质量保证金", "验收标准",
    "保修期", "售后服务", "免责条款"
]


class TenderParser:
    """招标文件解析器"""

    def __init__(self):
        # 初始化结巴分词
        jieba.initialize()
        # 虚拟坐标空间
        self.coordinate_space = {
            "qualification": {"x": 0.0, "y": 0.2},   # 资格条件区
            "scoring": {"x": 0.0, "y": 0.4},        # 评分办法区
            "technical": {"x": 0.0, "y": 0.6},       # 技术参数区
            "commercial": {"x": 0.0, "y": 0.8},      # 商务条款区
            "contract": {"x": 0.0, "y": 1.0}         # 合同条款区
        }

    def parse_tender(self, content: str) -> Dict[str, Any]:
        """
        解析招标文件，提取各部分内容
        返回结构化解析结果
        """
        lines = content.split('\n')
        structure = {
            "raw_content": content,
            "total_lines": len(lines),
            "chapters": [],
            "clauses": [],
            "coordinates": []
        }

        current_chapter = None
        current_section = None

        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检测章节标题
            chapter_match = re.match(r'^第[一二三四五六七八九十\d]+[章节篇]', line)
            section_match = re.match(r'^\d+[.、]\s*', line)

            if chapter_match:
                current_chapter = line
                structure["chapters"].append({
                    "title": line,
                    "line_start": idx,
                    "type": self._classify_chapter(line)
                })
            elif section_match:
                current_section = line
                # 记录条款坐标
                clause_type = self._classify_clause(line)
                coord = self._generate_coordinate(clause_type, idx, len(lines))
                structure["coordinates"].append({
                    "line": idx,
                    "type": clause_type,
                    "coordinate": coord,
                    "text": line
                })
                structure["clauses"].append({
                    "chapter": current_chapter,
                    "section": line,
                    "line_start": idx,
                    "type": clause_type,
                    "coordinate": coord
                })

        # 解析各区域内容
        structure["qualification_zone"] = self._extract_zone(content, QUALIFICATION_KEYWORDS)
        structure["scoring_zone"] = self._extract_zone(content, SCORING_KEYWORDS)
        structure["technical_zone"] = self._extract_zone(content, ["技术要求", "规格", "参数", "型号"])
        structure["commercial_zone"] = self._extract_zone(content, COMMERCIAL_KEYWORDS if 'COMMERCIAL_KEYWORDS' in dir() else [])
        structure["contract_zone"] = self._extract_zone(content, CONTRACT_KEYWORDS)

        return structure

    def _classify_chapter(self, title: str) -> str:
        """根据章节标题分类"""
        title_lower = title.lower()
        if any(k in title for k in ["资格", "投标人", "资质", "条件"]):
            return "qualification"
        elif any(k in title for k in ["评标", "评分", "评审"]):
            return "scoring"
        elif any(k in title for k in ["技术", "规格", "参数"]):
            return "technical"
        elif any(k in title for k in ["商务", "报价", "价格"]):
            return "commercial"
        elif any(k in title for k in ["合同", "协议"]):
            return "contract"
        return "general"

    def _classify_clause(self, clause_text: str) -> str:
        """根据条款内容分类"""
        if any(k in clause_text for k in BRAND_KEYWORDS):
            return "brand_restriction"
        elif any(k in clause_text for k in QUALIFICATION_KEYWORDS):
            return "qualification_exclusive"
        elif any(k in clause_text for k in SCORING_KEYWORDS):
            return "scoring_unclear"
        return "normal"

    def _generate_coordinate(self, clause_type: str, line_num: int, total_lines: float) -> Dict[str, float]:
        """生成虚拟条款坐标"""
        base = self.coordinate_space.get(clause_type.split('_')[0] if '_' in clause_type else "general", {"x": 0.5, "y": 0.5})
        # x轴基于行号（条款在文档中的相对位置）
        x = line_num / total_lines if total_lines > 0 else 0.5
        # y轴基于条款类型
        y = base["y"]
        # z轴用于区分同一区域内的不同条款
        z = np.random.uniform(0, 1)
        return {"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)}

    def _extract_zone(self, content: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """提取包含特定关键词的区域"""
        results = []
        lines = content.split('\n')
        for idx, line in enumerate(lines):
            for kw in keywords:
                if kw in line:
                    results.append({
                        "line": idx,
                        "keyword": kw,
                        "text": line.strip(),
                        "context": lines[max(0, idx-2):min(len(lines), idx+3)]
                    })
                    break
        return results

    def detect_risks(self, content: str) -> List[RiskItem]:
        """
        检测招标文件中的隐性风险
        返回风险项列表
        """
        risks = []
        lines = content.split('\n')

        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 限定品牌检测
            for keyword in BRAND_KEYWORDS:
                if keyword in line_stripped:
                    risks.append(RiskItem(
                        rule_id="RULE_T_001",
                        rule_type="exclusive_brand",
                        risk_name="限定品牌或供应商",
                        severity="high",
                        location=ClauseLocation(
                            chapter=self._find_chapter(idx, lines),
                            paragraph=line_stripped[:100],
                            line_start=idx,
                            line_end=idx,
                            raw_text=line_stripped
                        ),
                        evidence=f"检测到敏感词: '{keyword}' - {line_stripped[:80]}",
                        suggestion="删除限定性描述，改为'同等档次品牌'或'满足技术要求的品牌'"
                    ))
                    break

            # 排他性资质检测
            for keyword in QUALIFICATION_KEYWORDS:
                if keyword in line_stripped and any(k in line_stripped for k in ["仅限", "必须是", "具有甲级", "具有乙级", "特级", "一级", "特定"]):
                    risks.append(RiskItem(
                        rule_id="RULE_T_002",
                        rule_type="exclusive_qualification",
                        risk_name="排他性资质要求",
                        severity="high",
                        location=ClauseLocation(
                            chapter=self._find_chapter(idx, lines),
                            paragraph=line_stripped[:100],
                            line_start=idx,
                            line_end=idx,
                            raw_text=line_stripped
                        ),
                        evidence=f"检测到排他性资质描述: {line_stripped[:80]}",
                        suggestion="调整为'具有相应资质'或'满足招标要求'的通用描述"
                    ))
                    break

            # 评分标准不透明检测
            if any(k in line_stripped for k in ["综合评分", "专家评审", "评标委员会"]):
                # 检查是否有明确的评分标准
                context_lines = lines[max(0, idx):min(len(lines), idx+10)]
                context_text = '\n'.join(context_lines)
                if not re.search(r'\d+分|\d+%|权重|评分标准', context_text):
                    risks.append(RiskItem(
                        rule_id="RULE_T_003",
                        rule_type="unclear_scoring",
                        risk_name="评分标准不透明",
                        severity="medium",
                        location=ClauseLocation(
                            chapter=self._find_chapter(idx, lines),
                            paragraph=line_stripped[:100],
                            line_start=idx,
                            line_end=idx + 10,
                            raw_text=context_text[:200]
                        ),
                        evidence=f"评标方式缺少明确评分标准: {line_stripped[:60]}",
                        suggestion="明确各项评分指标、权重和分值分配"
                    ))

        return risks

    def _find_chapter(self, line_num: int, lines: List[str]) -> Optional[str]:
        """查找当前行所属的章节"""
        for i in range(line_num, -1, -1):
            if re.match(r'^第[一二三四五六七八九十\d]+[章节篇]', lines[i].strip()):
                return lines[i].strip()
        return None


if __name__ == "__main__":
    parser = TenderParser()
    test_content = """
    第一章 招标公告
    本次招标项目为某市政府信息化建设项目
    
    第二章 投标人资格要求
    投标人必须具有计算机系统集成一级资质
    投标人必须是本地企业
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
    structure = parser.parse_tender(test_content)
    print(f"解析章节数: {len(structure['chapters'])}")
    print(f"解析条款数: {len(structure['clauses'])}")

    risks = parser.detect_risks(test_content)
    print(f"检测到风险: {len(risks)} 项")
    for risk in risks:
        print(f"  - {risk.risk_name} ({risk.severity})")