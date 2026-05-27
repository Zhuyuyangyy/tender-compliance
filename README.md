# 招投标文件智能合规控制与围串标风险预警系统 V1.0

基于虚拟条款坐标、语义算子链、风险熵模型的智能招投标合规分析平台。

## 🎯 核心功能

### 1. 招标文件结构解析 (`tender_parser.py`)
- 虚拟条款坐标映射：构建"条款坐标空间"
- 检测：限定品牌、排他性资质、倾向性评分等隐性风险
- 多维度分类：资格条件、评分办法、技术参数、商务条款、合同条款

### 2. 围串标风险识别 (`similarity_analyzer.py`)
- 多投标文件语义相似度检测
- 报价曲线分析（价格雷同性）
- 主体关联检测（IP、联系人、地址）
- 投标相似度图谱构建

### 3. 风险熵评分 (`tender_risk_scorer.py`)
- 多维风险耦合模型
- 非线性熔断机制
- 风险等级：🟢 green / 🟡 yellow / 🔴 red

### 4. 规则引擎 (`rule_engine.py`)
- 语义算子链：P_REQUIRE / P_FORBID / P_BASIS / P_PREFER 等
- 检测"限定品牌"、"排他性资质"、"倾向性评分"等隐性风险
- 基于规则库的灵活配置

### 5. 合规报告生成 (`report_generator.py`)
- 全链路审计：触发规则、证据片段、整改建议
- 多格式导出：JSON / Markdown

## 📁 项目结构

```
tender-compliance/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py         # API路由
│   │   ├── core/
│   │   │   └── database.py       # SQLite数据库
│   │   ├── models/
│   │   │   └── schemas.py        # Pydantic模型
│   │   ├── services/
│   │   │   ├── tender_parser.py       # 招标文件解析
│   │   │   ├── tender_risk_scorer.py  # 风险熵评分
│   │   │   ├── similarity_analyzer.py # 相似度分析
│   │   │   ├── rule_engine.py         # 规则引擎
│   │   │   └── report_generator.py    # 报告生成
│   │   ├── rules/
│   │   │   └── tender_rules.json      # 规则库
│   │   └── main.py                # FastAPI入口
│   ├── frontend/
│   │   └── index.html             # Vue3前端
│   ├── requirements.txt
│   └── start.bat                  # 启动脚本
└── README.md
```

## 🚀 快速启动

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端
```bash
python app/main.py
# 或双击 start.bat
```

后端运行在: http://localhost:8012

### 3. 打开前端
直接用浏览器打开 `frontend/index.html`

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload_tender` | 上传招标文件 |
| POST | `/api/upload_bids` | 批量上传投标文件 |
| POST | `/api/analyze_tender` | 分析招标文件合规性 |
| POST | `/api/analyze_bids` | 分析投标相似度 |
| GET | `/api/get_risk_report/{tender_id}` | 获取综合风险报告 |
| GET | `/api/audit_logs` | 审计日志 |
| GET | `/api/health` | 健康检查 |

完整API文档: http://localhost:8012/docs

## 💾 数据库

SQLite: `tender_compliance.db`

### 表结构

- `rules` - 规则库
- `tenders` - 招标文件
- `bids` - 投标文件
- `analysis_results` - 分析结果
- `audit_logs` - 审计日志

## 📊 规则库 (tender_rules.json)

| 规则ID | 类型 | 描述 | 严重程度 |
|--------|------|------|----------|
| RULE_T_001 | exclusive_brand | 限定品牌/供应商（歧视性条款） | 🔴 high |
| RULE_T_002 | exclusive_qualification | 排他性资质要求 | 🔴 high |
| RULE_T_003 | unclear_scoring | 评分标准不透明 | 🟡 medium |
| RULE_T_004 | bid_similarity | 投标文件高度相似（围标检测） | 🔴 critical |
| RULE_T_005 | entity_connection | 多家公司IP/联系人异常 | 🔴 critical |
| RULE_T_006 | price_anomaly | 报价规律异常 | 🔴 high |
| RULE_T_007 | audit_trail | 评标过程缺乏可追溯审计 | 🟡 medium |
| RULE_T_008 | region_limitation | 地域限制条款 | 🟡 medium |
| RULE_T_009 | experience_exclusive | 业绩排斥条款 | 🟡 medium |

## 📈 风险雷达维度

1. **围标风险** - 投标文件高度相似
2. **排他风险** - 招标文件限定性条款
3. **评分异常** - 评标标准不透明
4. **主体关联** - 多家公司关联异常

## 🔬 专利技术

1. 一种基于虚拟条款坐标的招标文件合规检测方法
2. 一种基于投标主体关系图谱的围串标风险识别方法
3. 一种基于语义算子链的招标评分条款倾向性检测方法
4. 一种基于风险熵的招投标异常行为分级预警方法

## 🛠️ 技术栈

- Python 3.12 + FastAPI + uvicorn
- 规则引擎（本地规则库 JSON）
- 语义相似度（TF-IDF + 余弦相似度）
- 风险熵模型（多维耦合 + 非线性熔断）
- SQLite 数据库
- Vue3 前端（单文件，直接浏览器打开）

## 📝 使用说明

### 招标文件分析
1. 点击上传招标文件（或加载示例）
2. 系统自动解析并检测违规条款
3. 查看风险项列表和整改建议

### 投标相似度分析
1. 先上传并分析招标文件
2. 上传多个投标文件（至少2个）
3. 系统检测相似度、报价异常、主体关联
4. 查看综合风险报告

## 📜 License

MIT License