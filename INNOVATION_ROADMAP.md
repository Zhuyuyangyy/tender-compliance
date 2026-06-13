# Innovation Roadmap

## Patent Portfolio Strategy

This document outlines the innovation roadmap for the Tender Compliance System, including patentable inventions, their technical foundations, and implementation timelines.

---

## Patent 1: Virtual Clause Coordinate-Based Tender Document Compliance Detection

**Status**: Core implementation complete
**Patent Application Title**: 一种基于虚拟条款坐标的招标文件合规检测方法及系统

### Technical Innovation

Traditional document analysis relies on fixed template matching or positional heuristics. This invention introduces a **virtual clause coordinate space** where each clause in a tender document is mapped to a 2D coordinate:

- **X-axis**: Relative position in document (0.0 to 1.0, based on line number / total lines)
- **Y-axis**: Semantic category (qualification=0.2, scoring=0.4, technical=0.6, commercial=0.8, contract=1.0)
- **Z-axis**: Intra-category differentiation (random jitter for visualization)

### Claims

1. A method for mapping unstructured tender document clauses to a virtual coordinate space, comprising: automatic chapter detection via regex pattern matching; clause classification using keyword-based semantic analysis; coordinate generation based on positional and categorical features.
2. A system that uses said coordinate mapping to detect compliance violations by analyzing spatial clustering of risk-flagged clauses.
3. A method where coordinate-based analysis is layout-agnostic, working identically on documents with varying formatting, section numbering, and structure.

### Implementation

- **File**: `backend/app/services/tender_parser.py`
- **Key Methods**: `parse_tender()`, `_generate_coordinate()`, `_classify_chapter()`

---

## Patent 2: Bidder Relationship Graph-Based Bid-Rigging Risk Identification

**Status**: Core implementation complete, graph analysis enhancement planned
**Patent Application Title**: 一种基于投标主体关系图谱的围串标风险识别方法及系统

### Technical Innovation

Existing collusion detection focuses on pairwise document similarity. This invention constructs a **multi-dimensional relationship graph** among bidders:

- **Nodes**: Bidding entities
- **Edges**: Weighted by similarity score, shared contacts, shared addresses, shared IP addresses, price correlation
- **Risk Propagation**: Connected component analysis identifies collusion rings

### Claims

1. A method for constructing a multi-dimensional bidder relationship graph with edges weighted by document similarity, entity connection strength, and price correlation coefficients.
2. A system that applies graph community detection algorithms to identify collusion clusters beyond pairwise analysis.
3. A risk propagation model where entity connections amplify document similarity scores through nonlinear coupling.
4. A visualization method using force-directed graph layout for intuitive presentation of collusion risk topology.

### Implementation

- **File**: `backend/app/services/similarity_analyzer.py`
- **Key Methods**: `analyze_bids()`, `_detect_entity_connections()`, `build_similarity_graph()`
- **Enhancement Planned**: NetworkX integration for community detection

---

## Patent 3: Semantic Operator Chain-Based Biased Scoring Detection

**Status**: Core implementation complete
**Patent Application Title**: 一种基于语义算子链的招标评分条款倾向性检测方法及系统

### Technical Innovation

Keyword matching cannot detect implicit bias in scoring criteria. This invention introduces **semantic operators** modeled after first-order logic:

| Operator | Function | Example |
|----------|----------|---------|
| P_REQUIRE | Mandatory requirements | "必须", "应当" |
| P_FORBID | Prohibition clauses | "不得", "禁止", "排斥" |
| P_LIMIT | Restrictive clauses | "限于", "仅限", "指定" |
| P_PREFER | Preference clauses | "优先考虑", "同等条件下" |
| P_BASIS | Scoring basis | "基准价", "参考价" |
| P_RECOMMEND | Recommendations | "推荐", "建议" |

### Claims

