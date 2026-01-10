"""
FastAPI server for Database Reasoning Engine.
"""
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from main import DatabaseReasoningEngine
from api.models import (
    QueryRequest, QueryResponse,
    SchemaRequest, SchemaResponse,
    DatabaseRegistration, DatabaseInfo,
    QuestionSuggestionsRequest, QuestionSuggestionsResponse,
    HealthResponse
)
from agents.question_suggester import QuestionSuggestionAgent

logger = logging.getLogger(__name__)

# Global app state
app_state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app initialization."""
    settings = get_settings()
    
    # Initialize LLM client
    if settings.llm.provider == "openai":
        import openai
        llm_client = openai.OpenAI(api_key=settings.llm.api_key)
        llm_client.model = settings.llm.model
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm.provider}")
    
    # Initialize question suggester
    app_state['question_suggester'] = QuestionSuggestionAgent(llm_client, settings.llm.model)
    
    # Simple database registry (single database for now)
    app_state['engines'] = {}
    app_state['default_connection_string'] = settings.db.get_connection_string()
    
    logger.info("API server initialized")
    
    yield
    
    # Cleanup
    logger.info("API server shutting down")


app = FastAPI(
    title="Database Reasoning Engine API",
    description="Enterprise-grade agentic Text-to-SQL API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
settings = get_settings()
if settings.api.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def get_engine(database_id: Optional[str] = None) -> DatabaseReasoningEngine:
    """Get or create engine instance."""
    if database_id and database_id in app_state['engines']:
        return app_state['engines'][database_id]
    
    # Use default connection string
    connection_string = app_state.get('default_connection_string')
    if not connection_string:
        raise HTTPException(status_code=400, detail="No database connection configured")
    
    # Create engine (cache it)
    if database_id:
        engine = DatabaseReasoningEngine(connection_string)
        app_state['engines'][database_id] = engine
        return engine
    else:
        # Use default engine
        if 'default_engine' not in app_state:
            app_state['default_engine'] = DatabaseReasoningEngine(connection_string)
        return app_state['default_engine']


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        databases_registered=len(app_state.get('engines', {}))
    )


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """Execute natural language query."""
    try:
        engine = get_engine(request.database_id)
        result = engine.query(
            query=request.query,
            enable_critique=request.enable_critique,
            enable_repair=request.enable_repair,
            max_retries=request.max_retries
        )
        
        return QueryResponse(
            success=result['success'],
            query=request.query,  # Fixed: use request.query instead of result['query']
            sql=result.get('sql'),
            results=result.get('results'),
            row_count=result.get('row_count', 0),
            execution_time_ms=result.get('execution_time_ms', 0.0),
            attempts=result.get('attempts', 1),
            error=result.get('error'),
            reasoning_trace=result.get('reasoning_trace')
        )
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schema", response_model=SchemaResponse)
async def get_schema(request: SchemaRequest):
    """Get database schema information."""
    try:
        engine = get_engine(request.database_id)
        schema = engine.schema
        
        return SchemaResponse(
            success=True,
            database_name=schema.database_name,
            tables=list(schema.tables.keys()),
            total_tables=len(schema.tables),
            schema_info={
                "database_type": schema.database_type,
                "version_hash": schema.version_hash
            }
        )
    except Exception as e:
        logger.error(f"Schema error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/suggestions", response_model=QuestionSuggestionsResponse)
async def get_question_suggestions(request: QuestionSuggestionsRequest):
    """Get AI-generated question suggestions based on schema."""
    try:
        engine = get_engine(request.database_id)
        question_suggester = app_state['question_suggester']
        
        logger.info(f"Generating {request.count} question suggestions")
        
        # Generate suggestions
        suggestions = question_suggester.generate_suggestions(
            schema=engine.schema,
            graph=engine.graph,
            count=request.count,
            use_llm=request.use_llm
        )
        
        # Apply filters if requested
        if request.complexity_filter:
            suggestions = [s for s in suggestions if s.get('complexity') == request.complexity_filter]
        
        if request.type_filter:
            suggestions = [s for s in suggestions if s.get('type') == request.type_filter]
        
        # Convert to response model
        from api.models import QuestionSuggestion
        suggestion_models = [
            QuestionSuggestion(
                question=s['question'],
                complexity=s.get('complexity', 'medium'),
                tables=s.get('tables', []),
                type=s.get('type', 'general'),
                metadata={k: v for k, v in s.items() if k not in ['question', 'complexity', 'tables', 'type']}
            )
            for s in suggestions
        ]
        
        return QuestionSuggestionsResponse(
            success=True,
            suggestions=suggestion_models,
            count=len(suggestion_models),
            generated_with_llm=request.use_llm,
            database_name=engine.schema.database_name
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Question suggestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/suggestions/refresh", response_model=QuestionSuggestionsResponse)
async def refresh_suggestions(
    count: int = 10,
    use_llm: bool = False,
    database_id: Optional[str] = None
):
    """
    Refresh question suggestions (convenience endpoint).
    Same as POST /suggestions but as GET for easy browser access.
    """
    request = QuestionSuggestionsRequest(
        database_id=database_id,
        count=count,
        use_llm=use_llm
    )
    return await get_question_suggestions(request)
