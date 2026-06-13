"""
Tests for SimilarityAnalyzer (backend/app/services/similarity_analyzer.py).
Covers text similarity, price analysis, entity connections, graph building.
"""
import pytest


class TestAnalyzeBids:
    """Test the analyze_bids method."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    def test_single_bid(self, analyzer):
        bids = [{"id": 1, "bidder_name": "A", "content": "test"}]
        result = analyzer.analyze_bids(bids)
        assert result["similarity_pairs"] == []
        assert result["risk_level"] == "green"
        assert result["overall_risk"] == 0.0

    def test_two_bids(self, analyzer, sample_bids):
        result = analyzer.analyze_bids(sample_bids[:2])
        assert "similarity_pairs" in result
        assert "price_analysis" in result
        assert "entity_connections" in result
        assert "overall_risk" in result
        assert "risk_level" in result

    def test_three_bids(self, analyzer, sample_bids):
        result = analyzer.analyze_bids(sample_bids)
        assert result["risk_level"] in ["green", "yellow", "red"]

    def test_similar_bids_high_risk(self, analyzer):
        bids = [
            {"id": 1, "bidder_name": "A", "content": "华为服务器 Oracle数据库 一级资质 150万元"},
            {"id": 2, "bidder_name": "B", "content": "华为服务器 Oracle数据库 一级资质 148万元"}
        ]
        result = analyzer.analyze_bids(bids)
        # Very similar content should produce high similarity
        if result["similarity_pairs"]:
            assert result["similarity_pairs"][0]["similarity"] > 0.5

    def test_different_bids_low_risk(self, analyzer):
        bids = [
            {"id": 1, "bidder_name": "A", "content": "华为服务器高端配置方案"},
            {"id": 2, "bidder_name": "B", "content": "Dell存储设备中端配置"}
        ]
        result = analyzer.analyze_bids(bids)
        assert result["overall_risk"] < 0.5


class TestTextPreprocessing:
    """Test text preprocessing and vectorization."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    def test_preprocess_normal(self, analyzer):
        words = analyzer._preprocess("投标文件 联系人 张三")
        assert isinstance(words, list)
        assert len(words) > 0

    def test_preprocess_empty(self, analyzer):
        assert analyzer._preprocess("") == []

    def test_preprocess_filters_stopwords(self, analyzer):
        words = analyzer._preprocess("的 了 是 投标文件")
        assert "的" not in words

    def test_build_vocabulary(self, analyzer):
        texts = [["hello", "world"], ["hello", "test"]]
        vocab = analyzer._build_vocabulary(texts)
        assert "hello" in vocab
        assert "world" in vocab
        assert "test" in vocab

    def test_text_to_vector(self, analyzer):
        vocab = {"hello": 0, "world": 1}
        vec = analyzer._text_to_vector(["hello", "hello", "world"], vocab)
        assert 0 in vec  # hello index
        assert 1 in vec  # world index
        assert vec[0] > vec[1]  # hello appears more


class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    def test_identical_vectors(self, analyzer):
        vec = {0: 1.0, 1: 2.0, 2: 3.0}
        assert abs(analyzer._cosine_similarity(vec, vec) - 1.0) < 0.001

    def test_orthogonal_vectors(self, analyzer):
        vec1 = {0: 1.0, 1: 0.0}
        vec2 = {0: 0.0, 1: 1.0}
        assert abs(analyzer._cosine_similarity(vec1, vec2)) < 0.001

    def test_empty_vectors(self, analyzer):
        assert analyzer._cosine_similarity({}, {}) == 0.0

    def test_one_empty(self, analyzer):
        assert analyzer._cosine_similarity({0: 1.0}, {}) == 0.0
        assert analyzer._cosine_similarity({}, {0: 1.0}) == 0.0

    def test_partial_overlap(self, analyzer):
        vec1 = {0: 1.0, 1: 1.0}
        vec2 = {1: 1.0, 2: 1.0}
        sim = analyzer._cosine_similarity(vec1, vec2)
        assert 0 < sim < 1


