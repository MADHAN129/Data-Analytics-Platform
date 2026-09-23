import time
from typing import Optional

import pymssql

from app.schemas.connection import ColumnInfo, TableSchema, SchemaResponse, DatabaseTestResult, SyncResult
from app.utils.error_messages import friendly_error


class SQLServerConnector:

    def __init__(self, host: str, port: int, database: str, user: str, password: str,
                 schema: str = "dbo", ssl: bool = False):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self.ssl = ssl
        self._connection = None

    def _get_conn_params(self):
        params = {
            "server": f"{self.host}:{self.port}",
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "timeout": 10,
        }
        return params

    def connect(self):
        self._connection = pymssql.connect(**self._get_conn_params())
        return self._connection

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    def test_connection(self) -> DatabaseTestResult:
        start = time.time()
        try:
            conn = pymssql.connect(**self._get_conn_params())
            cur = conn.cursor()
            cur.execute("SELECT @@VERSION")
            version = cur.fetchone()[0]
            cur.close()
            conn.close()
            latency = int((time.time() - start) * 1000)
            return DatabaseTestResult(
                success=True,
                message="Connection successful",
                latency_ms=latency,
                server_version=version.split("\n")[0].strip() if version else None,
            )
        except Exception as e:
            return DatabaseTestResult(
                success=False,
                message=friendly_error(str(e)),
            )

    def get_schema(self) -> SchemaResponse:
        conn = self.connect()
        try:
            cur = conn.cursor()
            tables = self._get_tables(cur, "BASE TABLE")
            views = self._get_tables(cur, "VIEW")
            cur.close()
            return SchemaResponse(
                database_id=0,
                schema_name=self.schema,
                tables=tables,
                views=views,
                last_synced_at=None,
            )
        finally:
            self.close()

    def sync_schema(self, database_id: int) -> SyncResult:
        start = time.time()
        errors = []
        tables_synced = 0
        columns_synced = 0

        try:
            schema = self.get_schema()
            tables_synced = len(schema.tables) + len(schema.views)
            for table in schema.tables:
                columns_synced += len(table.columns)
            for view in schema.views:
                columns_synced += len(view.columns)
        except Exception as e:
            errors.append(friendly_error(str(e)))

        duration = int((time.time() - start) * 1000)
        return SyncResult(
            database_id=database_id,
            status="completed" if not errors else "failed",
            tables_synced=tables_synced,
            columns_synced=columns_synced,
            duration_ms=duration,
            errors=errors,
            synced_at=__import__("datetime").datetime.utcnow(),
        )

    def _get_tables(self, cur, table_type: str) -> list[TableSchema]:
        cur.execute("""
            SELECT
                t.TABLE_NAME,
                t.TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES t
            WHERE t.TABLE_SCHEMA = %s
                AND t.TABLE_TYPE = %s
            ORDER BY t.TABLE_NAME
        """, [self.schema, table_type])
        tables = []
        for row in cur.fetchall():
            table_name = row[0]
            columns = self._get_columns(cur, table_name)
            tables.append(TableSchema(
                name=table_name,
                schema_name=self.schema,
                type="table" if table_type == "BASE TABLE" else "view",
                columns=columns,
            ))
        return tables

    def _get_columns(self, cur, table_name: str) -> list[ColumnInfo]:
        cur.execute("""
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE,
                c.COLUMN_DEFAULT,
                c.CHARACTER_MAXIMUM_LENGTH,
                CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN (
                SELECT ku.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                    ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                    AND tc.TABLE_SCHEMA = ku.TABLE_SCHEMA
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                    AND tc.TABLE_SCHEMA = %s
                    AND tc.TABLE_NAME = %s
            ) pk ON pk.COLUMN_NAME = c.COLUMN_NAME
            WHERE c.TABLE_SCHEMA = %s
                AND c.TABLE_NAME = %s
            ORDER BY c.ORDINAL_POSITION
        """, [self.schema, table_name, self.schema, table_name])
        columns = []
        for row in cur.fetchall():
            default_val = str(row[3]) if row[3] is not None else None
            columns.append(ColumnInfo(
                name=row[0],
                data_type=row[1],
                nullable=row[2] == "YES",
                is_primary_key=bool(row[5]),
                default_value=default_val,
                max_length=row[4],
            ))
        return columns

    def get_tables_list(self) -> list[dict]:
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    t.TABLE_NAME,
                    t.TABLE_TYPE,
                    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                     WHERE TABLE_SCHEMA = %s AND TABLE_NAME = t.TABLE_NAME) as column_count
                FROM INFORMATION_SCHEMA.TABLES t
                WHERE t.TABLE_SCHEMA = %s
                ORDER BY t.TABLE_NAME
            """, [self.schema, self.schema])
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "name": r[0],
                    "type": "table" if r[1] == "BASE TABLE" else "view",
                    "column_count": r[2],
                }
                for r in rows
            ]
        finally:
            self.close()

    def execute_query(self, sql: str) -> dict:
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return {
                    "columns": columns,
                    "rows": [list(r) for r in rows],
                }
            return {"affected_rows": cur.rowcount}
        except Exception as e:
            raise type(e)(friendly_error(str(e)))
        finally:
            cur.close()
            self.close()

    def get_table_details(self, table_name: str) -> TableSchema:
        conn = self.connect()
        try:
            cur = conn.cursor()
            columns = self._get_columns(cur, table_name)
            cur.close()
            return TableSchema(
                name=table_name,
                schema_name=self.schema,
                columns=columns,
            )
        finally:
            self.close()
