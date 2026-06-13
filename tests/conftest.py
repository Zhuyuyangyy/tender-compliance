"""
Shared fixtures for the tender-compliance test suite.
"""
import os
import sys
import pytest
import tempfile
from pathlib import Path

# Ensure backend package is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_tender_content():
    """A realistic tender document with multiple risk types."""
    return """
第一章 招标公告
本次招标项目为某市政府信息化建设系统采购

第二章 投标人资格要求
1. 投标人必须具有计算机系统集成一级资质
2. 投标人必须是本地注册企业（仅限本市）
3. 投标人应当具备ISO9001质量管理体系认证
4. 投标人注册资金不低于5000万元
5. 不接受联合体投标业绩

第三章 评标办法
本项目采用综合评分法
评标委员会由专家组成，最终得分由评标委员会决定
技术标和商务标的权重由评标委员会确定

第四章 技术规格要求
1. 服务器设备必须是华为品牌
2. 存储设备指定供应商为EMC或IBM
3. 软件系统优先选用Oracle数据库
4. 网络设备必须是思科品牌

第五章 合同条款
付款方式：按进度付款
履约保证金：合同金额的10%
验收标准：由甲方确定
"""


@pytest.fixture
def clean_tender_content():
    """A clean tender document with no violations."""
    return """
第一章 招标公告
本次招标项目为某单位办公设备采购，采用公开招标方式。

第二章 投标人资格要求
1. 投标人应满足政府采购法相关规定
2. 投标人须具有合法经营资格
3. 投标人具备良好的商业信誉

第三章 评标办法
本项目采用综合评分法
技术标60分，商务标40分
技术方案完整性20分，技术指标满足度25分，售后服务15分
价格分=（基准价/投标价）*40

第四章 技术规格要求
1. 服务器：不低于Intel Xeon 4314处理器，128GB内存
2. 存储：不低于100TB可用容量
3. 软件：支持主流数据库系统

第五章 合同条款
付款方式：验收合格后30日内付清
质量保证期：3年
"""


@pytest.fixture
def sample_bids():
    """Three sample bid documents for similarity testing."""
    return [
        {
            "id": 1,
            "bidder_name": "科技创新有限公司",
            "content": """
投标文件 - 科技创新有限公司
联系人：张三
电话：010-12345678
地址：北京市海淀区中关村大街1号
注册资金：6000万元
投标报价：150万元
资质说明：我司具有计算机系统集成一级资质
技术方案：采用华为服务器设备，使用Oracle数据库
"""
        },
        {
            "id": 2,
            "bidder_name": "信息产业发展有限公司",
            "content": """
投标文件 - 信息产业发展有限公司
联系人：李四
电话：010-87654321
地址：北京市海淀区中关村大街1号
注册资金：5500万元
投标报价：148万元
资质说明：我司具备计算机系统集成一级资质
技术方案：采用华为服务器设备，使用Oracle数据库
"""
        },
        {
            "id": 3,
            "bidder_name": "数字技术股份有限公司",
            "content": """
投标文件 - 数字技术股份有限公司
联系人：王五
电话：010-55555555
地址：北京市朝阳区建国路100号
注册资金：8000万元
投标报价：200万元
资质说明：我司具有计算机系统集成二级资质
技术方案：采用Dell服务器设备，使用MySQL数据库
"""
        }
    ]


@pytest.fixture
def sample_risk_items():
    """Sample risk items for report and scorer testing."""
    from backend.app.models.schemas import RiskItem, ClauseLocation
    return [
        RiskItem(
            rule_id="RULE_T_001",
            rule_type="exclusive_brand",
            risk_name="限定品牌或供应商",
            severity="high",
            location=ClauseLocation(
                chapter="第四章 技术规格要求",
                line_start=20,
                line_end=20,
                raw_text="服务器设备必须是华为品牌"
            ),
            evidence="语义算子P_LIMIT激活: 检测到限定性表述 '必须是'",
            suggestion="删除指定品牌，改为'同等档次品牌'或'满足技术要求的品牌'"
        ),
        RiskItem(
            rule_id="RULE_T_002",
            rule_type="exclusive_qualification",
            risk_name="排他性资质要求",
            severity="high",
            location=ClauseLocation(
                chapter="第二章 投标人资格要求",
                line_start=8,
                line_end=8,
                raw_text="投标人必须具有计算机系统集成一级资质"
            ),
            evidence="语义算子P_FORBID激活: 检测到排他性资质描述",
            suggestion="调整为'具有相应资质'或'满足招标要求'"
        ),
        RiskItem(
            rule_id="RULE_T_008",
            rule_type="region_limitation",
            risk_name="地域限制条款",
            severity="medium",
            location=ClauseLocation(
                chapter="第二章 投标人资格要求",
                line_start=9,
                line_end=9,
                raw_text="投标人必须是本地注册企业（仅限本市）"
            ),
            evidence="检测到地域限制表述",
            suggestion="删除地域限制，确保公平竞争"
        )
    ]


@pytest.fixture
def tmp_db_path(tmp_path):
    """Provide a temporary database path for testing."""
    return str(tmp_path / "test_compliance.db")