1. A method for detecting implicit scoring bias in tender documents using a chain of semantic operators that capture predicate logic relationships.
2. A system where semantic operators are combined in sequence (chain) to detect compound restrictions that individual operators would miss.
3. A detection method that distinguishes between legitimate requirements (P_REQUIRE) and discriminatory restrictions (P_LIMIT + P_FORBID) based on operator co-activation patterns.
4. A scoring transparency validator that checks whether evaluation criteria referenced by P_PREFER operators have explicit quantitative definitions.

### Implementation

- **File**: `backend/app/services/rule_engine.py`
- **Key Classes**: `SemanticOperator`, `RuleEngine`
- **Key Methods**: `apply_semantic_chain()`, `detect_risks()`

---

## Patent 4: Risk Entropy-Based Bidding Anomaly Graduated Early Warning

**Status**: Core implementation complete
**Patent Application Title**: 一种基于风险熵的招投标异常行为分级预警方法及系统

### Technical Innovation

Traditional risk scoring uses linear weighted sums. This invention introduces **risk entropy** with nonlinear coupling:

- **Factor Weights**: Each risk dimension has a calibrated weight
- **Coupling Amplification**: When multiple risk factors co-occur, a coupling multiplier amplifies the combined score
- **Nonlinear Fuse**: Critical combinations (e.g., bid_similarity + entity_connection) trigger automatic escalation
- **Three-Level Classification**: Green (< 0.3), Yellow (0.3-0.6), Red (>= 0.6)

### Claims

1. A method for calculating multi-dimensional risk entropy from bidding analysis results, comprising weighted factor aggregation with coupling amplification.
2. A nonlinear fuse mechanism where specific combinations of risk factors trigger automatic risk level escalation beyond linear summation.
3. A graduated early warning system with three severity levels and automatic recommendation generation based on risk level transitions.
4. A bid-specific risk entropy model that integrates document similarity, price curve analysis, and entity connection metrics into a unified risk score.

### Implementation

- **File**: `backend/app/services/tender_risk_scorer.py`
- **Key Class**: `TenderRiskScorer`
- **Key Methods**: `calculate_tender_risk()`, `calculate_bid_similarity_risk()`

---

## Patent 5: Multi-Dimensional Collusion Marker Detection System (Planned)

**Status**: Planned for implementation
**Patent Application Title**: 一种基于多维围串标标记的协同检测方法及系统

### Technical Innovation

Current collusion detection uses individual markers. This invention combines multiple detection dimensions into a unified probability model:

- **Price Markers**: Identical decimals, price clustering, irregular intervals, herd pricing
- **Document Markers**: TF-IDF similarity, structural reuse, error pattern matching
- **Temporal Markers**: Submission time clustering, sequential pattern detection
- **Entity Markers**: Shared resources, cross-ownership, common personnel

### Claims

1. A method for computing collusion probability from multiple independent marker dimensions using Bayesian probability fusion.
2. A system that weights marker significance based on market context and historical collusion patterns.
3. A recommendation engine that maps collusion probability ranges to specific investigative actions.

### Implementation Plan

- **New File**: `backend/app/services/collusion_detector.py`
- **Timeline**: Q3 2026

---

## Innovation Timeline

```
2026 Q2  ─── Patent 1-4: Core implementation complete
              Patent 5: Design and specification
              
2026 Q3  ─── Patent 5: Implementation
              Deep learning similarity (Sentence-BERT)
              Bidder graph community detection (NetworkX)
              
2026 Q4  ─── Patent applications filed
              Historical benchmarking system
              Rule learning from feedback
              
2027 Q1  ─── Government platform integration
              Multi-language support
              Production deployment at scale
```

---

## Competitive Advantage

| Feature | Our System | Traditional Tools |
|---------|-----------|-------------------|
| Clause Coordinate Mapping | Yes (virtual 2D space) | No (template-based) |
| Semantic Operator Chain | 6 operators with chain logic | Simple keyword matching |
| Nonlinear Risk Coupling | Coupling amplification + fuse | Linear weighted sum |
| Entity Graph Analysis | Multi-dimensional graph | Pairwise comparison |
| Bid Similarity | TF-IDF + entity + price | Document comparison only |
| Audit Trail | Full chain with timestamps | Basic logging |
