import time
from datetime import datetime
from typing import Optional

import oracledb

from app.schemas.connection import ColumnInfo, TableSchema, SchemaResponse, DatabaseTestResult, SyncResult
from app.utils.error_messages import friendly_error


class OracleConnector:

    def __init__(self, host: str, port: int, database: str, user: str, password: str,
                 schema: str = None, ssl: bool = False):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = (schema or user).upper()
        self.ssl = ssl
        self._connection = None

    def _get_conn_params(self):
        # Support service name or SID in database field
        params = {
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
            "service_name": self.database,
        }
        return params

    def connect(self):
        self._connection = oracledb.connect(**self._get_conn_params())
        return self._connection

    def close(self):
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def test_connection(self) -> DatabaseTestResult:
        start = time.time()
        try:
            conn = oracledb.connect(**self._get_conn_params())
            cur = conn.cursor()
            version = None
            try:
                cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
                row = cur.fetchone()
                if row:
                    version = str(row[0])
            except Exception:
                cur.execute("SELECT 'Oracle Database' FROM DUAL")
                row = cur.fetchone()
                version = str(row[0]) if row else "Oracle"

            cur.close()
            conn.close()
            latency = int((time.time() - start) * 1000)
            return DatabaseTestResult(
                success=True,
                message="Connection successful",
                latency_ms=latency,
                server_version=version.split("\n")[0].strip() if version else "Oracle",
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
            tables = self._get_tables(cur, is_view=False)
            views = self._get_tables(cur, is_view=True)
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
            synced_at=datetime.utcnow(),
        )

    def _get_tables(self, cur, is_view: bool = False) -> list[TableSchema]:
        owner = self.schema
        if is_view:
            cur.execute("""
                SELECT view_name
                FROM all_views
                WHERE owner = :owner
                ORDER BY view_name
            """, {"owner": owner})
        else:
            cur.execute("""
                SELECT table_name
                FROM all_tables
                WHERE owner = :owner
                ORDER BY table_name
            """, {"owner": owner})

        tables = []
        for row in cur.fetchall():
            table_name = row[0]
            columns = self._get_columns(cur, table_name)
            tables.append(TableSchema(
                name=table_name,
                schema_name=self.schema,
                type="view" if is_view else "table",
                columns=columns,
            ))
        return tables

    def _get_columns(self, cur, table_name: str) -> list[ColumnInfo]:
        owner = self.schema
        cur.execute("""
            SELECT cols.column_name
            FROM all_constraints cons
            JOIN all_cons_columns cols
              ON cons.constraint_name = cols.constraint_name
             AND cons.owner = cols.owner
            WHERE cons.constraint_type = 'P'
              AND cons.owner = :owner
              AND cons.table_name = :table_name
        """, {"owner": owner, "table_name": table_name})
        pk_columns = {row[0] for row in cur.fetchall()}

        cur.execute("""
            SELECT
                column_name,
                data_type,
                nullable,
                data_default,
                data_length
            FROM all_tab_columns
            WHERE owner = :owner
              AND table_name = :table_name
            ORDER BY column_id
        """, {"owner": owner, "table_name": table_name})

        columns = []
        for row in cur.fetchall():
            default_val = str(row[3]).strip() if row[3] is not None else None
            columns.append(ColumnInfo(
                name=row[0],
                data_type=str(row[1]),
                nullable=row[2] == "Y",
                is_primary_key=row[0] in pk_columns,
                default_value=default_val,
                max_length=row[4],
            ))
        return columns

    def get_tables_list(self) -> list[dict]:
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name, 'table' as obj_type,
                       (SELECT COUNT(*) FROM all_tab_columns WHERE owner = t.owner AND table_name = t.table_name) as col_count
                FROM all_tables t
                WHERE owner = :owner
                UNION ALL
                SELECT view_name as table_name, 'view' as obj_type,
                       (SELECT COUNT(*) FROM all_tab_columns WHERE owner = v.owner AND table_name = v.view_name) as col_count
                FROM all_views v
                WHERE owner = :owner
                ORDER BY 1
            """, {"owner": self.schema})
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "name": r[0],
                    "type": r[1],
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
            cur.execute(sql.rstrip(";"))
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return {
                    "columns": columns,
                    "rows": [list(r) for r in rows],
                }
            conn.commit()
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
