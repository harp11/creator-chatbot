from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class QueryIntent(str, Enum):
    GREETING = "greeting"
    QUESTION = "question"
    HOW_TO = "how_to"
    PERSONAL_INFO = "personal_info"
    INAPPROPRIATE = "inappropriate"

class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"

# Database Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Creator(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str
    specialty: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    channel_name: Optional[str] = None
    subscriber_count: Optional[int] = None
    content_type: Optional[str] = None
    goals: List[str] = []
    equipment: List[str] = []
    profile_data: Dict[str, Any] = {}
    updated_at: datetime = Field(default_factory=datetime.now)

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    creator_id: str
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    creator_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)

# API Request/Response Models
class ChatRequest(BaseModel):
    user_id: str
    creator_id: str
    message: str
    conversation_id: Optional[str] = None
    session_token: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    context_used: int
    intent: QueryIntent
    processing_time: float

class RetrievalRequest(BaseModel):
    query: str
    creator_id: str
    max_chunks: int = 5
    similarity_threshold: float = 0.7

class RetrievalResponse(BaseModel):
    chunks: List[Dict[str, Any]]
    total_chunks: int
    creator_id: str
    retrieval_strategy: str

class ContextChunk(BaseModel):
    content: str
    source: str
    similarity: float
    creator_id: str
    metadata: Dict[str, Any] = {}

class QueryAnalysis(BaseModel):
    intent: QueryIntent
    complexity: QueryComplexity
    is_greeting: bool
    is_inappropriate: bool
    is_step_by_step: bool
    confidence: float

# Configuration Models
class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    database: str = "chatbot"
    username: str = "user"
    password: str = "password"
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None

class WeaviateConfig(BaseModel):
    host: str = "localhost"
    port: int = 8080
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

class ServiceConfig(BaseModel):
    name: str
    host: str = "0.0.0.0"
    port: int
    debug: bool = False
    workers: int = 1
    
class RateLimitConfig(BaseModel):
    max_requests: int = 100
    window_seconds: int = 3600
    
class AIConfig(BaseModel):
    google_api_key: str
    model_name: str = "gemini-1.5-flash"
    max_tokens: int = 2048
    temperature: float = 0.7 