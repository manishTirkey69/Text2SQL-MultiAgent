"""
Schema compression for LLM context optimization.
Reduces schema size while maintaining semantic information.
"""
from typing import Dict, List, Set, Optional, Any
import logging

from core.schema_info import DatabaseSchema, TableInfo, ColumnInfo
from core.graph_builder import SchemaGraph

logger = logging.getLogger(__name__)


class SchemaCompressor:
    """Compresses database schema for LLM context."""
    
    def __init__(self, schema: DatabaseSchema, graph: Optional[SchemaGraph] = None):
        """Initialize with schema and optional graph."""
        self.schema = schema
        self.graph = graph or SchemaGraph(schema)
    
    def compress_full_schema(self, detail_level: str = "medium") -> str:
        """
        Compress entire schema to text.
        
        Args:
            detail_level: 'low', 'medium', or 'high'
            
        Returns:
            Compressed schema string
        """
        lines = [f"# Database Schema: {self.schema.database_name}"]
        lines.append(f"Total Tables: {len(self.schema.tables)}\n")
        
        for table_name in sorted(self.schema.tables.keys()):
            table_info = self.schema.tables[table_name]
            lines.append(self._format_table(table_info, detail_level))
        
        return "\n".join(lines)
    
    def compress_relevant_schema(
        self,
        table_names: List[str],
        include_neighbors: bool = True,
        detail_level: str = "high"
    ) -> str:
        """
        Compress only relevant tables.
        
        Args:
            table_names: Tables to include
            include_neighbors: Include FK-related tables
            detail_level: Amount of detail
            
        Returns:
            Compressed schema string
        """
        # Collect tables to include
        tables_to_include = set(table_names)
        
        if include_neighbors:
            for table_name in table_names:
                # Add direct neighbors
                neighbors = self.graph.get_neighbors(table_name, direction="both")
                tables_to_include.update(neighbors)
        
        logger.info(f"Compressing {len(tables_to_include)} tables")
        
        lines = [f"# Relevant Schema ({len(tables_to_include)} tables)\n"]
        
        # Format primary tables
        lines.append("## Primary Tables:")
        for table_name in sorted(table_names):
            if table_name in self.schema.tables:
                table_info = self.schema.tables[table_name]
                lines.append(self._format_table(table_info, detail_level))
        
        # Format neighbor tables
        neighbor_tables = tables_to_include - set(table_names)
        if neighbor_tables:
            lines.append("\n## Related Tables:")
            for table_name in sorted(neighbor_tables):
                if table_name in self.schema.tables:
                    table_info = self.schema.tables[table_name]
                    lines.append(self._format_table(table_info, "low"))
        
        # Add relationship information
        lines.append("\n## Relationships:")
        for table_name in table_names:
            if table_name in self.schema.tables:
                table_info = self.schema.tables[table_name]
                for fk in table_info.foreign_keys:
                    if fk.referenced_table_name in tables_to_include:
                        fk_desc = (
                            f"- {table_name}.{', '.join(fk.column_names)} -> "
                            f"{fk.referenced_table_name}.{', '.join(fk.referenced_column_names)}"
                        )
                        lines.append(fk_desc)
        
        return "\n".join(lines)
    
    def _format_table(self, table: TableInfo, detail_level: str) -> str:
        """Format a single table based on detail level."""
        lines = [f"\n### Table: {table.name}"]
        
        if table.comment:
            lines.append(f"Description: {table.comment}")
        
        if detail_level == "low":
            # Just column names
            col_names = [col.name for col in table.columns[:5]]
            if len(table.columns) > 5:
                col_names.append(f"... +{len(table.columns) - 5} more")
            lines.append(f"Columns: {', '.join(col_names)}")
            
        elif detail_level == "medium":
            # Column names and types
            lines.append("Columns:")
            for col in table.columns:
                col_str = f"  - {col.name}: {col.data_type}"
                if col.is_primary_key:
                    col_str += " [PK]"
                if col.is_foreign_key:
                    col_str += " [FK]"
                lines.append(col_str)
                
        else:  # high
            # Full details
            lines.append("Columns:")
            for col in table.columns:
                col_str = f"  - {col.name}: {col.data_type}"
                if col.is_primary_key:
                    col_str += " [PK]"
                if col.is_foreign_key:
                    col_str += " [FK]"
                if not col.nullable:
                    col_str += " NOT NULL"
                if col.default_value:
                    col_str += f" DEFAULT {col.default_value}"
                if col.comment:
                    col_str += f" -- {col.comment}"
                lines.append(col_str)
            
            # Add constraints
            if table.foreign_keys:
                lines.append("Foreign Keys:")
                for fk in table.foreign_keys:
                    lines.append(
                        f"  - {', '.join(fk.column_names)} -> "
                        f"{fk.referenced_table_name}({', '.join(fk.referenced_column_names)})"
                    )
        
        if table.row_count > 0:
            lines.append(f"Row Count: ~{table.row_count:,}")
        
        return "\n".join(lines)
    
    def get_table_summary(self) -> Dict[str, Any]:
        """Get statistical summary of schema."""
        return {
            "total_tables": len(self.schema.tables),
            "total_columns": sum(len(t.columns) for t in self.schema.tables.values()),
            "total_fks": sum(len(t.foreign_keys) for t in self.schema.tables.values()),
            "total_rows": sum(t.row_count for t in self.schema.tables.values()),
            "tables_by_size": sorted(
                [(t.name, t.row_count) for t in self.schema.tables.values()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
