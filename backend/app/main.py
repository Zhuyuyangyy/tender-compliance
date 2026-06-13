"""
招投标文件智能合规控制与围串标风险预警系统
主程序入口
"""
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from datetime import datetime
import uvicorn
import json

from .core.database import init_db
from .api.routes import router
from .services.rule_engine import RuleEngine
from .services.tender_risk_scorer import TenderRiskScorer


# ============================================================
# 招标合规分析专用端点
# ============================================================
compliance_router = APIRouter(prefix="/api/v1", tags=["招标合规分析"])

# ---- Request Models ----

class BidAnalysisRequest(BaseModel):
    tender_id: str
    bids: List[Dict]  # [{"bidder": str, "price": float, "technical_score": float, "submitted_at": str}]

class CollusionMarkerRequest(BaseModel):
    tender_id: str
    bids: List[Dict]
    market_context: Optional[str] = ""

class RiskEntropyRequest(BaseModel):
    tender_id: str
    document_text: str
    clause_texts: List[str]

class CompareBidsRequest(BaseModel):
    tender_id: str
    bid_ids: List[str]


# ---- Endpoints ----

@compliance_router.post("/analyze_bid")
async def analyze_bid(req: BidAnalysisRequest):
    """Comprehensive bid analysis with price deviation detection"""
    prices = [b["price"] for b in req.bids]
    mean_price = sum(prices) / len(prices)
    results = []
    for b in req.bids:
        deviation = round((b["price"] - mean_price) / mean_price * 100, 2) if mean_price > 0 else 0
        price_score = round(max(0, 100 - abs(deviation) * 2), 1)
        results.append({
            "bidder": b["bidder"],
            "price": b["price"],
            "price_deviation_pct": deviation,
            "price_score": price_score,
            "technical_score": b.get("technical_score", 0),
            "comprehensive_score": round(price_score * 0.4 + b.get("technical_score", 0) * 0.6, 2),
            "rank": 0  # filled below
        })
    results.sort(key=lambda x: x["comprehensive_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    winner = results[0] if results else None
    suspicious = [r for r in results if abs(r["price_deviation_pct"]) > 30]
    return {
        "tender_id": req.tender_id,
        "total_bids": len(req.bids),
        "mean_price": round(mean_price, 2),
        "winner": winner,
        "suspicious_bids": suspicious,
        "analysis_time": datetime.now().isoformat()
    }


@compliance_router.post("/detect_collusion_markers")
async def detect_collusion_markers(req: CollusionMarkerRequest):
    """Detect collusion markers: price correlation, identical decimals, submission patterns"""
    prices = [b["price"] for b in req.bids]
    markers = []
    # Marker 1: Identical decimal patterns
    decimals = [round(p % 1, 4) for p in prices]
    if len(set(decimals)) == 1 and decimals[0] != 0:
        markers.append({
            "type": "identical_decimals",
            "severity": "high",
            "detail": f"All bids use same decimal: {decimals[0]}"
        })
    # Marker 2: Price clustering (too close)
    prices_sorted = sorted(prices)
    clusters = sum(1 for i in range(len(prices_sorted)-1) if prices_sorted[i+1] / prices_sorted[i] < 1.02)
    if clusters > len(prices) // 2:
        markers.append({
            "type": "price_clustering",
            "severity": "medium",
            "detail": f"{clusters} pairs of suspiciously close bids"
        })
    # Marker 3: Bid intervals
    intervals = [prices_sorted[i+1] - prices_sorted[i] for i in range(len(prices_sorted)-1)]
    if intervals and max(intervals) / (min(intervals) + 0.01) > 50:
        markers.append({
            "type": "irregular_intervals",
            "severity": "high",
            "detail": "Irregular bid increments suggest coordination"
        })
    # Marker 4: N-brand price correlation
    if len(prices) >= 3:
        corr = sum(1 for i in range(len(prices)-1) if (prices[i+1] - prices[i]) / (prices[i] + 0.01) < 0.01)
        if corr > len(prices) // 3:
            markers.append({
                "type": "herd_pricing",
                "severity": "medium",
                "detail": f"{corr} near-identical price steps"
            })
    collusion_probability = round(
        min(0.95,
            sum(1 for m in markers if m["severity"] == "high") * 0.4 +
            sum(1 for m in markers if m["severity"] == "medium") * 0.2
        ), 3
    )
    return {
        "tender_id": req.tender_id,
        "markers": markers,
        "collusion_probability": collusion_probability,
        "recommendation": "refer_investigation" if collusion_probability > 0.6 else "normal_monitoring"
    }


@compliance_router.post("/risk_entropy")
async def risk_entropy(req: RiskEntropyRequest):
    """Risk entropy scoring for tender documents using RuleEngine + TenderRiskScorer"""
    engine = RuleEngine()
    scorer = TenderRiskScorer()

    # Build full document text from clauses for rule engine analysis
    full_text = req.document_text if req.document_text else "\n".join(req.clause_texts)

    # Detect risks using the rule engine on full document
    all_risks = engine.detect_risks(full_text)

    # Score each clause individually
    results = []
    for i, clause in enumerate(req.clause_texts):
        clause_risks = engine.detect_risks(clause)
        if clause_risks:
            # Use actual risk scores from detected violations
            severity_scores = scorer._severity_to_score(clause_risks[0].severity)
            risk_type = clause_risks[0].risk_name
        else:
            severity_scores = 0.0
            risk_type = "正常条款"
        results.append({
            "clause_id": i + 1,
            "clause_preview": clause[:50],
            "risk_score": round(severity_scores, 3),
            "risk_type": risk_type
        })

    # Calculate overall risk using the scorer on all detected risks
    risk_result = scorer.calculate_tender_risk(all_risks)
    overall = risk_result["risk_score"]

    high_risk = [r for r in results if r["risk_score"] > 0.6]
    return {
        "tender_id": req.tender_id,
        "clause_count": len(results),
        "overall_risk": overall,
        "risk_level": risk_result["risk_level"],
        "coupling_multiplier": risk_result.get("coupling_multiplier", 1.0),
        "coupling_alerts": risk_result.get("coupling_alerts", []),
        "high_risk_clauses": high_risk,
        "risk_distribution": {
            "critical": sum(1 for r in results if r["risk_score"] > 0.8),
            "high": sum(1 for r in results if 0.6 < r["risk_score"] <= 0.8),
            "medium": sum(1 for r in results if 0.4 < r["risk_score"] <= 0.6),
            "low": sum(1 for r in results if r["risk_score"] <= 0.4)
        }
    }


@compliance_router.get("/compare_bids")
async def compare_bids(tender_id: str, bid_ids: str):
    """Compare selected bids with price deviation and statistics from database"""
    from .core.database import get_db_connection
    from .services.similarity_analyzer import SimilarityAnalyzer

    bid_list = [int(bid_id.strip()) for bid_id in bid_ids.split(",") if bid_id.strip()]
    if not bid_list:
        return {"success": False, "message": "No valid bid IDs provided"}

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch actual bid data from database
    placeholders = ",".join("?" * len(bid_list))
    cursor.execute(f"SELECT id, bidder_name, content FROM bids WHERE id IN ({placeholders})", bid_list)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"success": False, "message": "No bids found for given IDs"}

    analyzer = SimilarityAnalyzer()
    bids = []
    for row in rows:
        content = row["content"]
        price = analyzer._extract_price(content)
        bids.append({
            "bid_id": row["id"],
            "bidder": row["bidder_name"],
            "price": price,
            "content_preview": content[:200]
        })

    prices = [b["price"] for b in bids if b["price"] > 0]
    if not prices:
        return {"success": False, "message": "Could not extract prices from bid documents"}

    mean_price = sum(prices) / len(prices)
    for b in bids:
        if b["price"] > 0 and mean_price > 0:
            b["deviation_from_mean"] = round((b["price"] - mean_price) / mean_price * 100, 2)
        else:
            b["deviation_from_mean"] = 0.0

    bids_sorted = sorted(bids, key=lambda x: x.get("deviation_from_mean", 0), reverse=True)

    return {
        "tender_id": tender_id,
        "comparison": bids_sorted,
        "price_statistics": {
            "min": min(prices),
            "max": max(prices),
            "mean": round(mean_price, 2),
            "std_dev": round(
                (sum((p - mean_price) ** 2 for p in prices) / len(prices)) ** 0.5, 2
            )
        }
    }


# ============================================================
# FastAPI App
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("[System] 初始化数据库...")
    init_db()
    print("[System] 系统启动完成")
    yield
    print("[System] 系统关闭")


app = FastAPI(
    title="招投标文件智能合规控制与围串标风险预警系统",
    description="""
    ## 系统功能

    1. **招标文件结构解析** - 虚拟条款坐标映射，检测隐性风险
    2. **围串标风险识别** - 投标文件语义相似度检测
    3. **风险熵评分** - 多维风险耦合模型，非线性熔断机制
    4. **规则引擎** - 检测限定品牌、排他资质、倾向性评分等
    5. **合规报告生成** - 全链路审计，整改建议

    ## 专利技术

    - 一种基于虚拟条款坐标的招标文件合规检测方法
    - 一种基于投标主体关系图谱的围串标风险识别方法
    - 一种基于语义算子链的招标评分条款倾向性检测方法
    - 一种基于风险熵的招投标异常行为分级预警方法
    """,
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册原有路由
app.include_router(router, prefix="/api", tags=["招投标合规分析"])

# 注册招标合规分析路由
app.include_router(compliance_router)


@app.get("/")
async def root():
    """系统根路径"""
    return {
        "name": "招投标文件智能合规控制与围串标风险预警系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "api": "/api"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8012,
        reload=False,
        log_level="info"
    )