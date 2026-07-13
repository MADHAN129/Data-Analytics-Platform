from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    database_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    context = Column(JSON, default={})
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", backref="conversations")
    database = relationship("DatabaseConnection", backref="conversations")
    messages = relationship("ConversationMessage", backref="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.created_at")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
