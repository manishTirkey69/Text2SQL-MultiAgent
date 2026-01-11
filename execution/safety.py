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
        
        logger.info(f"SafetyValidator initialized: readonly={enforce_readonly}, max_rows={max_rows}")
    
    def validate(self, sql: str) -> Tuple[bool, List[str]]:
        """
        Validate SQL query for safety.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_safe, list_of_violations)
        """
        violations = []
        sql_upper = sql.upper().strip()
        
        # Check if it's a SELECT query
        if self.enforce_readonly:
            if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
                violations.append("Only SELECT queries are allowed (read-only mode)")
        
        # Check for blocked keywords
        for keyword in self.blocked_keywords:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                violations.append(f"Blocked keyword detected: {keyword}")
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                violations.append(f"Dangerous pattern detected")
        
        # Check for multiple statements (basic)
        if sql.count(';') > 1:
            violations.append("Multiple SQL statements not allowed")
        
        is_safe = len(violations) == 0
        
        # Log violations
        if not is_safe:
            logger.warning(f"SQL safety violations: {violations}")
        
        return is_safe, violations
    
    def enforce_limit(self, sql: str) -> str:
        """
        Add LIMIT clause if missing or reduce if too high.
        
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
                    logger.debug(f"Existing LIMIT {existing_limit} is within max_rows")
        else:
            # Add LIMIT at the end
            sql = sql.rstrip(';').strip()
            sql += f' LIMIT {self.max_rows}'
            logger.info(f"Added LIMIT {self.max_rows} to query")
        
        return sql
    
    def sanitize_sql(self, sql: str) -> str:
        """
        Sanitize SQL query by removing comments, extra whitespace, and enforcing LIMIT.
        
        Args:
            sql: Original SQL
            
        Returns:
            Sanitized SQL with LIMIT enforced
        """
        # Remove single-line comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        
        # Remove multi-line comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Remove extra whitespace and normalize
        sql = ' '.join(sql.split())
        
        # Enforce LIMIT
        sql = self.enforce_limit(sql)
        
        return sql
    
    def validate_table_access(
        self,
        sql: str,
        allowed_tables: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate that SQL only accesses allowed tables.
        
        Args:
            sql: SQL query
            allowed_tables: List of allowed table names (None = all allowed)
            
        Returns:
            Tuple of (is_valid, list_of_unauthorized_tables)
        """
        if allowed_tables is None:
            return True, []
        
        # Extract table names from SQL
        referenced_tables = self._extract_table_names(sql)
        
        # Check for unauthorized tables
        unauthorized = [
            table for table in referenced_tables
            if table.lower() not in [t.lower() for t in allowed_tables]
        ]
        
        is_valid = len(unauthorized) == 0
        
        if not is_valid:
            logger.warning(f"Unauthorized table access: {unauthorized}")
        
        return is_valid, unauthorized
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """
        Extract table names from SQL query (simple regex-based).
        
        Args:
            sql: SQL query
            
        Returns:
            List of table names
        """
        table_names = []
        
        # FROM clause
        from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        table_names.extend(re.findall(from_pattern, sql, re.IGNORECASE))
        
        # JOIN clauses
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        table_names.extend(re.findall(join_pattern, sql, re.IGNORECASE))
        
        # Remove duplicates and return
        return list(set(table_names))
