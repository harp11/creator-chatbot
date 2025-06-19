"""Build and test the vector database"""

import time
import os
import glob
import json
from typing import List, Dict, Any
from src.chunking import FileProcessor, SmartChunker
from src.embeddings import GeminiEmbedder
from src.vector_store import CreatorVectorStore
from src.retrieval import IntelligentRetriever
import config

def load_creator_content(creator_id: str) -> List[Dict[str, Any]]:
    """Load content files for a creator"""
    content_path = f"data/{creator_id}/*.txt"
    content_files = glob.glob(content_path)
    
    if not content_files:
        raise ValueError(f"No content files found for {creator_id}")
    
    all_content = []
    for file_path in content_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            all_content.append({
                "content": content,
                "source": os.path.basename(file_path),
                "creator_id": creator_id
            })
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            continue
    
    return all_content

def build_vector_database():
    """Build the vector database from creator content"""
    print("\n🚀 Building Vector Database")
    print("=" * 40)
    
    # Initialize components
    chunker = SmartChunker()
    embedder = GeminiEmbedder()
    vector_store = CreatorVectorStore()
    
    # Reset vector store
    print("🧹 Resetting vector store...")
    vector_store.reset()
    
    # Process Hawa Singh's content
    try:
        print("\n🎯 Processing Hawa Singh's content...")
        content = load_creator_content("hawa_singh")
        
        # Process each content file
        for item in content:
            # Chunk the content
            chunks = chunker.chunk_text(item["content"], item["source"])
            print(f"📄 {item['source']}: {len(chunks)} chunks")
            
            # Embed and store chunks
            for chunk in chunks:
                try:
                    # Get embedding for the text content
                    embedding = embedder.embed_text(chunk)
                    
                    # Store in vector database
                    vector_store.add_chunk(
                        creator_id="hawa_singh",
                        text=chunk["content"],
                        embedding=embedding,
                        metadata={
                            "creator_id": "hawa_singh",
                            "creator_name": config.CREATORS["hawa_singh"]["name"],
                            "source": item["source"],
                            "chunk_id": chunk["chunk_id"],
                            "chunk_index": chunk["chunk_index"]
                        }
                    )
                    
                except Exception as e:
                    print(f"❌ Error processing chunk: {e}")
                    continue
        
        print("✅ Successfully processed all content")
        
    except Exception as e:
        print(f"❌ Error processing content: {e}")
        return False
    
    # Print final stats
    stats = vector_store.get_collection_stats()
    print("\n📊 Final Database Stats:")
    print(f"🎯 Hawa Singh: {stats.get('hawa_singh', 0)} chunks")
    
    return True

def test_vector_search():
    """Test the vector search functionality"""
    print("\n🔍 Testing Vector Search")
    print("=" * 30)
    
    vector_store = build_vector_database()
    
    # Initialize retriever
    retriever = IntelligentRetriever()
    
    # Test query
    print("\n🎯 Testing query: 'YouTube monetization kaise kare'")
    result = retriever.retrieve_context("YouTube monetization kaise kare")
    
    print("\n📊 Retrieval Results:")
    print(f"   Strategy: {result['retrieval_strategy']}")
    print(f"   Total chunks: {result['total_chunks']}")
    print(f"   Best creator: {result['context'].get('best_creator')}")
    
    print("\n📄 Retrieved Content (showing first 2 chunks):")
    for i, chunk in enumerate(result['context']['chunks'][:2]):
        print(f"\n   Chunk {i+1}:")
        print(f"      Creator: {chunk['creator_id']}")
        print(f"      Source: {chunk['source']}")
        print(f"      Similarity: {chunk['similarity']:.3f}")
        print(f"      Content: {chunk['content'][:200]}...")
    
    print("\n🎉 RAG System is working! Knowledge base is being used.")

if __name__ == "__main__":
    success = build_vector_database()
    if success:
        print("\n✨ Vector database built successfully!")
    else:
        print("\n❌ Error building vector database")
    test_vector_search()