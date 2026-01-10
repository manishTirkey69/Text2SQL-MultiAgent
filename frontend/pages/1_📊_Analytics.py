"""
Analytics page with advanced visualizations.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")

st.title("📊 Query Analytics Dashboard")

if 'query_history' not in st.session_state or not st.session_state.query_history:
    st.info("No query history available. Execute some queries first!")
    st.stop()

# Create DataFrame from history
history = st.session_state.query_history
df = pd.DataFrame(history)

# Add datetime column
df['datetime'] = pd.to_datetime(df['timestamp'], format='%H:%M:%S')

# Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Queries", len(df))

with col2:
    success_rate = (df['success'].sum() / len(df)) * 100
    st.metric("Success Rate", f"{success_rate:.1f}%")

with col3:
    avg_time = df['execution_time'].mean()
    st.metric("Avg Execution Time", f"{avg_time:.2f}s")

with col4:
    st.metric("Failed Queries", (len(df) - df['success'].sum()))

# Visualizations
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Success vs Failure")
    
    success_counts = df['success'].value_counts()
    fig = px.pie(
        values=success_counts.values,
        names=['Failed', 'Success'],
        title='Query Success Rate',
        color_discrete_sequence=['#ff6b6b', '#51cf66']
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Execution Time Distribution")
    
    fig = px.histogram(
        df,
        x='execution_time',
        nbins=20,
        title='Query Execution Times',
        labels={'execution_time': 'Execution Time (s)'},
        color_discrete_sequence=['#667eea']
    )
    st.plotly_chart(fig, use_container_width=True)

# Timeline
st.subheader("Query Timeline")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df['datetime'],
    y=df['execution_time'],
    mode='lines+markers',
    name='Execution Time',
    line=dict(color='#667eea', width=2),
    marker=dict(
        size=8,
        color=df['success'].map({True: '#51cf66', False: '#ff6b6b'})
    )
))

fig.update_layout(
    title='Query Execution Over Time',
    xaxis_title='Time',
    yaxis_title='Execution Time (s)',
    hovermode='closest'
)

st.plotly_chart(fig, use_container_width=True)

# Query details table
st.markdown("---")
st.subheader("Query Details")

display_df = df[['query', 'success', 'timestamp', 'execution_time']].copy()
display_df['query'] = display_df['query'].str[:100] + '...'
display_df['status'] = display_df['success'].map({True: '✅', False: '❌'})
display_df = display_df.drop('success', axis=1)

st.dataframe(display_df, use_container_width=True, hide_index=True)
