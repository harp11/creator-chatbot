import google.generativeai as genai
from typing import Dict, List, Any
from src.query_analyzer import QueryIntent, QueryComplexity
import config

class HawaSinghPersonality:
    def __init__(self):
        genai.configure(api_key=config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(config.MODEL_NAME)
        self.name = "Hawa Singh"
        self.specialty = "YouTube Growth and Content Creation Expert"
    
    def generate_hingish_response(self, query: str, context_chunks: List[Dict[str, Any]], 
                                 query_analysis: Dict[str, Any]) -> str:
        """Generate response in Hingish style for YouTube expertise"""
        
        # Build context
        context_text = self._build_context_text(context_chunks)
        
        # Create Hingish personality prompt
        prompt = self._create_hingish_prompt(query, context_text, query_analysis)
        
        try:
            response = self.model.generate_content(prompt)
            return self._post_process_hingish_response(response.text, query_analysis)
        except Exception as e:
            print(f"❌ Error generating Hingish response: {e}")
            return self._fallback_hingish_response(query)
    
    def _build_context_text(self, context_chunks: List[Dict[str, Any]]) -> str:
        """Build context from chunks"""
        if not context_chunks:
            return "No specific context available."
        
        context_parts = []
        for i, chunk in enumerate(context_chunks):
            context_parts.append(f"Context {i+1}: {chunk['content']}")
        
        return "\n\n".join(context_parts)
    
    def _create_hingish_prompt(self, query: str, context: str, 
                              query_analysis: Dict[str, Any]) -> str:
        """Create prompt for Hingish YouTube expert response"""
        
        prompt = f"""You are Hawa Singh, a YouTube Growth and Content Creation Expert who speaks in natural Hingish (Hindi + English mix).

PERSONALITY:
- YouTube growth strategist and mentor with practical experience
- Speaks naturally mixing Hindi and English (Hingish style)
- Gives actionable, step-by-step advice
- Understands Indian YouTube ecosystem
- Encouraging but realistic about challenges
- Uses YouTube terminology in English, casual conversation in Hindi

SPEAKING STYLE:
- Mix Hindi and English naturally like Indian YouTubers do
- Use English for technical YouTube terms (algorithm, monetization, SEO, analytics, etc.)
- Use Hindi for emotions, emphasis, and casual conversation
- Give practical, actionable advice
- Reference real YouTube strategies and examples

HINGISH PATTERNS:
- "Dekho friends, YouTube mein success ka formula simple hai"
- "Aapko consistent content banana hoga"
- "SEO optimize karo properly"
- "Analytics dekho regularly"
- "Content quality pe focus karo"

CONTEXT INFORMATION:
{context}

USER QUESTION: {query}

RESPONSE GUIDELINES:
1. Respond in natural Hingish (Hindi-English mix)
2. Give practical YouTube advice
3. Use YouTube terms in English, conversation in Hindi
4. Be encouraging but realistic
5. Provide actionable steps
6. Reference your YouTube expertise

Generate a response as Hawa Singh would, mixing Hindi and English naturally while providing valuable YouTube advice."""

        return prompt
    
    def _post_process_hingish_response(self, response: str, query_analysis: Dict[str, Any]) -> str:
        """Post-process to enhance Hingish style"""
        
        # Add signature closing if not present
        common_closings = [
            "bas consistent rehna hai!",
            "keep creating, keep growing!",
            "YouTube journey mein patience rakhiye!",
            "all the best for your channel!"
        ]
        
        if not any(closing in response.lower() for closing in ["good luck", "all the best", "keep", "bas"]):
            response += f" {common_closings[0]}"
        
        return response.strip()
    
    def _fallback_hingish_response(self, query: str) -> str:
        """Fallback Hingish response"""
        return f"Dekho friend, YouTube ke baare mein aapka question hai '{query}' - main aapko detailed answer dena chahta hun lekin technical issue aa raha hai. Thoda wait karo aur try again karo!"

# Test the Hingish personality
def test_hingish_responses():
    """Test Hingish responses for YouTube queries"""
    
    print("🧪 Testing Hawa Singh's Hingish YouTube Expertise")
    print("=" * 50)
    
    personality = HawaSinghPersonality()
    
    test_queries = [
        "How to get more views on YouTube?",
        "YouTube monetization kaise kare?",
        "Thumbnail design tips batao",
        "YouTube algorithm kaise kaam karta hai?",
        "Small channel ko grow kaise kare?"
    ]
    
    # Mock context chunks
    mock_context = [
        {
            "content": "YouTube success requires consistent content creation and understanding your audience. Focus on quality over quantity and optimize for search."
        }
    ]
    
    # Mock query analysis
    mock_analysis = {
        "intent": QueryIntent.HOW_TO,
        "complexity": QueryComplexity.MEDIUM,
        "formality": "casual",
        "urgency": "normal",
        "keywords": []
    }
    
    for query in test_queries:
        print(f"\n🎯 Query: '{query}'")
        print("-" * 40)
        
        response = personality.generate_hingish_response(query, mock_context, mock_analysis)
        print(f"🎭 Hawa Singh: {response}")

if __name__ == "__main__":
    test_hingish_responses()