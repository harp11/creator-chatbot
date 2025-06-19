import sqlite3
import pandas as pd
import streamlit as st
import config

def create_database():
    """Create SQLite database for storing chat history"""
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  query TEXT,
                  response TEXT,
                  creator_id TEXT,
                  context_used TEXT,
                  similarity_score REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS analytics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  metric TEXT,
                  value TEXT)''')
    
    conn.commit()
    conn.close()

def add_chat_message(query, response, context_used, similarity_score):
    """Add a chat message to the database"""
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO chat_messages 
                 (query, response, creator_id, context_used, similarity_score)
                 VALUES (?, ?, ?, ?, ?)''',
              (query, response, "hawa_singh", context_used, similarity_score))
    
    conn.commit()
    conn.close()

def add_analytics_event(metric, value):
    """Add an analytics event to the database"""
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    c.execute('INSERT INTO analytics (metric, value) VALUES (?, ?)',
              (metric, value))
    
    conn.commit()
    conn.close()

def get_chat_history(limit=100):
    """Get recent chat history"""
    conn = sqlite3.connect('chat_history.db')
    
    query = '''SELECT timestamp, query, response, creator_id, 
               context_used, similarity_score 
               FROM chat_messages 
               ORDER BY timestamp DESC 
               LIMIT ?'''
    
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    
    return df

def get_analytics_summary():
    """Get summary of analytics events"""
    conn = sqlite3.connect('chat_history.db')
    
    query = '''SELECT metric, COUNT(*) as count, 
               AVG(CAST(value as FLOAT)) as avg_value,
               MIN(timestamp) as first_seen,
               MAX(timestamp) as last_seen
               FROM analytics 
               GROUP BY metric'''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def view_database():
    """Streamlit app to view database contents"""
    st.set_page_config(page_title="Chat History Viewer", layout="wide")
    
    st.title("🎯 Hawa Singh - Chat History Viewer")
    
    # Create database if not exists
    create_database()
    
    # Sidebar
    st.sidebar.title("📊 Database Stats")
        
    # Get basic stats
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM chat_messages')
    total_messages = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM analytics')
    total_analytics = c.fetchone()[0]
    
    st.sidebar.metric("Total Messages", total_messages)
    st.sidebar.metric("Analytics Events", total_analytics)
        
    # Main content
    tab1, tab2 = st.tabs(["Chat History", "Analytics"])
    
    with tab1:
        st.header("💬 Chat History")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            limit = st.number_input("Number of messages to show", 
                                  min_value=10, max_value=1000, value=100)
        
        # Get and display chat history
        chat_history = get_chat_history(limit)
        if not chat_history.empty:
            st.dataframe(chat_history, use_container_width=True)
            
            # Download button
            csv = chat_history.to_csv(index=False)
            st.download_button(
                "Download Chat History",
                csv,
                "chat_history.csv",
                "text/csv",
                key='download-chat-csv'
            )
        else:
            st.info("No chat messages found")
    
    with tab2:
        st.header("📈 Analytics")
        
        # Get and display analytics
        analytics = get_analytics_summary()
        if not analytics.empty:
            st.dataframe(analytics, use_container_width=True)
    
            # Download button
            csv = analytics.to_csv(index=False)
        st.download_button(
                "Download Analytics",
                csv,
                "analytics_summary.csv",
                "text/csv",
                key='download-analytics-csv'
            )
        else:
            st.info("No analytics events found")
    
    conn.close()

if __name__ == "__main__":
    view_database()