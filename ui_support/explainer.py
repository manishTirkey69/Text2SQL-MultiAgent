"""
Natural language explanation generator.
Generates human-readable explanations of SQL and reasoning.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class NaturalLanguageExplainer:
    """Generates natural language explanations."""
    
    @staticmethod
    def explain_sql(sql: str, plan: Dict[str, Any]) -> str:
        """
        Generate natural language explanation of SQL.
        
        Args:
            sql: SQL query
            plan: Query plan
            
        Returns:
            Natural language explanation
        """
        parts = []
        
        query_type = plan.get("query_type", "SELECT")
        tables = plan.get("tables_needed", [])
        aggregations = plan.get("aggregations", [])
        
        # Basic description
        if query_type == "SELECT":
            parts.append("This query retrieves data")
        elif query_type == "AGGREGATE":
            parts.append("This query aggregates data")
        elif query_type == "JOIN":
            parts.append("This query combines data")
        
        # Tables
        if len(tables) == 1:
            parts.append(f"from the {tables[0]} table")
        elif len(tables) > 1:
            parts.append(f"from {len(tables)} tables: {', '.join(tables)}")
        
        # Aggregations
        if aggregations:
            agg_str = ', '.join(aggregations)
            parts.append(f"using {agg_str}")
        
        # Filters
        filters = plan.get("filters", [])
        if filters:
            parts.append(f"with {len(filters)} filter(s)")
        
        # Ordering
        ordering = plan.get("ordering", [])
        if ordering:
            parts.append(f"sorted by {', '.join(ordering)}")
        
        # Limit
        limit = plan.get("limit")
        if limit:
            parts.append(f"limited to {limit} rows")
        
        return " ".join(parts) + "."
    
    @staticmethod
    def explain_error(error_type: str, error_msg: str) -> str:
        """
        Generate user-friendly error explanation.
        
        Args:
            error_type: Type of error
            error_msg: Raw error message
            
        Returns:
            Friendly explanation
        """
        explanations = {
            "TABLE_NOT_FOUND": "The query references a table that doesn't exist in the database.",
            "COLUMN_NOT_FOUND": "The query references a column that doesn't exist in the specified table.",
            "SYNTAX_ERROR": "The SQL query has a syntax error and needs to be corrected.",
            "AMBIGUOUS_COLUMN": "A column name is ambiguous because it exists in multiple tables. Table aliases are needed.",
            "TYPE_MISMATCH": "There's a data type mismatch in the query (e.g., comparing a number to text).",
            "TIMEOUT": "The query took too long to execute and was cancelled.",
            "GROUP_BY_ERROR": "When using aggregation functions, all non-aggregated columns must be in GROUP BY.",
            "SAFETY_VIOLATION": "The query was blocked for safety reasons (e.g., attempting to modify data)."
        }
        
        explanation = explanations.get(error_type, "An error occurred while executing the query.")
        return f"{explanation}\n\nTechnical details: {error_msg}"
