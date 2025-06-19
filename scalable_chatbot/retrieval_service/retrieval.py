import weaviate
import google.generativeai as genai
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from shared.models import RetrievalRequest, RetrievalResponse, ContextChunk, QueryAnalysis, QueryIntent, QueryComplexity
from config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class RetrievalConfig:
    creator_id: str
    max_chunks: int = 5
    similarity_threshold: float = 0.7
    retrieval_strategy: str = "balanced"

class WeaviateClient:
    """Weaviate client wrapper with connection management"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Weaviate client"""
        try:
            self.client = weaviate.Client(
                url=settings.weaviate.url,
                timeout_config=(5, 15),  # (connection, read) timeout
                additional_headers={
                    "X-OpenAI-Api-Key": settings.ai.google_api_key if hasattr(settings.ai, 'openai_key') else None
                }
            )
            logger.info(f"Weaviate client initialized: {settings.weaviate.url}")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Check if Weaviate is ready"""
        try:
            return self.client.is_ready()
        except Exception as e:
            logger.error(f"Weaviate readiness check failed: {e}")
            return False

class EmbeddingService:
    """Service for generating embeddings using Google AI"""
    
    def __init__(self):
        genai.configure(api_key=settings.ai.google_api_key)
        self.model_name = "models/embedding-001"
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text asynchronously"""
        try:
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                embedding = await loop.run_in_executor(
                    executor,
                    self._embed_text_sync,
                    text
                )
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def _embed_text_sync(self, text: str) -> List[float]:
        """Synchronous embedding generation"""
        result = genai.embed_content(
            model=self.model_name,
            content=text,
            task_type="retrieval_query"
        )
        return result['embedding']

class QueryAnalyzer:
    """Analyzes queries to determine intent and complexity"""
    
    def __init__(self):
        genai.configure(api_key=settings.ai.google_api_key)
        self.model = genai.GenerativeModel(settings.ai.model_name)
    
    async def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query intent and complexity"""
        try:
            # Run analysis in thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                analysis = await loop.run_in_executor(
                    executor,
                    self._analyze_query_sync,
                    query
                )
            return analysis
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            # Return default analysis
            return QueryAnalysis(
                intent=QueryIntent.QUESTION,
                complexity=QueryComplexity.SIMPLE,
                is_greeting=False,
                is_inappropriate=False,
                is_step_by_step=False,
                confidence=0.5
            )
    
    def _analyze_query_sync(self, query: str) -> QueryAnalysis:
        """Synchronous query analysis"""
        prompt = f"""Analyze this user query and classify it:

Query: "{query}"

Respond with a JSON object containing:
{{
    "intent": "greeting|question|how_to|personal_info|inappropriate",
    "complexity": "simple|complex",
    "is_greeting": boolean,
    "is_inappropriate": boolean,
    "is_step_by_step": boolean,
    "confidence": float (0.0-1.0)
}}

