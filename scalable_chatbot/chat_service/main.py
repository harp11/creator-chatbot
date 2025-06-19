from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import logging
import time
import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session
from database.connection import get_db, db_manager
from shared.models import ChatRequest, ChatResponse
from chat_service.chat_processor import ChatProcessor
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Chat Service",
    description="Scalable chat processing service for creator chatbots",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis for rate limiting
redis_client = redis.Redis(
    host=settings.redis.host,
    port=settings.redis.port,
    db=settings.redis.db,
    password=settings.redis.password,
    decode_responses=True
)

# Security
security = HTTPBearer(auto_error=False)

# Global chat processor
chat_processor = ChatProcessor()

class RateLimiter:
    """Rate limiting middleware"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        try:
            key = f"rate_limit:{user_id}"
            current = redis_client.get(key)
            
            if current is None:
                # First request in window
                redis_client.setex(key, self.window_seconds, 1)
                return True
            
            if int(current) >= self.max_requests:
                return False
            
            # Increment counter
            redis_client.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Allow request if Redis is down
            return True

rate_limiter = RateLimiter(
    max_requests=settings.rate_limit.max_requests,
    window_seconds=settings.rate_limit.window_seconds
)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from token (simplified for demo)"""
    if not credentials:
        # For demo purposes, use a default user ID
        return "demo_user"
    
    # In production, validate JWT token and extract user ID
    # For now, use token as user ID
    return credentials.credentials

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Chat Service starting up...")
    
    try:
        # Initialize database
        db_manager.initialize_sync_db()
        await db_manager.initialize_async_db()
        
        # Test Redis connection
        redis_client.ping()
        
        logger.info("Chat Service started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Chat Service shutting down...")
    await db_manager.close_connections()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        with db_manager.get_db_session() as db:
            db.execute("SELECT 1")
        
        # Check Redis
        redis_client.ping()
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": time.time()
            }
        )

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        # Quick health check
        with db_manager.get_db_session() as db:
            db.execute("SELECT 1")
        
        return {"status": "ready"}
        
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail={"status": "not_ready", "error": str(e)}
        )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process chat message"""
    start_time = time.time()
    
    try:
        # Override user_id from auth
        request.user_id = user_id
        
        logger.info(f"Processing chat for user: {user_id}, creator: {request.creator_id}")
        
        # Rate limiting
        if not await rate_limiter.check_rate_limit(user_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Validate request
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if not request.creator_id:
            raise HTTPException(status_code=400, detail="Creator ID is required")
        
        # Process chat
        response = await chat_processor.process_chat(request, db)
        
        processing_time = time.time() - start_time
        logger.info(f"Chat processed in {processing_time:.2f}s")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 20,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages from a conversation"""
    try:
        from database.models import Message, Conversation
        
        # Verify user owns the conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in reversed(messages)
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")

@app.get("/users/{user_id}/conversations")
async def get_user_conversations(
    user_id: str,
    limit: int = 20,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's conversations"""
    try:
        # Verify user can access these conversations
        if user_id != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
        from database.models import Conversation
        
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).limit(limit).all()
        
        return {
            "user_id": user_id,
            "conversations": [
                {
                    "id": str(conv.id),
                    "creator_id": str(conv.creator_id),
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                }
                for conv in conversations
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")

@app.get("/metrics")
async def get_metrics():
    """Get service metrics"""
    try:
        # Get basic metrics
        return {
            "service": "chat_service",
            "status": "running",
            "timestamp": time.time(),
            "uptime": time.time() - startup_time if 'startup_time' in globals() else 0,
            "database_status": "connected",
            "redis_status": "connected"
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {
            "service": "chat_service",
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Chat Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/chat",
            "conversations": "/conversations/{conversation_id}/messages",
            "user_conversations": "/users/{user_id}/conversations",
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics"
        }
    }

# Store startup time for metrics
startup_time = time.time()

if __name__ == "__main__":
    import uvicorn
    
    config = settings.get_service_config("chat_service")
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 