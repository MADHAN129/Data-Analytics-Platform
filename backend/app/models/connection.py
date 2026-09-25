from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, func
from app.database import Base


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    connection_type = Column("type", String(50), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database_name = Column(String(255), nullable=False)
    schema_name = Column(String(255), default="public")
    username = Column(String(255), nullable=False)
    password = Column(String(500), nullable=False)
    ssl = Column(Boolean, default=False)
    pool_size = Column(Integer, default=10)
    timeout_seconds = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    health_status = Column(Boolean, nullable=True)
    health_latency_ms = Column(Integer, nullable=True)
    health_checked_at = Column(DateTime(timezone=True), nullable=True)
    schema_cache = Column(JSON, nullable=True)
    schema_cache_updated_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=False)
    company_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
