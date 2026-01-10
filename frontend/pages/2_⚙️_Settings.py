"""
Settings page for configuration.
"""
import streamlit as st
import json

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings & Configuration")

# API Settings
st.subheader("🔌 API Configuration")

col1, col2 = st.columns(2)

with col1:
    api_url = st.text_input(
        "API Base URL",
        value=st.session_state.get('api_url', 'http://localhost:8000')
    )
    
    timeout = st.number_input(
        "Request Timeout (seconds)",
        min_value=10,
        max_value=300,
        value=60
    )

with col2:
    st.markdown("**Connection Status**")
    
    if st.session_state.get('api_client'):
        health = st.session_state.api_client.health_check()
        if health.get('status') == 'healthy':
            st.success("🟢 Connected")
            st.json(health)
        else:
            st.error("🔴 Disconnected")
    else:
        st.warning("⚠️ Not connected")

# Query Settings
st.markdown("---")
st.subheader("🛠️ Query Execution Settings")

col1, col2 = st.columns(2)

with col1:
    enable_repair = st.checkbox(
        "Enable Auto-Repair",
        value=st.session_state.get('enable_repair', True),
        help="Automatically attempt to fix SQL errors"
    )
    
    enable_critique = st.checkbox(
        "Enable Pre-execution Critique",
        value=True,
        help="Review SQL before execution"
    )
    
    max_retries = st.slider(
        "Maximum Retry Attempts",
        min_value=1,
        max_value=5,
        value=st.session_state.get('max_retries', 3)
    )

with col2:
    max_rows = st.number_input(
        "Maximum Rows to Return",
        min_value=10,
        max_value=100000,
        value=10000,
        step=100
    )
    
    enable_cache = st.checkbox(
        "Enable Query Caching",
        value=False,
        help="Cache query results"
    )

# Save settings
if st.button("💾 Save Settings", type="primary"):
    st.session_state.enable_repair = enable_repair
    st.session_state.max_retries = max_retries
    st.session_state.api_url = api_url
    
    st.success("✅ Settings saved successfully!")

# Advanced Settings
st.markdown("---")
st.subheader("🔧 Advanced Settings")

with st.expander("LLM Configuration"):
    llm_provider = st.selectbox("LLM Provider", ["OpenAI", "Anthropic", "LiteLLM"])
    llm_model = st.text_input("Model Name", value="gpt-4-turbo-preview")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.1)
    
    st.info("Note: These settings are configured on the backend")

with st.expander("Safety Settings"):
    st.checkbox("Enforce Read-Only Mode", value=True, disabled=True)
    st.checkbox("Block DDL Operations", value=True, disabled=True)
    st.checkbox("Block DML Operations", value=True, disabled=True)
    
    st.info("Safety settings are enforced on the backend for security")

# Export/Import Configuration
st.markdown("---")
st.subheader("📦 Export/Import Configuration")

col1, col2 = st.columns(2)

with col1:
    if st.button("📤 Export Settings", use_container_width=True):
        settings = {
            "api_url": api_url,
            "enable_repair": enable_repair,
            "max_retries": max_retries,
            "max_rows": max_rows,
            "enable_cache": enable_cache
        }
        
        st.download_button(
            "Download Settings JSON",
            data=json.dumps(settings, indent=2),
            file_name="db_reasoning_settings.json",
            mime="application/json"
        )

with col2:
    uploaded_file = st.file_uploader("📥 Import Settings", type=['json'])
    
    if uploaded_file:
        try:
            settings = json.load(uploaded_file)
            st.success("✅ Settings imported successfully!")
            st.json(settings)
        except Exception as e:
            st.error(f"❌ Error importing settings: {e}")

# Clear Data
st.markdown("---")
st.subheader("🗑️ Data Management")

col1, col2 = st.columns(2)

with col1:
    if st.button("🧹 Clear Query History", use_container_width=True):
        st.session_state.query_history = []
        st.success("✅ Query history cleared")

with col2:
    if st.button("🔄 Reset All Settings", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ All settings reset")
        st.rerun()
