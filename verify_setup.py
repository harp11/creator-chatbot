import os
import config
from src.vector_store import CreatorVectorStore

def verify_complete_setup() -> bool:
    """Verify that all required components are set up correctly"""
    
    # Check API key
    if not config.GOOGLE_API_KEY:
        print("❌ Missing GOOGLE_API_KEY in .env")
        return False
    
    # Check data directory structure
    required_paths = [
        "data/hawa_singh/content1.txt",
        config.VECTOR_DB_PATH
    ]
    
    for path in required_paths:
        if not os.path.exists(path):
            print(f"❌ Missing required path: {path}")
            return False
    
    # Check vector store
    try:
        vector_store = CreatorVectorStore()
        stats = vector_store.get_collection_stats()
        
        if not stats.get("hawa_singh", 0) > 0:
            print("❌ No chunks found in vector store for Hawa Singh")
            return False
            
        print("\n✅ Vector store verification passed")
        print(f"📊 Total chunks: {stats.get('hawa_singh', 0)}")
        
    except Exception as e:
        print(f"❌ Vector store error: {e}")
        return False
    
    return True

def test_verify_setup():
    """Test the verification process"""
    print("\n🔍 Testing Setup Verification")
    print("=" * 40)
    
    success = verify_complete_setup()
    
    if success:
        print("\n✅ All components verified successfully!")
    else:
        print("\n❌ Setup verification failed")
        print("Please check the errors above and fix any missing components")

if __name__ == "__main__":
    test_verify_setup()