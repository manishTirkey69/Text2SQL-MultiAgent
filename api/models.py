"""
API request/response models.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request for query execution."""
    query: str = Field(..., description="Natural language query")
    database_id: Optional[str] = Field(None, description="Database ID (for federation)")
    enable_critique: bool = Field(True, description="Enable pre-execution critique")
    enable_repair: bool = Field(True, description="Enable automatic repair")
    max_retries: int = Field(3, ge=0, le=5, description="Maximum repair attempts")


class QueryResponse(BaseModel):
    """Response from query execution."""
    success: bool
    query: str
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time_ms: float = 0.0
    attempts: int = 1
    error: Optional[str] = None
    reasoning_trace: Optional[Dict[str, Any]] = None


class SchemaRequest(BaseModel):
    """Request for schema information."""
    database_id: Optional[str] = None
    detail_level: str = Field("medium", description="Detail level: low, medium, high")


class SchemaResponse(BaseModel):
    """Response with schema information."""
    success: bool
    database_name: str
    tables: List[str]
    total_tables: int
    schema_info: Optional[Dict[str, Any]] = None


class DatabaseRegistration(BaseModel):
    """Database registration request."""
    database_id: str
    connection_string: str
    name: str
    description: Optional[str] = None


class DatabaseInfo(BaseModel):
    """Database information."""
    database_id: str
    name: str
    connection_string: str
    tables: List[str]
    total_tables: int


class QuestionSuggestionsRequest(BaseModel):
    """Request for question suggestions."""
    database_id: Optional[str] = None
    count: int = Field(10, ge=1, le=50, description="Number of suggestions")
    use_llm: bool = Field(False, description="Use LLM for generation (slower, better quality)")
    complexity_filter: Optional[str] = Field(None, description="Filter by complexity: low, medium, high")
    type_filter: Optional[str] = Field(None, description="Filter by type: simple, join, aggregation, etc.")


class QuestionSuggestion(BaseModel):
    """Single question suggestion."""
    question: str
    complexity: str
    tables: List[str]
    type: str
    metadata: Optional[Dict[str, Any]] = None


class QuestionSuggestionsResponse(BaseModel):
    """Response with question suggestions."""
    success: bool
    suggestions: List[QuestionSuggestion]
    count: int
    generated_with_llm: bool
    database_name: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "1.0.0"
    databases_registered: int = 0
