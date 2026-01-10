#!/bin/bash

# Start Streamlit frontend for Database Reasoning Engine

echo "Starting Database Reasoning Engine Frontend..."
echo "=============================================="
echo ""


# Start Streamlit
echo ""
echo "Starting Streamlit on http://localhost:8501"
echo "Make sure the API server is running on http://localhost:8000"
echo ""

streamlit run frontend/streamlit_app.py
