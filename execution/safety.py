"""
SQL safety validator.
Enforces read-only policy and blocks dangerous operations.
"""
from typing import List, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class SafetyValidator:
    """Validates SQL queries for safety."""
    
    def __init__(
        self,
        enforce_readonly: bool = True,
        blocked_keywords: Optional[List[str]] = None,
        max_rows: int = 10000
    ):
        """
        Initialize safety validator.
        
        Args:
            enforce_readonly: Block all mutating operations
            blocked_keywords: List of blocked SQL keywords
            max_rows: Maximum rows to return
        """
        self.enforce_readonly = enforce_readonly
        self.max_rows = max_rows
        
        self.blocked_keywords = blocked_keywords or [
            'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE',
            'ALTER', 'CREATE', 'REPLACE', 'GRANT', 'REVOKE',
            'EXEC', 'EXECUTE', 'CALL'
        ]
        
        # Dangerous patterns
        self.dangerous_patterns = [
            r'\bINTO\s+OUTFILE\b',  # File writes
            r'\bLOAD\s+DATA\b',      # Data loading
            r'\bLOAD_FILE\b',        # File operations
            r';\s*\w+',              # Multiple statements
        ]
    
    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        sql_upper = sql.upper().strip()
        
        # Check if it's a SELECT query
        if self.enforce_readonly:
            if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
                return False, "Only SELECT queries are allowed (read-only mode)"
        
        # Check for blocked keywords
        for keyword in self.blocked_keywords:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return False, f"Blocked keyword detected: {keyword}"
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return False, f"Dangerous pattern detected: {pattern}"
        
        # Check for multiple statements (basic)
        if sql.count(';') > 1:
            return False, "Multiple SQL statements not allowed"
        
        # Auto-add LIMIT if missing and enforcing
        if 'LIMIT' not in sql_upper and self.max_rows:
            logger.warning(f"No LIMIT clause found, will enforce max_rows={self.max_rows}")
        
        return True, None
    
    def enforce_limit(self, sql: str) -> str:
        """
        Add LIMIT clause if missing.
        
        Args:
            sql: Original SQL
            
        Returns:
            SQL with LIMIT enforced
        """
        sql_upper = sql.upper()
        
        if 'LIMIT' in sql_upper:
            # Validate existing LIMIT
            limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
            if limit_match:
                existing_limit = int(limit_match.group(1))
                if existing_limit > self.max_rows:
                    # Replace with max_rows
                    sql = re.sub(
                        r'LIMIT\s+\d+',
                        f'LIMIT {self.max_rows}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    logger.warning(f"Reduced LIMIT from {existing_limit} to {self.max_rows}")
        else:
            # Add LIMIT
            sql = sql.rstrip(';').strip()
            sql += f'\nLIMIT {self.max_rows};'
            logger.info(f"Added LIMIT {self.max_rows}")
        
        return sql
    
    def sanitize_sql(self, sql: str) -> str:
        """
        Sanitize SQL query.
        
        Args:
            sql: Original SQL
            
        Returns:
            Sanitized SQL
        """
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        return sql
