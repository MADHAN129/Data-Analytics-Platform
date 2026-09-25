"""
Milestone M1 Adversarial Challenge & Empirical Verification Harness
Author: teamwork_preview_challenger_m1_1
Role: EMPIRICAL CHALLENGER (critic, specialist)

This test suite rigorously challenges:
1. Dialect-aware SQL generation in dashboard_service.py across all supported, unsupported,
   and edge-case dialects (Oracle, SQL Server, PostgreSQL, MySQL, SQLite, etc.).
2. The stop_words heuristic in query_service.py to verify vehicle entities ('van', 'car', 'bike', etc.)
   are preserved while status and boolean words are strictly filtered.
3. Edge cases: empty tables list, None inputs, unsupported dialects, case insensitivity,
   and malformed schema contexts.
"""

import unittest
from unittest.mock import MagicMock, patch

from app.models.connection import DatabaseConnection
from app.services.dashboard_service import _get_empty_query_response, _heuristic_sql
from app.services.query_service import _get_schema_context


class SchemaMockHelper:
    """Helper to mock connectors and schema objects for query_service."""

    @staticmethod
    def create_mock_column(name: str, data_type: str = "VARCHAR", sample_values: list = None):
        col = MagicMock()
        col.name = name
        col.data_type = data_type
        col.sample_values = sample_values or []
        return col

    @classmethod
    def create_mock_table(cls, name: str, columns: list = None, row_count: int = 10, foreign_keys: list = None):
        table = MagicMock()
        table.name = name
        table.columns = columns or []
        table.row_count = row_count
        table.foreign_keys = foreign_keys or []
        return table

    @classmethod
    def create_mock_schema(cls, tables: list = None):
        schema = MagicMock()
        schema.tables = tables if tables is not None else []
        return schema


