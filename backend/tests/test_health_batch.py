import time
from unittest.mock import patch

from app.models.connection import DatabaseConnection
from app.services import connection_service


class _FakeConnector:
    def __init__(self, latency, healthy=True):
        self._latency = latency
        self._healthy = healthy

    def test_connection(self):
        time.sleep(self._latency)
        return type(
            "Result",
            (object,),
            {"success": self._healthy, "latency_ms": int(self._latency * 1000)},
        )()


def _make_conn(db_session, name, created_by):
    conn = DatabaseConnection(
        name=name, connection_type="postgresql", host="localhost",
        port=5432, database_name="db", username="u",
        password="plaintext-legacy-password", created_by=created_by,
    )
    db_session.add(conn)
    db_session.commit()
    return conn


class TestCheckAllHealthBounded:
    def test_batch_does_not_hang_on_slow_connectors(self, db_session, analyst):
        slow = _make_conn(db_session, "slow", analyst.id)
        fast = _make_conn(db_session, "fast", analyst.id)
        with patch.object(
            connection_service, "get_connector",
            side_effect=lambda conn: (
                _FakeConnector(0.05) if conn.id == fast.id
                else _FakeConnector(30.0)
            ),
        ):
            start = time.monotonic()
            result = connection_service.check_all_health(db_session)
            elapsed = time.monotonic() - start

        assert elapsed < 20.0, f"batch took {elapsed:.1f}s, expected bounded"
        by_id = {item.id: item for item in result.connections}
        assert by_id[fast.id].healthy is True
        assert by_id[slow.id].healthy is False

    def test_batch_reports_completed_connections(self, db_session, analyst):
        fast = _make_conn(db_session, "fast", analyst.id)
        with patch.object(
            connection_service, "get_connector",
            return_value=_FakeConnector(0.01),
        ):
            result = connection_service.check_all_health(db_session)
        assert len(result.connections) == 1
        assert result.connections[0].healthy is True
        assert result.connections[0].latency_ms == 10
