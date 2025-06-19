# 🚀 Scalable YouTube Creator Chatbot Architecture

## Current Problems ❌

### 1. Singleton Pattern Bottlenecks
- `IntelligentRetriever` and `CreatorVectorStore` use singleton patterns
- Only ONE instance per process = no horizontal scaling
- Shared state corruption across users

### 2. Streamlit Session State Issues
- All data in `st.session_state` (memory-only)
- Single-threaded, per-session storage
- Lost on restart, no persistence

### 3. Hardcoded Single Creator
- Everything assumes "hawa_singh"
- Not multi-tenant ready
- Cannot support multiple creators

### 4. No Proper Database Layer
- Only ChromaDB for vectors
- No user management, session persistence
- Cannot track analytics or scale data

## 🏗️ Proposed Scalable Architecture

### 1. **Multi-Tier Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│  API Gateway    │────│   Frontend      │
│   (nginx/ALB)   │    │  (FastAPI)      │    │  (React/Vue)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
            ┌─────────────────┐ ┌─────────────────┐
            │  Chat Service   │ │ Creator Service │
            │  (FastAPI)      │ │  (FastAPI)      │
            └─────────────────┘ └─────────────────┘
                       │                 │
            ┌─────────────────┐ ┌─────────────────┐
            │  Vector Store   │ │   Database      │
            │  (Weaviate)     │ │ (PostgreSQL)    │
            └─────────────────┘ └─────────────────┘
```

### 2. **Database Schema**

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Creators table
CREATE TABLE creators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    specialty VARCHAR(255),
    description TEXT,
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    creator_id UUID REFERENCES creators(id),
    session_token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    creator_id UUID REFERENCES creators(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User profiles
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) UNIQUE,
    channel_name VARCHAR(255),
    subscriber_count INTEGER,
    content_type VARCHAR(100),
    goals TEXT[],
    equipment TEXT[],
    profile_data JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rate limiting
CREATE TABLE rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    endpoint VARCHAR(100),
    requests_count INTEGER DEFAULT 0,
    window_start TIMESTAMP DEFAULT NOW(),
    INDEX idx_rate_limits_user_endpoint (user_id, endpoint)
);
```

### 3. **Microservices Architecture**

#### A. **API Gateway Service**
```python
# api_gateway/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import redis
from typing import Dict, Any

app = FastAPI(title="Creator Chatbot API Gateway")

# Redis for caching and rate limiting
redis_client = redis.Redis(host='redis', port=6379, db=0)

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def check_rate_limit(self, user_id: str) -> bool:
        key = f"rate_limit:{user_id}"
        current = redis_client.get(key)
        
        if current is None:
            redis_client.setex(key, self.window_seconds, 1)
            return True
        
        if int(current) >= self.max_requests:
            return False
        
        redis_client.incr(key)
        return True

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    user_id = request.headers.get("X-User-ID")
    if user_id:
        rate_limiter = RateLimiter()
        if not await rate_limiter.check_rate_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    response = await call_next(request)
    return response

# Route to chat service
@app.post("/api/v1/chat")
async def chat_proxy(request: Dict[Any, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://chat-service:8001/chat",
            json=request
        )
        return response.json()
```

#### B. **Chat Service**
```python
# chat_service/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI(title="Chat Service")

class ChatService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def process_message(
        self, 
        user_id: str, 
        creator_id: str, 
        message: str,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        
        # Run AI processing in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._process_message_sync,
            user_id, creator_id, message, conversation_id
        )
        return result
    
    def _process_message_sync(
        self, 
        user_id: str, 
        creator_id: str, 
        message: str,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        
        # 1. Get user context from database
        user_profile = self.get_user_profile(user_id)
        
        # 2. Retrieve relevant context (non-singleton)
        retriever = IntelligentRetriever(creator_id=creator_id)
        context = retriever.retrieve_context(message)
        
        # 3. Generate response
        response = self.generate_response(message, context, user_profile)
        
        # 4. Save to database
        self.save_message(user_id, creator_id, message, response, conversation_id)
        
        return {
            "response": response,
            "conversation_id": conversation_id,
            "context_used": len(context.get("chunks", []))
        }

chat_service = ChatService()

@app.post("/chat")
async def chat_endpoint(request: Dict[str, Any]):
    return await chat_service.process_message(
        user_id=request["user_id"],
        creator_id=request["creator_id"],
        message=request["message"],
        conversation_id=request.get("conversation_id")
    )
```

