"""Test retrieval from the vector database with different queries"""

import sys
from src.retrieval import IntelligentRetriever
from src.vector_store import CreatorVectorStore

def test_query(query: str):
    """Test a specific query and display results"""
    print("\n🔍 Testing Query System")
    print("=" * 50)
    print(f"Query: '{query}'")
    
    # Initialize components
    retriever = IntelligentRetriever()
    
    # Get results
    result = retriever.retrieve_context(query)
    
    # Display results
    print("\n📊 Retrieval Results:")
    print(f"Strategy: {result['retrieval_strategy']}")
    print(f"Total chunks: {result['total_chunks']}")
    print(f"Best creator: {result['context'].get('best_creator')}")
    
    print("\n📄 Retrieved Content:")
    print("-" * 50)
    
    for i, chunk in enumerate(result['context']['chunks']):
        print(f"\nChunk {i+1}:")
        print(f"Source: {chunk['source']}")
        print(f"Similarity: {chunk['similarity']:.3f}")
        print(f"Content:\n{chunk['content']}")
        print("-" * 50)

def main():
    # Get query from command line or use default
    query = sys.argv[1] if len(sys.argv) > 1 else "How to grow on YouTube?"
    test_query(query)

if __name__ == "__main__":
    main() 