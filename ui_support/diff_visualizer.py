"""
SQL diff visualization utilities.
Formats SQL differences for UI display.
"""
from typing import List, Dict, Any
import difflib
import logging

logger = logging.getLogger(__name__)


class SQLDiffVisualizer:
    """Visualizes SQL differences."""
    
    @staticmethod
    def generate_diff(old_sql: str, new_sql: str) -> List[Dict[str, Any]]:
        """
        Generate line-by-line diff.
        
        Args:
            old_sql: Original SQL
            new_sql: Modified SQL
            
        Returns:
            List of diff lines with metadata
        """
        old_lines = old_sql.splitlines()
        new_lines = new_sql.splitlines()
        
        differ = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=3  # Context lines
        )
        
        diff_output = []
        for line in differ:
            if line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('-'):
                diff_output.append({
                    "type": "removed",
                    "content": line[1:],
                    "line": line
                })
            elif line.startswith('+'):
                diff_output.append({
                    "type": "added",
                    "content": line[1:],
                    "line": line
                })
            elif line.startswith('@@'):
                diff_output.append({
                    "type": "header",
                    "content": line,
                    "line": line
                })
            else:
                diff_output.append({
                    "type": "context",
                    "content": line,
                    "line": line
                })
        
        return diff_output
    
    @staticmethod
    def highlight_changes(old_sql: str, new_sql: str) -> Dict[str, Any]:
        """
        Highlight character-level changes.
        
        Args:
            old_sql: Original SQL
            new_sql: Modified SQL
            
        Returns:
            Dictionary with highlighted sections
        """
        s = difflib.SequenceMatcher(None, old_sql, new_sql)
        
        changes = {
            "old_highlighted": [],
            "new_highlighted": [],
            "change_summary": []
        }
        
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == 'replace':
                changes["change_summary"].append({
                    "type": "replace",
                    "old": old_sql[i1:i2],
                    "new": new_sql[j1:j2]
                })
            elif tag == 'delete':
                changes["change_summary"].append({
                    "type": "delete",
                    "old": old_sql[i1:i2]
                })
            elif tag == 'insert':
                changes["change_summary"].append({
                    "type": "insert",
                    "new": new_sql[j1:j2]
                })
        
        return changes
