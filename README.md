# 🎯 Hawa Singh - YouTube Growth Expert Chatbot

A powerful AI chatbot that provides personalized YouTube growth advice in natural Hinglish (Hindi + English). Built with Streamlit, Google AI, and advanced RAG (Retrieval-Augmented Generation) technology.

## 🌟 Features

- **500K+ Subscriber Expert**: Hawa Singh has helped 1000+ creators grow their channels
- **Natural Hinglish**: Converses in natural Hindi-English mix like a real YouTube expert
- **Personalized Advice**: Learns about your channel and provides tailored recommendations
- **Smart Context**: Uses extensive knowledge base of YouTube strategies and tips
- **Multi-turn Conversations**: Intelligent conversation flow without repetitive greetings
- **Real-time Learning**: Extracts and remembers user profile information

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Google AI API Key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/creator-chatbot.git
cd creator-chatbot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file
echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
```

4. **Build the knowledge base**
```bash
python build_vector_database.py
```

5. **Run the chatbot**
```bash
streamlit run launch_working_chatbot.py
```

## 🎯 What Hawa Singh Can Help With

- **Channel Growth Strategy** (0 to 100K+ subscribers)
- **Content Planning & Creation**
- **Audience Engagement & Community Building**
- **Monetization Tips** (₹50K+ monthly income strategies)
- **YouTube Shorts Mastery** (Viral content creation)
- **SEO & Thumbnail Optimization**

## 💡 Example Conversations

**User**: "Hi, I'm starting a new YouTube channel about cooking"
**Hawa Singh**: "Namaste! Main Hawa Singh hoon - YouTube growth expert with 500K+ subscribers. Cooking channel great choice hai! Main aapki help karunga..."

**User**: "How can I get my first 1000 subscribers?"
**Hawa Singh**: "First 1000 subscribers ke liye ye complete strategy follow karo..."

## 🏗️ Architecture

- **Frontend**: Streamlit with beautiful UI
- **AI Model**: Google Gemini 2.0 Flash
- **Vector Database**: ChromaDB for knowledge retrieval
- **Embeddings**: Google AI Embeddings
- **Conversation Management**: Smart multi-turn detection

## 📁 Project Structure

```
creator-chatbot/
├── launch_working_chatbot.py    # Main Streamlit app
├── src/                         # Core modules
│   ├── retrieval.py            # Intelligent retrieval system
│   ├── embeddings.py           # Google AI embeddings
│   ├── vector_store.py         # ChromaDB integration
│   └── query_analyzer.py       # Query analysis
├── data/                       # Knowledge base content
├── english_transcripts/        # YouTube transcripts
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Your Google AI API key
- `OPENAI_API_KEY`: (Optional) For additional features

### Model Configuration
- **LLM**: `models/gemini-2.0-flash`
- **Embeddings**: `models/embedding-001`
- **Temperature**: 0.7 (balanced creativity)

## 🚀 Deployment

### Streamlit Cloud (Recommended)
1. Push code to GitHub
2. Connect to [Streamlit Cloud](https://share.streamlit.io/)
3. Set environment variables
4. Deploy!

### Other Platforms
- **Heroku**: Use provided Procfile
- **Railway**: Direct deployment from GitHub
- **Docker**: Use provided Dockerfile

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Hawa Singh for the YouTube expertise
- Google AI for the powerful language models
- Streamlit for the amazing web framework
- ChromaDB for vector storage

## 📞 Support

If you have any questions or need help:
- Open an issue on GitHub
- Check the documentation
- Join our community

---

**Made with ❤️ for YouTube creators** 