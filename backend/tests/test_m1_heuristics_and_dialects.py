"""
Tests for Milestone M1: Dialect-aware fallbacks, domain heuristic generalization,
and dead code elimination.
"""

import os
import unittest
from pathlib import Path

from app.services.dashboard_service import _get_empty_query_response, _heuristic_sql
from app.services.query_service import _get_schema_context
from app.models.connection import DatabaseConnection


class TestMilestone1Verification(unittest.TestCase):
    def test_empty_query_response_dialects(self):
        """Verify _get_empty_query_response produces valid dialect-safe queries."""
        oracle_empty = _get_empty_query_response("oracle")
        self.assertEqual(oracle_empty, "SELECT 1 FROM DUAL WHERE 1=0")

        pg_empty = _get_empty_query_response("postgresql")
        self.assertEqual(pg_empty, "SELECT 1 WHERE 1=0")

        mysql_empty = _get_empty_query_response("mysql")
        self.assertEqual(mysql_empty, "SELECT 1 WHERE 1=0")

        sqlite_empty = _get_empty_query_response("sqlite")
        self.assertEqual(sqlite_empty, "SELECT 1 WHERE 1=0")

        sqlserver_empty = _get_empty_query_response("sqlserver")
        self.assertEqual(sqlserver_empty, "SELECT 1 WHERE 1=0")

    def test_heuristic_sql_dialect_limits(self):
        """Verify _heuristic_sql generates dialect-compliant limit syntax."""
        schema = "Table: EMPLOYEES [(id INT, name VARCHAR, salary NUMERIC)]"

        # Oracle dialect
        oracle_sql = _heuristic_sql("Show all records", schema, connection_type="oracle")
        self.assertIn("FETCH FIRST 100 ROWS ONLY", oracle_sql)
        self.assertNotIn("LIMIT", oracle_sql)

        # SQL Server dialect
        sqlserver_sql = _heuristic_sql("Show all records", schema, connection_type="sqlserver")
        self.assertTrue(sqlserver_sql.startswith("SELECT TOP 100 * FROM EMPLOYEES"))
        self.assertNotIn("LIMIT", sqlserver_sql)

        # PostgreSQL dialect
        pg_sql = _heuristic_sql("Show all records", schema, connection_type="postgresql")
        self.assertIn("LIMIT 100", pg_sql)

        # MySQL dialect
        mysql_sql = _heuristic_sql("Show all records", schema, connection_type="mysql")
        self.assertIn("LIMIT 100", mysql_sql)

    def test_heuristic_sql_handles_empty_tables_gracefully(self):
        """Verify _heuristic_sql handles empty schema without assuming table named 'data'."""
        empty_schema = "Schema unavailable or no tables found"

        # For Oracle
        oracle_sql = _heuristic_sql("Show all records", empty_schema, connection_type="oracle")
        self.assertEqual(oracle_sql, "SELECT 1 FROM DUAL WHERE 1=0")
        self.assertNotIn("FROM data", oracle_sql)

        # For PostgreSQL
        pg_sql = _heuristic_sql("Show all records", empty_schema, connection_type="postgresql")
        self.assertEqual(pg_sql, "SELECT 1 WHERE 1=0")
        self.assertNotIn("FROM data", pg_sql)

    def test_generalized_stop_words_preserves_vehicle_entities(self):
        """Verify vehicle-specific words are not filtered out by generic stop words."""
        backend_dir = Path(__file__).resolve().parent.parent
        query_service_path = backend_dir / "app" / "services" / "query_service.py"
        with open(query_service_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Confirm stop_words line does not include vehicle terms
        for word in ['"van"', '"car"', '"bike"', '"full_day"']:
            self.assertNotIn(f"stop_words = {{..., {word}", content)
            # Check specifically in the stop_words set definition
            for line in content.splitlines():
                if "stop_words =" in line:
                    self.assertNotIn(word, line, f"Vehicle word {word} found in stop_words: {line}")

    def test_dead_code_files_removed(self):
        """Verify obsolete and redundant scratch files have been removed."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        
        # 1. Scratch PROJECT_PLAN_part.md
        self.assertFalse((repo_root / "PROJECT_PLAN_part.md").exists())

        # 2. Dead frontend placeholder-page.tsx
        self.assertFalse((repo_root / "frontend" / "src" / "components" / "shared" / "placeholder-page.tsx").exists())

        # 3. Dead backend mcp_client.py
        self.assertFalse((repo_root / "backend" / "app" / "services" / "mcp_client.py").exists())

    def test_dynamic_connection_lookup_in_test_suite(self):
        """Verify test_dynamic_data_analyzer.py does not hardcode filter_by(id=2)."""
        backend_dir = Path(__file__).resolve().parent.parent
        test_file = backend_dir / "tests" / "test_dynamic_data_analyzer.py"
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("filter_by(id=2)", content)
        self.assertIn('filter_by(connection_type="oracle").first()', content)


if __name__ == "__main__":
    unittest.main()
