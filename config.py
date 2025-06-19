import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Vector Database Configuration
VECTOR_DB_PATH = "./vector_store"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Embedding Configuration
EMBEDDING_MODEL = "models/embedding-001"  # Using the standard embedding model

# Creator Configuration
CREATORS = {
    "hawa_singh": {
        "name": "Hawa Singh",
        "specialty": "YouTube channel growth and optimization, particularly for small channels; viral video topic identification",
        "personality": "Helpful and encouraging, Practical and solution-oriented, Knowledgeable about YouTube algorithms and best practices"
    }
}

# LLM Configuration
TEMPERATURE = 0.7
MAX_TOKENS = 500
MODEL_NAME = "models/gemini-2.0-flash"
