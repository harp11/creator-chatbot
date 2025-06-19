import os
import json
import google.generativeai as genai
import config

# Configure Gemini
genai.configure(api_key=config.GOOGLE_API_KEY)
model = genai.GenerativeModel(config.MODEL_NAME)

def analyze_transcript_batches():
    """Analyze transcripts in manageable batches for comprehensive character analysis"""
    
    print("🔍 Analyzing transcripts for proper character reference...")
    
    hindi_folder = "hindi_transcripts"
    english_folder = "english_transcripts"
    
    # Get all files
    hindi_files = [f for f in os.listdir(hindi_folder) if f.endswith('.txt')] if os.path.exists(hindi_folder) else []
    english_files = [f for f in os.listdir(english_folder) if f.endswith('.txt')] if os.path.exists(english_folder) else []
    
    print(f"📄 Found {len(hindi_files)} Hindi files and {len(english_files)} English files")
    
    character_insights = []
    batch_count = min(10, max(len(hindi_files), len(english_files)))  # Process up to 10 files
    
    for i in range(batch_count):
        print(f"\n📊 Analyzing batch {i+1}/{batch_count}")
        
        # Get content for this batch
        hindi_content = ""
        english_content = ""
        
        if i < len(hindi_files):
            hindi_path = os.path.join(hindi_folder, hindi_files[i])
            try:
                with open(hindi_path, 'r', encoding='utf-8') as f:
                    hindi_content = f.read()[:2500]  # Limit to 2500 chars
                print(f"   📄 Hindi: {hindi_files[i]} ({len(hindi_content)} chars)")
            except Exception as e:
                print(f"   ❌ Error reading Hindi file: {e}")
        
        if i < len(english_files):
            english_path = os.path.join(english_folder, english_files[i])
            try:
                with open(english_path, 'r', encoding='utf-8') as f:
                    english_content = f.read()[:2500]  # Limit to 2500 chars
                print(f"   📄 English: {english_files[i]} ({len(english_content)} chars)")
            except Exception as e:
                print(f"   ❌ Error reading English file: {e}")
        
        # Analyze this batch
        if hindi_content or english_content:
            batch_analysis = analyze_single_batch(hindi_content, english_content, i+1)
            if batch_analysis:
                character_insights.append(batch_analysis)
                print(f"   ✅ Character insights extracted")
            else:
                print(f"   ❌ Failed to extract insights")
    
    return character_insights

