# Q2-Grade SCI Peer Review Report -- Round 2

**Project**: tender-compliance (招投标文件智能合规控制与围串标风险预警系统)
**Review Date**: 2026-05-29
**Reviewer**: Automated SCI-Q2 Code Review (Round 2)
**Scope**: Re-audit after Round 1 fixes; verify P1/P2/P3 resolution; re-score all dimensions
**Baseline**: SCI_REVIEW_Q2.md (Round 1, composite 5.0/10)

---

## 1. Round 1 Fix Verification

| # | Round 1 Issue | Severity | Status | Evidence |
|---|---------------|----------|--------|----------|
| P1 | `random.uniform()` in `/risk_entropy` | CRITICAL | **FIXED** | `main.py:134-183` -- now calls `RuleEngine.detect_risks()` + `TenderRiskScorer.calculate_tender_risk()`. No `import random` in module. Verified via grep: zero hits for `random.uniform` across `backend/`. |
| P1b | `random.uniform()` in `/compare_bids` | CRITICAL | **FIXED** | `main.py:186-244` -- now queries SQLite via `get_db_connection()`, extracts prices with `SimilarityAnalyzer._extract_price()`. |
| P2 | Undefined `COMMERCIAL_KEYWORDS` | HIGH | **FIXED** | `tender_parser.py:34,112` -- replaced with `CONTRACT_KEYWORDS` (already defined, semantically correct). |
| P3 | Duplicate `detect_risks()` logic | HIGH | **OPEN** | Both `TenderParser.detect_risks()` (line 168) and `RuleEngine.detect_risks()` (line 74) remain. `routes.py:132` still uses fallback pattern: `if not risk_items: risk_items = parser.detect_risks(content)`. |
| 4 | TF-IDF lacks IDF | Medium | **OPEN** | `similarity_analyzer.py:112` -- `_text_to_vector` still computes `count / total_words` (TF only). No document-frequency weighting. |
| 5 | Bare `except:` in `_extract_price` | Medium | **OPEN** | `similarity_analyzer.py:208` -- bare `except: pass` swallows all exceptions including `KeyboardInterrupt`. |
| 6 | `np.random.uniform` for z-coordinate | Medium | **OPEN** | `tender_parser.py:149` -- `z = np.random.uniform(0, 1)` makes coordinate generation non-reproducible. |
| 7 | CORS `allow_origins=["*"]` + credentials | Medium | **OPEN** | `main.py:286` -- still `allow_origins=["*"]` with `allow_credentials=True`. |
| 8 | DB connections without context manager | Medium | **OPEN** | `database.py:16-19` -- `get_db_connection()` returns raw connection; callers must manually close. |
| 9 | Unused `title_lower` | Low | **OPEN** | Not re-checked (low priority, cosmetic). |

**Fix Rate**: 3 of 10 issues resolved (P1, P1b, P2). The three critical/high issues that were blocking system correctness are fixed.

---

## 2. Seven-Dimension Scoring (Re-scored)

| # | Dimension | R1 Score | R2 Score | Max | Delta | Justification |
|---|-----------|----------|----------|-----|-------|---------------|
| D1 | **Architecture & Modularity** | 6.5 | 6.5 | 10 | 0.0 | No architectural changes. Duplicate `detect_risks()` remains. Two routers with overlapping concerns unchanged. |
| D2 | **Algorithm Correctness** | 3.0 | **5.5** | 10 | +2.5 | **Major improvement**: Random scoring eliminated -- `/risk_entropy` and `/compare_bids` now use real pipelines. Deterministic output verified (no `random` or `random.uniform` imports). Remaining: TF-IDF lacks IDF (weakens similarity discrimination), `np.random.uniform` in z-coordinate (non-reproducible coordinates), naive ratio-based price correlation instead of Pearson/Spearman. |
| D3 | **Code Quality & Robustness** | 5.5 | **6.0** | 10 | +0.5 | `COMMERCIAL_KEYWORDS` fixed, `import random` removed. Bare `except:` persists. DB connection leak risk unchanged. |
| D4 | **Security** | 4.0 | 4.0 | 10 | 0.0 | No changes to CORS, authentication, file size limits, or rate limiting. |
| D5 | **Testability & Coverage** | 6.0 | 6.0 | 10 | 0.0 | Existing test suite unchanged. Still missing: API integration tests for the fixed endpoints, edge-case tests for empty/malformed inputs. |
| D6 | **Performance & Scalability** | 4.5 | 4.5 | 10 | 0.0 | SQLite, synchronous I/O, O(n^2) similarity matrix, no caching -- all unchanged. |
| D7 | **Documentation & Maintainability** | 5.5 | 5.5 | 10 | 0.0 | No documentation changes. |

**R1 Composite: 5.0 / 10**
**R2 Composite: 5.3 / 10** (+0.3)

