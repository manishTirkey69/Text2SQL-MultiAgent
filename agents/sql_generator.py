"""
SQL generation agent.
Synthesizes SQL queries from execution plans and schema context.
"""
from typing import Dict, Any
import re
import logging

from agents.base_agent import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class SQLGeneratorAgent(BaseAgent):
    """Agent that generates SQL from plans."""
    
    def get_system_prompt(self) -> str:
        """Get system prompt for SQL generator."""
        return """You are an expert SQL generator. Your task is to generate safe, optimized SQL queries based on:
1. The user's natural language query
2. The database schema provided
3. The execution plan

Requirements:
- Generate ONLY SELECT queries (read-only)
- Use proper JOIN syntax when combining tables
- Include appropriate WHERE clauses for filters
- Use column aliases for clarity
- Optimize for performance (avoid SELECT *, use indexes)
- Handle NULL values appropriately
- Use LIMIT when appropriate to prevent huge result sets

Output ONLY the SQL query, no explanations. Format it clearly on multiple lines.

Example output:
```sql
SELECT 
    u.user_id,
    u.username,
    COUNT(o.order_id) AS total_orders
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
GROUP BY u.user_id, u.username
ORDER BY total_orders DESC
LIMIT 10;
```"""
    
    def process_response(self, response: str, context: AgentContext) -> str:
        """Extract SQL from response."""
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', response)
        sql = re.sub(r'```\s*$', '', sql)
        sql = sql.strip()
        
        # Basic validation
        if not sql.upper().startswith('SELECT'):
            raise ValueError("Generated SQL must be a SELECT query")
        
        # Remove any explanatory text after the query
        # Find the first semicolon and cut there
        if ';' in sql:
            sql = sql[:sql.index(';') + 1]
        
        logger.info(f"Generated SQL:\n{sql}")
        
        return sql
