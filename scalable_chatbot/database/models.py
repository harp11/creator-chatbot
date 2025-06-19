from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from config import Config
import uuid

# Conditional UUID column type
def get_uuid_column():
    """Return appropriate UUID column type based on database"""
    if Config.is_sqlite():
        return String(36)  # SQLite doesn't support UUID natively
    else:
        return UUID(as_uuid=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    rate_limits = relationship("RateLimit", back_populates="user", cascade="all, delete-orphan")

class Creator(Base):
    __tablename__ = "creators"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    specialty = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    personality_config = Column(JSON, nullable=True)  # Store personality settings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sessions = relationship("UserSession", back_populates="creator")
    conversations = relationship("Conversation", back_populates="creator")
    
    # Indexes
    __table_args__ = (
        Index('idx_creators_slug', 'slug'),
        Index('idx_creators_active', 'is_active'),
    )

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), nullable=False)
    creator_id = Column(get_uuid_column(), ForeignKey("creators.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    creator = relationship("Creator", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_sessions_token', 'session_token'),
        Index('idx_sessions_user', 'user_id'),
        Index('idx_sessions_expires', 'expires_at'),
    )

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), nullable=False)
    creator_id = Column(get_uuid_column(), ForeignKey("creators.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    creator = relationship("Creator", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_conversations_user', 'user_id'),
        Index('idx_conversations_creator', 'creator_id'),
        Index('idx_conversations_updated', 'updated_at'),
    )

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(get_uuid_column(), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Store additional message metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_messages_conversation', 'conversation_id'),
        Index('idx_messages_created', 'created_at'),
        Index('idx_messages_role', 'role'),
    )

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), unique=True, nullable=False)
    channel_name = Column(String(255), nullable=True)
    subscriber_count = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    goals = Column(JSON, nullable=True)  # Array of goals
    equipment = Column(JSON, nullable=True)  # Array of equipment
    profile_data = Column(JSON, nullable=True)  # Additional profile data
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    # Indexes
    __table_args__ = (
        Index('idx_profiles_user', 'user_id'),
        Index('idx_profiles_channel', 'channel_name'),
    )

class RateLimit(Base):
    __tablename__ = "rate_limits"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), nullable=False)
    endpoint = Column(String(100), nullable=False)
    requests_count = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="rate_limits")
    
    # Indexes
    __table_args__ = (
        Index('idx_rate_limits_user_endpoint', 'user_id', 'endpoint'),
        Index('idx_rate_limits_window', 'window_start'),
    )

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), nullable=True)
    creator_id = Column(get_uuid_column(), ForeignKey("creators.id"), nullable=True)
    event_type = Column(String(50), nullable=False)  # 'message_sent', 'session_started', etc.
    event_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_user', 'user_id'),
        Index('idx_analytics_creator', 'creator_id'),
        Index('idx_analytics_event', 'event_type'),
        Index('idx_analytics_created', 'created_at'),
    )

class SystemHealth(Base):
    __tablename__ = "system_health"
    
    id = Column(get_uuid_column(), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # 'healthy', 'degraded', 'unhealthy'
    response_time = Column(Integer, nullable=True)  # in milliseconds
    error_count = Column(Integer, default=0)
    health_metadata = Column(JSON, nullable=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_health_service', 'service_name'),
        Index('idx_health_status', 'status'),
        Index('idx_health_checked', 'checked_at'),
    ) 