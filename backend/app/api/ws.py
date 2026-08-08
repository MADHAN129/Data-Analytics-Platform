import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.dashboard import Dashboard, DashboardWidget
from app.utils.security import decode_token
from app.services.ws_manager import manager
from app.services.widget_poller import poll_manager, init_poller
from app.api.deps import user_has_permission_by_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

init_poller(SessionLocal)


async def _get_user_from_token(token: str | None) -> User | None:
    if not token:
        return None
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user and user.is_active:
            return user
        return None
    finally:
        db.close()


def _get_dashboard_for_user(dashboard_id: int, user: User) -> list[DashboardWidget]:
    """Return a dashboard's widgets only if the user owns it (or manages all)."""
    db = SessionLocal()
    try:
        include_all = user_has_permission_by_id(db, user.id, "access.manage")
        dash = db.query(Dashboard).filter(Dashboard.id == dashboard_id)
        if not include_all:
            dash = dash.filter(Dashboard.user_id == user.id)
        dash = dash.first()
        if not dash:
            return None
        return list(dash.widgets)
    finally:
        db.close()


def _widget_poll_target(widget: DashboardWidget) -> tuple[int | None, str | None, int]:
    """Resolve (database_id, sql, interval) for a widget's live poller.

    Prefers the widget's linked Query (generated_sql + database_id) so
    auto-generated widgets — whose config only stores natural language — still
    poll live. Falls back to config.sql / config.database_id for manually
    configured widgets. The refresh interval comes from config, defaulting to
    15s when unset so dashboards keep a heartbeat even without an explicit
    interval.
    """
    cfg = widget.config or {}
    database_id = cfg.get("database_id")
    sql = cfg.get("sql")
    interval = int(cfg.get("refresh_interval", 0) or 0)

    if (not sql or not database_id) and widget.query_id:
        db = SessionLocal()
        try:
            from app.models.query import Query
            query = db.query(Query).filter(Query.id == widget.query_id).first()
            if query:
                sql = sql or query.generated_sql
                database_id = database_id or query.database_id
        finally:
            db.close()

    if not interval and sql and database_id:
        interval = 15
    return database_id, sql, interval


def _restart_poller(dashboard_id: int, widget: DashboardWidget) -> bool:
    """Stop then start a widget's poller using its resolved query target.

    Returns True if a poller was (re)started, False if the widget has no
    runnable query (e.g. a placeholder with no linked query).
    """
    poll_manager.stop(dashboard_id, widget.id)
    database_id, sql, interval = _widget_poll_target(widget)
    if interval > 0 and widget.query_id and sql and database_id:
        poll_manager.start(
            dashboard_id=dashboard_id,
            widget_id=widget.id,
            interval=interval,
            database_id=database_id,
            sql=sql,
        )
        return True
    return False


@router.websocket("/ws/dashboards/{dashboard_id}")
async def dashboard_websocket(
    websocket: WebSocket,
    dashboard_id: int,
    token: str | None = Query(None),
):
    user = await _get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    widgets = await _get_dashboard_widgets_async(dashboard_id, user)
    if widgets is None:
        await websocket.close(code=4003, reason="Dashboard not found")
        return

    await manager.connect(dashboard_id, websocket)

    try:
        widgets = await _get_dashboard_widgets_async(dashboard_id)
        active = []
        for w in widgets:
            database_id, sql, interval = _widget_poll_target(w)
            if interval > 0 and w.query_id and sql and database_id:
                poll_manager.start(
                    dashboard_id=dashboard_id,
                    widget_id=w.id,
                    interval=interval,
                    database_id=database_id,
                    sql=sql,
                )
                active.append(w.id)

        await websocket.send_json({
            "type": "connected",
            "dashboard_id": dashboard_id,
            "active_pollers": active,
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "refresh_all":
                for w in widgets:
                    _restart_poller(dashboard_id, w)
                await websocket.send_json({
                    "type": "refresh_all",
                    "status": "started",
                })

            elif msg_type == "refresh_widget":
                widget_id = msg.get("widget_id")
                if widget_id:
                    w = next((x for x in widgets if x.id == widget_id), None)
                    if w:
                        started = _restart_poller(dashboard_id, w)
                        await websocket.send_json({
                            "type": "refresh_widget",
                            "widget_id": widget_id,
                            "status": "started" if started else "skipped",
                        })

    except WebSocketDisconnect:
        pass
    finally:
        poll_manager.stop_all(dashboard_id)
        await manager.disconnect(dashboard_id, websocket)


async def _get_dashboard_widgets_async(dashboard_id: int, user: User) -> list[DashboardWidget]:
    from asyncio import to_thread
    return await to_thread(_get_dashboard_for_user, dashboard_id, user)
