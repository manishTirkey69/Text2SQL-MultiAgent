"""
SQL repair agent.
Fixes broken SQL based on execution errors and feedback.
"""
from typing import Dict, Any, Optional
import logging
import re

from agents.base_agent import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class SQLRepairAgent(BaseAgent):
    """Agent that repairs broken SQL queries."""
    
    def get_system_prompt(self) -> str:
        """Get system prompt for SQL repair."""
        return """You are an expert SQL debugger and repair specialist. Your task is to fix broken SQL queries based on error messages.

You will receive:
1. The original natural language query
2. The database schema
3. The broken SQL query
4. The error message from execution

Your job:
- Analyze the error message carefully
- Identify the root cause (syntax error, missing table, wrong join, etc.)
- Generate a CORRECTED SQL query
- Ensure the fix addresses the user's original intent

Common issues to fix:
- Column/table name typos or non-existent references
- JOIN syntax errors or missing ON clauses
- Ambiguous column references (need table aliases)
- Type mismatches in comparisons
- Missing GROUP BY for aggregations
- Syntax errors

Output ONLY the corrected SQL query in ```sql code blocks, no explanations.

Example:
```sql
SELECT 
    u.user_id,
    u.name,
    COUNT(o.order_id) AS order_count
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE u.created_at > '2024-01-01'
GROUP BY u.user_id, u.name
ORDER BY order_count DESC;
```"""
    
    def process_response(self, response: str, context: AgentContext) -> str:
        """Extract repaired SQL from response."""
        # Extract SQL from code blocks
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Try to extract any SQL-like content
            sql = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
            sql = sql.strip()
        
        if not sql:
            raise ValueError("No SQL found in repair response")
        
        logger.info(f"Repaired SQL:\n{sql}")
        
        return sql
