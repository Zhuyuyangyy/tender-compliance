# Q2-Grade SCI Peer Review Report

**Project**: tender-compliance (招投标文件智能合规控制与围串标风险预警系统)
**Review Date**: 2026-05-29
**Reviewer**: Automated SCI-Q2 Code Review
**Scope**: Full codebase audit -- architecture, algorithm correctness, code quality, security, testing, performance, documentation

---

## 1. Seven-Dimension Scoring

| # | Dimension | Score | Max | Justification |
|---|-----------|-------|-----|---------------|
| D1 | **Architecture & Modularity** | 6.5 | 10 | Clear service-layer separation (parser, rule engine, scorer, similarity analyzer, report generator). Pydantic schemas for data contracts. However, risk detection logic is duplicated between `TenderParser.detect_risks()` and `RuleEngine.detect_risks()` with inconsistent behavior. Two routers (`router` and `compliance_router`) registered in `main.py` with overlapping concerns. |
| D2 | **Algorithm Correctness** | 3.0 | 10 | **CRITICAL**: `/risk_entropy` endpoint used `random.uniform(0.3, 0.95)` for risk scoring -- non-deterministic output in a compliance-critical system. `/compare_bids` endpoint also generated random data. Fixed in this review. TF-IDF in `SimilarityAnalyzer` only computes TF (no IDF), weakening similarity detection. Price curve correlation uses naive ratio-based method instead of Pearson/Spearman. Coordinate z-axis uses `np.random.uniform` -- non-reproducible. |
| D3 | **Code Quality & Robustness** | 5.5 | 10 | Good type hints and docstrings throughout. Bare `except:` in `_extract_price` (line 209). DB connections opened/closed manually without context managers -- leak risk on exceptions. `COMMERCIAL_KEYWORDS` referenced but undefined in `tender_parser.py` (fixed). Unused variable `title_lower` (fixed). `import random` was used only for fake scoring (removed). |
| D4 | **Security** | 4.0 | 10 | CORS `allow_origins=["*"]` with `allow_credentials=True` -- permissive and insecure. No authentication or authorization on any endpoint. No file size limits on uploads. No rate limiting. SQL queries use parameterized style (good). No input sanitization on document content before storage. |
| D5 | **Testability & Coverage** | 6.0 | 10 | Comprehensive smoke test suite (`test_smoke.py`) covering all service modules with fixtures. Tests for schema validation, risk scoring, similarity analysis, report generation. Missing: API integration tests, edge cases for empty/malformed inputs, concurrent access tests. No test for the (now-fixed) random scoring endpoints. |
| D6 | **Performance & Scalability** | 4.5 | 10 | SQLite unsuitable for concurrent production access. All analysis is synchronous/blocking. O(n^2) similarity matrix without optimization. Full document content stored in DB (memory concern for large tenders). No caching of rule engine patterns. No async DB operations despite using FastAPI. |
| D7 | **Documentation & Maintainability** | 5.5 | 10 | Good Chinese docstrings for domain context. FastAPI auto-generates OpenAPI docs. API_DOC.md exists. No CHANGELOG. Hardcoded thresholds/weights not configurable. No architecture diagram. Patent claims referenced in app description but not documented. |

**Composite Score: 5.0 / 10**

---

## 2. Top 3 Problems (Ranked by Severity)

### P1 [CRITICAL] -- Non-Deterministic Risk Scoring via `random.uniform()` (FIXED)

**Location**: `backend/app/main.py`, endpoint `POST /api/v1/risk_entropy` (lines 133-163)

**Problem**: The core risk entropy endpoint -- the system's primary analysis function -- used Python's `random.uniform(0.3, 0.95)` to generate risk scores for each clause. Risk types were also randomly selected from a hardcoded list. This means:
- Every call returns different results for the same input
- The system provides zero actual compliance analysis
- Results are scientifically meaningless and legally indefensible
- A compliance system that outputs random scores is worse than no system at all (false confidence)

The same pattern existed in `GET /api/v1/compare_bids`, which fabricated bid data with `random.uniform()` instead of querying the database.

**Impact**: Fatal. Undermines the entire system's purpose. Any auditor or regulator would immediately reject the system.

**Fix Applied**:
- Replaced `random.uniform()` scoring with actual `RuleEngine.detect_risks()` + `TenderRiskScorer.calculate_tender_risk()` pipeline
- Each clause is now analyzed by the rule engine for real pattern matching
- Overall risk uses the proper weighted-sum with coupling multiplier model
- `/compare_bids` now queries the SQLite database for actual bid records and extracts real prices via `SimilarityAnalyzer._extract_price()`
- Removed `import random` dependency

### P2 [HIGH] -- Undefined `COMMERCIAL_KEYWORDS` Reference (FIXED)

