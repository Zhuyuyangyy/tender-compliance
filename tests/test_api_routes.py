"""
Tests for API routes (backend/app/api/routes.py and backend/app/main.py).
Uses httpx TestClient for async endpoint testing.
"""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    """Import and return the FastAPI app."""
    from backend.app.main import app
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, client):
        async with client as c:
            resp = await c.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.mark.asyncio
    async def test_root(self, client):
        async with client as c:
            resp = await c.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert data["status"] == "running"


class TestRulesEndpoint:
    """Test rules listing endpoint."""

    @pytest.mark.asyncio
    async def test_get_rules(self, client):
        async with client as c:
            resp = await c.get("/api/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["rules"], list)


class TestTenderEndpoints:
    """Test tender upload and analysis endpoints."""

    @pytest.mark.asyncio
    async def test_upload_tender(self, client):
        async with client as c:
            resp = await c.post(
                "/api/upload_tender",
                data={"name": "Test Tender", "doc_type": "tender"},
                files={"file": ("test.txt", b"Test content", "text/plain")}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_list_tenders(self, client):
        async with client as c:
            resp = await c.get("/api/tenders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["tenders"], list)


class TestComplianceEndpoints:
    """Test the /api/v1 compliance analysis endpoints."""

    @pytest.mark.asyncio
    async def test_analyze_bid(self, client):
        payload = {
            "tender_id": "T001",
            "bids": [
                {"bidder": "A", "price": 100.0, "technical_score": 85},
                {"bidder": "B", "price": 110.0, "technical_score": 90},
                {"bidder": "C", "price": 95.0, "technical_score": 80}
            ]
        }
        async with client as c:
            resp = await c.post("/api/v1/analyze_bid", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tender_id"] == "T001"
        assert data["total_bids"] == 3
        assert "winner" in data
        assert data["winner"]["rank"] == 1

    @pytest.mark.asyncio
    async def test_detect_collusion_markers(self, client):
        payload = {
            "tender_id": "T001",
            "bids": [
                {"bidder": "A", "price": 100.1234},
                {"bidder": "B", "price": 100.1234},
                {"bidder": "C", "price": 100.1234}
            ]
        }
        async with client as c:
            resp = await c.post("/api/v1/detect_collusion_markers", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "markers" in data
        assert "collusion_probability" in data
        # Identical decimals should be detected
        marker_types = [m["type"] for m in data["markers"]]
        assert "identical_decimals" in marker_types

    @pytest.mark.asyncio
    async def test_risk_entropy(self, client):
        payload = {
            "tender_id": "T001",
            "document_text": "招标文件全文",
            "clause_texts": [
                "甲方有权单方面解除合同且无需赔偿",
                "验收标准由甲方确定"
            ]
        }
        async with client as c:
            resp = await c.post("/api/v1/risk_entropy", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["clause_count"] == 2
        assert "overall_risk" in data
        assert "risk_distribution" in data

    @pytest.mark.asyncio
    async def test_compare_bids(self, client):
        async with client as c:
            resp = await c.get("/api/v1/compare_bids?tender_id=T001&bid_ids=a,b,c")
        assert resp.status_code == 200
        data = resp.json()
        assert "comparison" in data
        assert "price_statistics" in data


class TestAuditLogs:
    """Test audit log endpoint."""

    @pytest.mark.asyncio
    async def test_audit_logs(self, client):
        async with client as c:
            resp = await c.get("/api/audit_logs?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestMainApp:
    """Test main app configuration."""

    def test_app_title(self, app):
        assert "合规" in app.title or "招投标" in app.title

    def test_app_version(self, app):
        assert app.version == "1.0.0"

    def test_cors_middleware(self, app):
        middlewares = [type(m).__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middlewares
