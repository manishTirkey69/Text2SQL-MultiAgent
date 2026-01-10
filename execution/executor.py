"""
SQL execution with safety and timeout controls.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of SQL execution."""
    success: bool
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "error_type": self.error_type
        }


class SQLExecutor:
    """Executes SQL queries with safety controls."""
    
    def __init__(self, engine: Any, timeout_seconds: int = 30):
        """
        Initialize executor.
        
        Args:
            engine: SQLAlchemy engine
            timeout_seconds: Query timeout
        """
        self.engine = engine
        self.timeout_seconds = timeout_seconds
    
    def execute(self, sql: str) -> ExecutionResult:
        """
        Execute SQL query.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            ExecutionResult
        """
        start_time = time.time()
        
        try:
            with self.engine.connect() as connection:
                # Set statement timeout if supported
                if 'postgresql' in str(self.engine.url):
                    connection.execute(text(f"SET statement_timeout = {self.timeout_seconds * 1000}"))
                
                # Execute query
                result = connection.execute(text(sql))
                
                # Fetch results
                if result.returns_rows:
                    rows = [dict(row._mapping) for row in result.fetchall()]
                    row_count = len(rows)
                else:
                    rows = []
                    row_count = result.rowcount
                
                execution_time = (time.time() - start_time) * 1000
                
                logger.info(f"Query executed successfully: {row_count} rows in {execution_time:.2f}ms")
                
                return ExecutionResult(
                    success=True,
                    rows=rows,
                    row_count=row_count,
                    execution_time_ms=execution_time
                )
        
        except SQLAlchemyError as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            error_type = self._classify_error(error_msg)
            
            logger.error(f"SQL execution failed: {error_type} - {error_msg}")
            
            return ExecutionResult(
                success=False,
                rows=[],
                row_count=0,
                execution_time_ms=execution_time,
                error=error_msg,
                error_type=error_type
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"Unexpected execution error: {error_msg}")
            
            return ExecutionResult(
                success=False,
                rows=[],
                row_count=0,
                execution_time_ms=execution_time,
                error=error_msg,
                error_type="UNKNOWN"
            )
    
    def _classify_error(self, error_msg: str) -> str:
        """
        Classify SQL error type.
        
        Args:
            error_msg: Error message
            
        Returns:
            Error type string
        """
        error_msg_lower = error_msg.lower()
        
        if 'syntax' in error_msg_lower:
            return "SYNTAX_ERROR"
        elif 'does not exist' in error_msg_lower or 'not found' in error_msg_lower:
            if 'column' in error_msg_lower:
                return "COLUMN_NOT_FOUND"
            elif 'table' in error_msg_lower or 'relation' in error_msg_lower:
                return "TABLE_NOT_FOUND"
            else:
                return "OBJECT_NOT_FOUND"
        elif 'ambiguous' in error_msg_lower:
            return "AMBIGUOUS_COLUMN"
        elif 'type' in error_msg_lower and ('mismatch' in error_msg_lower or 'cannot' in error_msg_lower):
            return "TYPE_MISMATCH"
        elif 'permission' in error_msg_lower or 'denied' in error_msg_lower:
            return "PERMISSION_DENIED"
        elif 'timeout' in error_msg_lower or 'cancelled' in error_msg_lower:
            return "TIMEOUT"
        elif 'group by' in error_msg_lower:
            return "GROUP_BY_ERROR"
        elif 'aggregate' in error_msg_lower:
            return "AGGREGATION_ERROR"
        else:
            return "EXECUTION_ERROR"
