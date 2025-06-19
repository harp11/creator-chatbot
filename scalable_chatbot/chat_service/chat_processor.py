import google.generativeai as genai
import httpx
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, UserProfile, Conversation, Message, Creator
from shared.models import (
    ChatRequest, ChatResponse, RetrievalRequest, QueryIntent, 
    MessageRole, QueryAnalysis
)
from config.settings import settings, get_creator_config

logger = logging.getLogger(__name__)

class UserProfileManager:
    """Manages user profiles and context extraction"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_user_profile(self, user_id: str) -> UserProfile:
        """Get existing user profile or create new one"""
        try:
            # Try to get existing profile
            profile = self.db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                # Create new profile
                profile = UserProfile(
                    user_id=user_id,
                    profile_data={}
                )
                self.db.add(profile)
                self.db.commit()
                self.db.refresh(profile)
                logger.info(f"Created new user profile for user: {user_id}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to get/create user profile: {e}")
            self.db.rollback()
            raise
    
    def extract_profile_info(self, message: str, current_profile: UserProfile) -> Dict[str, Any]:
        """Extract profile information from user message"""
        message_lower = message.lower()
        extracted_info = {}
        
        # Extract channel name
        channel_patterns = [
            r"my channel is (.+)",
            r"channel name is (.+)",
            r"i have a channel called (.+)",
            r"mera channel (.+) hai"
        ]
        
        import re
        for pattern in channel_patterns:
            match = re.search(pattern, message_lower)
            if match:
                channel_name = match.group(1).strip()
                # Clean up common words
                channel_name = re.sub(r'\b(called|named|hai|is)\b', '', channel_name).strip()
                if channel_name and len(channel_name) > 2:
                    extracted_info['channel_name'] = channel_name
                    break
        
        # Extract goals
        goal_keywords = ['goal', 'want to', 'planning to', 'trying to', 'chahta hun', 'karna hai']
        if any(keyword in message_lower for keyword in goal_keywords):
            goals = current_profile.goals or []
            # Simple goal extraction - can be enhanced with NLP
            if 'subscribers' in message_lower:
                goals.append('grow_subscribers')
            if 'monetize' in message_lower or 'money' in message_lower:
                goals.append('monetization')
            if 'views' in message_lower:
                goals.append('increase_views')
            
            extracted_info['goals'] = list(set(goals))  # Remove duplicates
        
        # Extract equipment mentions
        equipment_keywords = ['camera', 'mic', 'microphone', 'laptop', 'phone', 'editing software']
        equipment = current_profile.equipment or []
        for keyword in equipment_keywords:
            if keyword in message_lower and keyword not in equipment:
                equipment.append(keyword)
        
        if equipment != (current_profile.equipment or []):
            extracted_info['equipment'] = equipment
        
        return extracted_info
    
    def update_profile(self, user_id: str, extracted_info: Dict[str, Any]) -> UserProfile:
        """Update user profile with extracted information"""
        try:
            profile = self.get_or_create_user_profile(user_id)
            
            # Update fields
            for key, value in extracted_info.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
                else:
                    # Store in profile_data JSON field
                    profile_data = profile.profile_data or {}
                    profile_data[key] = value
                    profile.profile_data = profile_data
            
            self.db.commit()
            self.db.refresh(profile)
            
            logger.info(f"Updated profile for user {user_id}: {extracted_info}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            self.db.rollback()
            raise

class ConversationManager:
    """Manages conversations and message history"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_conversation(self, user_id: str, creator_id: str, conversation_id: Optional[str] = None) -> Conversation:
        """Get existing conversation or create new one"""
        try:
            if conversation_id:
                conversation = self.db.query(Conversation).filter(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                    Conversation.creator_id == creator_id
                ).first()
                
                if conversation:
                    return conversation
            
            # Create new conversation
            conversation = Conversation(
                user_id=user_id,
                creator_id=creator_id,
                title=f"Chat with {creator_id}"
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            
            logger.info(f"Created new conversation: {conversation.id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to get/create conversation: {e}")
            self.db.rollback()
            raise
    
    def save_message(self, conversation_id: str, role: MessageRole, content: str, metadata: Dict[str, Any] = None) -> Message:
        """Save message to database"""
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role.value,
                content=content,
                metadata=metadata or {}
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            self.db.rollback()
            raise
    
    def get_recent_messages(self, conversation_id: str, limit: int = 10) -> List[Message]:
        """Get recent messages from conversation"""
        try:
            messages = self.db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.desc()).limit(limit).all()
            
            return list(reversed(messages))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []

