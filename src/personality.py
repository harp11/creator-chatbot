import config
from typing import Dict, Any, List
import google.generativeai as genai

class PersonalityManager:
    def __init__(self):
        """Initialize the personality manager"""
        self.creator_id = "hawa_singh"
        self.creator_info = config.CREATORS[self.creator_id]
        
        # Configure Gemini
        genai.configure(api_key=config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(config.MODEL_NAME)
    
    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]], 
                         query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response using the creator's personality"""
        try:
            # Prepare context
            context_text = self._prepare_context(context_chunks)
        
            # Get response
            response = self._get_response(query, context_text, query_analysis)
        
            return {
                "success": True,
                "creator_name": self.creator_info["name"],
                "response": response,
                "creator_id": self.creator_id
            }
            
        except Exception as e:
            print(f"❌ Response generation error: {e}")
            return {
                "success": False,
                "creator_name": self.creator_info["name"],
                "response": self._get_error_response(query),
                "creator_id": self.creator_id
            }
    
    def _prepare_context(self, context_chunks: List[Dict[str, Any]]) -> str:
        """Prepare context from chunks"""
        if not context_chunks:
            return "No specific context available."
        
        # Sort chunks by similarity
        sorted_chunks = sorted(context_chunks, key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Combine context text
        context_parts = []
        for chunk in sorted_chunks:
            context_parts.append(chunk['content'])
        
        return "\n\n".join(context_parts)
    
    def _get_response(self, query: str, context: str, 
                                  query_analysis: Dict[str, Any]) -> str:
        """Get response from the model"""
        # Prepare system prompt
        system_prompt = f"""You are Hawa Singh, a YouTube growth expert who speaks in natural Hingish (Hindi + English mix).

PERSONALITY:
- YouTube growth strategist with practical experience
- Speaks naturally mixing Hindi and English (Hingish)
- Gives actionable, step-by-step advice
- Understands Indian YouTube ecosystem
- Encouraging but realistic about challenges

SPEAKING STYLE:
- Mix Hindi and English naturally like Indian YouTubers
- Use English for YouTube terms: algorithm, monetization, SEO, analytics, thumbnail
- Use Hindi for emotions, emphasis, casual conversation: dekho, aapko, karna hoga, friends
- Give practical advice with steps
- Be encouraging: "bas consistent rehna hai", "all the best"

CONTEXT:
{context}

USER QUESTION:
{query}

QUERY ANALYSIS:
Intent: {query_analysis['intent']}
Complexity: {query_analysis['complexity']}

Remember to:
1. Stay in character as Hawa Singh
2. Give practical, actionable advice
3. Use examples when helpful
4. Be encouraging and supportive
5. Mix Hindi and English naturally"""
        
        # Get response
        chat = self.model.start_chat(history=[])
        response = chat.send_message(system_prompt)
        
        return response.text
    
    def _get_error_response(self, query: str) -> str:
        """Get a fallback response for errors"""
        return f"Dekho friend, '{query}' ke baare mein main aapko help karna chahta hun, lekin technical issue aa raha hai. Thoda wait karo aur try again karo!"

def test_personality():
    """Test the personality system"""
    print("\n🎭 Testing Personality System")
    print("=" * 40)
    
    manager = PersonalityManager()
    
    # Test queries
    test_queries = [
        "How to get more views on YouTube?",
        "What is YouTube monetization?",
        "My video views are not increasing, help!",
        "Which is better: long videos or shorts?",
        "Suggest some video ideas for my channel"
    ]
    
    # Mock context and analysis
    mock_context = [{
        "content": "To increase YouTube views: 1) Create engaging thumbnails, 2) Use good SEO, 3) Post consistently",
        "similarity": 0.95,
        "creator_id": "hawa_singh",
        "source": "content1.txt"
    }]
    
    mock_analysis = {
        "intent": "how_to",
        "complexity": "medium"
    }
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = manager.generate_response(query, mock_context, mock_analysis)
        
        print(f"Success: {'✅' if result['success'] else '❌'}")
        print(f"Response preview: {result['response'][:100]}...")
        print("-" * 30)

if __name__ == "__main__":
    test_personality()