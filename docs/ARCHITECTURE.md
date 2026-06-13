# System Architecture

## Overview

The Tender Compliance System follows a layered architecture with clear separation between API, business logic, and data layers.

```
                        +-------------------+
                        |   Vue 3 Frontend  |
                        |  (index.html)     |
                        +--------+----------+
                                 |
                                 | HTTP/REST
                                 v
                        +--------+----------+
                        |   FastAPI Layer    |
                        |   main.py          |
                        |   routes.py        |
                        +--------+----------+
                                 |
              +------------------+------------------+
              |                  |                  |
     +--------v--------+ +------v------+ +--------v--------+
     |  TenderParser    | | RuleEngine  | | Similarity      |
     |  (NLP + coords)  | | (Semantic   | | Analyzer        |
     |                   | |  Operators) | | (TF-IDF + Graph)|
     +--------+----------+ +------+------+ +--------+--------+
              |                  |                  |
              +------------------+------------------+
                                 |
                        +--------v--------+
                        | TenderRiskScorer |
                        | (Risk Entropy)   |
                        +--------+--------+
                                 |
                        +--------v--------+
                        | ReportGenerator  |
                        | (JSON/Markdown)  |
                        +--------+--------+
                                 |
                        +--------v--------+
                        |   SQLite DB      |
                        | database.py      |
                        +-----------------+
```

## Component Responsibilities

### 1. TenderParser (tender_parser.py)
- Splits tender documents into chapters and clauses
- Maps clauses to virtual 2D coordinate space (x=position, y=category)
- Detects brand restrictions, qualification exclusions, unclear scoring
- Extracts qualification/scoring/technical/commercial/contract zones

### 2. RuleEngine (rule_engine.py)
- Loads configurable rules from `tender_rules.json`
- Applies semantic operator chain: P_LIMIT, P_FORBID, P_PREFER, P_BASIS
- Detects region limitations, experience exclusions
- Evaluates specific rule compliance with violation counting

### 3. SimilarityAnalyzer (similarity_analyzer.py)
- Computes TF-IDF vectors and cosine similarity between bid documents
- Extracts prices, contact info, addresses, bank accounts from text
- Detects entity connections (shared IP, contact, address)
- Builds similarity graph for visualization

### 4. TenderRiskScorer (tender_risk_scorer.py)
- Maps severity levels to numeric scores
- Applies weighted risk factor aggregation
- Implements nonlinear coupling amplification when multiple risks co-occur
- Classifies risk as green/yellow/red

### 5. ReportGenerator (report_generator.py)
- Generates structured tender compliance reports
- Generates bid similarity analysis reports
- Produces comprehensive risk reports combining both analyses
- Exports to JSON and Markdown formats
- Includes full audit trail with timestamps

### 6. Database (database.py)
- SQLite storage for tenders, bids, rules, analysis results, audit logs
- Initializes default compliance rules on first run
- Provides audit logging with action/target/details

## Data Flow

1. User uploads tender document via `/api/upload_tender`
2. User triggers analysis via `/api/analyze_tender`
   - TenderParser extracts structure and detects risks
   - RuleEngine applies semantic operator chain
   - TenderRiskScorer calculates risk entropy
3. User uploads bid documents via `/api/upload_bids`
4. User triggers bid analysis via `/api/analyze_bids`
   - SimilarityAnalyzer computes pairwise similarity
   - Entity connection detection runs
   - TenderRiskScorer calculates bid risk
5. Comprehensive report generated via `/api/get_risk_report/{id}`

## Design Decisions

- **SQLite**: Lightweight, zero-config, sufficient for single-instance deployment
- **Virtual Clause Coordinates**: Layout-agnostic analysis that works regardless of document formatting
- **Semantic Operators**: First-order logic predicates catch implicit restrictions that keyword matching misses
- **Nonlinear Coupling**: Multiple co-occurring risks amplify each other, reflecting real-world compounding violations
- **TF-IDF over Embeddings**: Chosen for deterministic, explainable similarity without GPU requirements