class AIResponseGenerator:
    """Generates AI responses using Google Gemini"""
    
    def __init__(self):
        genai.configure(api_key=settings.ai.google_api_key)
        self.model = genai.GenerativeModel(settings.ai.model_name)
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def generate_response(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        user_profile: UserProfile,
        creator_config: Dict[str, Any],
        query_analysis: QueryAnalysis,
        conversation_history: List[Message]
    ) -> str:
        """Generate AI response asynchronously"""
        
        try:
            # Run AI generation in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._generate_response_sync,
                query, context_chunks, user_profile, creator_config, query_analysis, conversation_history
            )
            return response
            
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return self._get_fallback_response(query_analysis)
    
    def _generate_response_sync(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        user_profile: UserProfile,
        creator_config: Dict[str, Any],
        query_analysis: QueryAnalysis,
        conversation_history: List[Message]
    ) -> str:
        """Synchronous AI response generation"""
        
        # Build system prompt
        system_prompt = self._build_system_prompt(creator_config, user_profile, query_analysis)
        
        # Build context
        context_text = self._build_context(context_chunks)
        
        # Build conversation history
        history_text = self._build_history(conversation_history)
        
        # Build final prompt
        prompt = f"""{system_prompt}

CONTEXT INFORMATION:
{context_text}

CONVERSATION HISTORY:
{history_text}

USER QUERY: {query}

RESPONSE:"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=settings.ai.max_tokens,
                    temperature=settings.ai.temperature,
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return self._get_fallback_response(query_analysis)
    
    def _build_system_prompt(self, creator_config: Dict[str, Any], user_profile: UserProfile, query_analysis: QueryAnalysis) -> str:
        """Build system prompt based on creator and query type"""
        
        creator_name = creator_config.get('name', 'AI Assistant')
        specialty = creator_config.get('specialty', 'YouTube Expert')
        personality = creator_config.get('personality', {})
        
        base_prompt = f"""You are {creator_name}, a {specialty}. 

PERSONALITY:
- Tone: {personality.get('tone', 'friendly and helpful')}
- Language Style: {personality.get('language_style', 'professional with casual elements')}
- Expertise: {', '.join(personality.get('expertise_areas', ['YouTube growth']))}

USER PROFILE:
- Channel: {user_profile.channel_name or 'Not specified'}
- Goals: {', '.join(user_profile.goals or ['General YouTube growth'])}
- Equipment: {', '.join(user_profile.equipment or ['Not specified'])}
"""
        
        # Add specific instructions based on query type
        if query_analysis.intent == QueryIntent.HOW_TO or query_analysis.is_step_by_step:
            base_prompt += """
RESPONSE FORMAT FOR HOW-TO QUESTIONS:
Provide detailed step-by-step instructions in this format:

**[Topic] ke Steps:**

**Step 1: [Title]**
- [Detailed explanation in Hindi/Hinglish]
- [Practical tip]

**Step 2: [Title]**
- [Detailed explanation]
- [Example if needed]

[Continue for 3-8 steps based on complexity]

**Pro Tips:**
1. [Specific actionable tip]
2. [Advanced technique]
3. [Common mistake to avoid]
4. [Bonus insight]

**Next Steps:**
[What to do after completing these steps]

Use authentic Hindi/Hinglish expressions like "bhai", "tu", "tujhe", "dekh", "samjha?"
"""
        elif query_analysis.intent == QueryIntent.INAPPROPRIATE:
            base_prompt += """
