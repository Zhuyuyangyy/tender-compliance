"""
合规报告生成服务
全链路审计：触发规则、证据片段、整改建议
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models.schemas import (
    RiskItem, TenderAnalysisResult, BidSimilarityResult,
    RiskReport, ClauseLocation
)


class ReportGenerator:
    """招投标合规报告生成器"""

    def __init__(self):
        self.report_templates = {
            "tender": self._tender_report_template,
            "bid_similarity": self._bid_similarity_report_template,
            "comprehensive": self._comprehensive_report_template
        }

    def generate_tender_report(
        self,
        tender_id: int,
        tender_name: str,
        analysis_result: Dict[str, Any],
        risk_items: List[RiskItem]
    ) -> Dict[str, Any]:
        """
        生成招标文件合规性分析报告
        """
        report = {
            "report_type": "tender_compliance",
            "tender_id": tender_id,
            "tender_name": tender_name,
            "generated_at": datetime.now().isoformat(),
            "summary": self._generate_tender_summary(analysis_result),
            "risk_distribution": self._analyze_risk_distribution(risk_items),
            "chapter_analysis": self._analyze_by_chapter(risk_items),
            "detail_items": self._format_risk_items(risk_items),
            "suggestions": self._generate_suggestions(risk_items),
            "audit_trail": self._generate_audit_trail("tender_analysis", tender_id, risk_items)
        }

        return report

    def generate_bid_similarity_report(
        self,
        tender_id: int,
        tender_name: str,
        similarity_result: Dict[str, Any],
        price_analysis: Dict[str, Any],
        entity_connections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成投标相似度分析报告
        """
        report = {
            "report_type": "bid_similarity",
            "tender_id": tender_id,
            "tender_name": tender_name,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_bids": len(similarity_result.get("bids", [])),
                "high_similarity_pairs": len([p for p in similarity_result.get("similarity_pairs", []) if p.get("risk_flag")]),
                "entity_connections": len(entity_connections),
                "price_anomaly": price_analysis.get("anomaly_detected", False)
            },
            "similarity_analysis": {
                "pairs": similarity_result.get("similarity_pairs", []),
                "graph_data": similarity_result.get("graph_data", {}),
                "risk_summary": similarity_result.get("risk_summary", {})
            },
            "price_analysis": price_analysis,
            "entity_connections": entity_connections,
            "suggestions": self._generate_bid_suggestions(similarity_result, entity_connections),
            "audit_trail": self._generate_audit_trail("bid_analysis", tender_id, similarity_result)
        }

        return report

    def generate_comprehensive_report(
        self,
        tender_id: int,
        tender_name: str,
        tender_analysis: Dict[str, Any],
        bid_analysis: Dict[str, Any]
    ) -> RiskReport:
        """
        生成综合风险报告（招标+投标）
        """
        final_risk_score = self._calculate_final_risk(
            tender_analysis.get("risk_score", 0),
            bid_analysis.get("overall_risk", 0)
        )

        final_risk_level = self._score_to_level(final_risk_score)

        # 构建报告对象
        report = RiskReport(
            tender_id=tender_id,
            tender_analysis=TenderAnalysisResult(
                tender_id=tender_id,
                risk_score=tender_analysis.get("risk_score", 0),
                risk_level=tender_analysis.get("risk_level", "green"),
                risk_items=tender_analysis.get("risk_items", []),
                summary=tender_analysis.get("summary", "")
            ),
            bid_analysis=BidSimilarityResult(
                tender_id=tender_id,
                total_bids=bid_analysis.get("total_bids", 0),
                similarity_pairs=bid_analysis.get("similarity_pairs", []),
                price_curve_analysis=bid_analysis.get("price_analysis", {}),
                entity_connections=bid_analysis.get("entity_connections", []),
                overall_risk_score=bid_analysis.get("overall_risk", 0),
                risk_level=bid_analysis.get("risk_level", "green")
            ),
            final_risk_score=final_risk_score,
            final_risk_level=final_risk_level
        )

        # 附加详细报告
        report.detailed_tender_report = self.generate_tender_report(
            tender_id, tender_name, tender_analysis, tender_analysis.get("risk_items", [])
        )
        report.detailed_bid_report = self.generate_bid_similarity_report(
            tender_id, tender_name, bid_analysis,
            bid_analysis.get("price_analysis", {}),
            bid_analysis.get("entity_connections", [])
        )

        return report

    def _generate_tender_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成招标文件分析摘要"""
        risk_score = analysis_result.get("risk_score", 0)
        risk_level = analysis_result.get("risk_level", "green")

        summary_text = {
            "green": "招标文件合规性良好，未发现明显违规条款",
            "yellow": "招标文件存在一定风险，建议检查并修改相关条款",
            "red": "招标文件存在严重违规风险，必须立即整改"
        }.get(risk_level, "无法确定风险等级")

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "summary_text": summary_text,
            "risk_count": analysis_result.get("risk_count", 0),
            "coupling_alerts": analysis_result.get("coupling_alerts", [])
        }

    def _analyze_risk_distribution(self, risk_items: List[RiskItem]) -> Dict[str, Any]:
        """分析风险分布"""
        distribution = {
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_type": {},
            "by_chapter": {}
        }

        for item in risk_items:
            distribution["by_severity"][item.severity] = distribution["by_severity"].get(item.severity, 0) + 1

            distribution["by_type"][item.rule_type] = distribution["by_type"].get(item.rule_type, 0) + 1

            chapter = item.location.chapter or "未分类"
            distribution["by_chapter"][chapter] = distribution["by_chapter"].get(chapter, 0) + 1

        return distribution

    def _analyze_by_chapter(self, risk_items: List[RiskItem]) -> List[Dict[str, Any]]:
        """按章节分析风险"""
        chapter_risks = {}

        for item in risk_items:
            chapter = item.location.chapter or "未分类"
            if chapter not in chapter_risks:
                chapter_risks[chapter] = {
                    "chapter": chapter,
                    "risk_count": 0,
                    "high_risk_count": 0,
                    "items": []
                }

            chapter_risks[chapter]["risk_count"] += 1
            if item.severity in ["high", "critical"]:
                chapter_risks[chapter]["high_risk_count"] += 1
            chapter_risks[chapter]["items"].append({
                "risk_name": item.risk_name,
                "severity": item.severity,
                "line": item.location.line_start,
                "suggestion": item.suggestion
            })

        return list(chapter_risks.values())

    def _format_risk_items(self, risk_items: List[RiskItem]) -> List[Dict[str, Any]]:
        """格式化风险项列表"""
        formatted = []
        for item in risk_items:
            formatted.append({
                "rule_id": item.rule_id,
                "rule_type": item.rule_type,
                "risk_name": item.risk_name,
                "severity": item.severity,
                "location": {
                    "chapter": item.location.chapter,
                    "line": f"{item.location.line_start}-{item.location.line_end}",
                    "raw_text": item.location.raw_text[:100]
                },
                "evidence": item.evidence,
                "suggestion": item.suggestion
            })
        return formatted

    def _generate_suggestions(self, risk_items: List[RiskItem]) -> List[Dict[str, Any]]:
        """生成整改建议"""
        suggestions = []

        # 按风险等级排序
        high_risks = [r for r in risk_items if r.severity in ["high", "critical"]]

        for risk in high_risks:
            suggestions.append({
                "priority": "high",
                "rule_id": risk.rule_id,
                "risk_name": risk.risk_name,
                "suggestion": risk.suggestion,
                "location": f"第{risk.location.line_start}行"
            })

        medium_risks = [r for r in risk_items if r.severity == "medium"]
        for risk in medium_risks:
            suggestions.append({
                "priority": "medium",
                "rule_id": risk.rule_id,
                "risk_name": risk.risk_name,
                "suggestion": risk.suggestion,
                "location": f"第{risk.location.line_start}行"
            })

        return suggestions

    def _generate_bid_suggestions(
        self,
        similarity_result: Dict[str, Any],
        entity_connections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成投标分析整改建议"""
        suggestions = []

        high_sim_pairs = [p for p in similarity_result.get("similarity_pairs", []) if p.get("risk_flag")]
        if high_sim_pairs:
            suggestions.append({
                "priority": "high",
                "type": "similarity",
                "issue": f"发现 {len(high_sim_pairs)} 对高度相似的投标文件",
                "action": "提交人工复核，检查是否存在围标行为"
            })

        critical_connections = [c for c in entity_connections if c.get("risk_level") == "high"]
        if critical_connections:
            suggestions.append({
                "priority": "high",
                "type": "entity_connection",
                "issue": f"发现 {len(critical_connections)} 项主体关联异常",
                "action": "标记关联关系，提交招标监督部门"
            })

        if similarity_result.get("price_analysis", {}).get("anomaly_detected"):
            suggestions.append({
                "priority": "medium",
                "type": "price_anomaly",
                "issue": "报价曲线存在异常",
                "action": "检查报价雷同性，分析价格操纵可能"
            })

        return suggestions

    def _generate_audit_trail(
        self,
        action_type: str,
        target_id: int,
        data: Any
    ) -> Dict[str, Any]:
        """生成审计追踪信息"""
        return {
            "action": action_type,
            "target_id": target_id,
            "timestamp": datetime.now().isoformat(),
            "operator": "system",
            "data_snapshot": json.dumps(data, ensure_ascii=False, default=str)[:1000]
        }

    def _calculate_final_risk(
        self,
        tender_risk: float,
        bid_risk: float
    ) -> float:
        """计算最终风险分数（招标风险和投标风险的加权融合）"""
        # 招标文件的合规性权重更高
        weights = {"tender": 0.6, "bid": 0.4}
        combined = weights["tender"] * tender_risk + weights["bid"] * bid_risk

        # 如果投标风险高，放大最终风险（耦合效应）
        if tender_risk > 0.5 and bid_risk > 0.4:
            combined = min(combined * 1.3, 1.0)

        return round(combined, 4)

    def _score_to_level(self, score: float) -> str:
        """分数转等级"""
        if score < 0.3:
            return "green"
        elif score < 0.6:
            return "yellow"
        else:
            return "red"

    def export_report_json(self, report: Dict[str, Any]) -> str:
        """导出报告为JSON格式"""
        return json.dumps(report, ensure_ascii=False, indent=2, default=str)

    def export_report_markdown(self, report: Dict[str, Any]) -> str:
        """导出报告为Markdown格式"""
        md_lines = [
            f"# {report.get('report_type', 'Unknown')} Report",
            f"Generated: {report.get('generated_at', 'N/A')}",
            "",
            f"## Summary",
            f"- Risk Level: {report.get('summary', {}).get('risk_level', 'N/A')}",
            f"- Risk Score: {report.get('summary', {}).get('risk_score', 0)}",
            ""
        ]

        if "detail_items" in report:
            md_lines.append("## Risk Details")
            for item in report["detail_items"]:
                md_lines.append(f"### [{item['severity'].upper()}] {item['risk_name']}")
                md_lines.append(f"- Location: {item['location']}")
                md_lines.append(f"- Evidence: {item['evidence']}")
                md_lines.append(f"- Suggestion: {item['suggestion']}")
                md_lines.append("")

        return "\n".join(md_lines)

    def _tender_report_template(self, data: Dict[str, Any]) -> str:
        """招标文件报告模板"""
        return self.export_report_json(data)

    def _bid_similarity_report_template(self, data: Dict[str, Any]) -> str:
        """投标相似度报告模板"""
        return self.export_report_json(data)

    def _comprehensive_report_template(self, data: Dict[str, Any]) -> str:
        """综合报告模板"""
        return self.export_report_json(data)