def analyze_single_batch(hindi_text, english_text, batch_num):
    """Analyze a single batch for detailed character insights"""
    
    prompt = f"""
    Analyze this content from Hawa Singh (Video/Content {batch_num}) for detailed character insights.
    
    HINDI CONTENT:
    {hindi_text}
    
    ENGLISH CONTENT:
    {english_text}
    
    Extract detailed character insights in JSON format:
    
    {{
        "personality_traits": [
            "Specific personality traits you observe with examples"
        ],
        "speaking_patterns": [
            "How he speaks, structures thoughts, rhetorical techniques"
        ],
        "hindi_expressions": [
            "Key Hindi phrases, idioms, or cultural expressions he uses"
        ],
        "values_demonstrated": [
            "Core values, beliefs, or principles shown in this content"
        ],
        "expertise_shown": [
            "Topics he demonstrates knowledge about"
        ],
        "communication_style": [
            "How he connects with audience, storytelling approach"
        ],
        "emotional_patterns": [
            "Emotions he expresses, energy levels, motivational techniques"
        ],
        "cultural_context": [
            "Indian cultural references, traditional wisdom, regional elements"
        ],
        "unique_characteristics": [
            "What makes him distinctively different from other speakers"
        ],
        "audience_connection": [
            "How he relates to his audience, addressing techniques"
        ]
    }}
    
    Be specific and detailed. Look for:
    - Authentic personality traits that come through consistently
    - Cultural expressions that show his background
    - Unique speaking patterns and rhetorical devices
    - Values and beliefs he promotes
    - How he motivates and connects with people
    - Traditional wisdom mixed with modern perspectives
    
    Respond ONLY with valid JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"   ❌ Batch analysis error: {e}")
        return None

def create_comprehensive_character_profile(all_insights):
    """Create a comprehensive character reference from all batch insights"""
    
    print("🎭 Creating comprehensive character reference...")
    
    # Aggregate all insights
    all_traits = []
    all_patterns = []
    all_expressions = []
    all_values = []
    all_expertise = []
    all_communication = []
    all_emotions = []
    all_cultural = []
    all_unique = []
    all_audience = []
    
    for batch in all_insights:
        all_traits.extend(batch.get('personality_traits', []))
        all_patterns.extend(batch.get('speaking_patterns', []))
        all_expressions.extend(batch.get('hindi_expressions', []))
        all_values.extend(batch.get('values_demonstrated', []))
        all_expertise.extend(batch.get('expertise_shown', []))
        all_communication.extend(batch.get('communication_style', []))
        all_emotions.extend(batch.get('emotional_patterns', []))
        all_cultural.extend(batch.get('cultural_context', []))
        all_unique.extend(batch.get('unique_characteristics', []))
        all_audience.extend(batch.get('audience_connection', []))
    
    # Create comprehensive analysis prompt
    synthesis_prompt = f"""
    Based on detailed analysis of multiple content pieces from Hawa Singh, create a comprehensive character reference profile.
    
    AGGREGATED INSIGHTS:
    
    Personality Traits: {all_traits}
    Speaking Patterns: {all_patterns}
    Hindi Expressions: {all_expressions}
    Values Demonstrated: {all_values}
    Expertise Areas: {all_expertise}
    Communication Style: {all_communication}
    Emotional Patterns: {all_emotions}
    Cultural Context: {all_cultural}
    Unique Characteristics: {all_unique}
    Audience Connection: {all_audience}
    
    Create a comprehensive character reference in JSON format:
    
    {{
        "basic_info": {{
            "name": "Hawa Singh",
            "primary_specialty": "Main area of expertise",
            "secondary_specialties": ["Other areas he covers"],
            "target_audience": "Primary audience description"
        }},
        "core_personality": {{
            "dominant_traits": ["Top 5-6 most consistent personality traits"],
            "character_strengths": ["His key strengths as a person/speaker"],
            "motivational_approach": ["How he motivates and inspires others"],
            "leadership_style": ["How he leads and influences"]
        }},
        "communication_profile": {{
            "speaking_style": ["Key elements of how he communicates"],
            "rhetorical_techniques": ["Specific techniques he uses"],
            "storytelling_approach": ["How he tells stories and gives examples"],
            "question_patterns": ["Types of questions he asks"],
            "emphasis_methods": ["How he emphasizes important points"]
        }},
        "language_and_expressions": {{
            "signature_hindi_phrases": ["Most characteristic Hindi expressions"],
            "cultural_idioms": ["Traditional sayings or wisdom he uses"],
            "motivational_catchphrases": ["Key phrases that define his message"],
            "addressing_style": ["How he addresses his audience"]
        }},
        "values_and_beliefs": {{
            "core_values": ["Fundamental values he consistently promotes"],
            "life_philosophy": ["His overall philosophy and worldview"],
            "success_principles": ["What he believes leads to success"],
            "spiritual_elements": ["Any spiritual or philosophical aspects"]
        }},
        "expertise_and_knowledge": {{
            "primary_topics": ["Main subjects he's expert in"],
            "knowledge_sources": ["Where his wisdom comes from - experience, study, etc."],
            "practical_advice_style": ["How he gives actionable advice"],
            "problem_solving_approach": ["How he approaches challenges"]
        }},
        "emotional_and_energy_profile": {{
            "emotional_range": ["Emotions he typically expresses"],
            "energy_levels": ["His typical energy and enthusiasm"],
            "empathy_style": ["How he shows understanding and connection"],
            "inspirational_methods": ["Specific ways he inspires others"]
        }},
        "cultural_and_background": {{
            "cultural_influences": ["Indian/regional cultural elements"],
            "traditional_wisdom": ["Traditional concepts he references"],
            "modern_perspective": ["How he blends traditional and modern views"],
            "social_context": ["Understanding of his social/cultural background"]
        }},
        "unique_differentiators": {{
            "distinctive_qualities": ["What makes him unique among speakers"],
            "signature_approaches": ["His unique methods or techniques"],
            "memorable_characteristics": ["What people remember about him"],
            "brand_elements": ["What defines his personal brand"]
        }},
        "response_generation_guide": {{
            "sentence_structure": ["How he typically structures sentences"],
            "paragraph_flow": ["How he organizes thoughts"],
            "example_usage": ["How and when he uses examples"],
            "question_integration": ["How he integrates questions"],
            "closing_style": ["How he typically ends his messages"]
        }}
    }}
    
    Guidelines:
    - Focus on consistent patterns across all content
    - Prioritize authentic characteristics over generic traits
    - Include specific cultural and linguistic elements
    - Ensure the profile enables authentic response generation
    - Balance traditional wisdom with modern appeal
    - Capture his unique voice and perspective
    
    This will be used to generate authentic responses in his voice, so be comprehensive and specific.
    
    Respond ONLY with valid JSON.
    """
    
    try:
        response = model.generate_content(synthesis_prompt)
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"❌ Character synthesis error: {e}")
        return None

def save_character_reference(character_profile):
    """Save the comprehensive character reference"""
    
    print("💾 Saving comprehensive character reference...")
    
    # Create hawa_singh folder
    os.makedirs("data/hawa_singh", exist_ok=True)
    
    # Save complete character reference
    reference_file = "data/hawa_singh/character_reference.json"
    with open(reference_file, 'w', encoding='utf-8') as f:
        json.dump(character_profile, f, indent=2, ensure_ascii=False)
    
    # Save readable character guide
    guide_file = "data/hawa_singh/character_guide.txt"
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write("HAWA SINGH - COMPREHENSIVE CHARACTER REFERENCE\n")
        f.write("=" * 60 + "\n\n")
        
        # Basic Info
        f.write("BASIC INFORMATION:\n")
        f.write(f"Name: {character_profile['basic_info']['name']}\n")
        f.write(f"Primary Specialty: {character_profile['basic_info']['primary_specialty']}\n")
        f.write(f"Target Audience: {character_profile['basic_info']['target_audience']}\n\n")
        
        # Core Personality
        f.write("CORE PERSONALITY:\n")
        for trait in character_profile['core_personality']['dominant_traits']:
            f.write(f"• {trait}\n")
        f.write("\n")
        
        # Communication Profile
        f.write("COMMUNICATION STYLE:\n")
        for style in character_profile['communication_profile']['speaking_style']:
            f.write(f"• {style}\n")
        f.write("\n")
        
        # Signature Phrases
        f.write("SIGNATURE HINDI PHRASES:\n")
        for phrase in character_profile['language_and_expressions']['signature_hindi_phrases']:
            f.write(f"• {phrase}\n")
        f.write("\n")
        
        # Core Values
        f.write("CORE VALUES:\n")
        for value in character_profile['values_and_beliefs']['core_values']:
            f.write(f"• {value}\n")
        f.write("\n")
        
        # Unique Qualities
        f.write("UNIQUE DIFFERENTIATORS:\n")
        for quality in character_profile['unique_differentiators']['distinctive_qualities']:
            f.write(f"• {quality}\n")
        f.write("\n")
        
        # Response Guide
        f.write("RESPONSE GENERATION GUIDE:\n")
        for guide in character_profile['response_generation_guide']['sentence_structure']:
            f.write(f"• {guide}\n")
    
    # Create config entry
    config_file = "data/hawa_singh/config_entry.txt"
    with open(config_file, 'w', encoding='utf-8') as f:
        personality_summary = ", ".join(character_profile['core_personality']['dominant_traits'][:3])
        
        f.write("Add this to your config.py CREATORS section:\n\n")
        f.write(f'"hawa_singh": {{\n')
        f.write(f'    "name": "{character_profile["basic_info"]["name"]}",\n')
        f.write(f'    "specialty": "{character_profile["basic_info"]["primary_specialty"]}",\n')
        f.write(f'    "personality": "{personality_summary}"\n')
        f.write(f'}},\n')
    
    print(f"✅ Character reference saved to: {reference_file}")
    print(f"✅ Character guide saved to: {guide_file}")
    print(f"✅ Config entry saved to: {config_file}")

def display_character_summary(character_profile):
    """Display a summary of the character reference"""
    
    print("\n🎭 HAWA SINGH - CHARACTER REFERENCE SUMMARY")
    print("=" * 60)
    
    print(f"👤 Name: {character_profile['basic_info']['name']}")
    print(f"🎯 Specialty: {character_profile['basic_info']['primary_specialty']}")
    print(f"👥 Audience: {character_profile['basic_info']['target_audience']}")
    
    print(f"\n🎭 Core Personality:")
    for trait in character_profile['core_personality']['dominant_traits']:
        print(f"   • {trait}")
    
    print(f"\n🗣️ Speaking Style:")
    for style in character_profile['communication_profile']['speaking_style'][:4]:
        print(f"   • {style}")
    
    print(f"\n💫 Signature Phrases:")
    for phrase in character_profile['language_and_expressions']['signature_hindi_phrases'][:4]:
        print(f"   • {phrase}")
    
    print(f"\n💎 Core Values:")
    for value in character_profile['values_and_beliefs']['core_values'][:4]:
        print(f"   • {value}")
    
    print(f"\n✨ Unique Qualities:")
    for quality in character_profile['unique_differentiators']['distinctive_qualities'][:3]:
        print(f"   • {quality}")

def main():
    print("🎭 Proper Character Reference Extractor for Hawa Singh")
    print("=" * 60)
    
    # Step 1: Analyze transcripts in batches
    character_insights = analyze_transcript_batches()
    
    if not character_insights:
        print("❌ No character insights extracted!")
        return
    
    print(f"✅ Extracted insights from {len(character_insights)} batches")
    
    # Step 2: Create comprehensive character profile
    character_profile = create_comprehensive_character_profile(character_insights)
    
    if not character_profile:
        print("❌ Failed to create character profile!")
        return
    
    # Step 3: Save character reference
    save_character_reference(character_profile)
    
    # Step 4: Display summary
    display_character_summary(character_profile)
    
    print(f"\n🎉 Comprehensive character reference created!")
    print(f"\n📁 Files created:")
    print(f"   • data/hawa_singh/character_reference.json (Complete reference)")
    print(f"   • data/hawa_singh/character_guide.txt (Human-readable guide)")
    print(f"   • data/hawa_singh/config_entry.txt (For config.py)")
    
    print(f"\n✨ This character reference includes:")
    print(f"   • Detailed personality analysis")
    print(f"   • Comprehensive communication style")
    print(f"   • Authentic Hindi expressions")
    print(f"   • Cultural context and background")
    print(f"   • Response generation guidelines")
    
    print(f"\n🚀 Next steps:")
    print(f"1. Review the character guide")
    print(f"2. Add config entry to config.py")
    print(f"3. Create content files")
    print(f"4. Build vector database")

if __name__ == "__main__":
    main()