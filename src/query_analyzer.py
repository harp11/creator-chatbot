import re
from typing import Dict, Any, List, Tuple
from enum import Enum

class QueryIntent(Enum):
    HOW_TO = "how_to"           # "How do I...?"
    WHAT_IS = "what_is"         # "What is...?"
    OPINION = "opinion"         # "What do you think about...?"
    COMPARISON = "comparison"   # "Which is better...?"
    TROUBLESHOOT = "troubleshoot" # "Why isn't this working...?"
    GENERAL = "general"         # General questions

class QueryComplexity(Enum):
    SIMPLE = "simple"           # Single concept
    MEDIUM = "medium"           # Multiple related concepts  
    COMPLEX = "complex"         # Multiple unrelated concepts

class QueryAnalyzer:
    def __init__(self):
        # Keywords that indicate different intents
        self.intent_keywords = {
            QueryIntent.HOW_TO: [
                r"how (to|do|can|should)",
                r"steps? to",
                r"ways? to",
                r"guide",
                r"tutorial",
                r"kaise",  # Hindi: how
                r"tarika",  # Hindi: method
            ],
            
            QueryIntent.WHAT_IS: [
                r"what (is|are|does)",
                r"explain",
                r"define",
                r"meaning of",
                r"kya h[ai]",  # Hindi: what is
                r"matlab",     # Hindi: meaning
            ],
            
            QueryIntent.OPINION: [
                r"what do you think",
                r"your thoughts",
                r"recommend",
                r"suggest",
                r"better",
                r"aapka kya",  # Hindi: what's your
                r"soch",       # Hindi: thought
            ],
            
            QueryIntent.COMPARISON: [
                r"(which|what).*better",
                r"compare",
                r"difference between",
                r"vs",
                r"versus",
                r"ya fir",     # Hindi: or else
                r"behtar",     # Hindi: better
            ],
            
            QueryIntent.TROUBLESHOOT: [
                r"why.*(not|isn't|doesn't|won't)",
                r"fix",
                r"issue",
                r"problem",
                r"error",
                r"help.*not working",
                r"nahi ho raha",  # Hindi: not working
                r"dikkat",        # Hindi: problem
            ]
        }
        
        # Topic-specific keywords
        self.topic_keywords = {
            "hawa_singh": [
                "youtube", "channel", "video", "content", "monetization",
                "subscriber", "view", "algorithm", "seo", "thumbnail",
                "viral", "analytics", "audience", "creator", "engagement",
                "upload", "playlist", "community", "shorts", "live"
            ]
        }
        
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze a query to determine intent, complexity, and other characteristics"""
        
        # Normalize query
        query_lower = query.lower()
        
        # Determine intent
        intent = self._determine_intent(query_lower)
        
        # Determine complexity
        complexity = self._determine_complexity(query_lower)
        
        # Determine topic relevance
        topic_scores = self._calculate_topic_scores(query_lower)
        
        return {
            "intent": intent.value,
            "complexity": complexity.value,
            "topic_scores": topic_scores,
            "original_query": query
        }
    
    def _determine_intent(self, query: str) -> QueryIntent:
        """Determine the primary intent of the query"""
        
        # Check each intent's keywords
        for intent, patterns in self.intent_keywords.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return intent
        
        # Default to general if no specific intent found
        return QueryIntent.GENERAL
    
    def _determine_complexity(self, query: str) -> QueryComplexity:
        """Determine query complexity based on various factors"""
        
        # Count key components
        question_count = len(re.findall(r'\?', query))
        and_count = len(re.findall(r'\band\b|\baur\b', query))  # Include Hindi 'and'
        concept_count = len(re.findall(r'[,;]', query))
        
        # Count total words
        word_count = len(query.split())
        
        # Determine complexity based on components and length
        if question_count > 1 or and_count > 1 or concept_count > 1 or word_count > 20:
            return QueryComplexity.COMPLEX
        elif question_count == 1 or and_count == 1 or concept_count == 1 or word_count > 10:
            return QueryComplexity.MEDIUM
        else:
            return QueryComplexity.SIMPLE
    
    def _calculate_topic_scores(self, query: str) -> Dict[str, float]:
        """Calculate relevance scores for different topics"""
        scores = {}
        
        # Calculate score for each topic
        for topic, keywords in self.topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query)
            scores[topic] = score / len(keywords)  # Normalize score
        
        return scores

def test_query_analyzer():
    """Test the query analyzer with various queries"""
    analyzer = QueryAnalyzer()
    
    test_queries = [
        "How to get more views on YouTube?",
        "What is YouTube monetization?",
        "My video views are not increasing, help!",
        "Which is better: long videos or shorts?",
        "Suggest some video ideas for my channel"
    ]
    
    print("\n🔍 Testing Query Analyzer")
    print("=" * 40)
    
    for query in test_queries:
        result = analyzer.analyze_query(query)
        print(f"\nQuery: {query}")
        print(f"Intent: {result['intent']}")
        print(f"Complexity: {result['complexity']}")
        print(f"Topic Scores: {result['topic_scores']}")
        print("-" * 30)