"""
SQL execution with safety and timeout controls.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from execution.safety import SafetyValidator

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
    sanitized_sql: Optional[str] = None  # Track if SQL was sanitized
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "error_type": self.error_type,
            "sanitized_sql": self.sanitized_sql
        }


class SQLExecutor:
    """Executes SQL queries with safety controls."""
    
    def __init__(
        self, 
        engine: Any, 
        safety_validator: Optional[SafetyValidator] = None,
        timeout_seconds: int = 30
    ):
        """
        Initialize executor.
        
        Args:
            engine: SQLAlchemy engine
            safety_validator: Safety validator instance (optional)
            timeout_seconds: Query timeout
        """
        self.engine = engine
        self.timeout_seconds = timeout_seconds
        
        # Initialize safety validator if not provided
        if safety_validator is None:
            from config.settings import get_settings
            settings = get_settings()
            self.safety_validator = SafetyValidator(
                enforce_readonly=settings.safety.enforce_readonly,
                max_rows=settings.safety.max_rows
            )
        else:
            self.safety_validator = safety_validator
        
        logger.info(f"SQLExecutor initialized with max_rows={self.safety_validator.max_rows}")
    
    def execute(self, sql: str, skip_sanitization: bool = False) -> ExecutionResult:
        """
        Execute SQL query.
        
        Args:
            sql: SQL query to execute
            skip_sanitization: Skip safety sanitization (use with caution)
            
        Returns:
            ExecutionResult
        """
        start_time = time.time()
        original_sql = sql
        sanitized = False
        
        try:
            # Validate safety
            is_safe, violations = self.safety_validator.validate(sql)
            
            if not is_safe:
                execution_time = (time.time() - start_time) * 1000
                error_msg = f"SQL safety violation: {', '.join(violations)}"
                logger.error(error_msg)
                
                return ExecutionResult(
                    success=False,
                    rows=[],
                    row_count=0,
                    execution_time_ms=execution_time,
                    error=error_msg,
                    error_type="SAFETY_VIOLATION"
                )
            
            # Sanitize SQL (add LIMIT if needed)
            if not skip_sanitization:
                sql = self.safety_validator.sanitize_sql(sql)
                if sql != original_sql:
                    sanitized = True
                    logger.info(f"SQL sanitized: LIMIT {self.safety_validator.max_rows} added")
            
            # Execute query
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
                    execution_time_ms=execution_time,
                    sanitized_sql=sql if sanitized else None
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
