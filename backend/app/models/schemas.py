"""
Pydantic数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class RuleBase(BaseModel):
    rule_id: str
    rule_type: str
    description: str
    severity: str
    penalty: Optional[str] = None


class RuleCreate(RuleBase):
    pass


class RuleResponse(RuleBase):
    id: int
    enabled: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TenderBase(BaseModel):
    name: str
    content: str
    doc_type: str = "tender"


class TenderCreate(TenderBase):
    pass


class TenderResponse(TenderBase):
    id: int
    upload_time: Optional[datetime] = None
    status: str = "pending"

    class Config:
        from_attributes = True


class BidBase(BaseModel):
    bidder_name: str
    content: str


class BidCreate(BidBase):
    tender_id: int


class BidResponse(BidBase):
    id: int
    tender_id: int
    similarity_score: float
    upload_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClauseLocation(BaseModel):
    """条款坐标位置"""
    chapter: Optional[str] = None
    section: Optional[str] = None
    paragraph: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    raw_text: str


class RiskItem(BaseModel):
    """风险项"""
    rule_id: str
    rule_type: str
    risk_name: str
    severity: str
    location: ClauseLocation
    evidence: str
    suggestion: str


class TenderAnalysisResult(BaseModel):
    """招标文件分析结果"""
    tender_id: int
    risk_score: float
    risk_level: str  # green, yellow, red
    risk_items: List[RiskItem]
    summary: str


class BidSimilarityResult(BaseModel):
    """投标文件相似度分析结果"""
    tender_id: int
    total_bids: int
    similarity_pairs: List[Dict[str, Any]]
    price_curve_analysis: Dict[str, Any]
    entity_connections: List[Dict[str, Any]]
    overall_risk_score: float
    risk_level: str


class RiskReport(BaseModel):
    """综合风险报告"""
    tender_id: int
    tender_analysis: TenderAnalysisResult
    bid_analysis: BidSimilarityResult
    final_risk_score: float
    final_risk_level: str
    generated_at: datetime = Field(default_factory=datetime.now)


class AuditLogEntry(BaseModel):
    """审计日志条目"""
    id: int
    action: str
    target_type: str
    target_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    success: bool
    message: str
    id: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime