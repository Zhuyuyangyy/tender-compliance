"""
围串标风险熵评估服务
多维风险耦合模型 + 非线性熔断机制
"""
import math
from typing import List, Dict, Any
from ..models.schemas import RiskItem


class TenderRiskScorer:
    """招投标风险熵评分器"""

    def __init__(self):
        # 风险等级阈值
        self.thresholds = {
            "green": 0.3,    # 低风险
            "yellow": 0.6,   # 中风险
            "red": 1.0       # 高风险
        }

        # 风险因子权重（用于计算综合风险熵）
        self.factor_weights = {
            "exclusive_brand": 0.15,           # 限定品牌
            "exclusive_qualification": 0.20,    # 排他资质
            "unclear_scoring": 0.12,            # 评分不透明
            "bid_similarity": 0.25,             # 投标相似度
            "entity_connection": 0.18,          # 主体关联
            "price_anomaly": 0.10                # 报价异常
        }

        # 非线性熔断因子（非线性耦合）
        self.coupling_factors = {
            # 当多个风险同时出现时的耦合放大效应
            ("exclusive_brand", "exclusive_qualification"): 1.5,  # 同时存在时放大
            ("exclusive_brand", "unclear_scoring"): 1.3,
            ("bid_similarity", "entity_connection"): 1.8,  # 围标+关联=高危
            ("bid_similarity", "price_anomaly"): 1.6,
            ("entity_connection", "price_anomaly"): 1.4
        }

    def calculate_tender_risk(self, risk_items: List[RiskItem]) -> Dict[str, Any]:
        """
        计算招标文件的综合风险熵
        使用非线性熔断模型
        """
        if not risk_items:
            return {
                "risk_score": 0.0,
                "risk_level": "green",
                "factor_scores": {},
                "coupling_alerts": []
            }

        # 计算各因子得分
        factor_scores = {}
        for item in risk_items:
            factor_type = item.rule_type
            if factor_type not in factor_scores:
                factor_scores[factor_type] = []
            factor_scores[factor_type].append(self._severity_to_score(item.severity))

        # 加权求和
        weighted_sum = 0.0
        for factor_type, scores in factor_scores.items():
            avg_score = sum(scores) / len(scores)
            weight = self.factor_weights.get(factor_type, 0.1)
            weighted_sum += avg_score * weight

        # 应用耦合熔断效应
        coupling_alerts = []
        activated_factors = list(factor_scores.keys())
        coupling_multiplier = 1.0

        for (factor1, factor2), multiplier in self.coupling_factors.items():
            if factor1 in activated_factors and factor2 in activated_factors:
                coupling_multiplier = max(coupling_multiplier, multiplier)
                coupling_alerts.append({
                    "factors": [factor1, factor2],
                    "multiplier": multiplier,
                    "reason": f"风险因子耦合: {factor1} + {factor2}"
                })

        final_score = min(weighted_sum * coupling_multiplier, 1.0)

        # 确定风险等级
        risk_level = self._score_to_level(final_score)

        return {
            "risk_score": round(final_score, 4),
            "risk_level": risk_level,
            "factor_scores": {k: round(sum(v)/len(v), 4) for k, v in factor_scores.items()},
            "coupling_multiplier": round(coupling_multiplier, 2),
            "coupling_alerts": coupling_alerts
        }

    def calculate_bid_similarity_risk(
        self,
        similarity_pairs: List[Dict[str, Any]],
        price_analysis: Dict[str, Any],
        entity_connections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算投标文件的综合风险
        基于相似度、报价曲线、主体关联
        """
        # 相似度风险
        similarity_score = 0.0
        high_similarity_pairs = []
        if similarity_pairs:
            for pair in similarity_pairs:
                if pair.get("similarity", 0) > 0.85:
                    similarity_score = max(similarity_score, pair["similarity"])
                    high_similarity_pairs.append(pair)
            # 多个高度相似时加权
            if len(high_similarity_pairs) >= 2:
                similarity_score = min(similarity_score * 1.2, 1.0)

        # 报价异常风险
        price_risk = 0.0
        if price_analysis:
            if price_analysis.get("price_deviation", 0) > 0.15:
                price_risk = 0.7
            if price_analysis.get("curve_correlation", 0) > 0.9:
                price_risk = max(price_risk, 0.8)

        # 主体关联风险
        entity_risk = 0.0
        if entity_connections:
            entity_risk = min(len(entity_connections) * 0.15, 0.9)

        # 综合风险熵计算
        weights = [0.40, 0.30, 0.30]  # 相似度、报价、关联
        values = [similarity_score, price_risk, entity_risk]
        combined_risk = sum(w * v for w, v in zip(weights, values))

        # 非线性熔断
        if similarity_score > 0.8 and entity_risk > 0.4:
            combined_risk = min(combined_risk * 1.5, 1.0)
        if price_analysis.get("curve_correlation", 0) > 0.95:
            combined_risk = min(combined_risk * 1.3, 1.0)

        risk_level = self._score_to_level(combined_risk)

        return {
            "risk_score": round(combined_risk, 4),
            "risk_level": risk_level,
            "components": {
                "similarity_risk": round(similarity_score, 4),
                "price_risk": round(price_risk, 4),
                "entity_risk": round(entity_risk, 4)
            },
            "high_similarity_pairs": len(high_similarity_pairs),
            "entity_connection_count": len(entity_connections)
        }

    def _severity_to_score(self, severity: str) -> float:
        """严重程度转换为数值分数"""
        mapping = {
            "critical": 1.0,
            "high": 0.75,
            "medium": 0.5,
            "low": 0.25,
            "info": 0.1
        }
        return mapping.get(severity.lower(), 0.3)

    def _score_to_level(self, score: float) -> str:
        """分数转换为风险等级"""
        if score < self.thresholds["green"]:
            return "green"
        elif score < self.thresholds["yellow"]:
            return "yellow"
        else:
            return "red"


if __name__ == "__main__":
    scorer = TenderRiskScorer()

    # 测试招标风险
    from ..models.schemas import ClauseLocation
    test_risks = [
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

    result = scorer.calculate_tender_risk(test_risks)
    print(f"招标文件风险熵: {result['risk_score']} ({result['risk_level']})")
    print(f"耦合警报: {result['coupling_alerts']}")

    # 测试投标风险
    bid_result = scorer.calculate_bid_similarity_risk(
        similarity_pairs=[
            {"bid1": "公司A", "bid2": "公司B", "similarity": 0.92}
        ],
        price_analysis={"price_deviation": 0.2, "curve_correlation": 0.95},
        entity_connections=[
            {"type": "ip", "entities": ["公司A", "公司C"]}
        ]
    )
    print(f"\n投标风险熵: {bid_result['risk_score']} ({bid_result['risk_level']})")
    print(f"风险组成: {bid_result['components']}")