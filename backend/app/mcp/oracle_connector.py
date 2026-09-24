import time
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

import oracledb

from app.schemas.connection import (
    ColumnInfo, TableSchema, SchemaResponse, DatabaseTestResult, SyncResult, ForeignKeyInfo,
)
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

    def _try_single_connect(self, host: str, use_sid: bool = False):
        params = {
            "user": self.user,
            "password": self.password,
            "host": host,
            "port": self.port,
        }
        if use_sid:
            params["sid"] = self.database
        else:
            params["service_name"] = self.database

        return oracledb.connect(**params)

    def _raw_connect(self):
        hosts_to_try = [self.host]
        if self.host in ("localhost", "127.0.0.1"):
            hosts_to_try.append("host.docker.internal")

        last_err = None
        for h in hosts_to_try:
            # 1. Try Service Name
            try:
                return self._try_single_connect(h, use_sid=False)
            except Exception as e:
                last_err = e
                # 2. Try SID
                try:
                    return self._try_single_connect(h, use_sid=True)
                except Exception as e2:
                    last_err = e2

        if last_err:
            raise last_err

    def connect(self):
        if not self._connection:
            self._connection = self._raw_connect()
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
            conn = self._raw_connect()
            cur = conn.cursor()
            version = "Oracle Database"
            try:
                cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
                row = cur.fetchone()
                if row and row[0]:
                    version = str(row[0])
            except Exception:
                try:
                    cur.execute("SELECT 'Oracle Database' FROM DUAL")
                    row = cur.fetchone()
                    if row:
                        version = str(row[0])
                except Exception:
                    pass

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

    def _get_foreign_keys(self, cur) -> list[ForeignKeyInfo]:
        owner = self.schema if self.schema and self.schema != "PUBLIC" else self.user.upper()
        try:
            cur.execute("""
                SELECT 
                    a.table_name, 
                    a_col.column_name, 
                    c_pk.table_name AS ref_table, 
                    r_col.column_name AS ref_col
                FROM all_constraints a
                JOIN all_cons_columns a_col 
                  ON a.constraint_name = a_col.constraint_name AND a.owner = a_col.owner
                JOIN all_constraints c_pk 
                  ON a.r_constraint_name = c_pk.constraint_name AND a.r_owner = c_pk.owner
                JOIN all_cons_columns r_col 
                  ON c_pk.constraint_name = r_col.constraint_name AND c_pk.owner = r_col.owner 
                 AND a_col.position = r_col.position
                WHERE a.constraint_type = 'R' 
                  AND a.owner = :owner
                  AND a.table_name NOT LIKE '%$%'
                  AND a.table_name NOT LIKE 'AQ$%'
                  AND a.table_name NOT LIKE 'MVIEW$%'
                ORDER BY a.table_name, a_col.position
            """, {"owner": owner})
            rows = cur.fetchall()
            return [
                ForeignKeyInfo(
                    table_name=r[0],
                    column_name=r[1],
                    referenced_table=r[2],
                    referenced_column=r[3],
                )
                for r in rows
            ]
        except Exception:
            return []

    def get_schema(self) -> SchemaResponse:
        conn = self.connect()
        try:
            cur = conn.cursor()
            fks = self._get_foreign_keys(cur)
            fk_by_table: dict[str, list[ForeignKeyInfo]] = {}
            for fk in fks:
                if fk.table_name:
                    fk_by_table.setdefault(fk.table_name.upper(), []).append(fk)

            tables = self._get_tables(cur, is_view=False, fk_by_table=fk_by_table)
            views = self._get_tables(cur, is_view=True, fk_by_table=fk_by_table)
            cur.close()
            return SchemaResponse(
                database_id=0,
                schema_name=self.schema,
                tables=tables,
                views=views,
                foreign_keys=fks,
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

    def _get_tables(self, cur, is_view: bool = False, fk_by_table: dict = None) -> list[TableSchema]:
        owner = self.schema if self.schema and self.schema != "PUBLIC" else self.user.upper()
        fk_by_table = fk_by_table or {}
        
        # System prefixes to filter out for cleaner application analytics
        sys_filters = (
            "table_name NOT LIKE '%$%' "
            "AND table_name NOT LIKE 'LOGMNR%' "
            "AND table_name NOT LIKE 'MVIEW$%' "
            "AND table_name NOT LIKE 'AQ$%' "
            "AND table_name NOT LIKE 'ROLLING$%' "
            "AND table_name NOT LIKE 'REDO_%' "
            "AND table_name NOT LIKE 'SCHEDULER_%' "
            "AND table_name NOT LIKE 'OL$%' "
            "AND table_name NOT LIKE 'LOGSTDBY$%' "
            "AND table_name NOT IN ('HELP', 'SQLPLUS_PRODUCT_PROFILE')"
        ) if not is_view else (
            "view_name NOT LIKE '%$%' "
            "AND view_name NOT LIKE 'LOGMNR%' "
            "AND view_name NOT LIKE 'MVIEW$%' "
            "AND view_name NOT LIKE 'AQ$%'"
        )

        if is_view:
            cur.execute(f"""
                SELECT view_name
                FROM all_views
                WHERE owner = :owner AND {sys_filters}
                ORDER BY view_name
            """, {"owner": owner})
        else:
            cur.execute(f"""
                SELECT table_name
                FROM all_tables
                WHERE owner = :owner AND {sys_filters}
                ORDER BY table_name
            """, {"owner": owner})

        rows = cur.fetchall()
        if not rows:
            if is_view:
                cur.execute("SELECT view_name FROM user_views ORDER BY view_name")
            else:
                cur.execute(f"SELECT table_name FROM user_tables WHERE {sys_filters} ORDER BY table_name")
            rows = cur.fetchall()

        tables = []
        for row in rows:
            table_name = row[0]
            table_fks = fk_by_table.get(table_name.upper(), [])
            columns = self._get_columns(cur, table_name, table_fks=table_fks)

            row_count = None
            if not is_view:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                    rc_row = cur.fetchone()
                    if rc_row:
                        row_count = int(rc_row[0])
                except Exception:
                    pass

            tables.append(TableSchema(
                name=table_name,
                schema_name=owner,
                type="view" if is_view else "table",
                row_count=row_count,
                columns=columns,
                foreign_keys=table_fks,
            ))
        return tables

    def _get_columns(self, cur, table_name: str, table_fks: list[ForeignKeyInfo] = None) -> list[ColumnInfo]:
        owner = self.schema
        pk_columns = set()
        fk_columns = {fk.column_name.upper() for fk in (table_fks or [])}
        try:
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
        except Exception:
            pass

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
        rows = cur.fetchall()

        if not rows:
            cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    nullable,
                    data_default,
                    data_length
                FROM user_tab_columns
                WHERE table_name = :table_name
                ORDER BY column_id
            """, {"table_name": table_name})
            rows = cur.fetchall()

        columns = []
        for row in rows:
            col_name = row[0]
            col_type = str(row[1])
            default_val = str(row[3]).strip() if row[3] is not None else None
            is_pk = col_name in pk_columns
            is_fk = col_name in fk_columns

            sample_values = None
            if ("VARCHAR" in col_type.upper() or "CHAR" in col_type.upper()) and (row[4] or 0) <= 255 and not is_pk and not is_fk:
                try:
                    cur.execute(f"SELECT DISTINCT {col_name} FROM {table_name} WHERE {col_name} IS NOT NULL FETCH FIRST 10 ROWS ONLY")
                    distinct_vals = [str(sv[0]) for sv in cur.fetchall() if sv[0] is not None]
                    if distinct_vals and len(distinct_vals) <= 10:
                        sample_values = distinct_vals
                except Exception:
                    pass

            columns.append(ColumnInfo(
                name=col_name,
                data_type=col_type,
                nullable=row[2] == "Y",
                is_primary_key=is_pk,
                is_foreign_key=is_fk,
                default_value=default_val,
                max_length=row[4],
                sample_values=sample_values,
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
            if not rows and self.schema == self.user.upper():
                cur.execute("""
                    SELECT table_name, 'table' as obj_type,
                           (SELECT COUNT(*) FROM user_tab_columns WHERE table_name = t.table_name) as col_count
                    FROM user_tables t
                    UNION ALL
                    SELECT view_name as table_name, 'view' as obj_type,
                           (SELECT COUNT(*) FROM user_tab_columns WHERE table_name = v.view_name) as col_count
                    FROM user_views v
                    ORDER BY 1
                """)
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

    def _serialize_cell(self, val):
        if val is None:
            return None
        if isinstance(val, (datetime, date)):
            return val.isoformat()
        if isinstance(val, (Decimal, int, float)):
            return float(val) if isinstance(val, Decimal) else val
        if hasattr(val, "read"):
            try:
                return val.read()
            except Exception:
                return str(val)
        return str(val)

    def execute_query(self, sql: str) -> dict:
        conn = self.connect()
        try:
            cur = conn.cursor()
            clean_sql = sql.strip().rstrip(";")
            cur.execute(clean_sql)
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                raw_rows = cur.fetchall()
                rows = [[self._serialize_cell(cell) for cell in row] for row in raw_rows]
                return {
                    "columns": columns,
                    "rows": rows,
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
