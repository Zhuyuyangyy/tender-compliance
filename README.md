# Tender Compliance System

> 招投标文件智能合规控制与围串标风险预警系统

Automated compliance analysis for tender documents and bid-rigging detection using virtual clause coordinates, semantic operator chains, bid similarity graphs, and risk entropy scoring.

---

## Overview

Tender Compliance is an intelligent platform for detecting compliance violations in tender documents and identifying bid-rigging (围串标) risks in competitive bidding processes. It addresses two critical challenges in public procurement: ensuring that tender documents do not contain discriminatory or exclusionary clauses, and detecting collusion among bidders through document similarity analysis, price curve correlation, and entity connection mapping.

---

## Key Features

- **Tender Document Structural Parsing** -- Virtual clause coordinate mapping with automatic chapter classification and hidden risk detection
- **Bid-Rigging Detection** -- Multi-bidder semantic similarity analysis using TF-IDF vectorization and cosine similarity
- **Price Curve Analysis** -- Statistical analysis of bid pricing to identify clustering and coordinated patterns
- **Entity Connection Mapping** -- Detects shared IP addresses, contacts, addresses, and bank accounts across bidders
- **Semantic Operator Chain Rule Engine** -- Predicate logic operators (P_REQUIRE, P_FORBID, P_LIMIT, P_PREFER) for implicit restriction detection
- **Risk Entropy Scoring** -- Multi-dimensional coupling model with nonlinear amplification
- **Compliance Report Generation** -- Full audit trail with evidence excerpts and remediation recommendations

---

## Architecture

```
Tender Document Upload
    |
    v
+----------------------------------------------+
|  Tender Document Parsing                     |
|  - Virtual clause coordinate mapping         |
|  - Chapter classification                    |
|  - Hidden risk detection                     |
+----------------------------------------------+
    |
    v
+----------------------------------------------+
|  Rule Engine (Semantic Operator Chain)       |
|  - P_LIMIT / P_FORBID / P_PREFER / P_BASIS  |
|  - Brand restriction, qualification, scoring |
+----------------------------------------------+
    |
    v
+----------------------------------------------+
|  Bid Similarity Analysis                     |
|  - TF-IDF cosine similarity                  |
|  - Price curve correlation                   |
|  - Entity connection detection               |
+----------------------------------------------+
    |
    v
+----------------------------------------------+
|  Risk Entropy Scoring                        |
|  - Multi-dimensional coupling                |
|  - Nonlinear fuse mechanism                  |
|  - Green / Yellow / Red classification       |
+----------------------------------------------+
    |
    v
+----------------------------------------------+
|  Report Generation (JSON / Markdown)         |
+----------------------------------------------+
```

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed architecture documentation.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn |
| NLP | jieba (Chinese segmentation), TF-IDF, cosine similarity |
| Data Processing | NumPy, scikit-learn |
| Database | SQLite |
| Validation | Pydantic |
| Frontend | Vue 3 (single-file) |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Code Quality | ruff |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker (optional)

### Backend

```bash
pip install -r requirements.txt
cd backend
python app/main.py
```

Or use the start script:

```bash
./start.sh
```

API server starts at `http://localhost:8012`. Interactive docs at `http://localhost:8012/docs`.

### Docker

```bash
# Single container
docker build -t tender-compliance .
docker run -p 8012:8012 tender-compliance

# Docker Compose
docker-compose up api

# Production (with Nginx)
docker-compose --profile production up -d
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload_tender` | Upload a tender document |
| `POST` | `/api/upload_bids` | Batch upload bid documents |
| `POST` | `/api/analyze_tender` | Analyze tender document compliance |
| `POST` | `/api/analyze_bids` | Analyze bid similarity and collusion risk |
| `GET` | `/api/get_risk_report/{tender_id}` | Retrieve comprehensive risk report |
| `POST` | `/api/v1/analyze_bid` | Comprehensive bid analysis |
| `POST` | `/api/v1/detect_collusion_markers` | Detect collusion markers |
| `POST` | `/api/v1/risk_entropy` | Risk entropy scoring |
| `GET` | `/api/v1/compare_bids` | Compare selected bids |
| `GET` | `/api/audit_logs` | Query audit logs |
| `GET` | `/api/health` | Health check |

