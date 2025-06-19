from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from typing import Dict, Any
from shared.models import RetrievalRequest, RetrievalResponse
from retrieval_service.retrieval import IntelligentRetriever
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Retrieval Service",
    description="Scalable context retrieval service for creator chatbots",
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

# Global retriever instance (not singleton, just a service instance)
retriever = IntelligentRetriever()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Retrieval Service starting up...")
    
    # Perform health check
    health = await retriever.health_check()
    if health["status"] != "healthy":
        logger.error(f"Service unhealthy on startup: {health}")
        raise Exception("Service failed health check on startup")
    
    logger.info("Retrieval Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Retrieval Service shutting down...")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health = await retriever.health_check()
        if health["status"] == "healthy":
            return health
        else:
            raise HTTPException(status_code=503, detail=health)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "error": str(e)})

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        health = await retriever.health_check()
        if health["status"] == "healthy":
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail={"status": "not_ready"})
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "error": str(e)})

@app.post("/retrieve", response_model=RetrievalResponse)
async def retrieve_context(request: RetrievalRequest):
    """Retrieve relevant context for a query"""
    start_time = time.time()
    
    try:
        logger.info(f"Retrieving context for creator: {request.creator_id}, query: {request.query[:100]}...")
        
        # Validate request
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not request.creator_id:
            raise HTTPException(status_code=400, detail="Creator ID is required")
        
        # Perform retrieval
        response = await retriever.retrieve_context(request)
        
        processing_time = time.time() - start_time
        logger.info(f"Retrieved {response.total_chunks} chunks in {processing_time:.2f}s")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    """Get service metrics"""
    try:
        health = await retriever.health_check()
        return {
            "service": "retrieval_service",
            "status": health["status"],
            "timestamp": time.time(),
            "uptime": time.time() - startup_time if 'startup_time' in globals() else 0
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {
            "service": "retrieval_service",
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Retrieval Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "retrieve": "/retrieve",
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics"
        }
    }

# Store startup time for metrics
startup_time = time.time()

if __name__ == "__main__":
    import uvicorn
    
    config = settings.get_service_config("retrieval_service")
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 