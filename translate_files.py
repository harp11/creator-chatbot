import json
import os
import google.generativeai as genai
import config

# Configure Gemini
genai.configure(api_key=config.GOOGLE_API_KEY)
model = genai.GenerativeModel(config.MODEL_NAME)

def translate_text(hindi_text):
    """Simple translation function"""
    
    prompt = f"""
   just translate as it is
    
    Hindi: {hindi_text}
    
    English:
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return f"[Could not translate: {hindi_text[:50]}...]"

def process_one_json_file(file_path):
    """Process one JSON file and extract only the transcriptions text"""
    
    print(f"📄 Processing: {os.path.basename(file_path)}")
    
    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract only the transcriptions part
        text_content = ""
        
        # Method 1: Look for 'transcriptions' key specifically
        if isinstance(data, dict) and 'transcriptions' in data:
            transcriptions = data['transcriptions']
            if isinstance(transcriptions, str):
                text_content = transcriptions
            elif isinstance(transcriptions, list):
                texts = []
                for item in transcriptions:
                    if isinstance(item, dict) and 'text' in item:
                        texts.append(item['text'])
                    elif isinstance(item, str):
                        texts.append(item)
                text_content = ' '.join(texts)
            print(f"   ✅ Found 'transcriptions' key")
        
        # Method 2: Look for 'transcription' (singular)
        elif isinstance(data, dict) and 'transcription' in data:
            transcription = data['transcription']
            if isinstance(transcription, str):
                text_content = transcription
            elif isinstance(transcription, list):
                text_content = ' '.join([str(item) for item in transcription])
            print(f"   ✅ Found 'transcription' key")
        
        # Method 3: Look for 'text' key as fallback
        elif isinstance(data, dict) and 'text' in data:
            text_content = data['text']
            print(f"   ✅ Found 'text' key")
        
        # Method 4: Look for segments with transcriptions
        elif isinstance(data, dict) and 'segments' in data:
            texts = []
            for segment in data['segments']:
                if isinstance(segment, dict):
                    if 'transcription' in segment:
                        texts.append(segment['transcription'])
                    elif 'text' in segment:
                        texts.append(segment['text'])
            text_content = ' '.join(texts)
            print(f"   ✅ Found segments with transcriptions")
        
        else:
            print(f"   ❌ Could not find 'transcriptions' key in JSON")
            print(f"   📋 Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dictionary'}")
            return ""
        
        if text_content:
            print(f"   📝 Extracted {len(text_content)} characters")
            return text_content
        else:
            print(f"   ⚠️ 'transcriptions' key was empty")
            return ""
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return ""

def main():
    print("🌐 Simple Hindi to English Translator")
    print("=" * 40)
    
    # Create separate output folders
    os.makedirs("hindi_transcripts", exist_ok=True)
    os.makedirs("english_transcripts", exist_ok=True)
    
    # Find JSON files
    downloads_folder = "downloads"
    json_files = [f for f in os.listdir(downloads_folder) if f.endswith('.json')]
    
    if not json_files:
        print("❌ No JSON files found in downloads folder")
        return
    
    print(f"📁 Found {len(json_files)} JSON files")
    
    # Process each file
    for filename in json_files:
        file_path = os.path.join(downloads_folder, filename)
        
        # Extract text from JSON
        hindi_text = process_one_json_file(file_path)
        
        if hindi_text:
            # Translate to English
            print(f"🔄 Translating {filename}...")
            english_text = translate_text(hindi_text)
            
            # Save in separate folders
            base_name = filename.replace('.json', '')
            
            # Save Hindi version in hindi_transcripts folder
            hindi_file = f"hindi_transcripts/{base_name}.txt"
            with open(hindi_file, 'w', encoding='utf-8') as f:
                f.write(hindi_text)
            
            # Save English version in english_transcripts folder
            english_file = f"english_transcripts/{base_name}.txt"
            with open(english_file, 'w', encoding='utf-8') as f:
                f.write(english_text)
            
            print(f"   ✅ Hindi saved: hindi_transcripts/{base_name}.txt")
            print(f"   ✅ English saved: english_transcripts/{base_name}.txt")
        else:
            print(f"   ⚠️ No text found in {filename}")
    
    print(f"\n🎉 Translation complete!")
    print(f"📁 Hindi files: hindi_transcripts/ folder")
    print(f"📁 English files: english_transcripts/ folder")

if __name__ == "__main__":
    main()