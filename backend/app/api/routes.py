"""
API路由定义
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from datetime import datetime
import json

from ..models.schemas import (
    UploadResponse, HealthResponse, AuditLogEntry,
    TenderAnalysisResult, BidSimilarityResult, RiskReport
)
from ..core.database import get_db_connection, init_db, log_audit
from ..services.tender_parser import TenderParser
from ..services.rule_engine import RuleEngine
from ..services.tender_risk_scorer import TenderRiskScorer
from ..services.similarity_analyzer import SimilarityAnalyzer
from ..services.report_generator import ReportGenerator

router = APIRouter()

# 初始化服务
parser = TenderParser()
rule_engine = RuleEngine()
scorer = TenderRiskScorer()
similarity_analyzer = SimilarityAnalyzer()
report_generator = ReportGenerator()


@router.post("/upload_tender", response_model=UploadResponse)
async def upload_tender(
    name: str = Form(...),
    doc_type: str = Form("tender"),
    file: UploadFile = File(...)
):
    """上传招标文件"""
    try:
        content = await file.read()
        content_text = content.decode("utf-8") if content else ""

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tenders (name, content, doc_type, status)
            VALUES (?, ?, ?, ?)
        """, (name, content_text, doc_type, "uploaded"))

        tender_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log_audit("upload_tender", "tender", tender_id, f"上传招标文件: {name}")

        return UploadResponse(
            success=True,
            message="招标文件上传成功",
            id=tender_id
        )
    except Exception as e:
        return UploadResponse(success=False, message=f"上传失败: {str(e)}")


