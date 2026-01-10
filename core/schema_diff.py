"""
Schema diff and evolution detection.
Tracks schema changes over time.
"""
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging

from core.schema_info import DatabaseSchema, TableInfo, ColumnInfo

logger = logging.getLogger(__name__)


@dataclass
class SchemaChange:
    """Represents a schema change."""
    change_type: str  # 'table_added', 'table_removed', 'column_added', 'column_removed', etc.
    table_name: str
    column_name: Optional[str] = None
    details: Optional[Dict] = None


class SchemaDiff:
    """Computes differences between two schemas."""
    
    @staticmethod
    def compute_diff(old_schema: DatabaseSchema, new_schema: DatabaseSchema) -> List[SchemaChange]:
        """
        Compute differences between two schemas.
        
        Args:
            old_schema: Previous schema version
            new_schema: Current schema version
            
        Returns:
            List of SchemaChange objects
        """
        changes = []
        
        old_tables = set(old_schema.tables.keys())
        new_tables = set(new_schema.tables.keys())
        
        # Tables added
        for table_name in new_tables - old_tables:
            changes.append(SchemaChange(
                change_type="table_added",
                table_name=table_name
            ))
        
        # Tables removed
        for table_name in old_tables - new_tables:
            changes.append(SchemaChange(
                change_type="table_removed",
                table_name=table_name
            ))
        
        # Tables modified
        common_tables = old_tables & new_tables
        for table_name in common_tables:
            table_changes = SchemaDiff._diff_table(
                old_schema.tables[table_name],
                new_schema.tables[table_name]
            )
            changes.extend(table_changes)
        
        return changes
    
    @staticmethod
    def _diff_table(old_table: TableInfo, new_table: TableInfo) -> List[SchemaChange]:
        """Diff a single table."""
        changes = []
        
        old_columns = {col.name: col for col in old_table.columns}
        new_columns = {col.name: col for col in new_table.columns}
        
        # Columns added
        for col_name in new_columns.keys() - old_columns.keys():
            changes.append(SchemaChange(
                change_type="column_added",
                table_name=old_table.name,
                column_name=col_name
            ))
        
        # Columns removed
        for col_name in old_columns.keys() - new_columns.keys():
            changes.append(SchemaChange(
                change_type="column_removed",
                table_name=old_table.name,
                column_name=col_name
            ))
        
        # Columns modified
        common_columns = old_columns.keys() & new_columns.keys()
        for col_name in common_columns:
            old_col = old_columns[col_name]
            new_col = new_columns[col_name]
            
            if old_col.data_type != new_col.data_type:
                changes.append(SchemaChange(
                    change_type="column_type_changed",
                    table_name=old_table.name,
                    column_name=col_name,
                    details={"old_type": old_col.data_type, "new_type": new_col.data_type}
                ))
        
        return changes
    
    @staticmethod
    def has_breaking_changes(changes: List[SchemaChange]) -> bool:
        """Check if changes include breaking changes."""
        breaking_types = {
            "table_removed",
            "column_removed",
            "column_type_changed"
        }
        
        return any(change.change_type in breaking_types for change in changes)
