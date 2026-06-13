"""
Tests for database module (backend/app/core/database.py).
Covers initialization, table creation, audit logging.
"""
import sqlite3
import pytest


class TestDatabaseInit:
    """Test database initialization."""

    def test_init_db_creates_tables(self, tmp_path, monkeypatch):
        """Test that init_db creates all required tables."""
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)

        db_mod.init_db()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "rules" in tables
        assert "tenders" in tables
        assert "bids" in tables
        assert "analysis_results" in tables
        assert "audit_logs" in tables

    def test_init_db_inserts_default_rules(self, tmp_path, monkeypatch):
        """Test that default rules are inserted."""
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)

        db_mod.init_db()

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rules")
        rules = cursor.fetchall()
        conn.close()

        assert len(rules) >= 7
        rule_ids = [r["rule_id"] for r in rules]
        assert "RULE_T_001" in rule_ids
        assert "RULE_T_007" in rule_ids

    def test_init_db_idempotent(self, tmp_path, monkeypatch):
        """Test that calling init_db twice doesn't fail or duplicate."""
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)

        db_mod.init_db()
        db_mod.init_db()  # Should not fail

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM rules")
        count = cursor.fetchone()["cnt"]
        conn.close()

        # Should not have doubled the rules
        assert count <= 10


class TestAuditLogging:
    """Test audit log functionality."""

    def test_log_audit_creates_entry(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)

        db_mod.init_db()
        db_mod.log_audit("test_action", "tender", 1, "test details")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs")
        logs = cursor.fetchall()
        conn.close()

        assert len(logs) == 1
        assert logs[0]["action"] == "test_action"
        assert logs[0]["target_type"] == "tender"
        assert logs[0]["target_id"] == 1

    def test_log_audit_optional_fields(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)

        db_mod.init_db()
        db_mod.log_audit("minimal_action", "system")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs")
        logs = cursor.fetchall()
        conn.close()

        assert len(logs) == 1
        assert logs[0]["target_id"] is None
        assert logs[0]["details"] is None

    def test_multiple_audit_entries(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)

        db_mod.init_db()
        for i in range(5):
            db_mod.log_audit(f"action_{i}", "tender", i)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM audit_logs")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 5


class TestTableSchema:
    """Test table schemas are correct."""

    def test_rules_table_columns(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)
        db_mod.init_db()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(rules)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "rule_id" in columns
        assert "rule_type" in columns
        assert "description" in columns
        assert "severity" in columns
        assert "enabled" in columns

    def test_tenders_table_columns(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)
        db_mod.init_db()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tenders)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "name" in columns
        assert "content" in columns
        assert "doc_type" in columns
        assert "status" in columns

    def test_bids_table_has_foreign_key(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)
        db_mod.init_db()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(bids)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "tender_id" in columns
        assert "bidder_name" in columns
        assert "similarity_score" in columns


class TestGetConnection:
    """Test database connection helper."""

    def test_get_connection_returns_connection(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)
        db_mod.init_db()

        conn = db_mod.get_db_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_row_factory_set(self, tmp_path, monkeypatch):
        import backend.app.core.database as db_mod
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)
        db_mod.init_db()

        conn = db_mod.get_db_connection()
        assert conn.row_factory == sqlite3.Row
        conn.close()
