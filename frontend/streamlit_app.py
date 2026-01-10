"""
Streamlit Frontend for Database Reasoning Engine.
Beautiful, interactive UI for natural language database queries.
"""
import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import time


# Page configuration
st.set_page_config(
    page_title="Database Reasoning Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #667eea;
        color: white;
    }
    
    .stButton>button:hover {
        background-color: #764ba2;
        color: white;
    }
    
    .suggestion-card {
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .suggestion-card:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    
    .sql-box {
        background-color: #2d2d2d;
        color: #f8f8f2;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
    }
    
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .info-box {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


class APIClient:
    """Client for Database Reasoning Engine API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": f"HTTP {response.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "message": "Cannot connect to API. Is the server running?"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def execute_query(
        self,
        query: str,
        enable_repair: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Execute natural language query."""
        payload = {
            "query": query,
            "enable_critique": True,
            "enable_repair": enable_repair,
            "max_retries": max_retries
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/query",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text[:200]}"
                }
        except Exception as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
    
    def get_suggestions(
        self,
        count: int = 10,
        use_llm: bool = False,
        complexity_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get question suggestions."""
        try:
            params = {
                "count": count,
                "use_llm": use_llm
            }
            
            if complexity_filter and complexity_filter != "All":
                params["complexity_filter"] = complexity_filter
            
            response = requests.get(
                f"{self.base_url}/suggestions/refresh",
                params=params,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}"
                }
        except Exception as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
    
    def get_schema(self, database_id: str = None, detail_level: str = "medium") -> Dict[str, Any]:
        """Get schema information."""
        payload = {
            "database_id": database_id,
            "detail_level": detail_level
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/schema",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}


def init_session_state():
    """Initialize session state variables."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = None
    
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    if 'current_query' not in st.session_state:
        st.session_state.current_query = ""
    
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None
    
    if 'suggestions' not in st.session_state:
        st.session_state.suggestions = []
    
    if 'schema_info' not in st.session_state:
        st.session_state.schema_info = None
    
    if 'api_url' not in st.session_state:
        st.session_state.api_url = "http://localhost:8000"
    
    if 'auto_connected' not in st.session_state:
        st.session_state.auto_connected = False
    
    if 'enable_repair' not in st.session_state:
        st.session_state.enable_repair = True
    
    if 'max_retries' not in st.session_state:
        st.session_state.max_retries = 3


def auto_connect_api():
    """Auto-connect to API on startup."""
    if not st.session_state.auto_connected and st.session_state.api_client is None:
        try:
            client = APIClient(st.session_state.api_url)
            health = client.health_check()
            
            if health.get("status") == "healthy":
                st.session_state.api_client = client
                st.session_state.auto_connected = True
                
                # Load schema info
                schema_response = client.get_schema()
                if schema_response.get("success"):
                    st.session_state.schema_info = schema_response
                
                return True
            else:
                st.session_state.auto_connected = True
                return False
        except Exception as e:
            st.session_state.auto_connected = True
            return False
    
    return st.session_state.api_client is not None


def render_header():
    """Render application header."""
    st.markdown('<h1 class="main-header">🧠 Database Reasoning Engine</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 1.2rem;">'
        'AI-Powered Natural Language to SQL with Self-Correction'
        '</p>',
        unsafe_allow_html=True
    )


def render_sidebar():
    """Render sidebar with settings and status."""
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=DB+Reasoning+Engine", use_container_width=True)
        
        st.markdown("---")
        
        # API Configuration
        st.subheader("⚙️ Configuration")
        
        api_url = st.text_input(
            "API URL",
            value=st.session_state.api_url,
            help="Database Reasoning Engine API endpoint"
        )
        
        # Update session state if URL changed
        if api_url != st.session_state.api_url:
            st.session_state.api_url = api_url
            st.session_state.api_client = None
            st.session_state.auto_connected = False
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔌 Connect", use_container_width=True):
                with st.spinner("Connecting to API..."):
                    client = APIClient(api_url)
                    health = client.health_check()
                    
                    if health.get("status") == "healthy":
                        st.session_state.api_client = client
                        st.success("✅ Connected!")
                        
                        # Load schema info
                        schema_response = client.get_schema()
                        if schema_response.get("success"):
                            st.session_state.schema_info = schema_response
                    else:
                        st.error(f"❌ Failed: {health.get('message', 'Unknown error')}")
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.session_state.api_client = None
                st.session_state.auto_connected = False
                st.rerun()
        
        # Status indicator
        st.markdown("---")
        st.markdown("### 📊 Status")
        
        if st.session_state.api_client:
            health = st.session_state.api_client.health_check()
            
            if health.get("status") == "healthy":
                st.success("🟢 **Connected**")
                
                # Show database info
                if st.session_state.schema_info:
                    info = st.session_state.schema_info
                    st.markdown(f"**Database:** {info.get('database_name', 'N/A')}")
                    st.markdown(f"**Tables:** {info.get('table_count', 0)}")
                    st.markdown(f"**Type:** {info.get('database_type', 'N/A')}")
            else:
                st.error("🔴 **Disconnected**")
                st.caption(health.get("message", "Unknown error"))
        else:
            st.warning("🟡 **Not Connected**")
            st.caption("Click 'Connect' or restart app")
        
        # Query settings
        st.markdown("---")
        st.markdown("### 🛠️ Query Settings")
        
        enable_repair = st.checkbox("Enable Auto-Repair", value=st.session_state.enable_repair, help="Automatically fix SQL errors")
        max_retries = st.slider("Max Retry Attempts", 1, 5, st.session_state.max_retries)
        
        st.session_state.enable_repair = enable_repair
        st.session_state.max_retries = max_retries
        
        # Query history
        if st.session_state.query_history:
            st.markdown("---")
            st.markdown("### 📜 Recent Queries")
            
            for i, hist in enumerate(reversed(st.session_state.query_history[-5:])):
                with st.expander(f"Query {len(st.session_state.query_history) - i}"):
                    st.markdown(f"**Q:** {hist['query'][:50]}...")
                    st.markdown(f"**Status:** {'✅' if hist['success'] else '❌'}")
                    st.markdown(f"**Time:** {hist['timestamp']}")


def render_suggestion_card(suggestion: Dict[str, Any], index: int):
    """Render a single suggestion card."""
    complexity = suggestion.get('complexity', 'medium')
    q_type = suggestion.get('type', 'general')
    tables = suggestion.get('tables', [])
    
    # Emoji based on complexity
    emoji = "🟢" if complexity == "low" else "🟡" if complexity == "medium" else "🔴"
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f"{emoji} **{suggestion['question']}**")
        if tables:
            st.caption(f"📊 Tables: {', '.join(tables)} | Type: {q_type}")
    
    with col2:
        if st.button("▶️ Run", key=f"run_sugg_{index}", use_container_width=True):
            st.session_state.current_query = suggestion['question']
            st.rerun()


def render_suggestions_panel():
    """Render question suggestions panel."""
    st.subheader("💡 Suggested Questions")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        suggestion_count = st.selectbox(
            "Number of suggestions",
            [5, 10, 15, 20],
            index=1,
            label_visibility="collapsed"
        )
    
    with col2:
        use_llm = st.checkbox("Use LLM", value=False, help="Higher quality, slower")
    
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            if st.session_state.api_client:
                with st.spinner("Generating suggestions..."):
                    response = st.session_state.api_client.get_suggestions(
                        count=suggestion_count,
                        use_llm=use_llm
                    )
                    
                    if response.get("success"):
                        st.session_state.suggestions = response.get("suggestions", [])
                        st.success(f"✅ Generated {len(st.session_state.suggestions)} suggestions!")
                    else:
                        st.error(f"❌ Error: {response.get('error')}")
            else:
                st.error("⚠️ **Not Connected to API**")
                st.info("👈 Click the '🔌 Connect' button in the sidebar to connect to the API")
    
    # Display suggestions
    if st.session_state.suggestions:
        st.markdown("---")
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            complexity_filter = st.selectbox(
                "Filter by complexity",
                ["All", "low", "medium", "high"],
                index=0
            )
        
        with col2:
            type_filter = st.selectbox(
                "Filter by type",
                ["All", "simple", "aggregation", "join", "time_series", "ranking", "comparison"],
                index=0
            )
        
        # Apply filters
        filtered_suggestions = st.session_state.suggestions
        
        if complexity_filter != "All":
            filtered_suggestions = [s for s in filtered_suggestions if s.get('complexity') == complexity_filter]
        
        if type_filter != "All":
            filtered_suggestions = [s for s in filtered_suggestions if s.get('type') == type_filter]
        
        # Display filtered suggestions
        if filtered_suggestions:
            for i, suggestion in enumerate(filtered_suggestions):
                render_suggestion_card(suggestion, i)
        else:
            st.info("No suggestions match the current filters")
    else:
        st.info("👆 Click 'Refresh' to generate question suggestions based on your database schema")


def render_query_interface():
    """Render main query interface."""
    st.subheader("💬 Ask Your Question")
    
    # Query input
    query = st.text_area(
        "Enter your question in natural language",
        value=st.session_state.current_query,
        height=100,
        placeholder="Example: Show me the top 10 customers by total order value",
        help="Ask questions about your database in plain English"
    )
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        execute_button = st.button("🚀 Execute Query", use_container_width=True, type="primary")
    
    with col2:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.current_query = ""
            st.session_state.last_result = None
            st.rerun()
    
    with col3:
        show_trace = st.checkbox("Show Trace", value=False)
    
    # Execute query
    if execute_button and query:
        if not st.session_state.api_client:
            st.error("⚠️ **Not Connected to API**")
            st.info("👈 Click the '🔌 Connect' button in the sidebar to connect")
            return
        
        with st.spinner("🤔 Analyzing query..."):
            start_time = time.time()
            
            result = st.session_state.api_client.execute_query(
                query=query,
                enable_repair=st.session_state.enable_repair,
                max_retries=st.session_state.max_retries
            )
            
            execution_time = time.time() - start_time
            
            # Store in history
            st.session_state.query_history.append({
                "query": query,
                "success": result.get("success", False),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "execution_time": execution_time
            })
            
            st.session_state.last_result = result
            st.session_state.current_query = query
    
    # Display results
    if st.session_state.last_result:
        render_query_results(st.session_state.last_result, show_trace)


def render_query_results(result: Dict[str, Any], show_trace: bool = False):
    """Render query results."""
    st.markdown("---")
    
    if result.get("success"):
        # Success message
        st.markdown(
            f'<div class="success-box">'
            f'<strong>✅ Query executed successfully!</strong><br>'
            f'Rows: {result.get("row_count", 0)} | '
            f'Time: {result.get("execution_time_ms", 0):.2f}ms | '
            f'Attempts: {result.get("attempts", 1)}'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Display SQL
        st.markdown("### 📝 Generated SQL")
        sql = result.get("sql", "")
        st.code(sql, language="sql")
        
        # Display results
        st.markdown("### 📊 Results")
        
        rows = result.get("results", [])
        
        if rows:
            # Convert to DataFrame
            df = pd.DataFrame(rows)
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Rows Returned", len(df))
            
            with col2:
                st.metric("Columns", len(df.columns))
            
            with col3:
                st.metric("Execution Time", f"{result.get('execution_time_ms', 0):.2f}ms")
            
            # Data table
            st.dataframe(df, use_container_width=True, height=400)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Visualizations
            render_data_visualizations(df)
        else:
            st.info("Query executed successfully but returned no rows")
    
    else:
        # Error message
        error = result.get("error", "Unknown error")
        st.markdown(
            f'<div class="error-box">'
            f'<strong>❌ Query failed</strong><br>'
            f'{error}'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Show SQL if available
        if result.get("sql"):
            st.markdown("### 📝 Generated SQL (Failed)")
            st.code(result.get("sql"), language="sql")
    
    # Show reasoning trace if requested
    if show_trace and result.get("reasoning_trace"):
        render_reasoning_trace(result["reasoning_trace"])


def render_data_visualizations(df: pd.DataFrame):
    """Render automatic data visualizations."""
    if len(df) == 0:
        return
    
    st.markdown("### 📈 Visualizations")
    
    # Detect numeric columns
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    
    if len(numeric_cols) == 0:
        st.info("No numeric columns available for visualization")
        return
    
    tab1, tab2 = st.tabs(["Bar Chart", "Line Chart"])
    
    with tab1:
        if len(df) <= 20:
            try:
                x_col = df.columns[0]
                y_col = numeric_cols[0]
                
                st.bar_chart(df.set_index(x_col)[y_col])
            except Exception as e:
                st.info(f"Could not generate bar chart: {str(e)}")
    
    with tab2:
        if len(numeric_cols) > 0:
            try:
                st.line_chart(df[numeric_cols[:3]])
            except Exception as e:
                st.info(f"Could not generate line chart: {str(e)}")


def render_reasoning_trace(trace: Dict[str, Any]):
    """Render reasoning trace."""
    with st.expander("🔍 Reasoning Trace", expanded=False):
        st.json(trace)


def render_schema_explorer():
    """Render schema explorer."""
    st.subheader("🗃️ Database Schema")
    
    if not st.session_state.api_client:
        st.warning("⚠️ **Not Connected to API**")
        st.info("👈 Click the '🔌 Connect' button in the sidebar to view schema")
        return
    
    if st.button("🔄 Refresh Schema"):
        with st.spinner("Loading schema..."):
            schema_response = st.session_state.api_client.get_schema()
            if schema_response.get("success"):
                st.session_state.schema_info = schema_response
                st.success("✅ Schema refreshed!")
            else:
                st.error(f"❌ Error: {schema_response.get('error')}")
    
    if st.session_state.schema_info:
        schema = st.session_state.schema_info
        
        # Overview metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Database", schema.get("database_name", "N/A"))
        with col2:
            st.metric("Tables", schema.get("table_count", 0))
        with col3:
            st.metric("Type", schema.get("database_type", "N/A"))
        
        st.markdown("---")
        
        tables = schema.get("tables", [])
        tables_detail = schema.get("tables_detail", {})
        
        if tables:
            # Search box
            search = st.text_input("🔍 Search tables", placeholder="Search by table name...")
            
            # Filter tables
            filtered_tables = [t for t in tables if search.lower() in t.lower()] if search else tables
            
            # Display tables
            for table_name in sorted(filtered_tables):
                with st.expander(f"📋 {table_name}"):
                    st.markdown(f"**Table:** `{table_name}`")
                    
                    if table_name in tables_detail:
                        detail = tables_detail[table_name]
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Columns", detail.get("column_count", len(detail.get("columns", []))))
                        with col2:
                            st.metric("Rows", f"~{detail.get('row_count', 0):,}")
                        with col3:
                            st.metric("Foreign Keys", detail.get("foreign_keys", 0))
                        
                        # Columns
                        if detail.get("columns"):
                            st.subheader("Columns")
                            cols_df = pd.DataFrame([
                                {"Column": col} for col in detail["columns"]
                            ])
                            st.dataframe(cols_df, use_container_width=True, hide_index=True)
                        
                        # Column details (high level)
                        if detail.get("column_details"):
                            st.subheader("Column Details")
                            cols_detail_df = pd.DataFrame(detail["column_details"])
                            st.dataframe(cols_detail_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Connect to API for detailed column information")
        else:
            st.info("No tables found in the database")
    else:
        st.info("Schema information not loaded. Click 'Refresh Schema' to load.")


def render_statistics():
    """Render usage statistics."""
    st.subheader("📊 Statistics")
    
    if not st.session_state.query_history:
        st.info("No queries executed yet")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_queries = len(st.session_state.query_history)
    successful = sum(1 for q in st.session_state.query_history if q['success'])
    failed = total_queries - successful
    success_rate = (successful / total_queries * 100) if total_queries > 0 else 0
    
    with col1:
        st.metric("Total Queries", total_queries)
    
    with col2:
        st.metric("Successful", successful, delta=f"{success_rate:.1f}%")
    
    with col3:
        st.metric("Failed", failed)
    
    with col4:
        avg_time = sum(q.get('execution_time', 0) for q in st.session_state.query_history) / total_queries
        st.metric("Avg Time", f"{avg_time:.2f}s")
    
    # Query history table
    st.markdown("### Recent Queries")
    
    history_df = pd.DataFrame([
        {
            "Query": q['query'][:50] + "..." if len(q['query']) > 50 else q['query'],
            "Status": "✅" if q['success'] else "❌",
            "Time": q['timestamp'],
            "Duration": f"{q.get('execution_time', 0):.2f}s"
        }
        for q in reversed(st.session_state.query_history[-10:])
    ])
    
    st.dataframe(history_df, use_container_width=True, hide_index=True)


def main():
    """Main application."""
    init_session_state()
    
    # Auto-connect to API on startup
    connection_status = auto_connect_api()
    
    render_header()
    
    # Show connection banner if not connected
    if not connection_status:
        st.warning("⚠️ Not connected to API. Please click 'Connect' in the sidebar or ensure the API is running at: http://localhost:8000")
    
    render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Query", "💡 Suggestions", "🗃️ Schema", "📊 Statistics"])
    
    with tab1:
        render_query_interface()
    
    with tab2:
        render_suggestions_panel()
    
    with tab3:
        render_schema_explorer()
    
    with tab4:
        render_statistics()
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #666;">'
        'Database Reasoning Engine v1.0 | Built with ❤️ using Streamlit'
        '</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