#### C. **Scalable Retrieval Service**
```python
# retrieval_service/retrieval.py
from typing import Dict, List, Any, Optional
import weaviate
from dataclasses import dataclass

@dataclass
class RetrievalConfig:
    creator_id: str
    max_chunks: int = 5
    similarity_threshold: float = 0.7

class IntelligentRetriever:
    """Non-singleton, stateless retriever"""
    
    def __init__(self, creator_id: str):
        self.creator_id = creator_id
        self.client = weaviate.Client("http://weaviate:8080")
    
    def retrieve_context(self, query: str, config: RetrievalConfig = None) -> Dict[str, Any]:
        """Stateless context retrieval"""
        if config is None:
            config = RetrievalConfig(creator_id=self.creator_id)
        
        # Vector search in Weaviate
        result = (
            self.client.query
            .get("CreatorContent")
            .with_near_text({"concepts": [query]})
            .with_where({
                "path": ["creator_id"],
                "operator": "Equal",
                "valueString": config.creator_id
            })
            .with_limit(config.max_chunks)
            .with_additional(["distance"])
            .do()
        )
        
        chunks = []
        if result.get("data", {}).get("Get", {}).get("CreatorContent"):
            for item in result["data"]["Get"]["CreatorContent"]:
                if item["_additional"]["distance"] <= config.similarity_threshold:
                    chunks.append({
                        "content": item["content"],
                        "source": item["source"],
                        "similarity": 1 - item["_additional"]["distance"]
                    })
        
        return {
            "chunks": chunks,
            "total_chunks": len(chunks),
            "creator_id": config.creator_id
        }
```

### 4. **Container Orchestration (Docker Compose)**

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api-gateway

  # API Gateway
  api-gateway:
    build: ./api_gateway
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@postgres:5432/chatbot
    depends_on:
      - redis
      - postgres

  # Chat Service (Multiple instances)
  chat-service:
    build: ./chat_service
    ports:
      - "8001-8003:8001"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/chatbot
      - WEAVIATE_URL=http://weaviate:8080
    depends_on:
      - postgres
      - weaviate
    deploy:
      replicas: 3

  # Creator Service
  creator-service:
    build: ./creator_service
    ports:
      - "8004:8004"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/chatbot
    depends_on:
      - postgres

  # Vector Database (Weaviate)
  weaviate:
    image: semitechnologies/weaviate:latest
    ports:
      - "8080:8080"
    environment:
      - QUERY_DEFAULTS_LIMIT=25
      - AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate
    volumes:
      - weaviate_data:/var/lib/weaviate

  # PostgreSQL Database
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=chatbot
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis for caching and rate limiting
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Frontend (React/Vue)
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://api-gateway:8000
    depends_on:
      - api-gateway

volumes:
  postgres_data:
  weaviate_data:
  redis_data:
```

### 5. **Kubernetes Deployment (Production)**

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chat-service
spec:
  replicas: 10  # Scale based on load
  selector:
    matchLabels:
      app: chat-service
  template:
    metadata:
      labels:
        app: chat-service
    spec:
      containers:
      - name: chat-service
        image: chatbot/chat-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: chat-service
spec:
  selector:
    app: chat-service
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: chat-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: chat-service
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 🚀 Scaling Benefits

### 1. **Horizontal Scaling**
- Multiple service instances
- Auto-scaling based on load
- No singleton bottlenecks

### 2. **Multi-Tenancy**
- Support unlimited creators
- Isolated user data
- Per-creator customization

### 3. **High Availability**
- Service redundancy
- Database replication
- Graceful failure handling

### 4. **Performance**
- Async processing
- Connection pooling
- Caching layers
- CDN for static assets

### 5. **Monitoring & Observability**
- Prometheus metrics
- Grafana dashboards
- Distributed tracing
- Log aggregation

## 📊 Performance Targets

- **Concurrent Users**: 10,000+
- **Response Time**: <2 seconds
- **Throughput**: 1,000 requests/second
- **Uptime**: 99.9%
- **Auto-scaling**: 0-50 instances based on load

## 🔄 Migration Strategy

1. **Phase 1**: Database setup and API gateway
2. **Phase 2**: Extract services from monolith
3. **Phase 3**: Implement caching and rate limiting
4. **Phase 4**: Container orchestration
5. **Phase 5**: Kubernetes deployment
6. **Phase 6**: Monitoring and optimization

This architecture eliminates all singleton patterns, provides true horizontal scaling, and supports unlimited creators and users simultaneously. 