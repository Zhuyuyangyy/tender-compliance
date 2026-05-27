"""
投标文件相似度分析服务
语义相似度检测 + 报价曲线分析 + 主体关联图谱
"""
import re
import math
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import jieba


class SimilarityAnalyzer:
    """投标文件相似度分析器"""

    def __init__(self):
        jieba.initialize()
        self.stopwords = set(['的', '了', '是', '在', '和', '与', '等', '及', '或', '等'])

    def analyze_bids(self, bids: List[Dict[str, Any]], tender_content: str = "") -> Dict[str, Any]:
        """
        综合分析投标文件
        返回相似度图谱、报价分析、主体关联
        """
        if len(bids) < 2:
            return {
                "similarity_pairs": [],
                "price_analysis": {},
                "entity_connections": [],
                "overall_risk": 0.0,
                "risk_level": "green"
            }

        # 1. 计算文本相似度
        similarity_pairs = self._compute_similarity_matrix(bids)

        # 2. 报价曲线分析
        price_analysis = self._analyze_price_curves(bids)

        # 3. 主体关联检测
        entity_connections = self._detect_entity_connections(bids)

        # 4. 综合风险评估
        overall_risk = self._compute_overall_risk(
            similarity_pairs, price_analysis, entity_connections
        )

        return {
            "similarity_pairs": similarity_pairs,
            "price_analysis": price_analysis,
            "entity_connections": entity_connections,
            "overall_risk": round(overall_risk, 4),
            "risk_level": "green" if overall_risk < 0.3 else "yellow" if overall_risk < 0.6 else "red"
        }

    def _compute_similarity_matrix(self, bids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """计算投标文件之间的相似度矩阵"""
        results = []
        n = len(bids)

        # 构建TF-IDF向量
        bid_texts = [self._preprocess(b.get("content", "")) for b in bids]
        vocab = self._build_vocabulary(bid_texts)
        vectors = [self._text_to_vector(text, vocab) for text in bid_texts]

        # 计算两两相似度
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self._cosine_similarity(vectors[i], vectors[j])
                if similarity > 0.5:  # 只记录有意义的相似度
                    results.append({
                        "bid1_id": bids[i].get("id", i),
                        "bid1_name": bids[i].get("bidder_name", f"投标方{i+1}"),
                        "bid2_id": bids[j].get("id", j),
                        "bid2_name": bids[j].get("bidder_name", f"投标方{j+1}"),
                        "similarity": round(similarity, 4),
                        "risk_flag": similarity > 0.85
                    })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    def _preprocess(self, text: str) -> List[str]:
        """文本预处理：分词 + 去停用词"""
        if not text:
            return []
        # 简单分词
        words = re.findall(r'[\w]+', text.lower())
        # 过滤停用词和短词
        return [w for w in words if w not in self.stopwords and len(w) > 1]

    def _build_vocabulary(self, texts: List[List[str]]) -> Dict[str, int]:
        """构建词汇表"""
        vocab = {}
        for text in texts:
            for word in text:
                if word not in vocab:
                    vocab[word] = len(vocab)
        return vocab

    def _text_to_vector(self, text: List[str], vocab: Dict[str, int]) -> Dict[int, float]:
        """将文本转换为词频向量"""
        vector = defaultdict(float)
        word_count = defaultdict(int)

        for word in text:
            word_count[word] += 1

        total_words = len(text) if text else 1
        for word, count in word_count.items():
            if word in vocab:
                # TF-IDF权重（简化版）
                vector[vocab[word]] = count / total_words

        return dict(vector)

    def _cosine_similarity(self, vec1: Dict[int, float], vec2: Dict[int, float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0

        # 计算点积
        dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in set(vec1.keys()) | set(vec2.keys()))

        # 计算模
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _analyze_price_curves(self, bids: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析投标报价曲线
        检测价格雷同性
        """
        # 提取报价信息
        prices = []
        for bid in bids:
            content = bid.get("content", "")
            price = self._extract_price(content)
            if price:
                prices.append({
                    "bid_id": bid.get("id", 0),
                    "bidder_name": bid.get("bidder_name", ""),
                    "price": price,
                    "procurement_category": self._extract_category(content)
                })

        if len(prices) < 2:
            return {}

        price_values = [p["price"] for p in prices]
        avg_price = sum(price_values) / len(price_values)
        max_deviation = max(abs(p - avg_price) / avg_price for p in price_values) if avg_price > 0 else 0

        # 计算报价曲线相关系数
        curve_correlation = 0.0
        if len(prices) >= 3:
            # 按价格排序，计算相邻价格的比值
            sorted_prices = sorted(price_values)
            ratios = [sorted_prices[i+1] / sorted_prices[i] if sorted_prices[i] > 0 else 1.0
                      for i in range(len(sorted_prices)-1)]
            # 如果比值接近1，说明价格高度接近
            avg_ratio = sum(ratios) / len(ratios) if ratios else 1.0
            curve_correlation = 1.0 - min(abs(avg_ratio - 1.0), 1.0)

        # 价格分布分析
        below_avg_count = sum(1 for p in price_values if p < avg_price)
        above_avg_count = len(price_values) - below_avg_count

        return {
            "total_bids": len(prices),
            "price_range": {
                "min": min(price_values),
                "max": max(price_values),
                "avg": round(avg_price, 2)
            },
            "price_deviation": round(max_deviation, 4),
            "curve_correlation": round(curve_correlation, 4),
            "distribution": {
                "below_average": below_avg_count,
                "above_average": above_avg_count
            },
            "anomaly_detected": max_deviation > 0.2 or curve_correlation > 0.9
        }

    def _extract_price(self, content: str) -> float:
        """从文本中提取报价金额"""
        patterns = [
            r'总价[是为：:]*\s*([\d,]+(?:\.\d+)?)\s*万元',
            r'报价[是为：:]*\s*([\d,]+(?:\.\d+)?)\s*万元',
            r'预算[是为：:]*\s*([\d,]+(?:\.\d+)?)\s*万元',
            r'金额[是为：:]*\s*([\d,]+(?:\.\d+)?)\s*万元',
            r'\$\s*([\d,]+(?:\.\d+)?)',
            r'￥\s*([\d,]+(?:\.\d+)?)',
            r'([\d,]+(?:\.\d+)?)\s*元',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    return float(price_str)
                except:
                    pass
        return 0.0

    def _extract_category(self, content: str) -> str:
        """提取采购品类"""
        categories = ["设备", "服务", "工程", "软件", "硬件", "咨询", "培训"]
        for cat in categories:
            if cat in content:
                return cat
        return "unknown"

    def _detect_entity_connections(self, bids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测投标主体之间的关联
        包括：IP关联、联系人关联、地址关联
        """
        connections = []

        # 提取各投标人的元数据
        bid_metadata = []
        for bid in bids:
            metadata = {
                "bid_id": bid.get("id", 0),
                "bidder_name": bid.get("bidder_name", ""),
                "content": bid.get("content", ""),
                "contact_info": self._extract_contact_info(bid.get("content", "")),
                "addresses": self._extract_addresses(bid.get("content", "")),
                "bank_accounts": self._extract_bank_accounts(bid.get("content", ""))
            }
            bid_metadata.append(metadata)

        n = len(bid_metadata)

        # 检测IP关联（简化版：通过文本中的IP模式）
        for i in range(n):
            for j in range(i + 1, n):
                ip_connection = self._check_ip_connection(bid_metadata[i], bid_metadata[j])
                if ip_connection:
                    connections.append(ip_connection)

                # 检测地址关联
                address_connection = self._check_address_connection(bid_metadata[i], bid_metadata[j])
                if address_connection:
                    connections.append(address_connection)

                # 检测联系人关联
                contact_connection = self._check_contact_connection(bid_metadata[i], bid_metadata[j])
                if contact_connection:
                    connections.append(contact_connection)

        return connections

    def _check_ip_connection(self, meta1: Dict, meta2: Dict) -> Dict[str, Any]:
        """检测IP关联"""
        content1 = meta1.get("content", "")
        content2 = meta2.get("content", "")

        # 简化：检测文档中是否包含相同IP地址模式
        ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        ips1 = set(re.findall(ip_pattern, content1))
        ips2 = set(re.findall(ip_pattern, content2))

        if ips1 and ips2 and ips1 == ips2:
            return {
                "type": "ip",
                "entities": [meta1["bidder_name"], meta2["bidder_name"]],
                "detail": f"共享IP地址: {list(ips1)[0]}",
                "risk_level": "high"
            }
        return None

    def _check_address_connection(self, meta1: Dict, meta2: Dict) -> Dict[str, Any]:
        """检测地址关联"""
        addrs1 = set(meta1.get("addresses", []))
        addrs2 = set(meta2.get("addresses", []))

        common_addrs = addrs1 & addrs2
        if common_addrs:
            return {
                "type": "address",
                "entities": [meta1["bidder_name"], meta2["bidder_name"]],
                "detail": f"注册地址相同: {list(common_addrs)[0]}",
                "risk_level": "medium"
            }
        return None

    def _check_contact_connection(self, meta1: Dict, meta2: Dict) -> Dict[str, Any]:
        """检测联系人关联"""
        contacts1 = set(meta1.get("contact_info", {}).get("names", []))
        contacts2 = set(meta2.get("contact_info", {}).get("names", []))

        common_contacts = contacts1 & contacts2
        if common_contacts:
            return {
                "type": "contact",
                "entities": [meta1["bidder_name"], meta2["bidder_name"]],
                "detail": f"联系人相同: {list(common_contacts)[0]}",
                "risk_level": "high"
            }
        return None

    def _extract_contact_info(self, content: str) -> Dict[str, List[str]]:
        """提取联系人信息"""
        names = re.findall(r'联系人[：:]\s*([^\s,，]+)', content)
        phones = re.findall(r'电话[：:]\s*([\d-]+)', content)
        return {"names": names, "phones": phones}

    def _extract_addresses(self, content: str) -> List[str]:
        """提取地址信息"""
        addresses = re.findall(r'地址[：:]\s*([^\n,，]+)', content)
        return addresses

    def _extract_bank_accounts(self, content: str) -> List[str]:
        """提取银行账号"""
        accounts = re.findall(r'账号[：:]\s*([\d]+)', content)
        return accounts

    def _compute_overall_risk(
        self,
        similarity_pairs: List[Dict[str, Any]],
        price_analysis: Dict[str, Any],
        entity_connections: List[Dict[str, Any]]
    ) -> float:
        """计算综合风险得分"""
        risk = 0.0

        # 高度相似对的风险贡献
        high_sim_count = sum(1 for p in similarity_pairs if p.get("risk_flag", False))
        if high_sim_count >= 2:
            risk += 0.4
        elif high_sim_count == 1:
            risk += 0.25

        # 价格异常的风险贡献
        if price_analysis.get("anomaly_detected", False):
            risk += 0.3
        if price_analysis.get("curve_correlation", 0) > 0.9:
            risk += 0.25

        # 主体关联的风险贡献
        critical_connections = [c for c in entity_connections if c.get("risk_level") == "high"]
        if len(critical_connections) >= 2:
            risk += 0.35
        elif len(critical_connections) == 1:
            risk += 0.15

        return min(risk, 1.0)

    def build_similarity_graph(self, similarity_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建相似度图谱
        用于可视化展示
        """
        nodes = []
        edges = []

        # 收集所有投标人作为节点
        bidder_names = set()
        for pair in similarity_pairs:
            bidder_names.add(pair["bid1_name"])
            bidder_names.add(pair["bid2_name"])

        for name in bidder_names:
            nodes.append({
                "id": name,
                "label": name,
                "type": "bidder"
            })

        # 添加相似度边
        for pair in similarity_pairs:
            if pair["similarity"] > 0.6:  # 只显示有意义的边
                edges.append({
                    "source": pair["bid1_name"],
                    "target": pair["bid2_name"],
                    "similarity": pair["similarity"],
                    "risk_flag": pair["risk_flag"]
                })

        return {
            "nodes": nodes,
            "edges": edges
        }


if __name__ == "__main__":
    analyzer = SimilarityAnalyzer()

    # 测试数据
    test_bids = [
        {
            "id": 1,
            "bidder_name": "公司A",
            "content": """
            投标文件
            联系人：张三
            电话：010-12345678
            地址：北京市海淀区中关村大街1号
            投标报价：150万元
            我公司具备系统集成一级资质
            """
        },
        {
            "id": 2,
            "bidder_name": "公司B",
            "content": """
            投标文件
            联系人：李四
            电话：010-87654321
            地址：北京市海淀区中关村大街1号
            投标报价：148万元
            我公司具备系统集成一级资质
            """
        },
        {
            "id": 3,
            "bidder_name": "公司C",
            "content": """
            投标文件
            联系人：王五
            电话：010-55555555
            地址：北京市朝阳区建国路100号
            投标报价：200万元
            我公司具备系统集成二级资质
            """
        }
    ]

    result = analyzer.analyze_bids(test_bids)
    print(f"相似度分析结果:")
    print(f"  相似度对数: {len(result['similarity_pairs'])}")
    print(f"  价格分析: {result['price_analysis']}")
    print(f"  主体关联: {len(result['entity_connections'])} 项")
    print(f"  综合风险: {result['overall_risk']} ({result['risk_level']})")

    if result['similarity_pairs']:
        print(f"\n高度相似对:")
        for pair in result['similarity_pairs'][:3]:
            print(f"  {pair['bid1_name']} <-> {pair['bid2_name']}: {pair['similarity']:.2%}")