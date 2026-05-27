# 招标合规分析 API 文档

> 生成时间: 2026-05-17
> 基础路径: `/api/v1`
> 服务端口: 8012

---

## 基础信息

| 项目 | 说明 |
|------|------|
| 标题 | 招投标文件智能合规控制与围串标风险预警系统 |
| 版本 | 1.0.0 |
| 文档地址 | `/docs` (Swagger UI) |
| API 基础路径 | `/api/v1` |

---

## 端点总览

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/analyze_bid` | 综合投标分析（含价格偏离检测） |
| POST | `/detect_collusion_markers` | 围串标标记检测 |
| POST | `/risk_entropy` | 招标文件风险熵评分 |
| GET | `/compare_bids` | 投标方案对比 |

---

## 1. POST `/analyze_bid`

综合投标分析，计算各投标人的价格偏离度、技术评分、综合排名，并标记异常报价。

### Request

```json
{
  "tender_id": "T2024001",
  "bids": [
    {
      "bidder": "投标方A",
      "price": 95.50,
      "technical_score": 88.5,
      "submitted_at": "2024-03-15 10:00:00"
    },
    {
      "bidder": "投标方B",
      "price": 102.30,
      "technical_score": 91.0,
      "submitted_at": "2024-03-15 10:05:00"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tender_id | string | ✅ | 招标项目编号 |
| bids | array | ✅ | 投标列表 |
| bids[].bidder | string | ✅ | 投标人名称 |
| bids[].price | float | ✅ | 投标报价 |
| bids[].technical_score | float | ✅ | 技术评分（0-100） |
| bids[].submitted_at | string | ❌ | 提交时间 |

### Response

```json
{
  "tender_id": "T2024001",
  "total_bids": 2,
  "mean_price": 98.9,
  "winner": {
    "bidder": "投标方A",
    "price": 95.5,
    "price_deviation_pct": -3.44,
    "price_score": 93.12,
    "technical_score": 88.5,
    "comprehensive_score": 90.35,
    "rank": 1
  },
  "suspicious_bids": [],
  "analysis_time": "2026-05-17T20:46:00.000000"
}
```

### 评分规则

- **价格分** = max(0, 100 - |价格偏离%| × 2)
- **综合分** = 价格分 × 0.4 + 技术分 × 0.6
- **异常报价阈值**: |价格偏离%| > 30% 标记为可疑

---

## 2. POST `/detect_collusion_markers`

检测围串标行为标记，综合分析价格相关性、相同小数位、提交模式等指标。

### Request

```json
{
  "tender_id": "T2024001",
  "bids": [
    { "bidder": "投标方A", "price": 100.1234, "submitted_at": "2024-03-15 10:00:00" },
    { "bidder": "投标方B", "price": 100.1234, "submitted_at": "2024-03-15 10:05:00" },
    { "bidder": "投标方C", "price": 100.1234, "submitted_at": "2024-03-15 10:10:00" }
  ],
  "market_context": "本地中小企业参与"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tender_id | string | ✅ | 招标项目编号 |
| bids | array | ✅ | 投标列表 |
| market_context | string | ❌ | 市场背景描述（用于辅助分析） |

### 围串标检测标记

| 标记类型 | 严重程度 | 说明 |
|----------|----------|------|
| `identical_decimals` | high | 所有报价使用相同小数位（如均为 100.1234），高度可疑 |
| `price_clustering` | medium | 多对报价极为接近（价差 < 2%），可能存在围标 |
| `irregular_intervals` | high | 报价间隔极不规律，增量梯度异常，暗示协调定价 |
| `herd_pricing` | medium | 多处出现极小价格差（< 1%），步进式报价 |

### Response

```json
{
  "tender_id": "T2024001",
  "markers": [
    {
      "type": "identical_decimals",
      "severity": "high",
      "detail": "All bids use same decimal: 0.1234"
    }
  ],
  "collusion_probability": 0.4,
  "recommendation": "normal_monitoring"
}
```

### 围串标概率计算

```
collusion_probability = min(0.95, high_count × 0.4 + medium_count × 0.2)
```

| 概率范围 | 建议操作 |
|----------|----------|
| > 0.6 | `refer_investigation` — 转交调查 |
| ≤ 0.6 | `normal_monitoring` — 正常监控 |

---

## 3. POST `/risk_entropy`

对招标文件各条款进行风险熵评分，识别高风险条款。

### Request

```json
{
  "tender_id": "T2024001",
  "document_text": "招标文件完整文本内容...",
  "clause_texts": [
    "合同金额超过预算200%时须经董事会审批",
    "中标人不得将合同分包给第三方",
    "甲方有权单方面解除合同且无需赔偿"
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tender_id | string | ✅ | 招标项目编号 |
| document_text | string | ✅ | 招标文件完整文本 |
| clause_texts | array[string] | ✅ | 待检测的条款文本列表 |

### 风险类型分类

| 风险类型 | 说明 |
|----------|------|
| 高金额条款偏离 | 合同金额严重偏离市场水平 |
| 排他性条款 | 指定特定品牌或供应商 |
| 模糊履约标准 | 验收标准不明确 |
| 单方面终止权 | 甲方可无故终止合同 |
| 过高违约金 | 违约金设置不合理 |
| 正常条款 / 合理条款 | 无明显风险 |

### Response

```json
{
  "tender_id": "T2024001",
  "clause_count": 3,
  "overall_risk": 0.623,
  "high_risk_clauses": [
    {
      "clause_id": 3,
      "clause_preview": "甲方有权单方面解除合同且无需赔偿",
      "risk_score": 0.871,
      "risk_type": "单方面终止权"
    }
  ],
  "risk_distribution": {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 0
  }
}
```

### 风险等级分布

| 等级 | 风险分区间 | 说明 |
|------|-----------|------|
| critical | > 0.8 | 严重风险 |
| high | 0.6 ~ 0.8 | 高风险 |
| medium | 0.4 ~ 0.6 | 中风险 |
| low | ≤ 0.4 | 低风险 |

---

## 4. GET `/compare_bids`

对比selected投标方案，返回价格偏离统计和技术排名。

### Request

```
GET /compare_bids?tender_id=T2024001&bid_ids=bid001,bid002,bid003
```

### Query 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tender_id | string | ✅ | 招标项目编号 |
| bid_ids | string | ✅ | 逗号分隔的投标ID列表 |

### Response

```json
{
  "tender_id": "T2024001",
  "comparison": [
    {
      "bidder": "投标方2",
      "price": 118.32,
      "technical_score": 94.1,
      "deviation_from_mean": 15.42
    },
    {
      "bidder": "投标方1",
      "price": 98.75,
      "technical_score": 89.5,
      "deviation_from_mean": -3.77
    }
  ],
  "price_statistics": {
    "min": 82.15,
    "max": 119.80,
    "mean": 100.15,
    "std_dev": 15.62
  }
}
```

---

## 错误响应格式

所有端点均使用标准 HTTP 状态码。错误响应格式：

```json
{
  "detail": "错误描述信息"
}
```

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |

---

## 调用示例

### cURL

```bash
# 综合投标分析
curl -X POST http://localhost:8012/api/v1/analyze_bid \
  -H "Content-Type: application/json" \
  -d '{"tender_id": "T2024001", "bids": [{"bidder": "A", "price": 100, "technical_score": 85}]}'

# 围串标检测
curl -X POST http://localhost:8012/api/v1/detect_collusion_markers \
  -H "Content-Type: application/json" \
  -d '{"tender_id": "T2024001", "bids": [{"bidder": "A", "price": 100.1234}]}'

# 风险熵评分
curl -X POST http://localhost:8012/api/v1/risk_entropy \
  -H "Content-Type: application/json" \
  -d '{"tender_id": "T2024001", "document_text": "...", "clause_texts": ["条款1", "条款2"]}'

# 对比投标
curl "http://localhost:8012/api/v1/compare_bids?tender_id=T2024001&bid_ids=a,b,c"
```

### Python

```python
import requests

BASE = "http://localhost:8012/api/v1"

# 投标分析
resp = requests.post(f"{BASE}/analyze_bid", json={
    "tender_id": "T2024001",
    "bids": [
        {"bidder": "A", "price": 95.5, "technical_score": 88.5},
        {"bidder": "B", "price": 102.3, "technical_score": 91.0}
    ]
})
print(resp.json())
```

---

## 完整文件路径

| 文件 | 路径 |
|------|------|
| 主程序 | `D:\ZYY Project\tender-compliance\backend\app\main.py` |
| API 文档 | `D:\ZYY Project\tender-compliance\backend\API_DOC.md` |