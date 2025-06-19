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

# Page config should be the first Streamlit command
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

def is_greeting_or_introduction(query: str) -> bool:
    """Use AI to determine if the query is just a greeting or introduction"""
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

def get_system_prompt(context: dict, query: str) -> str:
    """Get the system prompt with context"""
    
    # Use AI to detect greetings instead of hard-coded patterns
    if is_greeting_or_introduction(query):
        # Get the specific type of greeting response needed
        response_type = get_greeting_response_type(query)
        
        if response_type == "NAME_QUESTION":
            return f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user asked: "{query}"

Respond with a warm, natural introduction in Hinglish. Keep it conversational and friendly.

Example style:
"Namaste! Main Hawa Singh hoon - YouTube growth expert. Aapki channel ki growth mein help karta hoon. Kya puchna chahte ho?"

Keep it natural, warm, and under 25 words."""
        
        elif response_type == "INTRODUCTION":
            return f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user introduced themselves: "{query}"

Respond warmly, acknowledge their introduction, and introduce yourself naturally in Hinglish.

Example style:
"Nice to meet you! Main Hawa Singh hoon, YouTube expert. Aapki journey mein help karunga. Kya chahiye help?"

Keep it natural, warm, and under 25 words."""
        
        else:  # SIMPLE_GREETING
            return f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user greeted you: "{query}"

Respond with a warm, natural greeting back in Hinglish. Be friendly and inviting.

Example style:
"Namaste dost! Kaise ho? Main Hawa Singh - YouTube expert. Kya help chahiye aaj?"

Keep it natural, warm, and under 25 words."""
    
    # Original detailed system prompt for complex questions
    return f"""You are Hawa Singh, a YouTube Growth Expert who speaks in natural Hinglish (Hindi + English mix).

CRITICAL FORMATTING RULES:
- Use proper markdown formatting with line breaks
- Add blank lines between sections
- Use **bold** for section headers
- Use bullet points with emojis
- Keep sections visually separated

RESPONSE STRUCTURE (FOLLOW EXACTLY):

Namaste [name if available]! [Brief acknowledgment]

🎯 **Quick Analysis**

[1-2 lines about their situation]

📈 **Action Steps**

🔸 [Step 1 - keep concise]

🔸 [Step 2 - actionable tip]

🔸 [Step 3 - with example]

💡 **Pro Tip**

[One key insight]

[Natural follow-up questions in 1-2 lines]

FORMATTING EXAMPLE:
```
Namaste dost! Great question about thumbnails.

🎯 **Quick Analysis**

Thumbnails are crucial for click-through rates on YouTube.

📈 **Action Steps**

🔸 Use bright colors and clear text

🔸 Add your face for personal connection

🔸 Test different styles and see what works

💡 **Pro Tip**

Successful creators like Technical Guruji use consistent thumbnail styles.

Kya lagta hai? Try kar sakte ho ye tips?
```

IMPORTANT:
- Always add blank lines between sections
- Use markdown formatting properly
- Keep each section short (2-3 lines max)
- End with natural questions in Hinglish

Context: {context['context']['chunks'][0].get('content', context['context']['chunks'][0].get('text', 'No specific context found.')) if context['context']['chunks'] else 'No specific context found.'}

User Profile: {format_user_context(st.session_state.app_state["user_profile"])}

Recent Chat: {format_chat_history(st.session_state.app_state["messages"][-2:] if len(st.session_state.app_state["messages"]) > 0 else [])}

User Query: {query}

Respond in natural Hinglish with proper markdown formatting. Follow the structure exactly!"""

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

def format_chat_history(messages: list) -> str:
    """Format chat history for context"""
    if not messages:
        return "No previous context."
    
    formatted = []
    for msg in messages:
        role = "Hawa Singh" if msg["role"] == "assistant" else "User"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)

def extract_user_info(message: str, current_profile: dict) -> dict:
    """Extract user information from messages and update profile"""
    updated_profile = current_profile.copy()
    message_lower = message.lower()
    
    # Extract channel name patterns
    channel_patterns = [
        r"my channel name is (\w+)",
        r"channel name is (\w+)",
        r"my channel (\w+)",
        r"channel called (\w+)",
        r"channel is (\w+)"
    ]
    
    for pattern in channel_patterns:
        match = re.search(pattern, message_lower)
        if match:
            updated_profile["channel_name"] = match.group(1)
            break
    
    # Extract name patterns
    name_patterns = [
        r"my name is (\w+)",
        r"i'm (\w+)",
        r"call me (\w+)",
        r"i am (\w+)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, message_lower)
        if match:
            name = match.group(1)
            if name not in ["a", "an", "the", "from", "to", "going", "making", "doing"]:  # Filter common words
                updated_profile["name"] = name
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
    I'm Hawa Singh, your YouTube growth expert. Main aapki channel growth mein help karunga!
    
    **Meri Expertise:**
    - 📈 Channel Growth Strategy
    - 🎥 Content Planning & Creation
    - 👥 Audience Engagement
    - 💰 Monetization Tips
    - 🚀 YouTube Shorts Mastery
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
                # Use AI to detect if it's a greeting or introduction
                is_simple_greeting = is_greeting_or_introduction(prompt)
                
                # Debug info for greeting detection
                if st.session_state.app_state["debug_mode"]:
                    st.write(f"🔍 Debug: is_simple_greeting = {is_simple_greeting}")
                    if is_simple_greeting:
                        response_type = get_greeting_response_type(prompt)
                        st.write(f"🔍 Debug: response_type = {response_type}")
                
                if is_simple_greeting:
                    # Get the specific type of greeting response needed
                    response_type = get_greeting_response_type(prompt)
                    
                    if response_type == "NAME_QUESTION":
                        greeting_prompt = f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user asked: "{prompt}"

Respond with a warm, natural introduction in Hinglish. Keep it conversational and friendly.

Example style:
"Namaste! Main Hawa Singh hoon - YouTube growth expert. Aapki channel ki growth mein help karta hoon. Kya puchna chahte ho?"

Keep it natural, warm, and under 25 words."""
                    
                    elif response_type == "INTRODUCTION":
                        greeting_prompt = f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user introduced themselves: "{prompt}"

Respond warmly, acknowledge their introduction, and introduce yourself naturally in Hinglish.

Example style:
"Nice to meet you! Main Hawa Singh hoon, YouTube expert. Aapki journey mein help karunga. Kya chahiye help?"

Keep it natural, warm, and under 25 words."""
                    
                    else:  # SIMPLE_GREETING
                        greeting_prompt = f"""You are Hawa Singh, a friendly YouTube Growth Expert who speaks in natural Hinglish.

The user greeted you: "{prompt}"

Respond with a warm, natural greeting back in Hinglish. Be friendly and inviting.

Example style:
"Namaste dost! Kaise ho? Main Hawa Singh - YouTube expert. Kya help chahiye aaj?"

Keep it natural, warm, and under 25 words."""
                    
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