# Database Reasoning Engine

Enterprise-grade agentic Text-to-SQL system with self-correction, schema intelligence, and multi-database support.

## Features

- **Agentic Architecture**: Multi-agent system (Planner, Generator, Critic, Repair)
- **Schema Intelligence**: Graph-based FK relationships, join path discovery
- **Self-Correction**: Automatic SQL repair based on execution feedback
- **Semantic Search**: Embedding-based table and query retrieval
- **Safety First**: Read-only enforcement, query validation
- **Multi-Database**: Federated query execution across databases
- **Memory**: Conversational context and query history
- **Question Suggestions**: AI-generated question suggestions based on schema

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.env` file:

```bash
# LLM Configuration
LLM__API_KEY=your-openai-api-key
LLM__MODEL=gpt-4-turbo-preview

# Database Configuration
DB__TYPE=postgresql
DB__HOST=localhost
DB__DATABASE=your_database
DB__USERNAME=your_username
DB__PASSWORD=your_password

# Safety
SAFETY__ENFORCE_READONLY=true
```

### Usage

#### Interactive Mode

```bash
python main.py --interactive
```

#### Single Query

```bash
python main.py --query "Show me the top 10 customers by revenue"
```

#### API Server

```bash
python main.py --api
# Visit http://localhost:8000/docs
```

## 🎨 Streamlit Frontend

Beautiful, interactive web interface for the Database Reasoning Engine.

### Quick Start

```bash
# Terminal 1: Start API
python main.py --api

# Terminal 2: Start Frontend
cd frontend
streamlit run streamlit_app.py
```

Or use the convenience script:

```bash
# Linux/Mac
./frontend/run_frontend.sh

# Windows
frontend\run_frontend.bat
```

Or use Make:

```bash
make run-frontend
```

### Access

- **Frontend**: http://localhost:8501
- **API**: http://localhost:8000

### Features

- 💬 Natural language query interface
- 💡 AI-generated question suggestions
- 📊 Interactive data visualizations
- 📈 Real-time analytics dashboard
- 🗃️ Schema explorer
- 📜 Query history tracking
- ⚙️ Configurable settings
- 📥 Export results to CSV

### Docker

```bash
docker-compose up -d
# Access frontend at http://localhost:8501
```

The frontend includes:
- Clean, modern UI with gradient themes
- Real-time query execution with progress indicators
- Automatic data visualizations
- Suggestion cards for quick queries
- Comprehensive analytics dashboard

## Architecture

```
db_reasoning_engine/
├── core/           # Schema intelligence
├── agents/         # LLM-powered agents
├── execution/      # Safe SQL execution
├── memory/         # Conversational context
├── federation/     # Multi-database support
├── api/            # REST/WebSocket API
├── frontend/       # Streamlit UI
│   ├── streamlit_app.py
│   ├── pages/
│   └── requirements.txt
├── ui_support/     # UI utilities
└── config/         # Configuration
```

## Question Suggestions

The engine can automatically generate relevant questions based on your database schema.

### CLI Usage

```bash
# In interactive mode
python main.py --interactive

# Then type 'suggest' to see question ideas
Query: suggest
```

### Question Types

- **simple**: Single table queries
- **aggregation**: COUNT, SUM, AVG operations
- **join**: Multi-table queries
- **time_series**: Temporal analysis
- **ranking**: TOP N queries
- **comparison**: Group comparisons
- **statistical**: Statistical analysis
