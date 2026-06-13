# API Documentation

## Base URL

```
http://localhost:8012
```

## Authentication

Currently no authentication is required. For production deployment, add JWT or API key authentication.

---

## Endpoints

### Health Check

```
GET /api/health
```

Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-05-29T00:00:00"
}
```

---

### Upload Tender Document

```
POST /api/upload_tender
Content-Type: multipart/form-data
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Tender project name |
| doc_type | string | No | Document type (default: "tender") |
| file | file | Yes | Tender document file |

**Response:**
```json
{
  "success": true,
  "message": "招标文件上传成功",
  "id": 1
}
```

---

### Upload Bid Documents

```
POST /api/upload_bids
Content-Type: multipart/form-data
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| tender_id | integer | Yes | Associated tender ID |
| files | file[] | Yes | Bid document files (multiple) |

**Response:**
```json
{
  "success": true,
  "message": "成功上传 3 个投标文件",
  "bids": [
    {"id": 1, "bidder_name": "Company A"},
    {"id": 2, "bidder_name": "Company B"}
  ]
}
```

---

### Analyze Tender Document

```
POST /api/analyze_tender?tender_id={id}
```

Performs compliance analysis on the uploaded tender document.

**Response:**
```json
{
  "success": true,
  "analysis_id": 1,
  "tender_id": 1,
  "risk_score": 0.65,
  "risk_level": "yellow",
  "risk_items": [
    {
      "rule_id": "RULE_T_001",
      "rule_type": "exclusive_brand",
      "risk_name": "限定品牌或供应商",
      "severity": "high",
      "location": {
        "chapter": "第四章 技术规格要求",
        "line_start": 20,
        "line_end": 20,
        "raw_text": "服务器设备必须是华为品牌"
      },
      "evidence": "语义算子P_LIMIT激活...",
      "suggestion": "删除指定品牌..."
    }
  ],
  "coupling_alerts": []
}
```

---

### Analyze Bid Documents

```
POST /api/analyze_bids?tender_id={id}
```

Performs similarity analysis and collusion detection on uploaded bid documents.

**Response:**
```json
{
  "success": true,
  "analysis_id": 2,
  "tender_id": 1,
  "total_bids": 3,
  "similarity_pairs": [
    {
      "bid1_name": "Company A",
      "bid2_name": "Company B",
      "similarity": 0.92,
      "risk_flag": true
    }
  ],
  "price_analysis": {
    "price_deviation": 0.15,
    "curve_correlation": 0.85,
    "anomaly_detected": false
  },
  "entity_connections": [
    {
      "type": "address",
      "entities": ["Company A", "Company B"],
      "detail": "注册地址相同",
      "risk_level": "medium"
    }
  ],
  "overall_risk_score": 0.45,
  "risk_level": "yellow"
}
```

---

### Get Risk Report

```
GET /api/get_risk_report/{tender_id}
```

Returns comprehensive risk report combining tender and bid analysis.

---

### Bid Analysis (v1)

```
POST /api/v1/analyze_bid
Content-Type: application/json
```

**Request Body:**
```json
{
  "tender_id": "T001",
  "bids": [
    {"bidder": "A", "price": 100.0, "technical_score": 85},
    {"bidder": "B", "price": 110.0, "technical_score": 90}
  ]
}
```

---

### Detect Collusion Markers

```
POST /api/v1/detect_collusion_markers
Content-Type: application/json
```

Detects price clustering, identical decimals, irregular intervals, and herd pricing.

---

### Risk Entropy Scoring

```
POST /api/v1/risk_entropy
Content-Type: application/json
```

Scores individual clauses for risk using entropy model.

---

### Compare Bids

```
GET /api/v1/compare_bids?tender_id={id}&bid_ids=a,b,c
```

Compares selected bids with price deviation statistics.

---

### Audit Logs

```
GET /api/audit_logs?limit=50
```

Returns recent audit log entries.

---

### List Rules

```
GET /api/rules
```

Returns all active compliance rules.

---

### List Tenders

```
GET /api/tenders
```

Returns all uploaded tender documents.

---

### Get Bids

```
GET /api/bids/{tender_id}
```

Returns all bid documents for a specific tender.

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request / validation error |
| 404 | Resource not found |
| 422 | Request body validation failed |
| 500 | Internal server error |

## Interactive Documentation

Swagger UI is available at `/docs` when the server is running.
ReDoc is available at `/redoc`.
