"""
Reasoning trace serialization for UI.
Converts internal reasoning structures to UI-friendly JSON.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ReasoningSerializer:
    """Serializes reasoning traces for UI consumption."""
    
    @staticmethod
    def serialize_feedback_trace(trace: Any) -> Dict[str, Any]:
        """
        Serialize feedback loop trace.
        
        Args:
            trace: FeedbackTrace object
            
        Returns:
            Serialized dictionary
        """
        return {
            "initial_sql": trace.initial_sql,
            "final_sql": trace.get_final_sql(),
            "success": trace.success,
            "total_attempts": trace.get_total_attempts(),
            "attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "sql": attempt.sql,
                    "critique": attempt.critique,
                    "execution": {
                        "success": attempt.execution_result.success if attempt.execution_result else None,
                        "row_count": attempt.execution_result.row_count if attempt.execution_result else 0,
                        "error": attempt.execution_result.error if attempt.execution_result else None,
                        "error_type": attempt.execution_result.error_type if attempt.execution_result else None,
                        "execution_time_ms": attempt.execution_result.execution_time_ms if attempt.execution_result else 0
                    } if attempt.execution_result else None,
                    "repair_applied": attempt.repair_applied
                }
                for attempt in trace.attempts
            ]
        }
    
    @staticmethod
    def serialize_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize query plan."""
        return {
            "query_type": plan.get("query_type"),
            "tables": plan.get("tables_needed", []),
            "complexity": plan.get("complexity", "MEDIUM"),
            "description": plan.get("description", ""),
            "joins_required": len(plan.get("tables_needed", [])) > 1,
            "aggregations": plan.get("aggregations", []),
            "estimated_difficulty": plan.get("complexity", "MEDIUM").lower()
        }
    
    @staticmethod
    def serialize_join_path(join_path: Any) -> Dict[str, Any]:
        """Serialize join path."""
        if not join_path:
            return {}
        
        return {
            "source": join_path.source_table,
            "target": join_path.target_table,
            "steps": [
                {
                    "from": step.from_table,
                    "to": step.to_table,
                    "join_type": step.join_type,
                    "on_columns": step.join_columns
                }
                for step in join_path.steps
            ],
            "total_cost": join_path.total_cost,
            "path_length": join_path.path_length
        }
