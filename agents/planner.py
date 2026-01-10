"""
Query planning agent.
Analyzes natural language queries and creates structured execution plans.
"""
from typing import Dict, Any
import json
import logging

from agents.base_agent import BaseAgent, AgentContext, AgentResponse

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Agent that plans query execution strategy."""
    
    def get_system_prompt(self) -> str:
        """Get system prompt for planner."""
        return """You are a database query planning expert. Your task is to analyze natural language queries and create structured execution plans.

For each query, output a JSON object with:
{
  "query_type": "SELECT|JOIN|AGGREGATE|COMPARISON|TIME_SERIES",
  "tables_needed": ["table1", "table2", ...],
  "columns_needed": ["table.column1", "table.column2", ...],
  "join_strategy": "INNER|LEFT|RIGHT|FULL" (if joins needed),
  "aggregations": ["SUM", "COUNT", "AVG", ...] (if applicable),
  "filters": ["condition1", "condition2", ...],
  "ordering": ["column1 DESC", ...] (if applicable),
  "limit": number (if applicable),
  "complexity": "LOW|MEDIUM|HIGH",
  "description": "Brief explanation of the plan"
}

Focus on:
1. Identifying all required tables based on schema
2. Determining optimal join strategy
3. Identifying necessary aggregations and filters
4. Estimating query complexity

Only use tables and columns that exist in the provided schema."""
    
    def process_response(self, response: str, context: AgentContext) -> Dict[str, Any]:
        """Process planner response into structured plan."""
        # Extract JSON from response
        plan = self._extract_json(response)
        
        if not plan:
            # Fallback: try to parse the entire response as JSON
            try:
                plan = json.loads(response)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse planner response: {response}")
                raise ValueError("Could not parse planning response")
        
        # Validate required fields
        required_fields = ["query_type", "tables_needed"]
        for field in required_fields:
            if field not in plan:
                raise ValueError(f"Missing required field in plan: {field}")
        
        # Add defaults
        plan.setdefault("columns_needed", [])
        plan.setdefault("complexity", "MEDIUM")
        plan.setdefault("description", "")
        
        logger.info(f"Plan: {plan['query_type']} on {plan['tables_needed']}")
        
        return plan