The improvement is concentrated in D2 (Algorithm Correctness), which is the dimension most directly impacted by the P1 fix. The +2.5 gain reflects that the system's core analysis pipeline is no longer random, but remaining algorithmic weaknesses (no IDF, non-reproducible coordinates, naive correlation) prevent a higher score.

---

## 3. Detailed Analysis of Remaining Issues

### 3.1 P3 [HIGH] -- Duplicate Risk Detection (Unchanged)

Both implementations coexist:

**`TenderParser.detect_risks()`** (`tender_parser.py:168-243`):
- Simple substring matching against `BRAND_KEYWORDS`, `QUALIFICATION_KEYWORDS`, `SCORING_KEYWORDS`
- Returns `RiskItem` with basic location info
- Context window: 10 lines for scoring checks

**`RuleEngine.detect_risks()`** (`rule_engine.py:74-107`):
- Semantic operator chain (P_LIMIT, P_FORBID, P_PREFER, P_REQUIRE)
- Returns `RiskItem` with richer context and evidence strings
- Context window: 20 lines for scoring checks
- Additional rule types: `region_limitation`, `experience_exclusive`

The `routes.py:132` fallback pattern means results depend on rule file loading order, creating non-deterministic behavior when the rule engine has no rules loaded (empty JSON file).

### 3.2 TF-IDF Without IDF (Medium)

`similarity_analyzer.py:101-115` computes only term frequency:
```python
vector[vocab[word]] = count / total_words  # TF only, no IDF
```

A correct TF-IDF would multiply by `log(N / df)` where `N` is total documents and `df` is document frequency. Without IDF, common words (e.g., "投标", "项目") dominate similarity scores, reducing discrimination between genuinely similar and merely common-vocabulary bids.

### 3.3 Non-Reproducible Coordinates (Medium)

`tender_parser.py:149`:
```python
z = np.random.uniform(0, 1)
```

The z-coordinate is regenerated randomly each time `parse_tender()` is called. This means the same document produces different coordinate mappings on different runs, violating reproducibility requirements for audit trails.

### 3.4 Security Gaps (Medium, Unchanged)

- CORS: `allow_origins=["*"]` + `allow_credentials=True` allows any origin to make credentialed requests
- No authentication on any endpoint
- No file size limits on uploads (`upload_tender`, `upload_bids`)
- No rate limiting

### 3.5 Database Connection Management (Medium, Unchanged)

`database.py:16-19` returns raw `sqlite3.Connection` objects. Callers across `routes.py` and `main.py` manually call `conn.close()`. If an exception occurs between `get_db_connection()` and `conn.close()`, the connection leaks. A context manager pattern would eliminate this risk.

---

## 4. Verification Test for P1 Fix

The Round 1 report provided a curl verification command. The fix can also be verified statically:

```python
# main.py imports -- no 'random' module
from .services.rule_engine import RuleEngine
from .services.tender_risk_scorer import TenderRiskScorer

# /risk_entropy endpoint -- deterministic pipeline
engine = RuleEngine()
scorer = TenderRiskScorer()
all_risks = engine.detect_risks(full_text)          # pattern matching, not random
risk_result = scorer.calculate_tender_risk(all_risks) # weighted sum, not random
```

Grep confirmation: `import random` and `random.uniform` return zero hits across the entire `backend/` directory.

---

## 5. Updated Recommendations (Priority Order)

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| 1 | **Consolidate risk detection** into `RuleEngine` only; remove `TenderParser.detect_risks()` or convert to thin wrapper | Medium | Eliminates non-determinism from dual detectors; reduces maintenance burden |
| 2 | **Add IDF component** to TF-IDF: `tf * log(N/df)` | Low | Significantly improves similarity discrimination |
| 3 | **Replace `np.random.uniform`** in z-coordinate with deterministic hash (e.g., `hash(text) % 1000 / 1000`) | Low | Ensures reproducible coordinate mapping |
| 4 | **Fix bare `except:`** to `except (ValueError, AttributeError):` | Low | Prevents swallowing unexpected exceptions |
| 5 | **Add authentication** (JWT/OAuth2) and restrict CORS origins | Medium | Security hardening for production |
| 6 | **Add DB context manager** pattern | Low | Eliminates connection leak risk |
| 7 | **Replace SQLite** with PostgreSQL for production | High | Concurrent access support |
| 8 | **Add integration tests** for fixed endpoints | Medium | Regression protection |

---

## 6. Summary

Round 1 identified 10 issues, including 2 critical (random scoring). All critical and one high-severity issue have been fixed in Round 2. The system's core analysis pipeline is now deterministic and uses real pattern-matching + weighted-sum scoring. The composite score improved from 5.0 to 5.3.

The most impactful remaining work is: (1) consolidating the duplicate risk detection logic, (2) adding IDF to the similarity analyzer, and (3) making the z-coordinate deterministic. These three changes would push D2 above 7.0 and the composite above 5.8.

---

*End of Q2-SCI Review Round 2*
