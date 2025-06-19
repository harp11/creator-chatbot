import streamlit as st
import google.generativeai as genai
import config
import time
from src.retrieval import IntelligentRetriever
from verify_setup import verify_complete_setup
import subprocess
import sys
import re
from datetime import datetime
import os

# Page config should be the first Streamlit command
st.set_page_config(
    page_title="Hawa Singh - YouTube Expert",
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Production configuration
if os.getenv('STREAMLIT_SERVER_PORT'):
    # Running in production
    st.set_page_config(
        page_title="Hawa Singh - YouTube Expert",
        page_icon="🎯", 
        layout="wide",
        initial_sidebar_state="expanded"
    )

def check_watchdog():
    """Check if watchdog is installed and install if missing"""
    try:
        import watchdog
        return True
    except ImportError:
        if sys.platform == "darwin":  # macOS
            print("Installing required dependencies for better performance...")
            try:
                subprocess.run(["xcode-select", "--install"], capture_output=True)
            except:
                pass  # Ignore if xcode command line tools are already installed
            subprocess.run([sys.executable, "-m", "pip", "install", "watchdog"], check=True)
            return True
    return False

# Initialize session state at the module level
if "app_state" not in st.session_state:
    st.session_state.app_state = {
        "initialized": False,
        "messages": [],
        "retriever": None,
        "chat": None,
        "debug_mode": False,
        "startup_complete": False,
        "initialization_attempted": False,
        "current_question": None,
        "user_profile": {
            # Basic Info
            "channel_name": None,
            "name": None,
            "age": None,
            "location": None,
            "profession": None,
            
            # Channel Details
            "content_type": None,
            "niche": None,
            "subscriber_count": None,
            "upload_frequency": None,
            "channel_age": None,
            
            # Personal Preferences
            "language_preference": "hinglish",
            "experience_level": None,
            "goals": [],
            "interests": [],
            "target_audience": None,
            
            # Technical Setup
            "equipment": [],
            "editing_software": None,
            "budget": None,
            
            # Challenges & Aspirations
            "main_challenges": [],
            "inspiration": [],
            "dream_collab": None,
            
            # Metadata
            "last_updated": None,
            "conversation_count": 0
        }
    }

# Safety check to ensure user_profile exists (in case of partial initialization)
if "user_profile" not in st.session_state.app_state:
    st.session_state.app_state["user_profile"] = {
        # Basic Info
        "channel_name": None,
        "name": None,
        "age": None,
        "location": None,
        "profession": None,
        
        # Channel Details
        "content_type": None,
        "niche": None,
        "subscriber_count": None,
        "upload_frequency": None,
        "channel_age": None,
        
        # Personal Preferences
        "language_preference": "hinglish",
        "experience_level": None,
        "goals": [],
        "interests": [],
        "target_audience": None,
        
        # Technical Setup
        "equipment": [],
        "editing_software": None,
        "budget": None,
        
        # Challenges & Aspirations
        "main_challenges": [],
        "inspiration": [],
        "dream_collab": None,
        
        # Metadata
        "last_updated": None,
        "conversation_count": 0
    }

@st.cache_resource(show_spinner=False)
def get_retriever():
    """Get or create the retriever instance"""
    return IntelligentRetriever()

@st.cache_resource(show_spinner=False)
def get_chat():
    """Get or create the chat instance"""
    genai.configure(api_key=config.GOOGLE_API_KEY)
    model = genai.GenerativeModel(config.MODEL_NAME)
    return model.start_chat(history=[])

def initialize_app():
    """Initialize the app components"""
    # Only attempt initialization once
    if st.session_state.app_state["initialization_attempted"]:
        return st.session_state.app_state["initialized"]
        
    st.session_state.app_state["initialization_attempted"] = True
    
    try:
        with st.spinner("🚀 Initializing Creator Chatbot..."):
            if not verify_complete_setup():
                st.error("❌ Setup verification failed! Please run: python build_vector_database.py")
                st.stop()
                return False
                
            # Initialize components using cached functions
            st.session_state.app_state["retriever"] = get_retriever()
            st.session_state.app_state["chat"] = get_chat()
            st.session_state.app_state["initialized"] = True
            
            if st.session_state.app_state["debug_mode"]:
                st.success("✅ Initialization complete!")
                
    except Exception as e:
        st.error(f"❌ Initialization failed: {str(e)}")
        return False
        
    return True

def is_topic_continuation(query: str, messages: list) -> bool:
    """Detect if the user is continuing the same topic"""
    if len(messages) < 2:
        return False
    
    # Get the last assistant message to see what topic was discussed
    last_assistant_msg = None
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            last_assistant_msg = msg["content"]
            break
    
    if not last_assistant_msg:
        return False
    
    # Keywords that indicate continuation
    continuation_keywords = [
        "more", "also", "and", "what about", "how about", "tell me more",
        "aur", "bhi", "kya", "kaise", "kahan", "kab", "kyun", "kaun",
        "further", "next", "then", "after", "before", "during",
        "aage", "pehle", "baad", "duran", "samay", "process"
    ]
    
    query_lower = query.lower()
    last_msg_lower = last_assistant_msg.lower()
    
    # Check if query contains continuation keywords
    has_continuation_keywords = any(keyword in query_lower for keyword in continuation_keywords)
    
    # Check if query is asking for more details about the same topic
    topic_words = []
    for word in last_msg_lower.split():
        if len(word) > 3 and word not in ["the", "and", "for", "you", "are", "with", "this", "that"]:
            topic_words.append(word)
    
    # Check if any topic words from last message appear in current query
    topic_continuation = any(word in query_lower for word in topic_words[:5])  # Check first 5 topic words
    
    return has_continuation_keywords or topic_continuation

def is_greeting_or_introduction(query: str) -> bool:
    """Use AI to determine if the query is just a greeting or introduction"""
    
    # First check if this is a topic continuation
    messages = st.session_state.app_state["messages"]
    if is_topic_continuation(query, messages):
        return False  # Don't treat topic continuations as greetings
    
    try:
        # Create a simple prompt to classify the intent
        classification_prompt = f"""Analyze this user message and determine the intent:

User message: "{query}"

Respond with ONLY one word:
- "GREETING" if it's ONLY a simple greeting or casual hello (like "hi", "hello", "hey", "namaste", "kaise ho")
- "NAME_QUESTION" if they're asking ONLY about your name or identity (like "what's your name?", "who are you?", "aap ka name?")
- "QUESTION" if they're asking for information, advice, or anything else (including questions about themselves, locations, YouTube help, etc.)

Examples:
- "hi" → GREETING
- "hello bhai" → GREETING
- "namaste" → GREETING
- "what's your name?" → NAME_QUESTION
- "who are you?" → NAME_QUESTION
- "where am i from?" → QUESTION (asking for information)
- "how to grow channel?" → QUESTION
- "what are best thumbnails?" → QUESTION
- "tell me about myself" → QUESTION
- "where do I live?" → QUESTION

IMPORTANT: If they're asking for ANY information or advice (even about themselves), classify as QUESTION, not GREETING.

Your response (one word only):"""

        # Use the existing chat instance for classification
        model = genai.GenerativeModel(config.MODEL_NAME)
        temp_chat = model.start_chat(history=[])
        response = temp_chat.send_message(classification_prompt)
        
        result = response.text.strip().upper()
        return result in ["GREETING", "NAME_QUESTION"]
        
    except Exception as e:
        print(f"AI greeting detection error: {e}")
        # Fallback to simple keyword check
        query_lower = query.lower().strip()
        simple_greetings = ['hi', 'hello', 'hey', 'namaste']
        name_questions = ['name', 'who are', 'aap ka name', 'ur name']
        return query_lower in simple_greetings or any(keyword in query_lower for keyword in name_questions)

def get_greeting_response_type(query: str) -> str:
    """Determine the type of greeting response needed"""
    try:
        classification_prompt = f"""Analyze this user message and determine the response type needed:

User message: "{query}"

Respond with ONLY one word:
- "SIMPLE_GREETING" for basic greetings (hi, hello, kaise ho, etc.)
- "NAME_QUESTION" for name/identity questions (what's your name, who are you, etc.)
- "INTRODUCTION" for user introductions (I am John, my name is, etc.)

Examples:
- "hi" → SIMPLE_GREETING
- "kaise ho?" → SIMPLE_GREETING
- "what's your name?" → NAME_QUESTION
- "who are you?" → NAME_QUESTION
- "aap ka name?" → NAME_QUESTION
- "I am Hari" → INTRODUCTION

Your response (one word only):"""

        model = genai.GenerativeModel(config.MODEL_NAME)
        temp_chat = model.start_chat(history=[])
        response = temp_chat.send_message(classification_prompt)
        
        return response.text.strip().upper()
            
    except Exception as e:
        print(f"Greeting type detection error: {e}")
        return "SIMPLE_GREETING"

def is_inappropriate_content(query: str) -> bool:
    """Check if the query contains inappropriate content"""
    inappropriate_keywords = [
        'sex', 'sext', 'sexting', 'porn', 'adult', 'nsfw', 'nude', 'naked', 
        'explicit', 'intimate', 'sexual', 'erotic', 'xxx', 'dating', 'hookup',
        'flirt', 'romance', 'love', 'relationship', 'girlfriend', 'boyfriend'
    ]
    
    query_lower = query.lower().strip()
    
    # Check for direct matches or partial matches
    for keyword in inappropriate_keywords:
        if keyword in query_lower:
            return True
    
    return False

def is_step_by_step_question(query: str) -> bool:
    """Detect if the query is asking for step-by-step instructions"""
    step_keywords = [
        # English keywords
        'steps', 'how to', 'how do i', 'how can i', 'step by step', 'guide', 'tutorial',
        'process', 'method', 'procedure', 'way to', 'ways to', 'explain how',
        'show me how', 'teach me', 'walk me through', 'break down',
        
        # Hindi/Hinglish keywords
        'kaise', 'kaise karu', 'kaise kare', 'kaise banau', 'kaise banaye', 'kaise start karu',
        'banane ke', 'karne ke', 'shuru karne ke', 'banana hai', 'karna hai',
        'tareeka', 'tarika', 'vidhi', 'samjhao', 'batao', 'sikhao', 'bolo',
        'step batao', 'steps batao', 'process batao', 'method batao',
        
        # Question patterns
        'what are the steps', 'what steps', 'which steps', 'steps for',
        'how should i', 'what should i do', 'where do i start',
        'kya steps', 'kya karna', 'kya process', 'kahan se start',
        
        # Action-oriented keywords
        'create', 'build', 'make', 'start', 'begin', 'setup', 'set up',
        'banao', 'banaye', 'shuru karo', 'start karo', 'setup karo'
    ]
    
    query_lower = query.lower().strip()
    
    # Direct keyword matching
    if any(keyword in query_lower for keyword in step_keywords):
        return True
    
    # Pattern matching for question structures
    step_patterns = [
        r'\bhow\s+(to|do|can|should)\s+i\b',
        r'\bkaise\s+(karu|kare|banau|banaye|start)\b',
        r'\bsteps?\s+(for|to|ke\s+liye)\b',
        r'\bprocess\s+(for|to|ke\s+liye)\b',
        r'\bguide\s+(for|to|ke\s+liye)\b',
        r'\btutorial\s+(for|to|ke\s+liye)\b',
        r'\bbreak\s+down\b',
        r'\bwalk\s+me\s+through\b',
        r'\bshow\s+me\s+how\b',
        r'\bteach\s+me\b',
        r'\bexplain\s+how\b'
    ]
    
    for pattern in step_patterns:
        if re.search(pattern, query_lower):
            return True
    
    return False

def is_continuation_of_conversation(messages: list) -> bool:
    """Detect if this is a continuation of an existing conversation"""
    if len(messages) < 2:
        return False
    
    # Check if we have at least one exchange (user + assistant)
    user_messages = [msg for msg in messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
    
    return len(user_messages) >= 1 and len(assistant_messages) >= 1

def get_conversation_context(messages: list) -> str:
    """Get conversation context for multi-turn conversations"""
    if not is_continuation_of_conversation(messages):
        return "This is the start of a new conversation."
    
    # Get the last few exchanges for context
    recent_messages = messages[-4:]  # Last 2 exchanges (4 messages)
    
    context_parts = []
    for msg in recent_messages:
        role = "User" if msg["role"] == "user" else "Hawa Singh"
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        context_parts.append(f"{role}: {content}")
    
    return "Recent conversation:\n" + "\n".join(context_parts)

def get_system_prompt(context: dict, query: str) -> str:
    """Get the system prompt with context"""
    
    # Get conversation state
    messages = st.session_state.app_state["messages"]
    is_continuation = is_continuation_of_conversation(messages)
    conversation_context = get_conversation_context(messages)
    
    # Check for inappropriate content first
    if is_inappropriate_content(query):
        return f"""You are Hawa Singh, a professional YouTube Growth Expert who speaks in natural Hinglish.

The user sent an inappropriate message: "{query}"

Respond professionally and redirect to YouTube topics. Be polite but firm.

RESPONSE TEMPLATE:
"Sorry bhai, main sirf YouTube growth aur content creation ke baare mein help karta hoon. Let's focus on growing your channel! 

Kya aap YouTube ke baare mein kuch puchna chahte ho? Main help kar sakta hoon with:
- Channel growth tips
- Content ideas  
- Monetization strategies
- Audience engagement

Kya chahiye help?"

Keep it professional, brief, and redirect to YouTube topics."""
    
    # Use AI to detect greetings instead of hard-coded patterns
    if is_greeting_or_introduction(query):
        # Get the specific type of greeting response needed
        response_type = get_greeting_response_type(query)
        
        if response_type == "NAME_QUESTION":
            return f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user asked: "{query}"

Respond with a warm, natural introduction in Hinglish. Include your credentials.

Example style:
"Namaste! Main Hawa Singh hoon - YouTube growth expert with 500K+ subscribers. Aapki channel ki growth mein help karta hoon. Kya puchna chahte ho?"

Keep it natural, warm, and under 30 words."""
        
        elif response_type == "INTRODUCTION":
            return f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user introduced themselves: "{query}"

Respond warmly, acknowledge their introduction, and introduce yourself naturally in Hinglish.

Example style:
"Nice to meet you! Main Hawa Singh hoon, YouTube expert with 500K+ subscribers. Aapki journey mein help karunga. Kya chahiye help?"

Keep it natural, warm, and under 30 words."""
        
        else:  # SIMPLE_GREETING
            return f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user greeted you: "{query}"

Respond with a warm, natural greeting back in Hinglish. Be friendly and inviting.

Example style:
"Namaste dost! Kaise ho? Main Hawa Singh - YouTube expert with 500K+ subscribers. Kya help chahiye aaj?"

Keep it natural, warm, and under 30 words."""
    
    # Check if user is asking about their own information
    personal_info_queries = [
        "my channel name", "what's my channel", "whats my channel", "my name", "who am i", 
        "where am i from", "my age", "my location", "my subscribers", "my content", 
        "tell me about myself", "my profile", "my information", "what do you know about me"
    ]
    
    query_lower = query.lower()
    is_personal_query = any(phrase in query_lower for phrase in personal_info_queries)
    
    # Get user profile information
    user_profile = st.session_state.app_state["user_profile"]
    profile_context = format_user_context(user_profile)
    
    if is_personal_query:
        # Special handling for personal information queries
        return f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user is asking about their personal information: "{query}"

USER PROFILE INFORMATION:
{profile_context}

INSTRUCTIONS:
- If the user asks about specific information that IS available in their profile, provide it warmly
- If the user asks about information that is NOT available, politely explain you don't have that information yet
- Always be encouraging and suggest how they can share more information with you
- Use natural Hinglish and be conversational

RESPONSE EXAMPLES:
- If they ask "what's my channel name" and you have it: "Aapka channel name hai [channel_name]! Great choice, bhai!"
- If they ask "what's my channel name" and you DON'T have it: "Abhi tak aapne apna channel name nahi bataya hai. Kya hai aapka channel name? Main yaad rakh lunga!"
- If they ask "where am I from" and you have it: "Aap [location] se ho! Nice place, yaar!"
- If they ask "where am I from" and you DON'T have it: "Aapne abhi tak nahi bataya ki aap kahan se ho. Kahan se ho aap? Batao na!"

Keep it natural, warm, and conversational. Always end with a follow-up question to keep the conversation going.

User Query: {query}"""
    
    # Original detailed system prompt for complex questions
    is_how_to_question = is_step_by_step_question(query)
    
    if is_how_to_question:
        # Special format for step-by-step questions
        greeting_instruction = "start with a humble greeting" if not is_continuation else "don't start with a greeting since this is a continuation"
        
        return f"""You are Hawa Singh, a YouTube Growth Expert who speaks in natural Hinglish (Hindi + English mix).

The user is asking a HOW-TO/STEP-BY-STEP question: "{query}"

CONVERSATION CONTEXT:
{conversation_context}

RESPOND USING THIS EXACT FORMAT (adapt the content dynamically):

{greeting_instruction} !!][Extract main topic from query] simple hai — main tujhe step-by-step tareeke se samjhaata hoon, jisse tu bina kisi confusion ke [goal/outcome] kar le.

✅ [Main Topic Title] Ke Complete Steps

🟢 Step 1: [First Essential Step]
[Detailed explanation in simple Hindi/Hinglish - 2-3 lines]

[Add sub-points if needed using bullet points]
• [Sub-point 1]
• [Sub-point 2]

🟢 Step 2: [Second Essential Step]  
[Detailed explanation - 2-3 lines]

[Add practical examples or specific instructions]
• [Example/specific instruction]
• [Another example if needed]

🟢 Step 3: [Third Essential Step]
[Detailed explanation - 2-3 lines]

🟢 Step 4: [Fourth Step - if needed]
[Continue with as many steps as required for the topic]

🟢 Step 5: [Fifth Step - if needed]
[Add more steps dynamically based on complexity]

[Continue adding steps as needed - can go up to 8-10 steps for complex topics]

🔥 Pro Tips: [Topic] Ke Liye Important Baatein
• [Practical tip 1 - specific and actionable]
• [Practical tip 2 - based on experience] 
• [Practical tip 3 - common mistake to avoid]
• [Practical tip 4 - advanced suggestion if relevant]

💡 Extra Bonus Tips:
• [Advanced tip or insider knowledge]
• [Tool/resource recommendation]
• [Time-saving hack]

🚀 Next Steps Aur Growth:
[Suggest what to do after completing these steps - 1-2 lines]

Agar tu chahe to main [related specific help] bhi suggest kar sakta hoon. Bata [specific follow-up question related to the topic]?

IMPORTANT GUIDELINES:
- Use natural Hindi/Hinglish language like "bhai", "tu", "tujhe", "yaar"
- Be conversational and friendly throughout
- Give detailed, actionable steps (minimum 3 steps, maximum 10 based on complexity)
- Include practical examples and specific instructions
- Add sub-points under steps when needed for clarity
- Include 3-4 pro tips that are genuinely helpful
- Add bonus tips for advanced users
- Suggest logical next steps for continued growth
- End with a specific, helpful follow-up question
- Adapt the number of steps based on topic complexity
- Use emojis consistently for visual appeal
- Make each step substantial and valuable
- {greeting_instruction}

CONTEXT TO USE:
{context['context']['chunks'][0].get('content', context['context']['chunks'][0].get('text', 'No specific context found.')) if context['context']['chunks'] else 'No specific context found.'}

USER PROFILE CONTEXT:
{profile_context}

RECENT CONVERSATION:
{format_chat_history(st.session_state.app_state["messages"], max_messages=3)}

User Query: {query}

Remember: Make the response comprehensive, practical, and genuinely helpful. Adapt the structure dynamically based on the complexity of the question!"""
    
    else:
        # Regular format for general questions
        greeting_instruction = "Start with a greeting" if not is_continuation else "Don't start with a greeting - this is a continuation of our conversation"
        
        return f"""You are Hawa Singh, a YouTube Growth Expert who speaks in natural Hinglish (Hindi + English mix).

IMPORTANT: Use the provided context to give specific, detailed answers. Don't give generic responses.

CONVERSATION CONTEXT:
{conversation_context}

CONTEXT FROM KNOWLEDGE BASE:
{context['context']['chunks'][0].get('content', context['context']['chunks'][0].get('text', 'No specific context found.')) if context['context']['chunks'] else 'No specific context found.'}

USER PROFILE:
{profile_context}

RECENT CONVERSATION:
{format_chat_history(st.session_state.app_state["messages"], max_messages=st.session_state.app_state.get("context_limit", 6))}

USER QUERY: {query}

INSTRUCTIONS:
- Use the context above to provide specific, detailed answers
- Don't give generic responses like "That's a nice question"
- Provide actionable advice based on the context
- Use natural Hinglish language
- Be specific and helpful
- If the context doesn't have enough information, ask for more details
- {greeting_instruction}

RESPONSE FORMAT:
{greeting_instruction}

[Detailed answer using the context provided]

[Actionable steps or tips]

[Follow-up question]

Respond with specific, helpful information based on the context provided!"""

def clean_response_formatting(response_text: str) -> str:
    """Clean and format response to ensure proper markdown structure"""
    if not response_text:
        return response_text
    
    # Split into lines and clean up
    lines = response_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Ensure proper spacing around section headers
            if line.startswith('🎯') or line.startswith('📈') or line.startswith('💡'):
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')  # Add blank line before section
                cleaned_lines.append(line)
                cleaned_lines.append('')  # Add blank line after section header
            # Handle bullet points
            elif line.startswith('🔸'):
                cleaned_lines.append(line)
                cleaned_lines.append('')  # Add blank line after bullet
            else:
                cleaned_lines.append(line)
        else:
            # Preserve intentional blank lines but avoid multiple consecutive ones
            if cleaned_lines and cleaned_lines[-1] != '':
                cleaned_lines.append('')
    
    # Join back and clean up multiple consecutive blank lines
    result = '\n'.join(cleaned_lines)
    
    # Remove multiple consecutive blank lines
    import re
    result = re.sub(r'\n\n\n+', '\n\n', result)
    
    return result.strip()

def format_chat_history(messages: list, max_messages: int = 6) -> str:
    """Format chat history for context with configurable limit"""
    if not messages:
        return "No previous context."
    
    # Take the most recent messages up to the limit
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    formatted = []
    for msg in recent_messages:
        role = "Hawa Singh" if msg["role"] == "assistant" else "User"
        # Truncate very long messages to avoid token bloat
        content = msg['content']
        if len(content) > 200:
            content = content[:200] + "..."
        formatted.append(f"{role}: {content}")
    
    # Add context about truncation if needed
    if len(messages) > max_messages:
        formatted.insert(0, f"[Showing last {max_messages} of {len(messages)} total messages]")
    
    return "\n".join(formatted)

def extract_user_info(message: str, current_profile: dict) -> dict:
    """Extract user information from messages and update profile"""
    updated_profile = current_profile.copy()
    message_lower = message.lower()
    
    # Debug: Track what we're trying to extract
    if st.session_state.app_state.get("debug_mode", False):
        print(f"🔍 Profile Extraction Debug: Processing message: '{message}'")
    
    # Extract channel name patterns
    channel_patterns = [
        r"my channel name is ([a-zA-Z0-9\s]+)",
        r"channel name is ([a-zA-Z0-9\s]+)",
        r"my channel is called ([a-zA-Z0-9\s]+)",
        r"my channel ([a-zA-Z0-9\s]+)",
        r"channel called ([a-zA-Z0-9\s]+)",
        r"channel is ([a-zA-Z0-9\s]+)",
        r"i have a channel called ([a-zA-Z0-9\s]+)",
        r"i run ([a-zA-Z0-9\s]+) channel",
        r"my youtube channel ([a-zA-Z0-9\s]+)",
        r"channel name: ([a-zA-Z0-9\s]+)",
        r"channel - ([a-zA-Z0-9\s]+)"
    ]
    
    for pattern in channel_patterns:
        match = re.search(pattern, message_lower)
        if match:
            channel_name = match.group(1).strip().title()
            # Filter out common words that aren't channel names
            if (len(channel_name) > 1 and 
                channel_name.lower() not in ["is", "the", "a", "an", "my", "called", "name", "youtube", "channel"]):
                updated_profile["channel_name"] = channel_name
                if st.session_state.app_state.get("debug_mode", False):
                    print(f"✅ Profile Debug: Extracted channel name: '{channel_name}'")
                break
    
    # Extract name patterns
    name_patterns = [
        r"my name is ([a-zA-Z\s]+)",
        r"i'm ([a-zA-Z\s]+)",
        r"call me ([a-zA-Z\s]+)",
        r"i am ([a-zA-Z\s]+)",
        r"name is ([a-zA-Z\s]+)",
        r"i'm called ([a-zA-Z\s]+)",
        r"they call me ([a-zA-Z\s]+)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, message_lower)
        if match:
            name = match.group(1).strip().title()
            # Filter common words that aren't names
            if (len(name) > 1 and 
                name.lower() not in ["a", "an", "the", "from", "to", "going", "making", "doing", "years", "old", "channel", "youtube"]):
                updated_profile["name"] = name
                if st.session_state.app_state.get("debug_mode", False):
                    print(f"✅ Profile Debug: Extracted name: '{name}'")
                break
    
    # Extract age patterns
    age_patterns = [
        r"i am (\d+) years old",
        r"i'm (\d+) years old",
        r"my age is (\d+)",
        r"i am (\d+)",
        r"i'm (\d+)"
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, message_lower)
        if match:
            age = int(match.group(1))
            if 10 <= age <= 100:  # Reasonable age range
                updated_profile["age"] = age
                break
    
    # Extract location patterns
    location_patterns = [
        r"i am from ([a-zA-Z\s]+)",
        r"i'm from ([a-zA-Z\s]+)",
        r"i live in ([a-zA-Z\s]+)",
        r"from ([a-zA-Z\s]+)",
        r"based in ([a-zA-Z\s]+)"
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, message_lower)
        if match:
            location = match.group(1).strip().title()
            if len(location) > 2:  # Avoid single letters
                updated_profile["location"] = location
                break
    
    # Extract subscriber count patterns
    subscriber_patterns = [
        r"(\d+)k subscribers",
        r"(\d+) thousand subscribers",
        r"(\d+) subscribers",
        r"(\d+)k subs",
        r"have (\d+) subscribers"
    ]
    
    for pattern in subscriber_patterns:
        match = re.search(pattern, message_lower)
        if match:
            count = match.group(1)
            if "k" in pattern or "thousand" in pattern:
                updated_profile["subscriber_count"] = f"{count}K"
            else:
                updated_profile["subscriber_count"] = count
            break
    
    # Extract content type and niche
    content_keywords = {
        "travel": ["travel", "explore", "trip", "journey", "adventure", "places", "destination"],
        "tech": ["tech", "technology", "coding", "programming", "software", "gadgets", "reviews"],
        "gaming": ["gaming", "games", "gameplay", "streamer", "esports", "mobile games"],
        "cooking": ["cooking", "recipe", "food", "kitchen", "chef", "baking"],
        "fitness": ["fitness", "workout", "gym", "health", "yoga", "exercise"],
        "education": ["education", "tutorial", "teaching", "learning", "study", "academic"],
        "entertainment": ["comedy", "funny", "entertainment", "jokes", "memes", "reaction"],
        "music": ["music", "singing", "songs", "musician", "cover", "original"],
        "lifestyle": ["lifestyle", "vlog", "daily", "routine", "fashion", "beauty"],
        "business": ["business", "entrepreneur", "startup", "finance", "investment"],
        "art": ["art", "drawing", "painting", "creative", "design", "craft"]
    }
    
    for content_type, keywords in content_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            updated_profile["content_type"] = content_type
            # Also set niche if more specific
            for keyword in keywords:
                if keyword in message_lower:
                    updated_profile["niche"] = keyword
                    break
            break
    
    # Extract experience level
    if any(word in message_lower for word in ["beginner", "new", "started", "starting", "just began"]):
        updated_profile["experience_level"] = "beginner"
    elif any(word in message_lower for word in ["experienced", "years", "long time", "expert", "professional"]):
        updated_profile["experience_level"] = "experienced"
    
    # Extract goals
    goal_keywords = {
        "monetization": ["monetize", "money", "earn", "income", "revenue", "ads", "sponsorship"],
        "growth": ["grow", "subscribers", "views", "audience", "reach", "viral"],
        "engagement": ["engagement", "comments", "likes", "community", "interaction"],
        "viral": ["viral", "trending", "popular", "famous", "blow up"],
        "brand": ["brand", "personal brand", "branding", "recognition"],
        "education": ["teach", "educate", "help people", "share knowledge"]
    }
    
    for goal, keywords in goal_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            if goal not in updated_profile["goals"]:
                updated_profile["goals"].append(goal)
    
    # Extract interests
    interest_keywords = [
        "love", "enjoy", "passionate", "interested", "hobby", "favorite", "like"
    ]
    
    for keyword in interest_keywords:
        if keyword in message_lower:
            # Extract what comes after the interest keyword
            pattern = rf"{keyword} (\w+(?:\s+\w+)?)"
            match = re.search(pattern, message_lower)
            if match:
                interest = match.group(1)
                if interest not in updated_profile["interests"] and len(interest) > 2:
                    updated_profile["interests"].append(interest)
    
    # Extract equipment
    equipment_keywords = [
        "camera", "mic", "microphone", "phone", "iphone", "android", "laptop", 
        "editing", "lights", "tripod", "gimbal", "drone"
    ]
    
    for equipment in equipment_keywords:
        if equipment in message_lower:
            if equipment not in updated_profile["equipment"]:
                updated_profile["equipment"].append(equipment)
    
    # Extract editing software
    editing_software = ["premiere", "final cut", "davinci", "filmora", "canva", "photoshop"]
    for software in editing_software:
        if software in message_lower:
            updated_profile["editing_software"] = software
            break
    
    # Extract budget information
    budget_patterns = [
        r"budget is (\d+)",
        r"have (\d+) rupees",
        r"(\d+) rs budget",
        r"spend (\d+)"
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, message_lower)
        if match:
            updated_profile["budget"] = match.group(1)
            break
    
    # Extract challenges
    challenge_keywords = [
        "struggle", "problem", "issue", "difficulty", "challenge", "hard", "tough"
    ]
    
    for keyword in challenge_keywords:
        if keyword in message_lower:
            # Extract context around the challenge
            words = message_lower.split()
            try:
                idx = words.index(keyword)
                context = " ".join(words[max(0, idx-2):idx+3])
                if context not in updated_profile["main_challenges"]:
                    updated_profile["main_challenges"].append(context)
            except ValueError:
                continue
    
    # Extract upload frequency
    frequency_patterns = [
        r"upload (\w+)",
        r"post (\w+)",
        r"(\w+) videos per week",
        r"(\w+) times a week"
    ]
    
    for pattern in frequency_patterns:
        match = re.search(pattern, message_lower)
        if match:
            frequency = match.group(1)
            if frequency in ["daily", "weekly", "monthly", "twice", "once", "regularly"]:
                updated_profile["upload_frequency"] = frequency
                break
    
    # Extract inspiration/role models
    inspiration_patterns = [
        r"inspired by (\w+)",
        r"like (\w+)",
        r"follow (\w+)",
        r"watch (\w+)"
    ]
    
    for pattern in inspiration_patterns:
        match = re.search(pattern, message_lower)
        if match:
            inspiration = match.group(1)
            if len(inspiration) > 2 and inspiration not in updated_profile["inspiration"]:
                updated_profile["inspiration"].append(inspiration)
    
    # Update metadata
    updated_profile["last_updated"] = datetime.now().isoformat()
    updated_profile["conversation_count"] = updated_profile.get("conversation_count", 0) + 1
    
    return updated_profile

def format_user_context(profile: dict) -> str:
    """Format user profile for system prompt"""
    context_parts = []
    
    # Basic Information
    if profile.get("name"):
        context_parts.append(f"User Name: {profile['name']}")
    
    if profile.get("age"):
        context_parts.append(f"Age: {profile['age']} years old")
    
    if profile.get("location"):
        context_parts.append(f"Location: {profile['location']}")
    
    if profile.get("profession"):
        context_parts.append(f"Profession: {profile['profession']}")
    
    # Channel Information
    if profile.get("channel_name"):
        context_parts.append(f"Channel Name: {profile['channel_name']}")
    
    if profile.get("content_type"):
        content_info = f"Content Type: {profile['content_type']}"
        if profile.get("niche"):
            content_info += f" (Niche: {profile['niche']})"
        context_parts.append(content_info)
    
    if profile.get("subscriber_count"):
        context_parts.append(f"Subscribers: {profile['subscriber_count']}")
    
    if profile.get("upload_frequency"):
        context_parts.append(f"Upload Frequency: {profile['upload_frequency']}")
    
    if profile.get("experience_level"):
        context_parts.append(f"Experience Level: {profile['experience_level']}")
    
    # Goals and Interests
    if profile.get("goals"):
        context_parts.append(f"Goals: {', '.join(profile['goals'])}")
    
    if profile.get("interests"):
        context_parts.append(f"Interests: {', '.join(profile['interests'][:5])}")  # Limit to 5 interests
    
    if profile.get("target_audience"):
        context_parts.append(f"Target Audience: {profile['target_audience']}")
    
    # Technical Setup
    if profile.get("equipment"):
        context_parts.append(f"Equipment: {', '.join(profile['equipment'][:3])}")  # Limit to 3 items
    
    if profile.get("editing_software"):
        context_parts.append(f"Editing Software: {profile['editing_software']}")
    
    if profile.get("budget"):
        context_parts.append(f"Budget: ₹{profile['budget']}")
    
    # Challenges and Inspiration
    if profile.get("main_challenges"):
        challenges_summary = f"{len(profile['main_challenges'])} main challenges identified"
        context_parts.append(f"Challenges: {challenges_summary}")
    
    if profile.get("inspiration"):
        context_parts.append(f"Inspired by: {', '.join(profile['inspiration'][:3])}")  # Limit to 3
    
    if profile.get("dream_collab"):
        context_parts.append(f"Dream Collaboration: {profile['dream_collab']}")
    
    # Conversation History
    if profile.get("conversation_count", 0) > 0:
        context_parts.append(f"Previous Conversations: {profile['conversation_count']}")
    
    # Create personalized context summary
    if context_parts:
        context_summary = "\n".join(context_parts)
        
        # Add personalization instructions based on profile
        personalization_notes = []
        
        if profile.get("age"):
            age = profile["age"]
            if age < 20:
                personalization_notes.append("Use youth-friendly language and focus on beginner-friendly advice")
            elif age > 30:
                personalization_notes.append("Use professional tone and focus on business/monetization aspects")
        
        if profile.get("experience_level") == "beginner":
            personalization_notes.append("Provide step-by-step guidance and explain technical terms")
        elif profile.get("experience_level") == "experienced":
            personalization_notes.append("Focus on advanced strategies and optimization techniques")
        
        if profile.get("subscriber_count"):
            if "k" in str(profile["subscriber_count"]).lower():
                personalization_notes.append("Focus on scaling and monetization strategies")
            else:
                personalization_notes.append("Focus on growth fundamentals and audience building")
        
        if profile.get("content_type"):
            content_type = profile["content_type"]
            personalization_notes.append(f"Tailor advice specifically for {content_type} content creators")
        
        if personalization_notes:
            context_summary += f"\n\nPersonalization Guidelines:\n" + "\n".join([f"- {note}" for note in personalization_notes])
        
        return context_summary
    
    return "No detailed user profile information available. Provide general YouTube growth advice."

def manage_conversation_length(messages: list, max_messages: int = 30, preserve_recent: int = 10) -> list:
    """Smart conversation management to prevent token overflow"""
    if len(messages) <= max_messages:
        return messages
    
    # Always preserve the most recent messages
    recent_messages = messages[-preserve_recent:]
    
    # From the older messages, try to preserve important ones
    older_messages = messages[:-preserve_recent]
    
    # Keep messages that contain user profile information or important context
    important_keywords = [
        'channel', 'subscriber', 'name', 'age', 'location', 'content', 'niche',
        'goal', 'monetize', 'equipment', 'budget', 'experience'
    ]
    
    preserved_older = []
    for msg in older_messages[-10:]:  # Look at last 10 of the older messages
        if any(keyword in msg['content'].lower() for keyword in important_keywords):
            preserved_older.append(msg)
    
    # Combine preserved older messages with recent ones
    managed_messages = preserved_older + recent_messages
    
    # Add a marker to indicate conversation was trimmed
    if len(managed_messages) < len(messages):
        trim_marker = {
            "role": "system", 
            "content": f"[Conversation trimmed: Showing {len(managed_messages)} of {len(messages)} total messages]"
        }
        managed_messages.insert(0, trim_marker)
    
    return managed_messages

def main():
    # Initialize app
    if not initialize_app():
        return
    
    # Title and description with emoji
    st.title("🎯 Hawa Singh - YouTube Growth Expert")
    
    # Debug mode toggle at the top
    col1, col2 = st.columns([3, 1])
    with col2:
        st.session_state.app_state["debug_mode"] = st.checkbox("🔍 Show Context & Debug Info", value=st.session_state.app_state.get("debug_mode", False))
    
    # Welcome message with animation
    st.markdown("""
    <div style='padding: 20px; border-radius: 10px; border: 2px solid #f63366; margin-bottom: 20px'>
    <h3>🙏 Namaste Creator!</h3>
    <p><strong>Hi, I'm Hawa Singh!</strong> 🎯</p>
    <p>I have <strong>500K+ subscribers</strong> on YouTube and I'm here to help you grow your channel!</p>
    <p>Main aapki channel growth mein help karunga with proven strategies that work.</p>
    
    <p><strong>Meri Expertise:</strong></p>
    <ul>
    <li>📈 Channel Growth Strategy (0 to 100K+ subscribers)</li>
    <li>🎥 Content Planning & Creation</li>
    <li>👥 Audience Engagement & Community Building</li>
    <li>💰 Monetization Tips (₹50K+ monthly income strategies)</li>
    <li>🚀 YouTube Shorts Mastery (Viral content creation)</li>
    <li>🎯 SEO & Thumbnail Optimization</li>
    </ul>
    
    <p><em>Proven track record: Helped 1000+ creators grow their channels!</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick topic buttons
    st.markdown("### 🎯 Quick Topics")
    col1, col2, col3 = st.columns(3)

    def process_question(question):
        """Process a question and generate response"""
        if not st.session_state.app_state["initialized"]:
            return
        
        # Use AI to detect if it's a greeting or introduction
        is_simple_greeting = is_greeting_or_introduction(question)
        
        # Debug info for greeting detection
        if st.session_state.app_state["debug_mode"]:
            st.write(f"🔍 Debug: is_simple_greeting = {is_simple_greeting}")
            if is_simple_greeting:
                response_type = get_greeting_response_type(question)
                st.write(f"🔍 Debug: response_type = {response_type}")
            
            # Add step-by-step detection debug
            is_step_question = is_step_by_step_question(question)
            st.write(f"🔍 Debug: is_step_by_step_question = {is_step_question}")
        
        if is_simple_greeting:
            # For simple greetings, use completely clean response without any personalization
            simple_prompt = f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user just said: "{question}"

Respond with a warm, natural greeting in Hinglish. Be friendly and inviting.

Example style:
"Namaste dost! Kaise ho? Main Hawa Singh - YouTube expert. Kya help chahiye aaj?"

Keep it natural, warm, and under 25 words."""
            
            response = st.session_state.app_state["chat"].send_message(simple_prompt)
        else:
            # For complex questions, get context and show debug info
            context = st.session_state.app_state["retriever"].retrieve_context(question)
            
            # Show debug info about context retrieval
            if st.session_state.app_state["debug_mode"]:
                st.write(f"🔍 Debug: Context retrieval triggered for: '{question}'")
                st.write(f"📊 Debug: Retrieved {len(context['context']['chunks'])} chunks")
            
            # Show debug info about chunks BEFORE generating response
            if st.session_state.app_state["debug_mode"]:
                with st.expander("🔍 Retrieved Context Chunks", expanded=True):
                    for i, chunk in enumerate(context['context']['chunks']):
                        # Handle different chunk structures with better error handling
                        try:
                            score = chunk.get('score', chunk.get('similarity', 'N/A'))
                            content = chunk.get('content', chunk.get('text', str(chunk)))
                            
                            st.write(f"**Chunk {i+1}** (Score: {score})")
                            st.code(content)
                            st.markdown("---")
                        except Exception as chunk_error:
                            st.write(f"**Chunk {i+1}** (Error displaying chunk)")
                            st.code(f"Chunk data: {str(chunk)}")
                            st.markdown("---")
            
            system_prompt = get_system_prompt(context, question)
            response = st.session_state.app_state["chat"].send_message(system_prompt)
        
        # Clean and format the response
        formatted_response = clean_response_formatting(response.text)
        
        # Update messages in session state
        st.session_state.app_state["messages"].extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": formatted_response}
        ])

    with col1:
        if st.button("📈 Growth Tips"):
            st.session_state.app_state["current_question"] = "What are your top 3 tips for growing a YouTube channel in India?"
            process_question(st.session_state.app_state["current_question"])

    with col2:
        if st.button("💰 Monetization"):
            st.session_state.app_state["current_question"] = "How can I monetize my YouTube channel effectively in India?"
            process_question(st.session_state.app_state["current_question"])

    with col3:
        if st.button("🎥 Content Ideas"):
            st.session_state.app_state["current_question"] = "What type of content is trending on YouTube India right now?"
            process_question(st.session_state.app_state["current_question"])
    
    # Sidebar enhancements
    with st.sidebar:
        st.header("📊 Knowledge Base Stats")
        stats = st.session_state.app_state["retriever"].vector_store.get_collection_stats()
        st.metric("🎯 Hawa Singh", f"{stats.get('hawa_singh', 0)} chunks")
        
        # User Profile Section
        st.markdown("### 👤 Your Profile")
        profile = st.session_state.app_state["user_profile"]
        
        # Basic Info Section
        if any([profile.get("name"), profile.get("age"), profile.get("location")]):
            st.markdown("**🏠 Basic Info**")
            if profile.get("name"):
                st.write(f"👋 **Name:** {profile['name']}")
            if profile.get("age"):
                st.write(f"🎂 **Age:** {profile['age']} years")
            if profile.get("location"):
                st.write(f"📍 **Location:** {profile['location']}")
            if profile.get("profession"):
                st.write(f"💼 **Profession:** {profile['profession']}")
            st.markdown("---")
        
        # Channel Info Section
        if any([profile.get("channel_name"), profile.get("content_type"), profile.get("subscriber_count")]):
            st.markdown("**📺 Channel Info**")
            if profile.get("channel_name"):
                st.write(f"🎯 **Channel:** {profile['channel_name']}")
            if profile.get("content_type"):
                content_display = profile['content_type'].title()
                if profile.get("niche"):
                    content_display += f" ({profile['niche'].title()})"
                st.write(f"🎬 **Content:** {content_display}")
            if profile.get("subscriber_count"):
                st.write(f"👥 **Subscribers:** {profile['subscriber_count']}")
            if profile.get("upload_frequency"):
                st.write(f"📅 **Upload:** {profile['upload_frequency'].title()}")
            if profile.get("experience_level"):
                st.write(f"⭐ **Level:** {profile['experience_level'].title()}")
            st.markdown("---")
        
        # Goals & Interests Section
        if profile.get("goals") or profile.get("interests"):
            st.markdown("**🎯 Goals & Interests**")
            if profile.get("goals"):
                goals_display = ", ".join([goal.title() for goal in profile['goals']])
                st.write(f"🚀 **Goals:** {goals_display}")
            if profile.get("interests"):
                interests_display = ", ".join([interest.title() for interest in profile['interests'][:3]])  # Show first 3
                if len(profile['interests']) > 3:
                    interests_display += f" +{len(profile['interests'])-3} more"
                st.write(f"❤️ **Interests:** {interests_display}")
            if profile.get("target_audience"):
                st.write(f"👥 **Audience:** {profile['target_audience']}")
            st.markdown("---")
        
        # Technical Setup Section
        if profile.get("equipment") or profile.get("editing_software") or profile.get("budget"):
            st.markdown("**🛠️ Technical Setup**")
            if profile.get("equipment"):
                equipment_display = ", ".join([eq.title() for eq in profile['equipment'][:3]])
                if len(profile['equipment']) > 3:
                    equipment_display += f" +{len(profile['equipment'])-3} more"
                st.write(f"📷 **Equipment:** {equipment_display}")
            if profile.get("editing_software"):
                st.write(f"✂️ **Editing:** {profile['editing_software'].title()}")
            if profile.get("budget"):
                st.write(f"💰 **Budget:** ₹{profile['budget']}")
            st.markdown("---")
        
        # Challenges & Inspiration Section
        if profile.get("main_challenges") or profile.get("inspiration"):
            st.markdown("**💪 Growth Journey**")
            if profile.get("main_challenges"):
                challenges_count = len(profile['main_challenges'])
                st.write(f"⚠️ **Challenges:** {challenges_count} identified")
            if profile.get("inspiration"):
                inspiration_display = ", ".join([insp.title() for insp in profile['inspiration'][:2]])
                if len(profile['inspiration']) > 2:
                    inspiration_display += f" +{len(profile['inspiration'])-2} more"
                st.write(f"✨ **Inspired by:** {inspiration_display}")
            if profile.get("dream_collab"):
                st.write(f"🤝 **Dream Collab:** {profile['dream_collab']}")
            st.markdown("---")
        
        # Conversation Stats
        if profile.get("conversation_count", 0) > 0:
            st.markdown("**📊 Stats**")
            st.write(f"💬 **Conversations:** {profile['conversation_count']}")
            if profile.get("last_updated"):
                from datetime import datetime
                try:
                    last_update = datetime.fromisoformat(profile['last_updated'])
                    st.write(f"🕒 **Last Updated:** {last_update.strftime('%b %d, %Y')}")
                except:
                    pass
            st.markdown("---")
        
        # Show message if profile is empty
        if not any([
            profile.get("channel_name"), profile.get("name"), profile.get("content_type"),
            profile.get("age"), profile.get("location"), profile.get("goals"),
            profile.get("interests"), profile.get("equipment")
        ]):
            st.write("💬 *Tell me about yourself, your channel, age, location, interests, and goals to get highly personalized advice!*")
            st.markdown("**Try saying:**")
            st.markdown("- 'I'm 25 years old from Mumbai'")
            st.markdown("- 'My channel is about travel'")
            st.markdown("- 'I have 500 subscribers'")
            st.markdown("- 'I love photography and editing'")
        
        # Enhanced profile reset with confirmation
        if st.button("🔄 Reset Profile"):
            if st.session_state.get("confirm_profile_reset", False):
                st.session_state.app_state["user_profile"] = {
                    # Basic Info
                    "channel_name": None,
                    "name": None,
                    "age": None,
                    "location": None,
                    "profession": None,
                    
                    # Channel Details
                    "content_type": None,
                    "niche": None,
                    "subscriber_count": None,
                    "upload_frequency": None,
                    "channel_age": None,
                    
                    # Personal Preferences
                    "language_preference": "hinglish",
                    "experience_level": None,
                    "goals": [],
                    "interests": [],
                    "target_audience": None,
                    
                    # Technical Setup
                    "equipment": [],
                    "editing_software": None,
                    "budget": None,
                    
                    # Challenges & Aspirations
                    "main_challenges": [],
                    "inspiration": [],
                    "dream_collab": None,
                    
                    # Metadata
                    "last_updated": None,
                    "conversation_count": 0
                }
                st.session_state.confirm_profile_reset = False
                st.success("✅ Profile reset successfully!")
                st.rerun()
            else:
                st.session_state.confirm_profile_reset = True
                st.warning("⚠️ Click again to confirm profile reset")
        
        # Chat History Management Section
        st.markdown("### 💬 Chat Management")
        
        # Show current conversation stats
        msg_count = len(st.session_state.app_state["messages"])
        if msg_count > 0:
            total_chars = sum(len(msg["content"]) for msg in st.session_state.app_state["messages"])
            estimated_tokens = total_chars // 4
            st.metric("Messages", msg_count)
            st.metric("Est. Tokens", f"~{estimated_tokens}")
            
            # Context preservation settings
            st.markdown("**Context Settings:**")
            
            # Let users choose how much context to preserve
            context_options = {
                "Minimal (4 messages)": 4,
                "Balanced (6 messages)": 6, 
                "Extended (8 messages)": 8,
                "Maximum (12 messages)": 12
            }
            
            selected_context = st.selectbox(
                "Chat Context Level",
                options=list(context_options.keys()),
                index=1,  # Default to "Balanced"
                help="How many recent messages to include as context for AI responses"
            )
            
            # Store the selection in session state
            st.session_state.app_state["context_limit"] = context_options[selected_context]
            
            # Auto-trim option
            auto_trim = st.checkbox(
                "Auto-trim long conversations", 
                value=True,
                help="Automatically manage conversation length to prevent token overflow"
            )
            st.session_state.app_state["auto_trim"] = auto_trim
            
            # Manual trim button for long conversations
            if msg_count > 20:
                if st.button("✂️ Trim Old Messages"):
                    if st.session_state.get("confirm_trim", False):
                        # Apply smart trimming
                        st.session_state.app_state["messages"] = manage_conversation_length(
                            st.session_state.app_state["messages"],
                            max_messages=20,
                            preserve_recent=10
                        )
                        st.session_state.confirm_trim = False
                        st.success("✅ Conversation trimmed successfully!")
                        st.rerun()
                    else:
                        st.session_state.confirm_trim = True
                        st.warning("⚠️ Click again to confirm trimming")
        else:
            st.info("No messages yet. Start a conversation!")
        
        st.markdown("---")
        
        # Experience rating
        st.markdown("### 🌟 Rate Your Experience")
        st.slider("How helpful is Hawa Singh?", 1, 5, key="experience_rating")
        
        # Debug mode toggle
        st.session_state.app_state["debug_mode"] = st.checkbox("🔧 Debug Mode", value=st.session_state.app_state.get("debug_mode", False))
        
        # Clear chat button with confirmation
        if st.button("🗑️ Clear Chat History"):
            if st.session_state.get("confirm_clear", False):
                st.session_state.app_state["messages"] = []
                model = genai.GenerativeModel(config.MODEL_NAME)
                st.session_state.app_state["chat"] = model.start_chat(history=[])
                st.session_state.confirm_clear = False
                st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("Click again to confirm clearing chat history")
        
        if st.session_state.app_state["debug_mode"]:
            st.text("Debug Info:")
            st.text(f"Initialized: {st.session_state.app_state['initialized']}")
            st.text(f"Messages: {len(st.session_state.app_state['messages'])}")
            st.text(f"Retriever: {st.session_state.app_state['retriever'] is not None}")
            st.text(f"Chat: {st.session_state.app_state['chat'] is not None}")
            
            # Add profile debug information
            profile = st.session_state.app_state["user_profile"]
            st.text("User Profile Debug:")
            st.text(f"  Name: {profile.get('name', 'None')}")
            st.text(f"  Channel: {profile.get('channel_name', 'None')}")
            st.text(f"  Age: {profile.get('age', 'None')}")
            st.text(f"  Location: {profile.get('location', 'None')}")
            st.text(f"  Content Type: {profile.get('content_type', 'None')}")
            st.text(f"  Subscribers: {profile.get('subscriber_count', 'None')}")
            
            # Add token usage information
            if st.session_state.app_state["chat"]:
                try:
                    # Estimate token usage (rough calculation)
                    total_chars = sum(len(msg["content"]) for msg in st.session_state.app_state["messages"])
                    estimated_tokens = total_chars // 4  # Rough estimate: 4 chars per token
                    st.text(f"Estimated Tokens: ~{estimated_tokens}")
                    st.text(f"Chat History Length: {len(st.session_state.app_state['chat'].history)}")
                    
                    # Show configurable chat history in debug
                    if len(st.session_state.app_state["messages"]) > 0:
                        # Smart preview limit based on conversation length
                        if len(st.session_state.app_state["messages"]) <= 4:
                            preview_limit = len(st.session_state.app_state["messages"])
                        elif len(st.session_state.app_state["messages"]) <= 10:
                            preview_limit = 6
                        else:
                            preview_limit = 8
                        
                        with st.expander(f"🔍 Recent Chat Context (Last {preview_limit} Messages)", expanded=False):
                            recent_messages = st.session_state.app_state["messages"][-preview_limit:]
                            for i, msg in enumerate(recent_messages):
                                role_emoji = "🎯" if msg['role'] == "assistant" else "👤"
                                content_preview = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']
                                st.write(f"{role_emoji} **{msg['role'].title()}:** {content_preview}")
                            
                            # Show token usage for this preview
                            preview_chars = sum(len(msg["content"]) for msg in recent_messages)
                            preview_tokens = preview_chars // 4
                            st.caption(f"Preview tokens: ~{preview_tokens} | Total conversation: ~{estimated_tokens}")
                        
                        # Add conversation management options
                        if len(st.session_state.app_state["messages"]) > 20:
                            st.warning(f"⚠️ Long conversation ({len(st.session_state.app_state['messages'])} messages). Consider clearing history to improve performance.")
                            
                except Exception as e:
                    st.text(f"Token info error: {str(e)}")
    
    # Display chat history with enhanced styling
    for message in st.session_state.app_state["messages"]:
        if message["role"] == "assistant":
            avatar = "🎯"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input with placeholder
    if prompt := st.chat_input("💭 Kya puchna chahte ho? (What would you like to ask?)"):
        # Apply auto-trimming if enabled and conversation is getting long
        if (st.session_state.app_state.get("auto_trim", True) and 
            len(st.session_state.app_state["messages"]) > 25):
            st.session_state.app_state["messages"] = manage_conversation_length(
                st.session_state.app_state["messages"],
                max_messages=20,
                preserve_recent=8
            )
        
        # Extract and update user information
        st.session_state.app_state["user_profile"] = extract_user_info(
            prompt, 
            st.session_state.app_state["user_profile"]
        )
        
        # Add user message to chat history
        st.session_state.app_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Get response from selected creator
        with st.chat_message("assistant", avatar="🎯"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Check for inappropriate content first
                if is_inappropriate_content(prompt):
                    if st.session_state.app_state["debug_mode"]:
                        st.write(f"🚫 Debug: Inappropriate content detected: '{prompt}'")
                    
                    # Use the system prompt for inappropriate content
                    system_prompt = get_system_prompt({}, prompt)
                    
                    with st.spinner("Hawa Singh is responding..."):
                        response = st.session_state.app_state["chat"].send_message(system_prompt)
                        full_response = clean_response_formatting(response.text)
                        message_placeholder.markdown(full_response)
                
                else:
                    # Use AI to detect if it's a greeting or introduction
                    is_simple_greeting = is_greeting_or_introduction(prompt)
                    
                    # Debug info for greeting detection
                    if st.session_state.app_state["debug_mode"]:
                        st.write(f"🔍 Debug: is_simple_greeting = {is_simple_greeting}")
                        if is_simple_greeting:
                            response_type = get_greeting_response_type(prompt)
                            st.write(f"🔍 Debug: response_type = {response_type}")
                        
                        # Add step-by-step detection debug
                        is_step_question = is_step_by_step_question(prompt)
                        st.write(f"🔍 Debug: is_step_by_step_question = {is_step_question}")
                    
                    if is_simple_greeting:
                        # Get the specific type of greeting response needed
                        response_type = get_greeting_response_type(prompt)
                        
                        if response_type == "NAME_QUESTION":
                            greeting_prompt = f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user asked: "{prompt}"

Respond with a warm, natural introduction in Hinglish. Include your credentials.

Example style:
"Namaste! Main Hawa Singh hoon - YouTube growth expert with 500K+ subscribers. Aapki channel ki growth mein help karta hoon. Kya puchna chahte ho?"

Keep it natural, warm, and under 30 words."""
                        
                        elif response_type == "INTRODUCTION":
                            greeting_prompt = f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user introduced themselves: "{prompt}"

Respond warmly, acknowledge their introduction, and introduce yourself naturally in Hinglish.

Example style:
"Nice to meet you! Main Hawa Singh hoon, YouTube expert with 500K+ subscribers. Aapki journey mein help karunga. Kya chahiye help?"

Keep it natural, warm, and under 30 words."""
                        
                        else:  # SIMPLE_GREETING
                            greeting_prompt = f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user greeted you: "{prompt}"

Respond with a warm, natural greeting back in Hinglish. Be friendly and inviting.

Example style:
"Namaste dost! Kaise ho? Main Hawa Singh - YouTube expert with 500K+ subscribers. Kya help chahiye aaj?"

Keep it natural, warm, and under 30 words."""
                        
                        # Show typing indicator for greetings too
                        with st.spinner("Hawa Singh is typing..."):
                            response = st.session_state.app_state["chat"].send_message(greeting_prompt)
                            full_response = clean_response_formatting(response.text)
                            message_placeholder.markdown(full_response)
                    else:
                        # Get context from vector store for complex questions
                        context = st.session_state.app_state["retriever"].retrieve_context(prompt)
                        
                        # Show debug info about context retrieval
                        if st.session_state.app_state["debug_mode"]:
                            st.write(f"🔍 Debug: Context retrieval triggered for: '{prompt}'")
                            st.write(f"📊 Debug: Retrieved {len(context['context']['chunks'])} chunks")
                        
                        # Show debug info about chunks BEFORE generating response
                        if st.session_state.app_state["debug_mode"]:
                            with st.expander("🔍 Retrieved Context Chunks", expanded=True):
                                for i, chunk in enumerate(context['context']['chunks']):
                                    # Handle different chunk structures with better error handling
                                    try:
                                        score = chunk.get('score', chunk.get('similarity', 'N/A'))
                                        content = chunk.get('content', chunk.get('text', str(chunk)))
                                        
                                        st.write(f"**Chunk {i+1}** (Score: {score})")
                                        st.code(content)
                                        st.markdown("---")
                                    except Exception as chunk_error:
                                        st.write(f"**Chunk {i+1}** (Error displaying chunk)")
                                        st.code(f"Chunk data: {str(chunk)}")
                                        st.markdown("---")
                        
                        # Prepare system prompt with context
                        system_prompt = get_system_prompt(context, prompt)
                        
                        # Show typing indicator
                        with st.spinner("Hawa Singh is typing..."):
                            # Get response using preserved chat history
                            response = st.session_state.app_state["chat"].send_message(system_prompt)
                            
                            # Clean and format the response
                            full_response = clean_response_formatting(response.text)
                            
                            # Stream response with proper formatting
                            words = full_response.split()
                            displayed_response = ""
                            for word in words:
                                displayed_response += word + " "
                                time.sleep(0.03)
                                message_placeholder.markdown(displayed_response + "▌")
                                
                            message_placeholder.markdown(full_response)
            
            except Exception as e:
                error_message = str(e)
                if "429" in error_message:  # Rate limit error
                    error_message = """🚫 I apologize, but I'm currently experiencing high traffic and have hit the API rate limit. 
                    
                    Please try:
                    1. Waiting a minute before asking another question
                    2. Making your question more specific and focused
                    3. Coming back in a few minutes if the issue persists
                    
                    This is a temporary limitation and I'll be happy to help you once the rate limit resets!"""
                elif "embedding" in error_message.lower():
                    error_message = """🤔 I'm having trouble understanding your query. Could you try:
                    
                    1. Rephrasing your question
                    2. Being more specific about what you want to know
                    3. Using complete sentences
                    
                    This will help me provide a better response!"""
                else:
                    error_message = f"""⚠️ I encountered an issue while processing your request. 
                    
                    The specific error was: {error_message}
                    
                    Please try again in a moment."""
                
                if st.session_state.app_state["debug_mode"]:
                    st.error(f"Full error: {str(e)}")
                
                message_placeholder.markdown(error_message)
                full_response = error_message
                print(f"Error: {str(e)}")
            
            # Add assistant response to chat history
            st.session_state.app_state["messages"].append({"role": "assistant", "content": full_response})
            
            # Show engagement prompt
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.button("👍 Helpful")
            with col2:
                st.button("👎 Not Helpful")

if __name__ == "__main__":
    main()