import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any, Optional
import config
import json

class CreatorVectorStore:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            print("🔄 Creating new CreatorVectorStore instance")
            cls._instance = super(CreatorVectorStore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        print("🔄 Initializing CreatorVectorStore")
        # Initialize ChromaDB with persistent storage
        os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=config.VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Store collections for each creator
        self.collections = {}
        self._initialized = True
        
        # Load existing collections
        try:
            collections = self.client.list_collections()
            for collection in collections:
                creator_id = collection.name.replace("creator_", "")
                self.collections[creator_id] = collection
            print(f"📂 Loaded {len(collections)} existing collections")
        except Exception as e:
            print(f"❌ Error loading existing collections: {e}")
        
    def reset(self):
        """Reset all collections in the vector store"""
        try:
            # Delete all existing collections
            collections = self.client.list_collections()
            for collection in collections:
                self.client.delete_collection(collection.name)
            
            # Clear collections dict
            self.collections = {}
            print("✅ Vector store reset complete")
        except Exception as e:
            print(f"❌ Error resetting vector store: {e}")
        
    def create_creator_collection(self, creator_id: str) -> None:
        """Create or get collection for a specific creator"""
        collection_name = f"creator_{creator_id}"
        
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=collection_name)
            print(f"📂 Found existing collection for {creator_id}")
        except:
            # Create new collection
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"creator_id": creator_id}
            )
            print(f"🆕 Created new collection for {creator_id}")
        
        self.collections[creator_id] = collection
    
    def add_chunks_to_collection(self, creator_id: str, chunks: List[Dict[str, Any]]) -> None:
        """Add embedded chunks to creator's collection"""
        if creator_id not in self.collections:
            self.create_creator_collection(creator_id)
        
        collection = self.collections[creator_id]
        
        # Prepare data for ChromaDB
        ids = [chunk['chunk_id'] for chunk in chunks]
        embeddings = [chunk['embedding'] for chunk in chunks]
        documents = [chunk['content'] for chunk in chunks]
        
        # Prepare metadata (ChromaDB doesn't like nested dicts)
        metadatas = []
        for chunk in chunks:
            metadata = {
                "source": chunk['source'],
                "chunk_index": chunk['chunk_index'],
                "word_count": chunk['word_count'],
                "creator_id": chunk['creator_id'],
                "creator_name": chunk['creator_name'],
                "creator_specialty": chunk['creator_specialty']
            }
            metadatas.append(metadata)
        
        # Add to collection
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"✅ Added {len(chunks)} chunks to {creator_id} collection")
    
    def search_creator(self, creator_id: str, query_embedding: List[float], 
                      n_results: int = 5) -> Dict[str, Any]:
        """Search within a specific creator's content"""
        if creator_id not in self.collections:
            print(f"❌ No collection found for creator: {creator_id}")
            return {"documents": [], "metadatas": [], "distances": []}
        
        collection = self.collections[creator_id]
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def search_all_creators(self, query_embedding: List[float], 
                           n_results_per_creator: int = 3) -> Dict[str, Any]:
        """Search across all creators and return best matches"""
        all_results = {}
        
        for creator_id in self.collections.keys():
            results = self.search_creator(creator_id, query_embedding, n_results_per_creator)
            if results["documents"] and results["documents"][0]:  # Check if we got results
                all_results[creator_id] = results
        
        return all_results
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about stored collections"""
        stats = {}
        for creator_id, collection in self.collections.items():
            count = collection.count()
            stats[creator_id] = count
        return stats
    
    def delete_creator_collection(self, creator_id: str) -> None:
        """Delete a creator's collection (useful for rebuilding)"""
        collection_name = f"creator_{creator_id}"
        try:
            self.client.delete_collection(name=collection_name)
            if creator_id in self.collections:
                del self.collections[creator_id]
            print(f"🗑️ Deleted collection for {creator_id}")
        except Exception as e:
            print(f"❌ Error deleting collection for {creator_id}: {e}")

    def add_chunk(self, creator_id: str, text: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        """Add a single chunk to the creator's collection"""
        if creator_id not in self.collections:
            self.create_creator_collection(creator_id)
        
        collection = self.collections[creator_id]
        
        # Add to collection
        collection.add(
            ids=[metadata["chunk_id"]],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )