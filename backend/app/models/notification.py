from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, func
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    company_id = Column(Integer, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="security_alert", index=True)
    severity = Column(String(20), default="high")
    is_read = Column(Boolean, default=False, index=True)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
