import re
import os
from typing import List, Dict, Any
import config

class SmartChunker:
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.overlap = overlap or config.CHUNK_OVERLAP
    
    def chunk_text(self, text: str, source: str = "") -> List[Dict[str, Any]]:
        """
        Smart chunking that preserves context and meaning
        """
        # Clean the text first
        text = self._clean_text(text)
        
        # Split into sentences for better boundaries
        sentences = self._split_into_sentences(text)
        
        # Create chunks with semantic boundaries
        chunks = self._create_semantic_chunks(sentences)
        
        # Add metadata to each chunk
        chunk_objects = []
        for i, chunk in enumerate(chunks):
            chunk_obj = {
                "content": chunk,
                "chunk_id": f"{source}_chunk_{i}",
                "source": source,
                "chunk_index": i,
                "word_count": len(chunk.split()),
                "character_count": len(chunk)
            }
            chunk_objects.append(chunk_obj)
        
        return chunk_objects
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-"]', '', text)
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using multiple delimiters"""
        # Split on common sentence endings
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Also split on paragraph breaks and other logical breaks
        all_sentences = []
        for sentence in sentences:
            # Further split on line breaks that indicate new thoughts
            sub_sentences = sentence.split('\n')
            for sub in sub_sentences:
                if sub.strip():
                    all_sentences.append(sub.strip())
        
        return all_sentences
    
    def _create_semantic_chunks(self, sentences: List[str]) -> List[str]:
        """Create chunks that respect semantic boundaries"""
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Check if adding this sentence would exceed our limit
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # Current chunk is full, save it and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Handle overlap - take last few sentences from previous chunk
                if chunks and self.overlap > 0:
                    overlap_text = self._get_overlap_text(current_chunk, self.overlap)
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk = sentence
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get the last part of text for overlap"""
        if len(text) <= overlap_size:
            return text
        
        # Try to find a good break point near the overlap size
        words = text.split()
        overlap_words = []
        char_count = 0
        
        # Work backwards from the end
        for word in reversed(words):
            if char_count + len(word) + 1 <= overlap_size:
                overlap_words.insert(0, word)
                char_count += len(word) + 1
            else:
                break
        
        return " ".join(overlap_words)

class FileProcessor:
    def __init__(self):
        self.chunker = SmartChunker()
        self.supported_extensions = ['.txt', '.md']
    
    def process_creator_files(self, creator_id: str) -> List[Dict[str, Any]]:
        """Process all files for a specific creator"""
        creator_path = os.path.join("data", creator_id)
        all_chunks = []
        
        if not os.path.exists(creator_path):
            print(f"❌ Creator path not found: {creator_path}")
            return []
        
        for filename in os.listdir(creator_path):
            file_path = os.path.join(creator_path, filename)
            
            # Skip if not a supported file type
            if not any(filename.endswith(ext) for ext in self.supported_extensions):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Create source identifier
                source = f"{creator_id}/{filename}"
                
                # Chunk the content
                file_chunks = self.chunker.chunk_text(content, source)
                
                # Add creator info to each chunk
                for chunk in file_chunks:
                    chunk["creator_id"] = creator_id
                    chunk["creator_name"] = config.CREATORS[creator_id]["name"]
                    chunk["creator_specialty"] = config.CREATORS[creator_id]["specialty"]
                
                all_chunks.extend(file_chunks)
                print(f"✅ Processed {filename}: {len(file_chunks)} chunks")
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
        
        return all_chunks
    
    def process_all_creators(self) -> Dict[str, List[Dict[str, Any]]]:
        """Process files for all creators"""
        all_creator_chunks = {}
        
        for creator_id in config.CREATORS.keys():
            print(f"\n📂 Processing creator: {creator_id}")
            chunks = self.process_creator_files(creator_id)
            all_creator_chunks[creator_id] = chunks
            print(f"✅ Total chunks for {creator_id}: {len(chunks)}")
        
        return all_creator_chunks

def preview_chunks(chunks: List[Dict[str, Any]], max_chunks: int = 3):
    """Preview chunks to see how they look"""
    print(f"\n🔍 Previewing first {min(max_chunks, len(chunks))} chunks:")
    print("=" * 60)
    
    for i, chunk in enumerate(chunks[:max_chunks]):
        print(f"\nChunk {i + 1}:")
        print(f"Source: {chunk['source']}")
        print(f"Words: {chunk['word_count']}, Characters: {chunk['character_count']}")
        print(f"Content: {chunk['content'][:200]}...")
        print("-" * 40)