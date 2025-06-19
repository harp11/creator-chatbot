from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import redis
import logging
import time
import json
from typing import Dict, Any, Optional
from shared.models import ChatRequest, ChatResponse
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Creator Chatbot API Gateway",
    description="API Gateway for scalable creator chatbot microservices",
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

# Initialize Redis for caching and rate limiting
redis_client = redis.Redis(
    host=settings.redis.host,
    port=settings.redis.port,
    db=settings.redis.db,
    password=settings.redis.password,
    decode_responses=True
)

# Security
security = HTTPBearer(auto_error=False)

class LoadBalancer:
    """Simple round-robin load balancer for services"""
    
    def __init__(self):
        self.service_instances = {
            "chat_service": [
                "http://chat-service-1:8001",
                "http://chat-service-2:8001",
                "http://chat-service-3:8001"
            ],
            "retrieval_service": [
                "http://retrieval-service-1:8003",
                "http://retrieval-service-2:8003"
            ]
        }
        self.current_index = {service: 0 for service in self.service_instances}
    
    def get_service_url(self, service_name: str) -> str:
        """Get next available service instance URL"""
        if service_name not in self.service_instances:
            # Fallback to settings
            return settings.get_service_url(service_name)
        
        instances = self.service_instances[service_name]
        current_idx = self.current_index[service_name]
        
        # Round-robin selection
        url = instances[current_idx]
        self.current_index[service_name] = (current_idx + 1) % len(instances)
        
        return url

load_balancer = LoadBalancer()

class RateLimiter:
    """Advanced rate limiting with different tiers"""
    
    def __init__(self):
        self.limits = {
            "free": {"requests": 50, "window": 3600},      # 50/hour
            "premium": {"requests": 500, "window": 3600},   # 500/hour
            "enterprise": {"requests": 5000, "window": 3600} # 5000/hour
        }
    
    async def check_rate_limit(self, user_id: str, tier: str = "free") -> Dict[str, Any]:
        """Check rate limit and return status"""
        try:
            limit_config = self.limits.get(tier, self.limits["free"])
            key = f"rate_limit:{tier}:{user_id}"
            
            current = redis_client.get(key)
            
            if current is None:
                # First request in window
                redis_client.setex(key, limit_config["window"], 1)
                return {
                    "allowed": True,
                    "remaining": limit_config["requests"] - 1,
                    "reset_time": time.time() + limit_config["window"]
                }
            
            current_count = int(current)
            
            if current_count >= limit_config["requests"]:
                ttl = redis_client.ttl(key)
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": time.time() + ttl,
                    "retry_after": ttl
                }
            
            # Increment counter
            redis_client.incr(key)
            
            return {
                "allowed": True,
                "remaining": limit_config["requests"] - current_count - 1,
                "reset_time": time.time() + redis_client.ttl(key)
            }
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Allow request if Redis is down
            return {"allowed": True, "remaining": 999, "reset_time": time.time() + 3600}

rate_limiter = RateLimiter()

class CircuitBreaker:
    """Circuit breaker for service resilience"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = {}
        self.last_failure_time = {}
        self.state = {}  # "closed", "open", "half-open"
    
    def is_available(self, service_name: str) -> bool:
        """Check if service is available"""
        current_state = self.state.get(service_name, "closed")
        
        if current_state == "closed":
            return True
        elif current_state == "open":
            # Check if recovery timeout has passed
            last_failure = self.last_failure_time.get(service_name, 0)
            if time.time() - last_failure > self.recovery_timeout:
                self.state[service_name] = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self, service_name: str):
        """Record successful request"""
        self.failure_count[service_name] = 0
        self.state[service_name] = "closed"
    
    def record_failure(self, service_name: str):
        """Record failed request"""
        self.failure_count[service_name] = self.failure_count.get(service_name, 0) + 1
        self.last_failure_time[service_name] = time.time()
        
        if self.failure_count[service_name] >= self.failure_threshold:
            self.state[service_name] = "open"
            logger.warning(f"Circuit breaker opened for {service_name}")

circuit_breaker = CircuitBreaker()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Extract user information from token"""
    if not credentials:
        return {
            "user_id": "anonymous",
            "tier": "free",
            "permissions": ["chat"]
        }
    
    # In production, validate JWT token
    # For demo, parse simple token format: "user_id:tier"
    try:
        parts = credentials.credentials.split(":")
        user_id = parts[0] if len(parts) > 0 else "demo_user"
        tier = parts[1] if len(parts) > 1 else "free"
        
        return {
            "user_id": user_id,
            "tier": tier,
            "permissions": ["chat", "history"]
        }
    except:
        return {
            "user_id": "demo_user",
            "tier": "free",
            "permissions": ["chat"]
        }

@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Add rate limiting headers to responses"""
    response = await call_next(request)
    
    # Add standard rate limit headers
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Window"] = "3600"
    
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize gateway on startup"""
    logger.info("API Gateway starting up...")
    
    try:
        # Test Redis connection
        redis_client.ping()
        
        # Test service connections
        async with httpx.AsyncClient() as client:
            for service_name in ["chat_service", "retrieval_service"]:
                try:
                    url = load_balancer.get_service_url(service_name)
                    response = await client.get(f"{url}/health", timeout=5.0)
                    if response.status_code == 200:
                        logger.info(f"{service_name} is healthy")
                    else:
                        logger.warning(f"{service_name} health check failed: {response.status_code}")
                except Exception as e:
                    logger.error(f"Failed to connect to {service_name}: {e}")
        
        logger.info("API Gateway started successfully")
        
    except Exception as e:
        logger.error(f"Gateway startup failed: {e}")
        raise

