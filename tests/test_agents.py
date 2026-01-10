"""
Tests for agents.
"""
import pytest
from unittest.mock import Mock, MagicMock
from agents.base_agent import AgentContext, AgentResponse
from agents.planner import PlannerAgent
from agents.sql_generator import SQLGeneratorAgent


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = Mock()
    client.model = "gpt-4"
    
    # Mock completion response
    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = '{"query_type": "SELECT", "tables_needed": ["users"]}'
    mock_response.choices = [Mock(message=mock_message)]
    
    client.chat.completions.create = Mock(return_value=mock_response)
    
    return client


@pytest.fixture
def sample_context():
    """Sample agent context."""
    return AgentContext(
        query="Show me all users",
        schema="Table: users\nColumns: user_id, username, email",
        relevant_tables=["users"],
        conversation_history=[],
        metadata={}
    )


def test_planner_agent(mock_llm_client, sample_context):
    """Test planner agent execution."""
    agent = PlannerAgent(mock_llm_client)
    
    # Mock response
    mock_llm_client.chat.completions.create.return_value.choices[0].message.content = '''
    {
        "query_type": "SELECT",
        "tables_needed": ["users"],
        "columns_needed": ["user_id", "username"],
        "complexity": "LOW"
    }
    '''
    
    response = agent.execute(sample_context)
    
    assert response.success
    assert "query_type" in response.output
    assert response.output["query_type"] == "SELECT"


def test_sql_generator_agent(mock_llm_client, sample_context):
    """Test SQL generator agent."""
    agent = SQLGeneratorAgent(mock_llm_client)
    
    # Mock SQL response
    mock_llm_client.chat.completions.create.return_value.choices[0].message.content = '''
    ```sql
    SELECT user_id, username, email
    FROM users
    LIMIT 100;
    ```
    '''
    
    response = agent.execute(sample_context)
    
    assert response.success
    assert "SELECT" in response.output
    assert "FROM users" in response.output


def test_question_suggester_templates():
    """Test question suggester with templates."""
    from core.schema_info import DatabaseSchema, TableInfo, ColumnInfo
    from core.graph_builder import SchemaGraph
    from agents.question_suggester import QuestionSuggestionAgent
    
    # Create a simple schema
    users_table = TableInfo(
        name="users",
        schema=None,
        columns=[ColumnInfo(name="user_id", data_type="INT", nullable=False)],
        primary_keys=["user_id"],
        foreign_keys=[],
        indexes=[],
        row_count=100
    )
    
    schema = DatabaseSchema(
        database_name="test_db",
        schema_name=None,
        tables={"users": users_table},
        version_hash="test",
        extracted_at="2026-01-10",
        database_type="postgresql"
    )
    
    graph = SchemaGraph(schema)
    suggester = QuestionSuggestionAgent(None)  # No LLM needed for templates
    
    suggestions = suggester.generate_suggestions(
        schema=schema,
        graph=graph,
        count=10,
        use_llm=False
    )
    
    assert len(suggestions) > 0
    assert len(suggestions) <= 10
    
    # Check structure
    for suggestion in suggestions:
        assert 'question' in suggestion
        assert 'complexity' in suggestion
        assert 'tables' in suggestion
        assert 'type' in suggestion
        assert suggestion['complexity'] in ['low', 'medium', 'high']
