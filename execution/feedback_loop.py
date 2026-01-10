"""
Execution feedback loop with self-correction.
Orchestrates execution, critique, and repair cycles.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

from execution.executor import SQLExecutor, ExecutionResult
from agents.base_agent import AgentContext

logger = logging.getLogger(__name__)


@dataclass
class ExecutionAttempt:
    """Single execution attempt."""
    attempt_number: int
    sql: str
    critique: Optional[Dict[str, Any]] = None
    execution_result: Optional[ExecutionResult] = None
    repair_applied: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "attempt_number": self.attempt_number,
            "sql": self.sql,
            "critique": self.critique,
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "repair_applied": self.repair_applied
        }


@dataclass
class FeedbackTrace:
    """Complete feedback loop trace."""
    initial_sql: str
    attempts: List[ExecutionAttempt] = field(default_factory=list)
    success: bool = False
    final_sql: Optional[str] = None
    final_result: Optional[ExecutionResult] = None
    
    def add_attempt(self, attempt: ExecutionAttempt):
        """Add an execution attempt."""
        self.attempts.append(attempt)
    
    def get_final_sql(self) -> str:
        """Get the final SQL."""
        return self.final_sql or self.initial_sql
    
    def get_final_result(self) -> Optional[ExecutionResult]:
        """Get final execution result."""
        return self.final_result
    
    def get_total_attempts(self) -> int:
        """Get total number of attempts."""
        return len(self.attempts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "initial_sql": self.initial_sql,
            "attempts": [a.to_dict() for a in self.attempts],
            "success": self.success,
            "final_sql": self.final_sql,
            "final_result": self.final_result.to_dict() if self.final_result else None,
            "total_attempts": len(self.attempts)
        }


class FeedbackLoopOrchestrator:
    """Manages execution feedback and self-correction."""
    
    def __init__(
        self,
        sql_executor: SQLExecutor,
        sql_critic: Any,
        sql_repair: Any,
        max_retries: int = 3
    ):
        """
        Initialize feedback loop.
        
        Args:
            sql_executor: SQL executor
            sql_critic: SQL critic agent
            sql_repair: SQL repair agent
            max_retries: Maximum repair attempts
        """
        self.executor = sql_executor
        self.critic_agent = sql_critic
        self.repair_agent = sql_repair
        self.max_retries = max_retries
    
    def execute_with_feedback(
        self,
        sql: str,
        schema: str,
        original_query: str,
        enable_repair: bool = True,
        max_retries: Optional[int] = None
    ) -> FeedbackTrace:
        """
        Execute SQL with feedback loop.
        
        Args:
            sql: Initial SQL query
            schema: Compressed schema string
            original_query: Original natural language query
            enable_repair: Attempt repairs on failure
            max_retries: Override max retries
            
        Returns:
            FeedbackTrace with complete execution history
        """
        max_attempts = max_retries if max_retries is not None else self.max_retries
        trace = FeedbackTrace(initial_sql=sql)
        current_sql = sql
        attempt_num = 1
        
        logger.info(f"Starting feedback loop (max retries: {max_attempts})")
        
        # Create context for agents
        context = AgentContext(
            query=original_query,
            schema=schema,
            relevant_tables=[],
            conversation_history=[],
            metadata={}
        )
        
        while attempt_num <= max_attempts + 1:
            logger.info(f"Attempt {attempt_num}/{max_attempts + 1}")
            
            attempt = ExecutionAttempt(
                attempt_number=attempt_num,
                sql=current_sql
            )
            
            # Execute SQL
            exec_result = self.executor.execute(current_sql)
            attempt.execution_result = exec_result
            trace.add_attempt(attempt)
            
            if exec_result.success:
                # Success!
                logger.info(f"✓ Execution successful on attempt {attempt_num}")
                trace.success = True
                trace.final_sql = current_sql
                trace.final_result = exec_result
                break
            
            else:
                # Execution failed
                logger.error(f"✗ Execution failed: {exec_result.error}")
                
                # Try repair if enabled and retries remaining
                if enable_repair and attempt_num <= max_attempts:
                    logger.info(f"Attempting repair (attempt {attempt_num}/{max_attempts})...")
                    
                    repaired_sql = self._run_repair(
                        original_sql=current_sql,
                        error=exec_result.error,
                        error_type=exec_result.error_type or "UNKNOWN",
                        context=context
                    )
                    
                    if repaired_sql and repaired_sql != current_sql:
                        logger.info(f"✓ Repair generated new SQL")
                        current_sql = repaired_sql
                        attempt.repair_applied = True
                        attempt_num += 1
                        continue
                    else:
                        logger.warning("⚠ Repair failed or produced same SQL")
                        trace.final_sql = current_sql
                        trace.final_result = exec_result
                        break
                else:
                    logger.error(f"❌ No more retries available")
                    trace.final_sql = current_sql
                    trace.final_result = exec_result
                    break
        
        # Log final status
        if trace.success:
            logger.info(f"✓ Feedback loop succeeded after {trace.get_total_attempts()} attempts")
        else:
            logger.error(f"✗ Feedback loop failed after {trace.get_total_attempts()} attempts")
        
        return trace
    
    def _run_critique(self, sql: str, context: AgentContext) -> Dict[str, Any]:
        """Run critique on SQL."""
        try:
            context.metadata['sql'] = sql
            critique_response = self.critic_agent.execute(context)
            
            if critique_response.success:
                return critique_response.output
            else:
                logger.error(f"Critique agent failed: {critique_response.error}")
                return {"approved": True, "explanation": "Critique skipped due to error"}
        
        except Exception as e:
            logger.error(f"Critique failed: {e}")
            return {"approved": True, "explanation": "Critique skipped due to exception"}
    
    def _run_repair(
        self,
        original_sql: str,
        error: str,
        error_type: str,
        context: AgentContext
    ) -> Optional[str]:
        """Run repair agent."""
        try:
            # Format repair context
            repair_context = AgentContext(
                query=context.query,
                schema=context.schema,
                relevant_tables=context.relevant_tables,
                conversation_history=context.conversation_history,
                metadata={
                    'original_sql': original_sql,
                    'error': error,
                    'error_type': error_type,
                    'task': 'repair'
                }
            )
            
            repair_response = self.repair_agent.execute(repair_context)
            
            if repair_response.success:
                return repair_response.output
            else:
                logger.error(f"Repair agent failed: {repair_response.error}")
                return None
        
        except Exception as e:
            logger.error(f"Repair failed: {e}", exc_info=True)
            return None


# Alias for backward compatibility
FeedbackLoop = FeedbackLoopOrchestrator
