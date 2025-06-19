import streamlit as st
import google.generativeai as genai
import config
from src.retrieval import IntelligentRetriever
from src.personality import PersonalityManager
from verify_setup import verify_complete_setup

def main():
    """Main application function"""
    # First verify the setup
    print("🚀 Launching Creator Chatbot System")
    print("=" * 40)
    
    print("🔍 Step 1: Verifying setup...")
    if not verify_complete_setup():
        st.error("❌ Setup verification failed! Please run: python build_vector_database.py")
        st.stop()
        return
    
    print("✅ Setup verified successfully!")
    print("\n🌐 Launching Streamlit interface...")
    
    # Configure page
    st.set_page_config(
        page_title="Hawa Singh - YouTube Expert",
        page_icon="🎯",
        layout="wide"
    )
    
    # Title and description
    st.title("🎯 Hawa Singh - YouTube Growth Expert")
    st.markdown("""
    Welcome! I'm Hawa Singh, your YouTube growth expert. I specialize in:
    - Channel optimization
    - Content strategy
    - Audience growth
    - Monetization tips
    Ask me anything about growing your YouTube channel!
    """)
    
    # Initialize components
    try:
        retriever = IntelligentRetriever()
        personality = PersonalityManager()
        
        # Show database stats
        stats = retriever.vector_store.get_collection_stats()
        st.sidebar.header("📊 Knowledge Base Stats")
        st.sidebar.metric("🎯 Hawa Singh", f"{stats.get('hawa_singh', 0)} chunks")
        
    except Exception as e:
        st.error(f"❌ Error initializing system: {e}")
        st.stop()
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            with st.chat_message(message["role"], avatar="🎯"):
                st.markdown(message["content"])
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about YouTube growth!"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant", avatar="🎯"):
            message_placeholder = st.empty()
            
            try:
                # Get context from vector store
                context = retriever.retrieve_context(prompt)
                
                # Generate response
                response = personality.generate_response(
                    prompt,
                    context["context"]["chunks"],
                    context
                )
                
                if response["success"]:
                    message_placeholder.markdown(response["response"])
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["response"]
                    })
                else:
                    message_placeholder.error("❌ Failed to generate response")
                
            except Exception as e:
                message_placeholder.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()