@router.post("/upload_bids")
async def upload_bids(
    tender_id: int = Form(...),
    files: List[UploadFile] = File(...)
):
    """批量上传投标文件"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查tender是否存在
        cursor.execute("SELECT id FROM tenders WHERE id = ?", (tender_id,))
        if not cursor.fetchone():
            conn.close()
            return {"success": False, "message": "招标文件不存在"}

        uploaded_bids = []
        for file in files:
            content = await file.read()
            content_text = content.decode("utf-8") if content else ""

            # 提取投标人名称（从文件名）
            bidder_name = file.filename.replace(".txt", "").replace(".docx", "").strip()

            cursor.execute("""
                INSERT INTO bids (tender_id, bidder_name, content)
                VALUES (?, ?, ?)
            """, (tender_id, bidder_name, content_text))

            bid_id = cursor.lastrowid
            uploaded_bids.append({
                "id": bid_id,
                "bidder_name": bidder_name
            })

        conn.commit()
        conn.close()

        log_audit("upload_bids", "bids", tender_id, f"上传 {len(files)} 个投标文件")

        return {
            "success": True,
            "message": f"成功上传 {len(files)} 个投标文件",
            "bids": uploaded_bids
        }
    except Exception as e:
        return {"success": False, "message": f"上传失败: {str(e)}"}


@router.post("/analyze_tender")
async def analyze_tender(tender_id: int):
    """分析招标文件的合规性"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,))
        tender = cursor.fetchone()

        if not tender:
            conn.close()
            raise HTTPException(status_code=404, detail="招标文件不存在")

        content = tender["content"]

        # 使用规则引擎检测风险
        risk_items = rule_engine.detect_risks(content)

        # 如果规则引擎没检测到，用parser补充
        if not risk_items:
            risk_items = parser.detect_risks(content)

        # 计算风险熵
        risk_result = scorer.calculate_tender_risk(risk_items)

        # 生成报告
        tender_analysis = {
            "risk_score": risk_result["risk_score"],
            "risk_level": risk_result["risk_level"],
            "risk_items": risk_items,
            "risk_count": len(risk_items),
            "coupling_alerts": risk_result.get("coupling_alerts", []),
            "factor_scores": risk_result.get("factor_scores", {}),
            "summary": f"检测到 {len(risk_items)} 个风险项"
        }

        # 保存分析结果
        cursor.execute("""
            INSERT INTO analysis_results (tender_id, risk_score, risk_level, details_json)
            VALUES (?, ?, ?, ?)
        """, (
            tender_id,
            risk_result["risk_score"],
            risk_result["risk_level"],
            json.dumps(tender_analysis, ensure_ascii=False, default=str)
        ))

        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log_audit("analyze_tender", "analysis", analysis_id, f"分析招标文件 ID={tender_id}")

        return {
            "success": True,
            "analysis_id": analysis_id,
            "tender_id": tender_id,
            "risk_score": risk_result["risk_score"],
            "risk_level": risk_result["risk_level"],
            "risk_items": [
                {
                    "rule_id": r.rule_id,
                    "rule_type": r.rule_type,
                    "risk_name": r.risk_name,
                    "severity": r.severity,
                    "location": {
                        "chapter": r.location.chapter,
                        "line_start": r.location.line_start,
                        "line_end": r.location.line_end,
                        "raw_text": r.location.raw_text[:100]
                    },
                    "evidence": r.evidence,
                    "suggestion": r.suggestion
                }
                for r in risk_items
            ],
            "coupling_alerts": risk_result.get("coupling_alerts", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": f"分析失败: {str(e)}"}


@router.post("/analyze_bids")
async def analyze_bids(tender_id: int):
    """分析投标文件的相似度和围串标风险"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取所有投标文件
        cursor.execute("SELECT * FROM bids WHERE tender_id = ?", (tender_id,))
        bids = cursor.fetchall()

        if len(bids) < 2:
            conn.close()
            return {
                "success": False,
                "message": "需要至少2个投标文件才能进行相似度分析"
            }

        # 转换格式
        bids_data = [
            {
                "id": b["id"],
                "bidder_name": b["bidder_name"],
                "content": b["content"],
                "similarity_score": b.get("similarity_score", 0)
            }
            for b in bids
        ]

        # 获取招标文件内容（用于参考）
        cursor.execute("SELECT content FROM tenders WHERE id = ?", (tender_id,))
        tender = cursor.fetchone()
        tender_content = tender["content"] if tender else ""

        # 执行相似度分析
        similarity_result = similarity_analyzer.analyze_bids(bids_data, tender_content)

        # 获取价格分析
        price_analysis = similarity_result.get("price_analysis", {})

        # 获取主体关联
        entity_connections = similarity_result.get("entity_connections", [])

        # 计算综合风险
        bid_risk_result = scorer.calculate_bid_similarity_risk(
            similarity_result.get("similarity_pairs", []),
            price_analysis,
            entity_connections
        )

        # 更新投标文件的相似度分数
        for bid in bids_data:
            cursor.execute(
                "UPDATE bids SET similarity_score = ? WHERE id = ?",
                (bid.get("similarity_score", 0), bid["id"])
            )

        # 保存分析结果
        cursor.execute("""
            INSERT INTO analysis_results (tender_id, bid_ids, risk_score, risk_level, details_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            tender_id,
            json.dumps([b["id"] for b in bids_data]),
            bid_risk_result["risk_score"],
            bid_risk_result["risk_level"],
            json.dumps(similarity_result, ensure_ascii=False, default=str)
        ))

        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log_audit("analyze_bids", "analysis", analysis_id, f"分析投标相似度 tender_id={tender_id}")

        return {
            "success": True,
            "analysis_id": analysis_id,
            "tender_id": tender_id,
            "total_bids": len(bids),
            "similarity_pairs": similarity_result.get("similarity_pairs", []),
            "price_analysis": price_analysis,
            "entity_connections": entity_connections,
            "overall_risk_score": bid_risk_result["risk_score"],
            "risk_level": bid_risk_result["risk_level"],
            "components": bid_risk_result.get("components", {})
        }
    except Exception as e:
        return {"success": False, "message": f"分析失败: {str(e)}"}


@router.get("/get_risk_report/{tender_id}")
async def get_risk_report(tender_id: int):
    """获取综合风险报告"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取招标文件
        cursor.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,))
        tender = cursor.fetchone()
        if not tender:
            conn.close()
            raise HTTPException(status_code=404, detail="招标文件不存在")

        # 获取分析结果
        cursor.execute("""
            SELECT * FROM analysis_results
            WHERE tender_id = ?
            ORDER BY created_at DESC
        """, (tender_id,))
        analysis_results = cursor.fetchall()
        conn.close()

        if not analysis_results:
            return {
                "success": False,
                "message": "请先执行分析（/analyze_tender 和 /analyze_bids）"
            }

        # 构建综合报告
        tender_analysis_data = None
        bid_analysis_data = None

        for result in analysis_results:
            details = json.loads(result["details_json"] or "{}")
            if "risk_items" in details:  # 招标文件分析
                tender_analysis_data = details
            else:  # 投标分析
                bid_analysis_data = details

        # 生成综合报告
        final_risk_score = 0.0
        final_risk_level = "green"

        if tender_analysis_data and bid_analysis_data:
            final_risk_score = report_generator._calculate_final_risk(
                tender_analysis_data.get("risk_score", 0),
                bid_analysis_data.get("overall_risk", bid_analysis_data.get("risk_score", 0))
            )
            final_risk_level = report_generator._score_to_level(final_risk_score)

        # 生成完整报告
        report = {
            "tender_id": tender_id,
            "tender_name": tender["name"],
            "generated_at": datetime.now().isoformat(),
            "tender_analysis": {
                "risk_score": tender_analysis_data.get("risk_score", 0) if tender_analysis_data else 0,
                "risk_level": tender_analysis_data.get("risk_level", "green") if tender_analysis_data else "green",
                "risk_count": tender_analysis_data.get("risk_count", 0) if tender_analysis_data else 0,
                "risk_items": tender_analysis_data.get("risk_items", []) if tender_analysis_data else [],
                "coupling_alerts": tender_analysis_data.get("coupling_alerts", []) if tender_analysis_data else []
            },
            "bid_analysis": {
                "total_bids": len(bid_analysis_data.get("bids", [])) if bid_analysis_data else 0,
                "similarity_pairs": bid_analysis_data.get("similarity_pairs", []) if bid_analysis_data else [],
                "price_analysis": bid_analysis_data.get("price_analysis", {}) if bid_analysis_data else {},
                "entity_connections": bid_analysis_data.get("entity_connections", []) if bid_analysis_data else [],
                "overall_risk_score": bid_analysis_data.get("overall_risk", 0) if bid_analysis_data else 0,
                "risk_level": bid_analysis_data.get("risk_level", "green") if bid_analysis_data else "green"
            },
            "final_risk_score": final_risk_score,
            "final_risk_level": final_risk_level,
            "radar_data": {
                "surround_bid_risk": bid_analysis_data.get("overall_risk", 0) * 100 if bid_analysis_data else 0,
                "exclusive_risk": tender_analysis_data.get("risk_score", 0) * 100 if tender_analysis_data else 0,
                "scoring_anomaly": tender_analysis_data.get("factor_scores", {}).get("unclear_scoring", 0) * 100 if tender_analysis_data else 0,
                "entity_connection": len(bid_analysis_data.get("entity_connections", [])) * 20 if bid_analysis_data else 0
            }
        }

        return report
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": f"获取报告失败: {str(e)}"}


@router.get("/audit_logs", response_model=List[AuditLogEntry])
async def get_audit_logs(limit: int = 50):
    """获取审计日志"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM audit_logs
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    logs = cursor.fetchall()
    conn.close()

    return [
        AuditLogEntry(
            id=log["id"],
            action=log["action"],
            target_type=log["target_type"],
            target_id=log["target_id"],
            details=log["details"],
            created_at=log["created_at"]
        )
        for log in logs
    ]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@router.get("/rules")
async def get_rules():
    """获取规则列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules WHERE enabled = 1")
    rules = cursor.fetchall()
    conn.close()

    return {
        "success": True,
        "rules": [
            {
                "id": r["id"],
                "rule_id": r["rule_id"],
                "rule_type": r["rule_type"],
                "description": r["description"],
                "severity": r["severity"],
                "penalty": r["penalty"]
            }
            for r in rules
        ]
    }


@router.get("/tenders")
async def list_tenders():
    """获取招标文件列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tenders ORDER BY upload_time DESC")
    tenders = cursor.fetchall()
    conn.close()

    return {
        "success": True,
        "tenders": [
            {
                "id": t["id"],
                "name": t["name"],
                "doc_type": t["doc_type"],
                "upload_time": t["upload_time"],
                "status": t["status"]
            }
            for t in tenders
        ]
    }


@router.get("/bids/{tender_id}")
async def get_bids(tender_id: int):
    """获取某招标项目的投标文件列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bids WHERE tender_id = ?", (tender_id,))
    bids = cursor.fetchall()
    conn.close()

    return {
        "success": True,
        "bids": [
            {
                "id": b["id"],
                "bidder_name": b["bidder_name"],
                "similarity_score": b["similarity_score"],
                "upload_time": b["upload_time"]
            }
            for b in bids
        ]
    }