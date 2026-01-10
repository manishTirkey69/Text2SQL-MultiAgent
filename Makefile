.PHONY: help install run-api run-frontend run-full install-frontend clean

help:
	@echo "Database Reasoning Engine - Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          - Install all dependencies"
	@echo "  make run-api          - Start the API server"
	@echo "  make run-frontend     - Start the Streamlit frontend"
	@echo "  make run-full         - Start both API and frontend"
	@echo "  make install-frontend - Install frontend dependencies"
	@echo "  make clean            - Clean temporary files"

install:
	pip install -r requirements.txt

run-api:
	python main.py --api

run-frontend:
	streamlit run frontend/streamlit_app.py

run-full:
	@echo "Starting full stack..."
	@echo "API will run in background. Frontend will start..."
	make run-api & make run-frontend

install-frontend:
	pip install -r frontend/requirements.txt

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
