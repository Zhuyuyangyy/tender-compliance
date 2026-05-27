"""
数据库初始化模块
使用SQLite存储招投标数据
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "tender_compliance.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 规则表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT UNIQUE NOT NULL,
            rule_type TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL,
            penalty TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 招标文件表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)

    # 投标文件表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER NOT NULL,
            bidder_name TEXT NOT NULL,
            content TEXT NOT NULL,
            similarity_score REAL DEFAULT 0.0,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tender_id) REFERENCES tenders(id)
        )
    """)

    # 分析结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER,
            bid_ids TEXT,
            risk_score REAL DEFAULT 0.0,
            risk_level TEXT DEFAULT 'green',
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tender_id) REFERENCES tenders(id)
        )
    """)

    # 审计日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 插入默认规则
    default_rules = [
        {
            "rule_id": "RULE_T_001",
            "rule_type": "exclusive_brand",
            "description": "限定品牌或供应商（歧视性条款）",
            "severity": "high",
            "penalty": "修改招标文件，取消限制性描述"
        },
        {
            "rule_id": "RULE_T_002",
            "rule_type": "exclusive_qualification",
            "description": "排他性资质要求",
            "severity": "high",
            "penalty": "删除排他性资质条款"
        },
        {
            "rule_id": "RULE_T_003",
            "rule_type": "unclear_scoring",
            "description": "评分标准不透明",
            "severity": "medium",
            "penalty": "明确评分标准和权重"
        },
        {
            "rule_id": "RULE_T_004",
            "rule_type": "bid_similarity",
            "description": "投标文件高度相似（围标检测）",
            "severity": "critical",
            "penalty": "标记为高风险，提交人工复核"
        },
        {
            "rule_id": "RULE_T_005",
            "rule_type": "entity_connection",
            "description": "多家公司IP/联系人异常",
            "severity": "critical",
            "penalty": "标记关联关系，提交人工复核"
        },
        {
            "rule_id": "RULE_T_006",
            "rule_type": "price_anomaly",
            "description": "报价规律异常",
            "severity": "high",
            "penalty": "分析报价曲线，标记异常"
        },
        {
            "rule_id": "RULE_T_007",
            "rule_type": "audit_trail",
            "description": "评标过程缺乏可追溯审计",
            "severity": "medium",
            "penalty": "完善评标记录和审计追踪"
        }
    ]

    for rule in default_rules:
        cursor.execute("""
            INSERT OR IGNORE INTO rules (rule_id, rule_type, description, severity, penalty)
            VALUES (?, ?, ?, ?, ?)
        """, (rule["rule_id"], rule["rule_type"], rule["description"], rule["severity"], rule["penalty"]))

    conn.commit()
    conn.close()
    print(f"[DB] 数据库初始化完成: {DB_PATH}")


def log_audit(action: str, target_type: str, target_id: int = None, details: str = None):
    """记录审计日志"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (action, target_type, target_id, details)
        VALUES (?, ?, ?, ?)
    """, (action, target_type, target_id, details))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()