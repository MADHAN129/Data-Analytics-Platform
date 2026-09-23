from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    layout_config = Column(JSON, default=lambda: {"columns": 12})
    is_template = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    auto_generated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", backref="dashboards")
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan", order_by="DashboardWidget.position_y, DashboardWidget.position_x")


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=False)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=True)
    widget_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=6)
    height = Column(Integer, default=4)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    dashboard = relationship("Dashboard", back_populates="widgets")
    query = relationship("Query", backref="widgets")