@app.get("/health")
async def health_check():
    """Gateway health check"""
    try:
        # Check Redis
        redis_client.ping()
        
        # Check downstream services
        service_health = {}
        async with httpx.AsyncClient() as client:
            for service_name in ["chat_service", "retrieval_service"]:
                try:
                    url = load_balancer.get_service_url(service_name)
                    response = await client.get(f"{url}/health", timeout=5.0)
                    service_health[service_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time": response.elapsed.total_seconds()
                    }
                except Exception as e:
                    service_health[service_name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
        
        return {
            "status": "healthy",
            "gateway": "running",
            "redis": "connected",
            "services": service_health,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "error": str(e)})

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_proxy(
    request: ChatRequest,
    user_info: Dict[str, Any] = Depends(get_current_user)
):
    """Proxy chat requests to chat service"""
    start_time = time.time()
    
    try:
        # Rate limiting
        rate_limit_result = await rate_limiter.check_rate_limit(
            user_info["user_id"], 
            user_info["tier"]
        )
        
        if not rate_limit_result["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": rate_limit_result.get("retry_after", 3600)
                },
                headers={
                    "Retry-After": str(rate_limit_result.get("retry_after", 3600)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(rate_limit_result["reset_time"]))
                }
            )
        
        # Check circuit breaker
        if not circuit_breaker.is_available("chat_service"):
            raise HTTPException(
                status_code=503,
                detail="Chat service is temporarily unavailable"
            )
        
        # Override user_id from auth
        request.user_id = user_info["user_id"]
        
        # Get service URL
        service_url = load_balancer.get_service_url("chat_service")
        
        # Forward request to chat service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/chat",
                json=request.dict(),
                headers={
                    "Authorization": f"Bearer {user_info['user_id']}:{user_info['tier']}",
                    "X-Request-ID": str(time.time())
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                circuit_breaker.record_success("chat_service")
                result = response.json()
                
                # Add gateway metadata
                result["gateway_processing_time"] = time.time() - start_time
                result["rate_limit_remaining"] = rate_limit_result["remaining"]
                
                return result
            else:
                circuit_breaker.record_failure("chat_service")
                logger.error(f"Chat service error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Chat service error: {response.text}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        circuit_breaker.record_failure("chat_service")
        logger.error(f"Chat proxy failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gateway error: {str(e)}")

@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_conversation_messages_proxy(
    conversation_id: str,
    limit: int = 20,
    user_info: Dict[str, Any] = Depends(get_current_user)
):
    """Proxy conversation messages request"""
    try:
        # Check permissions
        if "history" not in user_info["permissions"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        service_url = load_balancer.get_service_url("chat_service")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{service_url}/conversations/{conversation_id}/messages",
                params={"limit": limit},
                headers={
                    "Authorization": f"Bearer {user_info['user_id']}:{user_info['tier']}"
                },
                timeout=15.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Conversation messages proxy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}/conversations")
async def get_user_conversations_proxy(
    user_id: str,
    limit: int = 20,
    user_info: Dict[str, Any] = Depends(get_current_user)
):
    """Proxy user conversations request"""
    try:
        # Verify user can access these conversations
        if user_id != user_info["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        service_url = load_balancer.get_service_url("chat_service")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{service_url}/users/{user_id}/conversations",
                params={"limit": limit},
                headers={
                    "Authorization": f"Bearer {user_info['user_id']}:{user_info['tier']}"
                },
                timeout=15.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User conversations proxy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/creators")
async def get_creators():
    """Get available creators"""
    from config.settings import get_all_creators
    
    creators = get_all_creators()
    return {
        "creators": [
            {
                "id": creator_id,
                "name": config["name"],
                "slug": config["slug"],
                "specialty": config["specialty"],
                "description": config["description"],
                "avatar_url": config["avatar_url"],
                "is_active": config["is_active"]
            }
            for creator_id, config in creators.items()
            if config.get("is_active", True)
        ]
    }

@app.get("/api/v1/metrics")
async def get_gateway_metrics():
    """Get gateway metrics"""
    try:
        return {
            "gateway": {
                "status": "running",
                "uptime": time.time() - startup_time if 'startup_time' in globals() else 0,
                "requests_processed": "N/A",  # Would track in production
                "error_rate": "N/A"
            },
            "circuit_breakers": {
                service: {
                    "state": circuit_breaker.state.get(service, "closed"),
                    "failure_count": circuit_breaker.failure_count.get(service, 0)
                }
                for service in ["chat_service", "retrieval_service"]
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {"error": str(e), "timestamp": time.time()}

@app.get("/")
async def root():
    """Gateway root endpoint"""
    return {
        "service": "Creator Chatbot API Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/v1/chat",
            "conversations": "/api/v1/conversations/{conversation_id}/messages",
            "user_conversations": "/api/v1/users/{user_id}/conversations",
            "creators": "/api/v1/creators",
            "health": "/health",
            "metrics": "/api/v1/metrics"
        },
        "documentation": "/docs"
    }

# Store startup time for metrics
startup_time = time.time()

if __name__ == "__main__":
    import uvicorn
    
    config = settings.get_service_config("api_gateway")
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 