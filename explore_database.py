import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import chromadb
from chromadb.config import Settings
import config
import os

class DatabaseExplorer:
    def __init__(self):
        # Initialize ChromaDB connection
        self.client = chromadb.PersistentClient(
            path=config.VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collections = {}
        self._load_collections()
    
    def _load_collections(self):
        """Load all available collections"""
        try:
            for creator_id in config.CREATORS.keys():
                collection_name = f"creator_{creator_id}"
                try:
                    collection = self.client.get_collection(name=collection_name)
                    self.collections[creator_id] = collection
                except:
                    st.warning(f"No collection found for {creator_id}")
        except Exception as e:
            st.error(f"Error loading collections: {e}")
    
    def get_collection_data(self, creator_id):
        """Get all data from a collection"""
        if creator_id not in self.collections:
            return None
        
        collection = self.collections[creator_id]
        
        # Get all documents with metadata and embeddings
        results = collection.get(
            include=["documents", "metadatas", "embeddings"]
        )
        
        return results
    
    def create_dataframe(self, collection_data, creator_id):
        """Convert collection data to pandas DataFrame"""
        if not collection_data or not collection_data['documents']:
            return pd.DataFrame()
        
        data = []
        for i, (doc, metadata, embedding) in enumerate(zip(
            collection_data['documents'],
            collection_data['metadatas'], 
            collection_data['embeddings']
        )):
            row = {
                'chunk_id': collection_data['ids'][i],
                'creator_id': creator_id,
                'creator_name': metadata.get('creator_name', ''),
                'source': metadata.get('source', ''),
                'chunk_index': metadata.get('chunk_index', 0),
                'word_count': metadata.get('word_count', 0),
                'content': doc,
                'content_preview': doc[:100] + "..." if len(doc) > 100 else doc,
                'embedding_dim': len(embedding) if embedding else 0,
                'embedding': embedding
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def visualize_embeddings(self, df, method='PCA'):
        """Create 2D visualization of embeddings"""
        if df.empty or 'embedding' not in df.columns:
            return None
        
        # Extract embeddings
        embeddings = np.array(df['embedding'].tolist())
        n_samples = len(embeddings)
        
        # Check if we have enough data
        if n_samples < 2:
            st.warning(f"⚠️ Need at least 2 data points for visualization. Found {n_samples}.")
            return self._create_single_point_plot(df)
        
        try:
            if method == 'PCA':
                # For PCA, we need at least 2 samples
                if n_samples < 2:
                    return self._create_single_point_plot(df)
                reducer = PCA(n_components=min(2, n_samples), random_state=42)
            else:  # t-SNE
                # For t-SNE, we need at least 3 samples and perplexity < n_samples
                if n_samples < 3:
                    st.info("📊 Using PCA instead of t-SNE (need at least 3 data points for t-SNE)")
                    reducer = PCA(n_components=min(2, n_samples), random_state=42)
                else:
                    # Set perplexity to be less than n_samples
                    perplexity = min(30, max(1, n_samples - 1))
                    reducer = TSNE(n_components=2, random_state=42, perplexity=perplexity)
            
            # Reduce dimensions
            reduced_embeddings = reducer.fit_transform(embeddings)
            
            # Handle case where we only get 1 dimension back
            if reduced_embeddings.shape[1] == 1:
                # Add a zero second dimension
                zeros = np.zeros((reduced_embeddings.shape[0], 1))
                reduced_embeddings = np.hstack([reduced_embeddings, zeros])
            
            # Create visualization dataframe
            viz_df = df.copy()
            viz_df['x'] = reduced_embeddings[:, 0]
            viz_df['y'] = reduced_embeddings[:, 1]
            
            # Create scatter plot
            fig = px.scatter(
                viz_df,
                x='x', y='y',
                color='creator_name',
                hover_data=['source', 'word_count'],
                hover_name='content_preview',
                title=f'Content Embeddings Visualization ({method}) - {n_samples} chunks',
                width=800, height=600
            )
            
            fig.update_layout(
                xaxis_title=f'{method} Component 1',
                yaxis_title=f'{method} Component 2'
            )
            
            return fig
            
        except Exception as e:
            st.error(f"❌ Visualization error: {e}")
            return self._create_fallback_plot(df)
    
    def _create_single_point_plot(self, df):
        """Create a simple plot for single data point"""
        viz_df = df.copy()
        viz_df['x'] = 0
        viz_df['y'] = 0
        
        fig = px.scatter(
            viz_df,
            x='x', y='y',
            color='creator_name',
            hover_data=['source', 'word_count'],
            hover_name='content_preview',
            title=f'Content Overview - {len(df)} chunk(s)',
            width=800, height=600
        )
        
        fig.update_layout(
            xaxis_title='Single Point View',
            yaxis_title='(Add more content for clustering)',
            xaxis=dict(range=[-1, 1]),
            yaxis=dict(range=[-1, 1])
        )
        
        return fig
    
    def _create_fallback_plot(self, df):
        """Create a fallback plot when dimensionality reduction fails"""
        # Use chunk index vs word count as a simple 2D plot
        viz_df = df.copy()
        viz_df['x'] = viz_df['chunk_index']
        viz_df['y'] = viz_df['word_count']
        
        fig = px.scatter(
            viz_df,
            x='x', y='y',
            color='creator_name',
            hover_data=['source'],
            hover_name='content_preview',
            title=f'Content Overview - Chunk Index vs Word Count',
            width=800, height=600
        )
        
        fig.update_layout(
            xaxis_title='Chunk Index',
            yaxis_title='Word Count'
        )
        
        return fig
    
    def get_statistics(self, df):
        """Get database statistics"""
        if df.empty:
            return {}
        
        stats = {
            'total_chunks': len(df),
            'total_words': df['word_count'].sum(),
            'avg_words_per_chunk': df['word_count'].mean(),
            'sources': df['source'].nunique(),
            'embedding_dimension': df['embedding_dim'].iloc[0] if len(df) > 0 else 0
        }
        
        return stats

def main():
    st.set_page_config(
        page_title="Vector Database Explorer",
        page_icon="🗄️",
        layout="wide"
    )
    
    st.title("🗄️ Vector Database Explorer")
    st.markdown("Explore your creator knowledge base visually")
    
    # Initialize explorer
    explorer = DatabaseExplorer()
    
    if not explorer.collections:
        st.error("❌ No database collections found!")
        st.info("💡 Run `python build_vector_database.py` first to create the database.")
        return
    
    # Sidebar controls
    with st.sidebar:
        st.header("🔧 Controls")
        
        # Creator selection
        creator_options = list(explorer.collections.keys())
        selected_creator = st.selectbox(
            "Select Creator",
            creator_options,
            format_func=lambda x: config.CREATORS[x]["name"]
        )
        
        # Visualization method
        viz_method = st.selectbox(
            "Visualization Method",
            ["PCA", "t-SNE"],
            help="PCA is faster, t-SNE shows clusters better"
        )
        
        # Show raw data
        show_raw_data = st.checkbox("Show Raw Data Table")
        show_embeddings = st.checkbox("Show Embedding Vectors")
    
    # Main content
    if selected_creator:
        creator_name = config.CREATORS[selected_creator]["name"]
        st.subheader(f"📊 {creator_name}'s Knowledge Base")
        
        # Load data
        with st.spinner("Loading data..."):
            collection_data = explorer.get_collection_data(selected_creator)
            df = explorer.create_dataframe(collection_data, selected_creator)
        
        if df.empty:
            st.warning(f"No data found for {creator_name}")
            return
        
        # Statistics
        stats = explorer.get_statistics(df)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Chunks", stats['total_chunks'])
        with col2:
            st.metric("Total Words", f"{stats['total_words']:,}")
        with col3:
            st.metric("Avg Words/Chunk", f"{stats['avg_words_per_chunk']:.1f}")
        with col4:
            st.metric("Sources", stats['sources'])
        with col5:
            st.metric("Embedding Dim", stats['embedding_dimension'])
        
        # Visualizations
        st.subheader("🎨 Embedding Visualization")
        
        with st.spinner(f"Creating {viz_method} visualization..."):
            fig = explorer.visualize_embeddings(df, viz_method)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Each point represents a content chunk. Similar content should cluster together.")
        
        # Word count distribution
        st.subheader("📈 Content Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Word count histogram
            fig_hist = px.histogram(
                df,
                x='word_count',
                title='Word Count Distribution',
                nbins=20
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Sources breakdown
            source_counts = df['source'].value_counts()
            fig_pie = px.pie(
                values=source_counts.values,
                names=source_counts.index,
                title='Content by Source'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Content preview
        st.subheader("📄 Content Preview")
        
        # Search functionality
        search_term = st.text_input("🔍 Search content:", placeholder="Enter keywords to search...")
        
        if search_term:
            mask = df['content'].str.contains(search_term, case=False, na=False)
            filtered_df = df[mask]
            st.info(f"Found {len(filtered_df)} chunks containing '{search_term}'")
        else:
            filtered_df = df
        
        # Display content
        for idx, row in filtered_df.head(10).iterrows():
            with st.expander(f"📝 {row['source']} - Chunk {row['chunk_index']} ({row['word_count']} words)"):
                st.markdown(f"**Content:**")
                st.write(row['content'])
                
                if show_embeddings:
                    st.markdown(f"**Embedding (first 10 dimensions):**")
                    embedding_preview = row['embedding'][:10] if row['embedding'] else []
                    st.code(f"[{', '.join([f'{x:.4f}' for x in embedding_preview])}...]")
        
        # Raw data table
        if show_raw_data:
            st.subheader("🗃️ Raw Data Table")
            display_df = df.drop(['embedding'], axis=1) if 'embedding' in df.columns else df
            st.dataframe(display_df, use_container_width=True)
    
    # All creators overview
    st.markdown("---")
    st.subheader("🌍 All Creators Overview")
    
    # Combine all data
    all_data = []
    for creator_id in explorer.collections.keys():
        collection_data = explorer.get_collection_data(creator_id)
        creator_df = explorer.create_dataframe(collection_data, creator_id)
        if not creator_df.empty:
            all_data.append(creator_df)
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Overview stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Creators", len(explorer.collections))
        with col2:
            st.metric("Total Chunks", len(combined_df))
        with col3:
            st.metric("Total Words", f"{combined_df['word_count'].sum():,}")
        
        # Creator comparison
        creator_stats = combined_df.groupby('creator_name').agg({
            'chunk_id': 'count',
            'word_count': ['sum', 'mean']
        }).round(1)
        
        creator_stats.columns = ['Total Chunks', 'Total Words', 'Avg Words/Chunk']
        st.dataframe(creator_stats, use_container_width=True)
        
        # Combined visualization
        if len(combined_df) > 1:
            st.subheader("🎯 All Creators Embedding Space")
            with st.spinner("Creating combined visualization..."):
                combined_fig = explorer.visualize_embeddings(combined_df, viz_method)
            
            if combined_fig:
                st.plotly_chart(combined_fig, use_container_width=True)
                st.caption("This shows how different creators' content is distributed in the embedding space.")

if __name__ == "__main__":
    main()