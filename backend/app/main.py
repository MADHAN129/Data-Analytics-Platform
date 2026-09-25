from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base
from app.api import auth, users, roles, permissions, audit, connections, queries, conversations, templates, dashboards, activity, ws
from app.schemas.common import HealthResponse
from app.services.ws_manager import manager
from app.services.widget_poller import poll_manager
from app.mcp_server import create_mcp_asgi

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        services={
            "database": "connected",
            "redis": "connected",
            "llm": "ready",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(queries.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(dashboards.router, prefix="/api/v1")
app.include_router(activity.router, prefix="/api/v1")
app.include_router(ws.router)

if settings.MCP_ENABLED:
    app.mount("/mcp", create_mcp_asgi())

poll_manager.set_broadcast_cb(manager.broadcast)
