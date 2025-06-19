from typing import Dict, List, Any, Optional
from src.embeddings import GeminiEmbedder, calculate_similarity
from src.vector_store import CreatorVectorStore
from src.query_analyzer import QueryAnalyzer, QueryIntent, QueryComplexity
import config
import time

class IntelligentRetriever:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            print("🔄 Creating new IntelligentRetriever instance")
            cls._instance = super(IntelligentRetriever, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        print("🔄 Initializing IntelligentRetriever")
        self.embedder = GeminiEmbedder()
        self.vector_store = CreatorVectorStore()
        self.query_analyzer = QueryAnalyzer()
        self.last_query_time = 0
        self.min_query_interval = 2  # Minimum seconds between queries
        
        # Load existing collections
        self._load_existing_collections()
        self._initialized = True
    
    def _load_existing_collections(self):
        """Load existing creator collections"""
        for creator_id in config.CREATORS.keys():
            try:
                collection_name = f"creator_{creator_id}"
                collection = self.vector_store.client.get_collection(name=collection_name)
                self.vector_store.collections[creator_id] = collection
                print(f"📂 Loaded collection for {creator_id}")
            except:
                print(f"⚠️ No collection found for {creator_id}")
    
    def retrieve_context(self, query: str, creator_id: str = "hawa_singh") -> Dict[str, Any]:
        """Retrieve relevant context for a query"""
        # Rate limiting
        current_time = time.time()
        time_since_last_query = current_time - self.last_query_time
        if time_since_last_query < self.min_query_interval:
            time.sleep(self.min_query_interval - time_since_last_query)
        
        # Update last query time
        self.last_query_time = time.time()
        
        # Analyze query
        query_type = self._analyze_query(query)
        print(f"🔍 Query Analysis: {', '.join(query_type)}")
        
        try:
            # Get embedding for query
            query_embedding = self.embedder.embed_text({"content": query})
            
            # Choose retrieval strategy based on query type
            if "specific" in query_type:
                n_results = 2
                strategy = "focused_search"
            elif "how_to" in query_type:
                n_results = 3
                strategy = "focused_search"
            else:
                n_results = 3
                strategy = "balanced_search"
                
            print(f"🎯 Retrieval Strategy: {strategy}")
            
            # Search vector store
            results = self.vector_store.search_creator(
                creator_id=creator_id,
                query_embedding=query_embedding,
                n_results=n_results
            )
            
            # Process results
            chunks = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    chunk = {
                        "content": results["documents"][0][i],
                        "creator_id": creator_id,
                        "similarity": 1 - (results["distances"][0][i] if results["distances"] else 0),
                        "source": results["metadatas"][0][i]["source"] if results["metadatas"] else "unknown"
                    }
                    chunks.append(chunk)
            
            return {
                "retrieval_strategy": strategy,
                "total_chunks": len(chunks),
                "context": {
                    "chunks": chunks,
                    "best_creator": creator_id if chunks else None
                }
            }
            
        except Exception as e:
            print(f"❌ Retrieval error: {str(e)}")
            if "429" in str(e):
                raise Exception("Rate limit exceeded. Please wait a moment and try again.")
            elif "embedding" in str(e).lower():
                raise Exception("Unable to process your query. Please try rephrasing it.")
            else:
                raise Exception("An error occurred while retrieving context. Please try again.")
    
    def _analyze_query(self, query: str) -> List[str]:
        """Analyze query to determine type"""
        query = query.lower()
        query_types = []
        
        # Check for specific questions
        if any(word in query for word in ["what", "how", "why", "when", "where", "which"]):
            query_types.append("specific")
            
        # Check for how-to questions
        if "how" in query and "to" in query:
            query_types.append("how_to")
            
        # Default to general if no specific types found
        if not query_types:
            query_types.append("general")
            
        # Add complexity indicator
        if len(query.split()) > 10:
            query_types.append("complex")
        else:
            query_types.append("simple")
            
        return query_types
    
    def _determine_retrieval_strategy(self, query_analysis: Dict[str, Any]) -> str:
        """Determine the best retrieval strategy based on query analysis"""
        intent = query_analysis["intent"]
        complexity = query_analysis["complexity"]
        
        if complexity == "complex":
            return "comprehensive_search"
        elif intent in ["how_to", "what_is"]:
            return "focused_search"
        else:
            return "balanced_search"
    
    def _execute_retrieval(self, query_embedding: List[float], 
                          query_analysis: Dict[str, Any],
                          retrieval_strategy: str) -> Dict[str, Any]:
        """Execute the retrieval strategy"""
        if retrieval_strategy == "comprehensive_search":
            return self._comprehensive_search(query_embedding)
        elif retrieval_strategy == "focused_search":
            return self._focused_search(query_embedding)
        else:
            return self._balanced_search(query_embedding)
    
    def _comprehensive_search(self, query_embedding: List[float]) -> Dict[str, Any]:
        """Comprehensive search across all content"""
        results = self.vector_store.search_creator("hawa_singh", query_embedding, n_results=5)
        
        chunks = []
        if results["documents"] and results["documents"][0]:
            for i, (doc, meta, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                chunks.append({
                    "content": doc,
                    "creator_id": meta["creator_id"],
                    "source": meta["source"],
                    "similarity": 1 - distance
                })
        
        return {
            "chunks": chunks,
            "best_creator": "hawa_singh"
        }
    
    def _focused_search(self, query_embedding: List[float]) -> Dict[str, Any]:
        """Focused search for specific answers"""
        results = self.vector_store.search_creator("hawa_singh", query_embedding, n_results=3)
        
        chunks = []
        if results["documents"] and results["documents"][0]:
            for i, (doc, meta, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                chunks.append({
                    "content": doc,
                    "creator_id": meta["creator_id"],
                    "source": meta["source"],
                    "similarity": 1 - distance
                })
        
        return {
            "chunks": chunks,
            "best_creator": "hawa_singh"
        }
    
    def _balanced_search(self, query_embedding: List[float]) -> Dict[str, Any]:
        """Balanced search for general queries"""
        results = self.vector_store.search_creator("hawa_singh", query_embedding, n_results=3)
        
        chunks = []
        if results["documents"] and results["documents"][0]:
            for i, (doc, meta, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                chunks.append({
                    "content": doc,
                    "creator_id": meta["creator_id"],
                    "source": meta["source"],
                    "similarity": 1 - distance
                })
        
        return {
            "chunks": chunks,
            "best_creator": "hawa_singh"
        }

def test_retrieval():
    """Test the retrieval system"""
    retriever = IntelligentRetriever()
    
    # Test queries
    test_queries = [
        "How to get more views on YouTube?",
        "What is YouTube monetization?",
        "My video views are not increasing, help!",
        "Which is better: long videos or shorts?",
        "Suggest some video ideas for my channel"
    ]
    
    print("\n🔍 Testing Retrieval System")
    print("=" * 40)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = retriever.retrieve_context(query)
        
        print(f"Strategy: {result['retrieval_strategy']}")
        print(f"Total chunks: {result['total_chunks']}")
        
        if result['context']['chunks']:
            chunk = result['context']['chunks'][0]
            print(f"Top chunk similarity: {chunk['similarity']:.3f}")
            print(f"Content preview: {chunk['content'][:100]}...")
        else:
            print("No relevant chunks found")
        
        print("-" * 30)

if __name__ == "__main__":
    test_retrieval()