**Location**: `backend/app/services/tender_parser.py`, line 112

**Problem**: `parse_tender()` references `COMMERCIAL_KEYWORDS` which is never defined as a module-level constant. The code uses `COMMERCIAL_KEYWORDS if 'COMMERCIAL_KEYWORDS' in dir() else []` which always evaluates to `[]` due to how `dir()` works in this context. Result: commercial zone extraction silently returns empty, missing all commercial clause risks.

**Fix Applied**: Replaced with `CONTRACT_KEYWORDS` (already defined and semantically appropriate for commercial/contract analysis).

### P3 [HIGH] -- Duplicate Risk Detection Logic with Inconsistent Behavior

**Location**: `backend/app/services/tender_parser.py` (`detect_risks()`) vs `backend/app/services/rule_engine.py` (`detect_risks()`)

**Problem**: Two independent implementations of risk detection exist:
- `TenderParser.detect_risks()`: Simple keyword matching, returns `RiskItem` objects
- `RuleEngine.detect_risks()`: Semantic operator chain with context analysis, returns `RiskItem` objects

The API route `analyze_tender` calls both (line 132: "if rule engine didn't detect, use parser as fallback"), but the two have different keyword lists, different severity mappings, and different context window sizes. This leads to:
- Non-reproducible results depending on which detector fires
- Maintenance burden of keeping two parallel implementations in sync
- Potential for missed detections or false positives

**Recommendation**: Consolidate into a single `RuleEngine.detect_risks()` call. Remove `TenderParser.detect_risks()` or convert it to a thin wrapper. This was not fixed inline because it requires architectural refactoring and test updates.

---

## 3. Additional Issues (Lower Priority)

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 4 | Medium | `similarity_analyzer.py:113` | TF-IDF implementation lacks IDF component -- only computes term frequency, reducing discrimination power |
| 5 | Medium | `similarity_analyzer.py:208` | Bare `except:` clause swallows all exceptions during price extraction |
| 6 | Medium | `tender_parser.py:150` | `np.random.uniform(0, 1)` for z-coordinate makes analysis non-reproducible |
| 7 | Medium | `main.py:234-240` | CORS `allow_origins=["*"]` with credentials is a security vulnerability |
| 8 | Medium | `database.py` | No connection pooling or context manager pattern; leak risk on exceptions |
| 9 | Low | `main.py:167-194` | `compare_bids` generates fake bid data with random values (now fixed) |
| 10 | Low | `tender_parser.py:119` | Unused variable `title_lower` (now fixed) |

---

## 4. Architecture Diagram (As-Is)

```
+-------------------+     +-------------------+     +-------------------+
|  TenderParser     |     |  RuleEngine       |     |  SimilarityAnalyzer|
|  (parse + detect) |     |  (detect + chain) |     |  (TF-IDF + price) |
+--------+----------+     +--------+----------+     +--------+----------+
         |                          |                          |
         v                          v                          v
+------------------------------------------------------------------+
|                    TenderRiskScorer                               |
|  (weighted sum + coupling multiplier + severity mapping)         |
+------------------------------------------------------------------+
         |
         v
+-------------------+     +-------------------+
|  ReportGenerator  |     |  SQLite (DB)      |
|  (JSON + MD)      |     |  (tenders, bids,  |
+-------------------+     |   analysis, audit)|
                          +-------------------+
         ^
         |
+-------------------+
|  FastAPI Routes   |
|  (routes.py +     |
|   main.py inline) |
+-------------------+
```

---

## 5. Fix Verification

The `risk_entropy` fix can be verified by calling the endpoint twice with identical input -- results should now be deterministic:

```bash
# Before fix: two calls return different scores
# After fix: two calls return identical scores

curl -X POST http://localhost:8012/api/v1/risk_entropy \
  -H "Content-Type: application/json" \
  -d '{
    "tender_id": "test-001",
    "document_text": "投标人必须具有甲级资质\n服务器必须是华为品牌",
    "clause_texts": [
      "投标人必须具有甲级资质",
      "服务器必须是华为品牌"
    ]
  }'
```

Expected: `risk_score` is deterministic and reflects actual detected violations (not random values between 0.3-0.95).

---

## 6. Recommendations for Next Sprint

1. **Consolidate risk detection** into `RuleEngine` as single source of truth; deprecate `TenderParser.detect_risks()`
2. **Add IDF component** to TF-IDF similarity calculation for better discrimination
3. **Replace SQLite** with PostgreSQL for production concurrent access
4. **Add authentication** (JWT/OAuth2) and CORS origin whitelist
5. **Add integration tests** for all API endpoints using `httpx.AsyncClient`
6. **Make thresholds configurable** via environment variables or config file
7. **Add async DB operations** using `aiosqlite` (already in requirements)

---

*End of Q2-SCI Review*
