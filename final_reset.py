import os
import shutil

def final_reset():
    """Clean reset for final build"""
    
    print("🗑️ Final Reset - Cleaning Everything")
    print("=" * 40)
    
    # Remove old databases
    paths_to_clean = [
        "vector_store",
        "embedding_cache", 
        ".chroma"
    ]
    
    for path in paths_to_clean:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"✅ Removed: {path}")
        else:
            print(f"ℹ️ Not found: {path}")
    
    print("\n🎉 Clean reset complete!")
    print("Ready for final build!")

if __name__ == "__main__":
    final_reset()