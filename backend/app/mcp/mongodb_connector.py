import re
import time

import pymongo
from bson import ObjectId

from app.schemas.connection import ColumnInfo, TableSchema, SchemaResponse, DatabaseTestResult, SyncResult
from app.utils.error_messages import friendly_error


class MongoDBConnector:

    def __init__(self, host: str, port: int, database: str, user: str, password: str,
                 schema: str = None, ssl: bool = False):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.ssl = ssl
        self._connection = None
        self._db = None

    def _get_connection_string(self):
        if self.user and self.password:
            return f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?authSource=admin"
        return f"mongodb://{self.host}:{self.port}/{self.database}"

    def connect(self):
        client = pymongo.MongoClient(
            self._get_connection_string(),
            serverSelectionTimeoutMS=10000,
            tls=self.ssl,
        )
        client.server_info()
        self._connection = client
        self._db = client[self.database]
        return self._connection

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            self._db = None

    def test_connection(self) -> DatabaseTestResult:
        start = time.time()
        try:
            client = pymongo.MongoClient(
                self._get_connection_string(),
                serverSelectionTimeoutMS=10000,
                tls=self.ssl,
            )
            info = client.server_info()
            client.close()
            latency = int((time.time() - start) * 1000)
            return DatabaseTestResult(
                success=True,
                message="Connection successful",
                latency_ms=latency,
                server_version=info.get("version", ""),
            )
        except Exception as e:
            return DatabaseTestResult(
                success=False,
                message=friendly_error(str(e)),
            )

    def get_schema(self) -> SchemaResponse:
        self.connect()
        try:
            collection_names = self._db.list_collection_names()
            tables = []
            for coll_name in sorted(collection_names):
                columns = self._infer_columns(coll_name)
                tables.append(TableSchema(
                    name=coll_name,
                    schema_name=self.database,
                    type="table",
                    columns=columns,
                ))
            return SchemaResponse(
                database_id=0,
                schema_name=self.database,
                tables=tables,
                views=[],
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
            tables_synced = len(schema.tables)
            for table in schema.tables:
                columns_synced += len(table.columns)
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

    def _infer_columns(self, collection_name: str) -> list[ColumnInfo]:
        doc = self._db[collection_name].find_one()
        if not doc:
            return []

        columns = []
        for key, value in doc.items():
            if key == "_id":
                columns.append(ColumnInfo(
                    name="_id",
                    data_type="ObjectId",
                    nullable=False,
                    is_primary_key=True,
                    default_value=None,
                    max_length=None,
                ))
                continue
            bson_type = type(value).__name__ if value is not None else "null"
            columns.append(ColumnInfo(
                name=key,
                data_type=bson_type,
                nullable=True,
                is_primary_key=False,
                default_value=None,
                max_length=len(str(value)) if isinstance(value, str) else None,
            ))
        return columns

    def get_tables_list(self) -> list[dict]:
        self.connect()
        try:
            collection_names = self._db.list_collection_names()
            return [
                {
                    "name": name,
                    "type": "table",
                    "column_count": len(self._infer_columns(name)),
                }
                for name in sorted(collection_names)
            ]
        finally:
            self.close()

    def execute_query(self, sql: str) -> dict:
        self.connect()
        try:
            sql_lower = sql.strip().lower()

            count_match = re.match(r"select\s+count\s*\(\s*(?:\*|1)\s*\)\s+from\s+(\w+)", sql_lower)
            if count_match:
                coll = count_match.group(1)
                count = self._db[coll].count_documents({})
                return {"columns": ["count"], "rows": [[count]]}

            select_match = re.match(
                r"select\s+(.+?)\s+from\s+(\w+)(?:\s+where\s+(.+?))?(?:\s+order\s+by\s+(.+?))?(?:\s+limit\s+(\d+))?\s*;?\s*$",
                sql_lower,
            )
            if select_match:
                raw_columns = select_match.group(1).strip()
                coll = select_match.group(2)
                where_clause = select_match.group(3)
                order_clause = select_match.group(4)
                limit_clause = select_match.group(5)

                query_filter = {}
                if where_clause:
                    for part in re.split(r"\s+and\s+", where_clause):
                        op_match = re.match(r"(\w+)\s*(>=|<=|!=|=|>|<)\s*(.+)", part)
                        if op_match:
                            field, op, val = op_match.groups()
                            val = val.strip("'\"")
                            numeric_val = _to_number(val)
                            op_map = {">=": "$gte", "<=": "$lte", "!=": "$ne", "=": "$eq", ">": "$gt", "<": "$lt"}
                            mongo_op = op_map.get(op, "$eq")
                            if op == "=":
                                query_filter[field] = numeric_val if numeric_val is not None else val
                            else:
                                if field not in query_filter:
                                    query_filter[field] = {}
                                query_filter[field][mongo_op] = numeric_val if numeric_val is not None else val

                cursor = self._db[coll].find(query_filter)
                if order_clause:
                    order_parts = order_clause.split(",")
                    sort_list = []
                    for part in order_parts:
                        part = part.strip()
                        if "desc" in part:
                            sort_list.append((part.split()[0].strip(), -1))
                        else:
                            sort_list.append((part.split()[0].strip(), 1))
                    cursor = cursor.sort(sort_list)
                if limit_clause:
                    cursor = cursor.limit(int(limit_clause))
                else:
                    cursor = cursor.limit(100)

                docs = list(cursor)
                if not docs:
                    return {"columns": [], "rows": []}

                if raw_columns == "*":
                    columns = list(docs[0].keys())
                else:
                    columns = [c.strip() for c in raw_columns.split(",")]

                rows = []
                for doc in docs:
                    row = []
                    for c in columns:
                        val = doc.get(c, None)
                        if isinstance(val, ObjectId):
                            val = str(val)
                        elif not isinstance(val, (str, int, float, bool, type(None))):
                            val = str(val)
                        row.append(val)
                    rows.append(row)

                return {"columns": columns, "rows": rows}

            return {"columns": [], "rows": [], "error": f"Unsupported MongoDB query: {sql}"}
        finally:
            self.close()

    def get_table_details(self, collection_name: str) -> TableSchema:
        self.connect()
        try:
            columns = self._infer_columns(collection_name)
            return TableSchema(
                name=collection_name,
                schema_name=self.database,
                columns=columns,
            )
        finally:
            self.close()


def _to_number(val):
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        return None