INAPPROPRIATE CONTENT RESPONSE:
Politely decline and redirect to YouTube-related topics. Be professional but firm.
"""
        
        return base_prompt
    
    def _build_context(self, context_chunks: List[Dict[str, Any]]) -> str:
        """Build context from retrieved chunks"""
        if not context_chunks:
            return "No specific context available."
        
        context_parts = []
        for i, chunk in enumerate(context_chunks[:5], 1):  # Limit to top 5 chunks
            context_parts.append(f"Context {i}: {chunk.get('content', '')}")
        
        return "\n\n".join(context_parts)
    
    def _build_history(self, messages: List[Message]) -> str:
        """Build conversation history"""
        if not messages:
            return "No previous conversation."
        
        history_parts = []
        for message in messages[-6:]:  # Last 6 messages
            role = "User" if message.role == "user" else "Assistant"
            history_parts.append(f"{role}: {message.content}")
        
        return "\n".join(history_parts)
    
    def _get_fallback_response(self, query_analysis: QueryAnalysis) -> str:
        """Get fallback response when AI generation fails"""
        if query_analysis.intent == QueryIntent.GREETING:
            return "Namaste! Main Hawa Singh hun, YouTube growth expert. Kaise help kar sakta hun aapki?"
        elif query_analysis.intent == QueryIntent.INAPPROPRIATE:
            return "Main sirf YouTube growth aur content creation ke baare mein help kar sakta hun. Koi YouTube related question hai?"
        else:
            return "Sorry, main abhi response generate nahi kar pa raha. Thoda wait karke phir try karo ya question ko simple words mein poocho."

class ChatProcessor:
    """Main chat processing orchestrator"""
    
    def __init__(self):
        self.ai_generator = AIResponseGenerator()
    
    async def process_chat(self, request: ChatRequest, db: Session) -> ChatResponse:
        """Process chat request and generate response"""
        start_time = time.time()
        
        try:
            # Initialize managers
            profile_manager = UserProfileManager(db)
            conversation_manager = ConversationManager(db)
            
            # Get or create user profile
            user_profile = profile_manager.get_or_create_user_profile(request.user_id)
            
            # Extract profile information from message
            extracted_info = profile_manager.extract_profile_info(request.message, user_profile)
            if extracted_info:
                user_profile = profile_manager.update_profile(request.user_id, extracted_info)
            
            # Get or create conversation
            conversation = conversation_manager.get_or_create_conversation(
                request.user_id, request.creator_id, request.conversation_id
            )
            
            # Save user message
            conversation_manager.save_message(
                conversation.id, MessageRole.USER, request.message
            )
            
            # Get conversation history
            conversation_history = conversation_manager.get_recent_messages(conversation.id)
            
            # Get context from retrieval service
            context_chunks = await self._get_context(request.message, request.creator_id)
            
            # Analyze query (simple analysis for now)
            query_analysis = self._analyze_query_simple(request.message)
            
            # Get creator configuration
            creator_config = get_creator_config(request.creator_id)
            
            # Generate AI response
            ai_response = await self.ai_generator.generate_response(
                query=request.message,
                context_chunks=context_chunks,
                user_profile=user_profile,
                creator_config=creator_config,
                query_analysis=query_analysis,
                conversation_history=conversation_history
            )
            
            # Save assistant message
            conversation_manager.save_message(
                conversation.id, MessageRole.ASSISTANT, ai_response,
                metadata={
                    "context_chunks_used": len(context_chunks),
                    "processing_time": time.time() - start_time,
                    "query_intent": query_analysis.intent.value
                }
            )
            
            processing_time = time.time() - start_time
            
            return ChatResponse(
                response=ai_response,
                conversation_id=conversation.id,
                context_used=len(context_chunks),
                intent=query_analysis.intent,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            raise
    
    async def _get_context(self, query: str, creator_id: str) -> List[Dict[str, Any]]:
        """Get context from retrieval service"""
        try:
            retrieval_request = RetrievalRequest(
                query=query,
                creator_id=creator_id,
                max_chunks=5,
                similarity_threshold=0.7
            )
            
            # Call retrieval service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.get_service_url('retrieval_service')}/retrieve",
                    json=retrieval_request.dict(),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("chunks", [])
                else:
                    logger.error(f"Retrieval service error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return []
    
    def _analyze_query_simple(self, query: str) -> QueryAnalysis:
        """Simple query analysis (fallback when retrieval service is unavailable)"""
        query_lower = query.lower()
        
        # Check for greetings
        greetings = ["hi", "hello", "hey", "namaste", "hola"]
        is_greeting = any(greeting in query_lower for greeting in greetings)
        
        # Check for inappropriate content
        inappropriate_keywords = ["sex", "porn", "adult", "nsfw", "sext"]
        is_inappropriate = any(keyword in query_lower for keyword in inappropriate_keywords)
        
        # Check for how-to questions
        is_step_by_step = "how to" in query_lower or "steps" in query_lower or "kaise" in query_lower
        
        # Determine intent
        if is_greeting:
            intent = QueryIntent.GREETING
        elif is_inappropriate:
            intent = QueryIntent.INAPPROPRIATE
        elif is_step_by_step:
            intent = QueryIntent.HOW_TO
        else:
            intent = QueryIntent.QUESTION
        
        return QueryAnalysis(
            intent=intent,
            complexity=QueryComplexity.SIMPLE,
            is_greeting=is_greeting,
            is_inappropriate=is_inappropriate,
            is_step_by_step=is_step_by_step,
            confidence=0.8
        ) 