Classification rules:
- greeting: Simple greetings like "hi", "hello", "namaste"
- question: Information seeking queries
- how_to: Step-by-step instruction requests
- personal_info: Questions about user's personal information
- inappropriate: Sexual, offensive, or off-topic content
- simple: Short, straightforward queries
- complex: Long, multi-part queries
"""
        
        try:
            response = self.model.generate_content(prompt)
            # Parse JSON response
            import json
            result = json.loads(response.text.strip())
            
            return QueryAnalysis(
                intent=QueryIntent(result.get("intent", "question")),
                complexity=QueryComplexity(result.get("complexity", "simple")),
                is_greeting=result.get("is_greeting", False),
                is_inappropriate=result.get("is_inappropriate", False),
                is_step_by_step=result.get("is_step_by_step", False),
                confidence=result.get("confidence", 0.8)
            )
        except Exception as e:
            logger.error(f"Query analysis parsing failed: {e}")
            # Fallback to simple heuristics
            return self._fallback_analysis(query)
    
    def _fallback_analysis(self, query: str) -> QueryAnalysis:
        """Fallback analysis using simple heuristics"""
        query_lower = query.lower()
        
        # Check for greetings
        greetings = ["hi", "hello", "hey", "namaste", "hola"]
        is_greeting = any(greeting in query_lower for greeting in greetings)
        
        # Check for how-to questions
        is_step_by_step = "how to" in query_lower or "steps" in query_lower
        
        # Check for inappropriate content
        inappropriate_keywords = ["sex", "porn", "adult", "nsfw"]
        is_inappropriate = any(keyword in query_lower for keyword in inappropriate_keywords)
        
        # Determine intent
        if is_greeting:
            intent = QueryIntent.GREETING
        elif is_inappropriate:
            intent = QueryIntent.INAPPROPRIATE
        elif is_step_by_step:
            intent = QueryIntent.HOW_TO
        else:
            intent = QueryIntent.QUESTION
        
        # Determine complexity
        complexity = QueryComplexity.COMPLEX if len(query.split()) > 10 else QueryComplexity.SIMPLE
        
        return QueryAnalysis(
            intent=intent,
            complexity=complexity,
            is_greeting=is_greeting,
            is_inappropriate=is_inappropriate,
            is_step_by_step=is_step_by_step,
            confidence=0.7
        )

class IntelligentRetriever:
    """Stateless, scalable retrieval service"""
    
    def __init__(self):
        self.weaviate_client = WeaviateClient()
        self.embedding_service = EmbeddingService()
        self.query_analyzer = QueryAnalyzer()
    
    async def retrieve_context(self, request: RetrievalRequest) -> RetrievalResponse:
        """Retrieve relevant context for a query"""
        start_time = time.time()
        
        try:
            # Analyze query
            query_analysis = await self.query_analyzer.analyze_query(request.query)
            
            # Skip retrieval for greetings or inappropriate content
            if query_analysis.is_greeting or query_analysis.is_inappropriate:
                return RetrievalResponse(
                    chunks=[],
                    total_chunks=0,
                    creator_id=request.creator_id,
                    retrieval_strategy="skip"
                )
            
            # Generate embedding
            query_embedding = await self.embedding_service.embed_text(request.query)
            
            # Determine retrieval strategy
            strategy = self._determine_strategy(query_analysis, request)
            
            # Execute retrieval
            chunks = await self._execute_retrieval(
                query_embedding=query_embedding,
                creator_id=request.creator_id,
                strategy=strategy,
                max_chunks=request.max_chunks,
                similarity_threshold=request.similarity_threshold
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Retrieved {len(chunks)} chunks in {processing_time:.2f}s")
            
            return RetrievalResponse(
                chunks=[chunk.dict() for chunk in chunks],
                total_chunks=len(chunks),
                creator_id=request.creator_id,
                retrieval_strategy=strategy
            )
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return RetrievalResponse(
                chunks=[],
                total_chunks=0,
                creator_id=request.creator_id,
                retrieval_strategy="error"
            )
    
    def _determine_strategy(self, analysis: QueryAnalysis, request: RetrievalRequest) -> str:
        """Determine retrieval strategy based on query analysis"""
        if analysis.complexity == QueryComplexity.COMPLEX:
            return "comprehensive"
        elif analysis.intent == QueryIntent.HOW_TO:
            return "focused"
        elif analysis.is_step_by_step:
            return "structured"
        else:
            return "balanced"
    
    async def _execute_retrieval(
        self,
        query_embedding: List[float],
        creator_id: str,
        strategy: str,
        max_chunks: int,
        similarity_threshold: float
    ) -> List[ContextChunk]:
        """Execute retrieval based on strategy"""
        
        try:
            # Build Weaviate query
            query_builder = (
                self.weaviate_client.client.query
                .get("CreatorContent")
                .with_near_vector({
                    "vector": query_embedding,
                    "certainty": similarity_threshold
                })
                .with_where({
                    "path": ["creator_id"],
                    "operator": "Equal",
                    "valueString": creator_id
                })
                .with_limit(max_chunks)
                .with_additional(["certainty", "distance"])
            )
            
            # Execute query
            result = query_builder.do()
            
            # Process results
            chunks = []
            if result.get("data", {}).get("Get", {}).get("CreatorContent"):
                for item in result["data"]["Get"]["CreatorContent"]:
                    certainty = item.get("_additional", {}).get("certainty", 0)
                    
                    if certainty >= similarity_threshold:
                        chunk = ContextChunk(
                            content=item.get("content", ""),
                            source=item.get("source", "unknown"),
                            similarity=certainty,
                            creator_id=creator_id,
                            metadata=item.get("metadata", {})
                        )
                        chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Weaviate query failed: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the retrieval service"""
        try:
            is_ready = self.weaviate_client.is_ready()
            return {
                "status": "healthy" if is_ready else "unhealthy",
                "weaviate_ready": is_ready,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            } 