class TestDialectAwareSQLAdversarial(unittest.TestCase):
    """Stress-tests dialect-aware SQL generation across dialects and edge cases."""

    def test_oracle_dialect_queries(self):
        """Oracle queries must use FETCH FIRST 100 ROWS ONLY and FROM DUAL for empty queries."""
        oracle_variants = ["oracle", "ORACLE", "Oracle", "oracle-19c", "Oracle-Cloud"]
        schema = "Table: VEHICLES [(id INT, model VARCHAR, price NUMERIC)]"

        for dialect in oracle_variants:
            with self.subTest(dialect=dialect):
                # 1. Fallback query with table
                sql = _heuristic_sql("Show all vehicles", schema, connection_type=dialect)
                self.assertIn("FETCH FIRST 100 ROWS ONLY", sql, f"Failed for dialect: {dialect}")
                self.assertNotIn("LIMIT", sql, f"LIMIT found in Oracle query for dialect: {dialect}")
                self.assertTrue(sql.startswith("SELECT * FROM VEHICLES"), f"Unexpected start for: {sql}")

                # 2. Empty query response
                empty_sql = _get_empty_query_response(connection_type=dialect)
                self.assertEqual(empty_sql, "SELECT 1 FROM DUAL WHERE 1=0", f"Failed for dialect: {dialect}")
                self.assertIn("FROM DUAL", empty_sql)

                # 3. Empty schema fallback
                fallback_sql = _heuristic_sql("Show records", "", connection_type=dialect)
                self.assertEqual(fallback_sql, "SELECT 1 FROM DUAL WHERE 1=0", f"Failed for empty schema, dialect: {dialect}")

    def test_sqlserver_dialect_queries(self):
        """SQL Server queries must use SELECT TOP 100 and no LIMIT."""
        sqlserver_variants = ["sqlserver", "SQLSERVER", "SqlServer", "mssql", "MSSQL", "mssql-2022"]
        schema = "Table: INVOICES [(id INT, amount NUMERIC)]"

        for dialect in sqlserver_variants:
            with self.subTest(dialect=dialect):
                # 1. Fallback query with table
                sql = _heuristic_sql("Show invoices", schema, connection_type=dialect)
                self.assertTrue(
                    sql.startswith("SELECT TOP 100 * FROM INVOICES"),
                    f"SQL Server query does not start with SELECT TOP 100: {sql} (dialect: {dialect})"
                )
                self.assertNotIn("LIMIT", sql, f"LIMIT found in SQL Server query: {sql}")

                # 2. Empty query response (SQL Server does not use FROM DUAL)
                empty_sql = _get_empty_query_response(connection_type=dialect)
                self.assertEqual(empty_sql, "SELECT 1 WHERE 1=0", f"Failed for dialect: {dialect}")
                self.assertNotIn("FROM DUAL", empty_sql)

                # 3. Empty schema fallback
                fallback_sql = _heuristic_sql("Show records", "", connection_type=dialect)
                self.assertEqual(fallback_sql, "SELECT 1 WHERE 1=0")

    def test_standard_limit_dialects(self):
        """PostgreSQL, MySQL, and SQLite must produce LIMIT 100."""
        standard_dialects = [
            ("postgresql", "PostgreSQL", "POSTGRESQL"),
            ("mysql", "MySQL", "MYSQL"),
            ("sqlite", "SQLite", "SQLITE"),
            ("mariadb", "MariaDB", "MARIADB"),
        ]
        schema = "Table: CUSTOMERS [(id INT, name VARCHAR)]"

        for family in standard_dialects:
            for dialect in family:
                with self.subTest(dialect=dialect):
                    # 1. Fallback query with table
                    sql = _heuristic_sql("Show customers", schema, connection_type=dialect)
                    self.assertIn("LIMIT 100", sql, f"LIMIT 100 missing for dialect: {dialect}")
                    self.assertNotIn("FETCH FIRST", sql)
                    self.assertNotIn("TOP 100", sql)

                    # 2. Empty query response
                    empty_sql = _get_empty_query_response(connection_type=dialect)
                    self.assertEqual(empty_sql, "SELECT 1 WHERE 1=0")
                    self.assertNotIn("FROM DUAL", empty_sql)

    def test_unsupported_and_unknown_dialects(self):
        """Unknown or unsupported dialects should safely default to standard SQL."""
        unknown_dialects = ["cockroachdb", "clickhouse", "snowflake", "bigquery", "unknown_engine", "custom_db"]
        schema = "Table: ORDERS [(id INT, status VARCHAR)]"

        for dialect in unknown_dialects:
            with self.subTest(dialect=dialect):
                # 1. Fallback query with table
                sql = _heuristic_sql("Show orders", schema, connection_type=dialect)
                self.assertEqual(sql, "SELECT * FROM ORDERS LIMIT 100", f"Failed for unknown dialect: {dialect}")

                # 2. Empty query response
                empty_sql = _get_empty_query_response(connection_type=dialect)
                self.assertEqual(empty_sql, "SELECT 1 WHERE 1=0")

    def test_none_and_empty_dialect(self):
        """None or empty string for connection_type should not crash and fall back to standard SQL."""
        schema = "Table: ASSETS [(id INT, name VARCHAR)]"

        for dialect in [None, ""]:
            with self.subTest(dialect=dialect):
                sql = _heuristic_sql("Show assets", schema, connection_type=dialect)
                self.assertEqual(sql, "SELECT * FROM ASSETS LIMIT 100")

                empty_sql = _get_empty_query_response(connection_type=dialect)
                self.assertEqual(empty_sql, "SELECT 1 WHERE 1=0")


