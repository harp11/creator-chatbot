from src.retrieval import IntelligentRetriever
from src.vector_store import CreatorVectorStore
from src.embeddings import GeminiEmbedder
import config

def check_rag_system_status():
    """Check if RAG system is actually working with knowledge base"""
    
    print("🔍 Checking RAG System Status")
    print("=" * 35)
    
    # Check 1: Vector Database
    print("📊 1. Vector Database Status:")
    try:
        vector_store = CreatorVectorStore()
        
        # Load collections
        for creator_id in config.CREATORS.keys():
            try:
                collection_name = f"creator_{creator_id}"
                collection = vector_store.client.get_collection(name=collection_name)
                vector_store.collections[creator_id] = collection
                count = collection.count()
                print(f"   ✅ {creator_id}: {count} chunks")
            except Exception as e:
                print(f"   ❌ {creator_id}: Collection not found - {e}")
        
        total_chunks = sum(vector_store.get_collection_stats().values())
        print(f"   📈 Total chunks: {total_chunks}")
        
    except Exception as e:
        print(f"   ❌ Vector database error: {e}")
        return False
    
    # Check 2: Retrieval System
    print(f"\n🔍 2. Retrieval System Test:")
    try:
        retriever = IntelligentRetriever()
        
        test_queries = [
            "YouTube monetization",
            "Python programming", 
            "muscle building"
        ]
        
        for query in test_queries:
            try:
                result = retriever.retrieve_context(query)
                chunks_found = len(result.get('context', {}).get('chunks', []))
                best_creator = result.get('context', {}).get('best_creator', 'None')
                print(f"   Query: '{query}'")
                print(f"      ✅ Found {chunks_found} chunks, routed to: {best_creator}")
            except Exception as e:
                print(f"   Query: '{query}'")
                print(f"      ❌ Retrieval failed: {e}")
                
    except Exception as e:
        print(f"   ❌ Retrieval system error: {e}")
        return False
    
    # Check 3: Embeddings
    print(f"\n🧮 3. Embedding System Test:")
    try:
        embedder = GeminiEmbedder()
        test_text = "YouTube monetization tips"
        embedding = embedder.embed_text(test_text)
        print(f"   ✅ Embedding generated: {len(embedding)} dimensions")
        
    except Exception as e:
        print(f"   ❌ Embedding error: {e}")
        return False
    
    print(f"\n🎯 4. Knowledge Base Content Check:")
    try:
        # Check if we actually have Hawa Singh's content
        if 'hawa_singh' in vector_store.collections:
            collection = vector_store.collections['hawa_singh']
            sample_docs = collection.get(limit=3, include=["documents"])
            
            if sample_docs['documents']:
                print(f"   ✅ Hawa Singh has {len(sample_docs['documents'])} sample documents")
                print(f"   📄 Sample content preview:")
                for i, doc in enumerate(sample_docs['documents'][:2]):
                    preview = doc[:100] + "..." if len(doc) > 100 else doc
                    print(f"      {i+1}. {preview}")
            else:
                print(f"   ❌ Hawa Singh collection is empty!")
        else:
            print(f"   ❌ Hawa Singh collection not found!")
            
    except Exception as e:
        print(f"   ❌ Content check error: {e}")
    
    print(f"\n✅ RAG System Check Complete!")
    return True

def test_actual_rag_retrieval():
    """Test if we're actually using knowledge base content"""
    
    print(f"\n🧪 Testing Actual RAG Retrieval")
    print("=" * 35)
    
    try:
        retriever = IntelligentRetriever()
        
        # Test with specific YouTube query
        query = "YouTube monetization kaise kare"
        print(f"🎯 Testing query: '{query}'")
        
        result = retriever.retrieve_context(query)
        
        print(f"\n📊 Retrieval Results:")
        print(f"   Strategy: {result.get('retrieval_strategy', 'Unknown')}")
        print(f"   Total chunks: {result.get('total_chunks', 0)}")
        print(f"   Best creator: {result.get('context', {}).get('best_creator', 'None')}")
        
        chunks = result.get('context', {}).get('chunks', [])
        if chunks:
            print(f"\n📄 Retrieved Content (showing first 2 chunks):")
            for i, chunk in enumerate(chunks[:2]):
                print(f"   Chunk {i+1}:")
                print(f"      Creator: {chunk.get('creator_id', 'Unknown')}")
                print(f"      Source: {chunk.get('source', 'Unknown')}")
                print(f"      Similarity: {chunk.get('similarity', 0):.3f}")
                print(f"      Content: {chunk.get('content', '')[:150]}...")
                print()
        else:
            print(f"   ❌ No chunks retrieved!")
            
        return len(chunks) > 0
        
    except Exception as e:
        print(f"❌ RAG retrieval test failed: {e}")
        return False

if __name__ == "__main__":
    system_working = check_rag_system_status()
    if system_working:
        retrieval_working = test_actual_rag_retrieval()
        
        if retrieval_working:
            print(f"\n🎉 RAG System is working! Knowledge base is being used.")
        else:
            print(f"\n⚠️ RAG System has issues - not retrieving content properly.")
    else:
        print(f"\n❌ RAG System is not working properly.")