if __name__ == "__main__":
    generator = ReportGenerator()

    # 测试报告生成
    test_tender_analysis = {
        "risk_score": 0.65,
        "risk_level": "yellow",
        "risk_count": 5,
        "coupling_alerts": [
            {"factors": ["exclusive_brand", "exclusive_qualification"], "multiplier": 1.5}
        ]
    }

    test_risk_items = [
        RiskItem(
            rule_id="RULE_T_001",
            rule_type="exclusive_brand",
            risk_name="限定品牌",
            severity="high",
            location=ClauseLocation(chapter="第三章 技术要求", line_start=10, line_end=10, raw_text="必须是华为品牌"),
            evidence="检测到限定品牌",
            suggestion="改为同等档次品牌"
        )
    ]

    tender_report = generator.generate_tender_report(
        tender_id=1,
        tender_name="某政府信息化项目",
        analysis_result=test_tender_analysis,
        risk_items=test_risk_items
    )

    print("=== 招标文件合规性报告 ===")
    print(f"风险等级: {tender_report['summary']['risk_level']}")
    print(f"风险分数: {tender_report['summary']['risk_score']}")
    print(f"风险项数: {tender_report['summary']['risk_count']}")
    print(f"耦合警报: {tender_report['summary']['coupling_alerts']}")