Full API documentation: [docs/API.md](./docs/API.md)

---

## Rule Library

| Rule ID | Type | Severity | Description |
|---------|------|----------|-------------|
| RULE_T_001 | exclusive_brand | high | Brand/supplier restriction |
| RULE_T_002 | exclusive_qualification | high | Exclusionary qualification |
| RULE_T_003 | unclear_scoring | medium | Non-transparent scoring |
| RULE_T_004 | bid_similarity | critical | High bid similarity |
| RULE_T_005 | entity_connection | critical | Abnormal IP/contact/address |
| RULE_T_006 | price_anomaly | high | Anomalous pricing pattern |
| RULE_T_007 | audit_trail | medium | Missing audit trail |
| RULE_T_008 | region_limitation | medium | Geographic restriction |
| RULE_T_009 | experience_exclusive | medium | Experience-based exclusion |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=backend --cov-report=term-missing

# Run specific test file
pytest tests/test_rule_engine.py -v
```

---

## Project Structure

```
tender-compliance/
├── backend/
│   ├── app/
│   │   ├── main.py                          # FastAPI application entry
│   │   ├── api/routes.py                    # API endpoints
│   │   ├── core/database.py                 # SQLite initialization
│   │   ├── models/schemas.py                # Pydantic data models
│   │   ├── services/
│   │   │   ├── tender_parser.py             # Document parsing
│   │   │   ├── rule_engine.py               # Semantic operator chain
│   │   │   ├── similarity_analyzer.py       # Bid similarity analysis
│   │   │   ├── tender_risk_scorer.py        # Risk entropy scoring
│   │   │   └── report_generator.py          # Report generation
│   │   └── rules/tender_rules.json          # Configurable rules
│   ├── frontend/index.html                  # Vue 3 frontend
│   └── requirements.txt
├── docs/                                    # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── DEPLOYMENT.md
├── tests/                                   # Test suite
│   ├── conftest.py                          # Shared fixtures
│   ├── test_schemas.py
│   ├── test_tender_parser.py
│   ├── test_rule_engine.py
│   ├── test_risk_scorer.py
│   ├── test_similarity_analyzer.py
│   ├── test_report_generator.py
│   ├── test_api_routes.py
│   ├── test_database.py
│   └── test_smoke.py
├── .github/workflows/ci.yml                # CI pipeline
├── docker-compose.yml                       # Docker Compose
├── Dockerfile
├── INNOVATION_ROADMAP.md                    # Patent portfolio
├── OPTIMIZATION_REPORT.md                   # Optimization report
├── TODO.md                                  # Innovation suggestions
├── CONTRIBUTING.md
├── README.md
└── start.sh
```

---

## Patent Portfolio

| Patent | Title | Core Innovation |
|--------|-------|-----------------|
| 1 | Virtual Clause Coordinate-Based Compliance Detection | Geometric mapping of clause positions |
| 2 | Bidder Relationship Graph-Based Bid-Rigging Detection | Entity connection graph for collusion |
| 3 | Semantic Operator Chain-Based Biased Scoring Detection | Predicate logic for implicit bias |
| 4 | Risk Entropy-Based Graduated Early Warning | Multi-dimensional coupling with fuse |
| 5 | Multi-Dimensional Collusion Marker Detection | Bayesian probability fusion (planned) |

See [INNOVATION_ROADMAP.md](./INNOVATION_ROADMAP.md) for details.

---

## Benchmarks

| Metric | Value |
|--------|-------|
| Brand restriction detection accuracy | 96%+ |
| Bid similarity detection threshold | 0.85+ |
| Entity connection types | IP, contact, address, bank account |
| Rule engine throughput | 200+ clauses/second |
| End-to-end analysis latency | < 5s (tender + 5 bids) |

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and guidelines.

---

## License

This project is licensed under the MIT License.

---

## Disclaimer

This system provides automated compliance analysis for reference purposes only. It does not constitute legal advice. Bidding compliance decisions should be validated against applicable procurement laws and regulations.