class TestPriceAnalysis:
    """Test price curve analysis."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    def test_extract_price_wan(self, analyzer):
        assert analyzer._extract_price("投标报价：150万元") == 150.0

    def test_extract_price_total(self, analyzer):
        assert analyzer._extract_price("总价为200万元") == 200.0

    def test_extract_price_yuan(self, analyzer):
        assert analyzer._extract_price("金额：10000元") == 10000.0

    def test_extract_price_rmb_symbol(self, analyzer):
        assert analyzer._extract_price("￥50000") == 50000.0

    def test_extract_price_no_match(self, analyzer):
        assert analyzer._extract_price("没有价格信息") == 0.0

    def test_extract_category(self, analyzer):
        assert analyzer._extract_category("服务器设备采购") == "设备"
        assert analyzer._extract_category("系统集成服务") == "服务"
        assert analyzer._extract_category("软件开发项目") == "软件"

    def test_extract_category_unknown(self, analyzer):
        assert analyzer._extract_category("普通文本") == "unknown"

    def test_analyze_price_curves_with_bids(self, analyzer):
        bids = [
            {"id": 1, "bidder_name": "A", "content": "投标报价：100万元"},
            {"id": 2, "bidder_name": "B", "content": "投标报价：105万元"},
            {"id": 3, "bidder_name": "C", "content": "投标报价：200万元"}
        ]
        result = analyzer._analyze_price_curves(bids)
        assert "price_range" in result
        assert result["price_range"]["min"] == 100.0
        assert result["price_range"]["max"] == 200.0

    def test_analyze_price_curves_single_bid(self, analyzer):
        bids = [{"id": 1, "bidder_name": "A", "content": "投标报价：100万元"}]
        result = analyzer._analyze_price_curves(bids)
        assert result == {}


class TestEntityConnections:
    """Test entity connection detection."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    def test_shared_address(self, analyzer, sample_bids):
        result = analyzer.analyze_bids(sample_bids)
        address_conns = [c for c in result["entity_connections"] if c["type"] == "address"]
        assert len(address_conns) >= 1  # A and B share address

    def test_shared_contact(self, analyzer):
        bids = [
            {"id": 1, "bidder_name": "A", "content": "联系人：张三 电话：010-123"},
            {"id": 2, "bidder_name": "B", "content": "联系人：张三 电话：010-456"}
        ]
        result = analyzer.analyze_bids(bids)
        contact_conns = [c for c in result["entity_connections"] if c["type"] == "contact"]
        assert len(contact_conns) >= 1

    def test_no_connections(self, analyzer):
        bids = [
            {"id": 1, "bidder_name": "A", "content": "联系人：张三 地址：北京"},
            {"id": 2, "bidder_name": "B", "content": "联系人：李四 地址：上海"}
        ]
        result = analyzer.analyze_bids(bids)
        assert len(result["entity_connections"]) == 0

    def test_extract_contact_info(self, analyzer):
        info = analyzer._extract_contact_info("联系人：张三 电话：010-12345678")
        assert "张三" in info["names"]
        assert "010-12345678" in info["phones"]

    def test_extract_addresses(self, analyzer):
        addrs = analyzer._extract_addresses("地址：北京市海淀区中关村大街1号")
        assert len(addrs) >= 1
        assert "北京市海淀区" in addrs[0]

    def test_extract_bank_accounts(self, analyzer):
        accounts = analyzer._extract_bank_accounts("账号：123456789012")
        assert "123456789012" in accounts


class TestSimilarityGraph:
    """Test similarity graph construction."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    def test_build_graph(self, analyzer):
        pairs = [
            {"bid1_name": "A", "bid2_name": "B", "similarity": 0.9, "risk_flag": True},
            {"bid1_name": "A", "bid2_name": "C", "similarity": 0.3, "risk_flag": False},
            {"bid1_name": "B", "bid2_name": "C", "similarity": 0.7, "risk_flag": False}
        ]
        graph = analyzer.build_similarity_graph(pairs)
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == 3  # A, B, C
        # Only edges with similarity > 0.6
        assert len(graph["edges"]) == 2  # 0.9 and 0.7

    def test_build_graph_empty(self, analyzer):
        graph = analyzer.build_similarity_graph([])
        assert graph["nodes"] == []
        assert graph["edges"] == []

    def test_graph_node_structure(self, analyzer):
        pairs = [{"bid1_name": "A", "bid2_name": "B", "similarity": 0.9, "risk_flag": True}]
        graph = analyzer.build_similarity_graph(pairs)
        node = graph["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "type" in node


class TestOverallRiskComputation:
    """Test _compute_overall_risk method."""

    @pytest.fixture
    def analyzer(self):
        from backend.app.services.similarity_analyzer import SimilarityAnalyzer
        return SimilarityAnalyzer()

    def test_no_risk(self, analyzer):
        risk = analyzer._compute_overall_risk([], {}, [])
        assert risk == 0.0

    def test_high_similarity_contributes(self, analyzer):
        pairs = [{"risk_flag": True}, {"risk_flag": True}]
        risk = analyzer._compute_overall_risk(pairs, {}, [])
        assert risk >= 0.4

    def test_price_anomaly_contributes(self, analyzer):
        price = {"anomaly_detected": True}
        risk = analyzer._compute_overall_risk([], price, [])
        assert risk >= 0.3

    def test_entity_connections_contribute(self, analyzer):
        connections = [{"risk_level": "high"}, {"risk_level": "high"}]
        risk = analyzer._compute_overall_risk([], {}, connections)
        assert risk >= 0.35

    def test_risk_capped_at_one(self, analyzer):
        pairs = [{"risk_flag": True}, {"risk_flag": True}]
        price = {"anomaly_detected": True, "curve_correlation": 0.95}
        connections = [{"risk_level": "high"}, {"risk_level": "high"}, {"risk_level": "high"}]
        risk = analyzer._compute_overall_risk(pairs, price, connections)
        assert risk <= 1.0
