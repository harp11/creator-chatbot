"""Embeddings module for converting text to vectors"""

import google.generativeai as genai
import numpy as np
from typing import List, Dict, Any, Optional, Union
import config
import time

class GeminiEmbedder:
    """Convert text to vector embeddings using Gemini"""
    
    def __init__(self):
        """Initialize the embedder"""
        genai.configure(api_key=config.GOOGLE_API_KEY)
        self.model_name = config.EMBEDDING_MODEL
        self.embedding_dimension = None  # Will be set after first embedding
        
    def embed_text(self, text: Union[str, Dict[str, Any]]) -> List[float]:
        """Convert text to vector embedding using Gemini"""
        try:
            # Extract text content if input is a dictionary
            if isinstance(text, dict):
                if 'content' not in text:
                    raise ValueError("Dictionary input must have a 'content' key")
                text = text['content']
            elif not isinstance(text, str):
                raise ValueError("Input must be either a string or a dictionary with 'content' key")
            
            # Validate text
            if not text.strip():
                raise ValueError("Empty or whitespace-only text cannot be embedded")
                
            # Format content according to Gemini's expected structure
            content = {
                "parts": [{"text": text}]
            }
            
            # Retry logic for API calls
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    result = genai.embed_content(
                        model=self.model_name,
                        content=content
                    )
                    embedding = result['embedding']
                    
                    # Set dimension on first run
                    if self.embedding_dimension is None:
                        self.embedding_dimension = len(embedding)
                        print(f"📏 Embedding dimension: {self.embedding_dimension}")
                    
                    return embedding
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:  # Rate limit error
                        print(f"⚠️ Rate limit hit, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    raise  # Re-raise the exception if it's not a rate limit error or we're out of retries
            
        except Exception as e:
            print(f"❌ Embedding error: {str(e)}")
            raise  # Re-raise the exception to be handled by the caller
    
    def embed_batch(self, texts: List[Union[str, Dict[str, Any]]], batch_size: int = 5) -> List[List[float]]:
        """Embed multiple texts with rate limiting"""
        embeddings = []
        
        print(f"🔄 Embedding {len(texts)} texts in batches of {batch_size}")
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for text in batch:
                embedding = self.embed_text(text)
                batch_embeddings.append(embedding)
                
                # Rate limiting - small delay between requests
                time.sleep(0.1)
            
            embeddings.extend(batch_embeddings)
            print(f"✅ Processed batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        return embeddings
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add embeddings to chunk objects"""
        print(f"🧮 Creating embeddings for {len(chunks)} chunks...")
        
        # Extract text content for embedding
        texts = [chunk['content'] for chunk in chunks]
        
        # Get embeddings
        embeddings = self.embed_batch(texts)
        
        # Add embeddings to chunk objects
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
            chunk['embedding_model'] = self.model_name
        
        print("✅ All chunks now have embeddings!")
        return chunks

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    # Convert to numpy arrays
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    # Calculate cosine similarity
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    return float(similarity)

def test_embedding_similarity():
    """Test that similar texts have high similarity scores"""
    embedder = GeminiEmbedder()
    
    # Test texts
    text1 = "Python programming is easy to learn"
    text2 = "Learning Python is simple"
    text3 = "Dogs are great pets"
    
    # Get embeddings
    embedding1 = embedder.embed_text(text1)
    embedding2 = embedder.embed_text(text2)
    embedding3 = embedder.embed_text(text3)
    
    # Calculate similarities
    similar_score = calculate_similarity(embedding1, embedding2)
    different_score = calculate_similarity(embedding1, embedding3)
    
    print(f"🔍 Similarity Test Results:")
    print(f"   '{text1}' vs '{text2}': {similar_score:.3f}")
    print(f"   '{text1}' vs '{text3}': {different_score:.3f}")
    
    if similar_score > different_score:
        print("✅ Embeddings correctly identify similar content!")
    else:
        print("❌ Embedding similarity test failed")
    
    return similar_score > different_score