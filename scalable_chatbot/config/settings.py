import os
from typing import Dict, Any
from shared.models import (
    DatabaseConfig, RedisConfig, WeaviateConfig, 
    ServiceConfig, RateLimitConfig, AIConfig
)

class Settings:
    """Centralized configuration management"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Database Configuration
        self.database = DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "chatbot"),
            username=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASSWORD", "password")
        )
        
        # Redis Configuration
        self.redis = RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD")
        )
        
        # Weaviate Configuration
        self.weaviate = WeaviateConfig(
            host=os.getenv("WEAVIATE_HOST", "localhost"),
            port=int(os.getenv("WEAVIATE_PORT", "8080"))
        )
        
        # AI Configuration
        self.ai = AIConfig(
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            model_name=os.getenv("AI_MODEL_NAME", "gemini-1.5-flash"),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.7"))
        )
        
        # Rate Limiting
        self.rate_limit = RateLimitConfig(
            max_requests=int(os.getenv("RATE_LIMIT_MAX", "100")),
            window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "3600"))
        )
        
        # Service Configurations
        self.services = {
            "api_gateway": ServiceConfig(
                name="api_gateway",
                port=int(os.getenv("API_GATEWAY_PORT", "8000")),
                workers=int(os.getenv("API_GATEWAY_WORKERS", "4"))
            ),
            "chat_service": ServiceConfig(
                name="chat_service",
                port=int(os.getenv("CHAT_SERVICE_PORT", "8001")),
                workers=int(os.getenv("CHAT_SERVICE_WORKERS", "8"))
            ),
            "creator_service": ServiceConfig(
                name="creator_service",
                port=int(os.getenv("CREATOR_SERVICE_PORT", "8002")),
                workers=int(os.getenv("CREATOR_SERVICE_WORKERS", "4"))
            ),
            "retrieval_service": ServiceConfig(
                name="retrieval_service",
                port=int(os.getenv("RETRIEVAL_SERVICE_PORT", "8003")),
                workers=int(os.getenv("RETRIEVAL_SERVICE_WORKERS", "6"))
            )
        }
        
        # Service URLs (for inter-service communication)
        self.service_urls = {
            "chat_service": os.getenv("CHAT_SERVICE_URL", "http://chat-service:8001"),
            "creator_service": os.getenv("CREATOR_SERVICE_URL", "http://creator-service:8002"),
            "retrieval_service": os.getenv("RETRIEVAL_SERVICE_URL", "http://retrieval-service:8003")
        }
        
        # Security
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
        
        # CORS
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = os.getenv("LOG_FORMAT", "json")
        
        # Performance
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        
        # Vector Store
        self.vector_store_collection_prefix = os.getenv("VECTOR_STORE_PREFIX", "creator_")
        
        # Content Processing
        self.max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        
    def get_service_config(self, service_name: str) -> ServiceConfig:
        """Get configuration for a specific service"""
        return self.services.get(service_name)
    
    def get_service_url(self, service_name: str) -> str:
        """Get URL for a specific service"""
        return self.service_urls.get(service_name)
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"

# Global settings instance
settings = Settings()

# Creator configurations (can be moved to database later)
CREATORS = {
    "hawa_singh": {
        "id": "hawa_singh",
        "name": "Hawa Singh",
        "slug": "hawa-singh",
        "specialty": "YouTube Growth Expert",
        "description": "Expert in YouTube channel growth, content strategy, and creator monetization",
        "avatar_url": "/avatars/hawa_singh.jpg",
        "is_active": True,
        "personality": {
            "tone": "friendly_expert",
            "language_style": "hinglish",
            "expertise_areas": [
                "youtube_growth", "content_strategy", "monetization",
                "thumbnails", "seo", "analytics", "audience_building"
            ]
        }
    }
    # Add more creators here as needed
}

def get_creator_config(creator_id: str) -> Dict[str, Any]:
    """Get configuration for a specific creator"""
    return CREATORS.get(creator_id, {})

def get_all_creators() -> Dict[str, Dict[str, Any]]:
    """Get all creator configurations"""
    return CREATORS 