class TestDashboardServiceEdgeCases(unittest.TestCase):
    """Stress-tests edge cases in dashboard heuristic generation."""

    def test_empty_and_whitespace_schema_context(self):
        """Empty or whitespace schema context must return dialect-safe empty query without referencing 'data'."""
        empty_schemas = [
            "",
            "   ",
            "\n\t",
            "No tables found",
            "Schema unavailable",
            "DATABASE TYPE: POSTGRESQL. Schema unavailable.",
        ]
        for schema in empty_schemas:
            for dialect in ["oracle", "sqlserver", "postgresql"]:
                with self.subTest(schema=schema, dialect=dialect):
                    sql = _heuristic_sql("Show anything", schema, connection_type=dialect)
                    self.assertNotIn("FROM data", sql, f"Found obsolete 'FROM data' assumption in: {sql}")
                    if "oracle" in dialect:
                        self.assertEqual(sql, "SELECT 1 FROM DUAL WHERE 1=0")
                    else:
                        self.assertEqual(sql, "SELECT 1 WHERE 1=0")

    def test_heuristic_aggregation_priorities(self):
        """Verifies aggregations (date trend, total sum, category count) take priority over limit."""
        schema = "Table: SALES [(id INT, created_at TIMESTAMP, amount NUMERIC, category VARCHAR)]"

        # Date trend -> GROUP BY date
        sql_date = _heuristic_sql("Sales trend per day", schema, connection_type="oracle")
        self.assertIn("GROUP BY created_at", sql_date)

        # Sum / Total -> SUM(amount)
        sql_sum = _heuristic_sql("Total revenue", schema, connection_type="sqlserver")
        self.assertIn("SUM(amount) AS total", sql_sum)

        # Category -> GROUP BY category
        sql_cat = _heuristic_sql("Sales breakdown per category", schema, connection_type="postgresql")
        self.assertIn("GROUP BY category", sql_cat)

        # Count -> COUNT(*)
        sql_cnt = _heuristic_sql("Number of sales", schema, connection_type="mysql")
        self.assertEqual(sql_cnt, "SELECT COUNT(*) AS count FROM SALES")

    def test_schema_context_none_raises_type_error_unhandled(self):
        """Empirically test whether _heuristic_sql handles schema_context=None.
        
        Demonstrates that passing None raises TypeError because re.findall expects str.
        """
        with self.assertRaises(TypeError):
            _heuristic_sql("Show records", None, connection_type="postgresql")

    def test_question_none_raises_attribute_error_unhandled(self):
        """Empirically test whether _heuristic_sql handles question=None.
        
        Demonstrates that passing question=None raises AttributeError because question.lower() is called.
        """
        with self.assertRaises(AttributeError):
            _heuristic_sql(None, "Table: EMPLOYEES [(id INT)]", connection_type="postgresql")


