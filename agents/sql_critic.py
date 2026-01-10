"""
SQL critique agent.
Reviews generated SQL for correctness, safety, and optimization opportunities.
"""
from typing import Dict, Any
import json
import logging

from agents.base_agent import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class SQLCriticAgent(BaseAgent):
    """Agent that critiques and validates SQL queries."""
    
    def get_system_prompt(self) -> str:
        """Get system prompt for SQL critic."""
        return """You are an expert SQL reviewer and security analyst. Your task is to review SQL queries for:

1. **Correctness**: Does it match the user's intent?
2. **Safety**: No mutations (INSERT/UPDATE/DELETE), no dangerous operations
3. **Performance**: Proper JOIN usage, index utilization, avoiding cartesian products
4. **Schema Compliance**: All tables and columns exist in schema
5. **Syntax**: Valid SQL syntax for the database type

Output a JSON object:
{
  "approved": true/false,
  "issues": [
    {"severity": "ERROR|WARNING|INFO", "message": "description", "location": "optional"}
  ],
  "suggestions": ["improvement1", "improvement2"],
  "risk_score": 0-10,
  "explanation": "Brief summary"
}

- If approved=false, explain why in issues with ERROR severity
- risk_score: 0=safe, 10=dangerous
- Be strict about mutations and schema violations"""
    
    def process_response(self, response: str, context: AgentContext) -> Dict[str, Any]:
        """Process critique response."""
        critique = self._extract_json(response)
        
        if not critique:
            try:
                critique = json.loads(response)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse critique: {response}")
                raise ValueError("Could not parse critique response")
        
        # Validate structure
        if "approved" not in critique:
            raise ValueError("Critique must include 'approved' field")
        
        # Add defaults
        critique.setdefault("issues", [])
        critique.setdefault("suggestions", [])
        critique.setdefault("risk_score", 5)
        critique.setdefault("explanation", "")
        
        # Log results
        if critique["approved"]:
            logger.info(f"SQL approved (risk: {critique['risk_score']}/10)")
        else:
            logger.warning(f"SQL rejected: {critique.get('explanation', 'Unknown reason')}")
            for issue in critique["issues"]:
                if issue.get("severity") == "ERROR":
                    logger.error(f"  - {issue['message']}")
        
        return critique


class SQLCriticAgentSimple(BaseAgent):
    """Simplified SQL critic for basic validation without LLM."""
    
    def __init__(self, llm_client: Any = None, model: str = None):
        """Initialize simple critic (no LLM needed)."""
        super().__init__(llm_client, model)
        self.dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE', 
            'ALTER', 'CREATE', 'GRANT', 'REVOKE'
        ]
    
    def get_system_prompt(self) -> str:
        """Not used in simple mode."""
        return ""
    
    def execute(self, context: AgentContext) -> Any:
        """Execute simple validation without LLM."""
        from agents.base_agent import AgentResponse
        
        sql = context.metadata.get('sql', '')
        
        issues = []
        
        # Check for dangerous keywords
        sql_upper = sql.upper()
        for keyword in self.dangerous_keywords:
            if keyword in sql_upper:
                issues.append({
                    "severity": "ERROR",
                    "message": f"Dangerous keyword detected: {keyword}",
                    "location": keyword
                })
        
        # Check if it's a SELECT query
        if not sql_upper.strip().startswith('SELECT'):
            issues.append({
                "severity": "ERROR",
                "message": "Only SELECT queries are allowed",
                "location": "query_start"
            })
        
        # Basic schema validation
        relevant_tables = context.relevant_tables
        for table in relevant_tables:
            if table.lower() not in sql.lower():
                issues.append({
                    "severity": "WARNING",
                    "message": f"Expected table '{table}' not found in query",
                    "location": table
                })
        
        approved = len([i for i in issues if i["severity"] == "ERROR"]) == 0
        risk_score = len(issues) * 2
        
        critique = {
            "approved": approved,
            "issues": issues,
            "suggestions": [],
            "risk_score": min(risk_score, 10),
            "explanation": "Basic validation complete" if approved else "Validation failed"
        }
        
        return AgentResponse(
            success=True,
            output=critique,
            metadata={"agent": "SQLCriticSimple"}
        )
    
    def process_response(self, response: str, context: AgentContext) -> Dict[str, Any]:
        """Not used in simple mode."""
        return {}
