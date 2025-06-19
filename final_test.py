import config
from src.embeddings import GeminiEmbedder
from src.vector_store import CreatorVectorStore
from src.retrieval import IntelligentRetriever
from src.query_analyzer import QueryAnalyzer

def test_complete_system():
    """Test the complete chatbot system"""
    print("\n🚀 Testing Complete System")
    print("=" * 40)
    
    # Test queries
    test_queries = [
        "How to get more views on YouTube?",
        "What is YouTube monetization?",
        "My video views are not increasing, help!",
        "Which is better: long videos or shorts?",
        "Suggest some video ideas for my channel"
    ]
    
    # Initialize components
    print("\n🔧 Initializing components...")
    try:
        embedder = GeminiEmbedder()
        vector_store = CreatorVectorStore()
        retriever = IntelligentRetriever()
        query_analyzer = QueryAnalyzer()
        print("✅ Components initialized successfully")
    except Exception as e:
        print(f"❌ Component initialization error: {e}")
        return
    
    # Test embeddings
    print("\n🧮 Testing embeddings...")
    try:
        test_text = "How to grow your YouTube channel?"
        embedding = embedder.embed_text(test_text)
        print(f"✅ Embedding created successfully (dimension: {len(embedding)})")
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return
    
    # Test vector store
    print("\n🗄️ Testing vector store...")
    try:
        stats = vector_store.get_collection_stats()
        print(f"✅ Vector store accessible")
        print(f"📊 Total chunks: {stats.get('hawa_singh', 0)}")
    except Exception as e:
        print(f"❌ Vector store error: {e}")
        return
    
    # Test retrieval
    print("\n🔍 Testing retrieval system...")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = retriever.retrieve_context(query)
            print(f"Strategy: {result['retrieval_strategy']}")
            print(f"Total chunks: {result['total_chunks']}")
            if result['context']['chunks']:
                chunk = result['context']['chunks'][0]
                print(f"Top chunk similarity: {chunk['similarity']:.3f}")
            else:
                print("No chunks found")
        except Exception as e:
            print(f"❌ Retrieval error: {e}")
            continue
    
    print("\n✨ System test complete!")

if __name__ == "__main__":
    test_complete_system()