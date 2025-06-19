"""Test script to verify context preservation in the chatbot"""

import google.generativeai as genai
import config
from src.retrieval import IntelligentRetriever
import time

def test_context_preservation():
    """Test context preservation with a series of related questions"""
    
    print("\n🔍 Testing Context Preservation")
    print("=" * 40)
    
    # Initialize components
    genai.configure(api_key=config.GOOGLE_API_KEY)
    model = genai.GenerativeModel(config.MODEL_NAME)
    chat = model.start_chat(history=[])
    retriever = IntelligentRetriever()
    
    # Test questions in sequence
    test_sequence = [
        {
            "query": "What's the best way to start growing my YouTube channel?",
            "expected_context": ["growth", "strategy", "start"]
        },
        {
            "query": "How often should I post?",
            "expected_context": ["frequency", "schedule", "consistency"]
        },
        {
            "query": "What about Shorts? Are they better for growth?",
            "expected_context": ["shorts", "growth", "comparison"]
        },
        {
            "query": "Can you give me specific tips for my first Short?",
            "expected_context": ["shorts", "tips", "first"]
        },
        {
            "query": "How long should it be?",
            "expected_context": ["duration", "length", "shorts"]
        }
    ]
    
    chat_history = []
    
    for i, test_case in enumerate(test_sequence, 1):
        print(f"\n📝 Test {i}: {test_case['query']}")
        print("-" * 30)
        
        try:
            # Get context from vector store
            context = retriever.retrieve_context(test_case["query"])
            print(f"Retrieved {len(context['context']['chunks'])} relevant chunks")
            
            # Format chat history for context
            history_text = ""
            if chat_history:
                history_text = "Previous conversation:\n"
                for msg in chat_history[-3:]:  # Last 3 messages
                    role = "Hawa Singh" if msg["role"] == "assistant" else "User"
                    history_text += f"{role}: {msg['content']}\n"
            
            # Prepare system prompt
            system_prompt = f"""You are Hawa Singh, a YouTube growth expert who specializes in helping small channels grow.
            Your expertise includes:
            - YouTube algorithm optimization
            - Content strategy and planning
            - Channel growth techniques
            - Audience engagement
            - Monetization strategies
            
            Style:
            - Friendly and encouraging
            - Practical and solution-oriented
            - Use clear examples
            - Focus on actionable advice
            
            Context for this query:
            {context['context']['chunks'][0]['content'] if context['context']['chunks'] else 'No specific context found.'}
            
            {history_text}
            
            Remember to:
            1. Stay in character as Hawa Singh
            2. Give practical, actionable advice
            3. Use examples when helpful
            4. Be encouraging and supportive
            
            User query: {test_case['query']}
            """
            
            # Get response
            response = chat.send_message(system_prompt)
            
            # Add to chat history
            chat_history.append({"role": "user", "content": test_case["query"]})
            chat_history.append({"role": "assistant", "content": response.text})
            
            # Check for expected context words
            context_found = []
            for word in test_case["expected_context"]:
                if word.lower() in response.text.lower():
                    context_found.append(word)
            
            print("\n✅ Response Analysis:")
            print(f"Context words found: {', '.join(context_found)}")
            print(f"Expected: {', '.join(test_case['expected_context'])}")
            print(f"Context retention: {len(context_found)}/{len(test_case['expected_context'])}")
            
            # Add delay to avoid rate limits
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error in test {i}: {str(e)}")
            continue
    
    print("\n🎉 Context Preservation Test Complete!")
    print("=" * 40)

if __name__ == "__main__":
    test_context_preservation() 