class TestQueryServiceStopWordsAdversarial(unittest.TestCase):
    """Stress-tests query_service stop_words filtering and categorical mapping."""

    @patch("app.services.query_service.get_connector")
    def test_vehicle_terms_retained_in_categorical_map(self, mock_get_connector):
        """Verify vehicle-specific terms ('van', 'car', 'bike', 'truck', etc.) are preserved in categorical_map."""
        vehicle_terms = ["van", "car", "bike", "truck", "suv", "sedan", "motorcycle", "full_day"]

        columns = [
            SchemaMockHelper.create_mock_column(
                name="VEHICLE_TYPE",
                data_type="VARCHAR(50)",
                sample_values=vehicle_terms,
            )
        ]
        table = SchemaMockHelper.create_mock_table(name="FLEET", columns=columns, row_count=50)
        mock_schema = SchemaMockHelper.create_mock_schema(tables=[table])

        mock_connector = MagicMock()
        mock_connector.get_schema.return_value = mock_schema
        mock_get_connector.return_value = mock_connector

        db_conn = DatabaseConnection(
            name="test_fleet_db",
            connection_type="postgresql",
            schema_name="public",
        )

        _, _, schema_metadata = _get_schema_context(db_conn)
        categorical_map = schema_metadata.get("categorical_map", {})

        for term in vehicle_terms:
            self.assertIn(
                term.lower(),
                categorical_map,
                f"Vehicle term '{term}' was incorrectly filtered out of categorical_map!"
            )
            matches = categorical_map[term.lower()]
            self.assertTrue(any(m["value"] == term for m in matches))

    @patch("app.services.query_service.get_connector")
    def test_status_and_boolean_stop_words_strictly_filtered(self, mock_get_connector):
        """Verify core status and boolean stop words are strictly excluded from categorical_map."""
        status_stop_words = [
            "paid", "active", "inactive", "booked", "completed",
            "in progress", "true", "false", "none", "null"
        ]

        columns = [
            SchemaMockHelper.create_mock_column(
                name="STATUS",
                data_type="VARCHAR(50)",
                sample_values=status_stop_words,
            )
        ]
        table = SchemaMockHelper.create_mock_table(name="ORDERS", columns=columns, row_count=100)
        mock_schema = SchemaMockHelper.create_mock_schema(tables=[table])

        mock_connector = MagicMock()
        mock_connector.get_schema.return_value = mock_schema
        mock_get_connector.return_value = mock_connector

        db_conn = DatabaseConnection(
            name="test_orders_db",
            connection_type="postgresql",
            schema_name="public",
        )

        _, _, schema_metadata = _get_schema_context(db_conn)
        categorical_map = schema_metadata.get("categorical_map", {})

        for sw in status_stop_words:
            self.assertNotIn(
                sw.lower(),
                categorical_map,
                f"Status stop word '{sw}' was NOT filtered out of categorical_map!"
            )

    @patch("app.services.query_service.get_connector")
    def test_case_insensitive_and_whitespace_filtering(self, mock_get_connector):
        """Verify case insensitivity and whitespace stripping on stop words and vehicle terms."""
        mixed_samples = [
            "  van  ",      # whitespace vehicle -> keep as "van"
            "Van",          # title case vehicle -> keep as "van"
            "CAR",          # upper case vehicle -> keep as "car"
            "  PAID  ",     # whitespace + uppercase stop word -> filter
            "Active",       # title case stop word -> filter
            "IN PROGRESS",  # uppercase multi-word stop word -> filter
            "None",         # title case stop word -> filter
            "x",            # single char (< 2 len) -> filter
        ]

        columns = [
            SchemaMockHelper.create_mock_column(
                name="TAGS",
                data_type="VARCHAR(50)",
                sample_values=mixed_samples,
            )
        ]
        table = SchemaMockHelper.create_mock_table(name="ITEMS", columns=columns, row_count=20)
        mock_schema = SchemaMockHelper.create_mock_schema(tables=[table])

        mock_connector = MagicMock()
        mock_connector.get_schema.return_value = mock_schema
        mock_get_connector.return_value = mock_connector

        db_conn = DatabaseConnection(
            name="test_items_db",
            connection_type="postgresql",
            schema_name="public",
        )

        _, _, schema_metadata = _get_schema_context(db_conn)
        categorical_map = schema_metadata.get("categorical_map", {})

        # Vehicle terms should be retained (normalized lowercase)
        self.assertIn("van", categorical_map)
        self.assertIn("car", categorical_map)

        # Stop words and short chars should NOT be in categorical_map
        self.assertNotIn("paid", categorical_map)
        self.assertNotIn("active", categorical_map)
        self.assertNotIn("in progress", categorical_map)
        self.assertNotIn("none", categorical_map)
        self.assertNotIn("x", categorical_map)

    @patch("app.services.query_service.get_connector")
    def test_schema_context_empty_tables_list(self, mock_get_connector):
        """Verify _get_schema_context handles empty schema.tables gracefully."""
        mock_schema = SchemaMockHelper.create_mock_schema(tables=[])
        mock_connector = MagicMock()
        mock_connector.get_schema.return_value = mock_schema
        mock_get_connector.return_value = mock_connector

        db_conn = DatabaseConnection(
            name="empty_db",
            connection_type="mysql",
            schema_name="test",
        )

        context, all_cols, metadata = _get_schema_context(db_conn)
        self.assertIn("DATABASE TYPE: MYSQL (empty_db)", context)
        self.assertEqual(all_cols, {})
        self.assertEqual(metadata.get("categorical_map"), {})
        self.assertEqual(metadata.get("active_tables"), {})

    @patch("app.services.query_service.get_connector")
    def test_schema_context_none_tables_fallback(self, mock_get_connector):
        """Verify _get_schema_context handles schema.tables=None without uncaught exception.
        
        Because _get_schema_context has a top-level try/except, it catches the TypeError
        and returns fallback schema string and empty maps.
        """
        mock_schema = MagicMock()
        mock_schema.tables = None  # None tables
        mock_connector = MagicMock()
        mock_connector.get_schema.return_value = mock_schema
        mock_get_connector.return_value = mock_connector

        db_conn = DatabaseConnection(
            name="none_tables_db",
            connection_type="oracle",
            schema_name="TEST",
        )

        context, cat_map, pk_map = _get_schema_context(db_conn)
        self.assertIn("Schema unavailable", context)
        self.assertEqual(cat_map, {})
        self.assertEqual(pk_map, {})


if __name__ == "__main__":
    unittest.main()
