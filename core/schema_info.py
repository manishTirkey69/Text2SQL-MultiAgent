"""
Database schema introspection and extraction.
Provides classes and utilities for analyzing database structure.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import logging
from sqlalchemy import create_engine, inspect, MetaData, Table, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    nullable: bool = True
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    comment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "default_value": self.default_value,
            "is_primary_key": self.is_primary_key,
            "is_foreign_key": self.is_foreign_key,
            "comment": self.comment
        }


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key constraint."""
    constraint_name: str
    table_name: str
    column_names: List[str]
    referenced_table_name: str
    referenced_column_names: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "constraint_name": self.constraint_name,
            "table_name": self.table_name,
            "column_names": self.column_names,
            "referenced_table_name": self.referenced_table_name,
            "referenced_column_names": self.referenced_column_names
        }


@dataclass
class IndexInfo:
    """Information about a database index."""
    name: str
    column_names: List[str]
    unique: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "column_names": self.column_names,
            "unique": self.unique
        }


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    schema: Optional[str] = None
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    row_count: int = 0
    comment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "schema": self.schema,
            "columns": [col.to_dict() for col in self.columns],
            "primary_keys": self.primary_keys,
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "indexes": [idx.to_dict() for idx in self.indexes],
            "row_count": self.row_count,
            "comment": self.comment
        }


@dataclass
class DatabaseSchema:
    """Complete database schema representation."""
    database_name: str
    schema_name: Optional[str]
    tables: Dict[str, TableInfo]
    version_hash: str = ""
    extracted_at: str = ""
    database_type: str = "postgresql"
    
    def __post_init__(self):
        """Compute hash after initialization."""
        if not self.version_hash:
            self.version_hash = self.compute_hash()
        if not self.extracted_at:
            self.extracted_at = datetime.utcnow().isoformat()
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of schema."""
        # Create a simplified dict for hashing (exclude timestamps and counts)
        hash_dict = {
            "database_name": self.database_name,
            "schema_name": self.schema_name,
            "tables": {
                name: {
                    "name": table.name,
                    "columns": [col.name for col in table.columns],
                    "primary_keys": table.primary_keys,
                    "foreign_keys": [fk.constraint_name for fk in table.foreign_keys]
                }
                for name, table in self.tables.items()
            }
        }
        schema_str = json.dumps(hash_dict, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "database_name": self.database_name,
            "schema_name": self.schema_name,
            "tables": {name: table.to_dict() for name, table in self.tables.items()},
            "version_hash": self.version_hash,
            "extracted_at": self.extracted_at,
            "database_type": self.database_type
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseSchema':
        """Create from dictionary."""
        tables = {}
        for name, table_data in data.get("tables", {}).items():
            columns = [ColumnInfo(**col) for col in table_data.get("columns", [])]
            foreign_keys = [ForeignKeyInfo(**fk) for fk in table_data.get("foreign_keys", [])]
            
            # Handle indexes - they might be list of strings or list of dicts
            indexes = []
            for idx in table_data.get("indexes", []):
                if isinstance(idx, dict):
                    indexes.append(IndexInfo(**idx))
                elif isinstance(idx, str):
                    indexes.append(IndexInfo(name=idx, column_names=[]))
            
            tables[name] = TableInfo(
                name=table_data["name"],
                schema=table_data.get("schema"),
                columns=columns,
                primary_keys=table_data.get("primary_keys", []),
                foreign_keys=foreign_keys,
                indexes=indexes,
                row_count=table_data.get("row_count", 0),
                comment=table_data.get("comment")
            )
        
        return cls(
            database_name=data["database_name"],
            schema_name=data.get("schema_name"),
            tables=tables,
            version_hash=data.get("version_hash", ""),
            extracted_at=data.get("extracted_at", ""),
            database_type=data.get("database_type", "postgresql")
        )


class SchemaExtractor:
    """Extracts schema information from a database."""
    
    def __init__(self, engine: Engine):
        """
        Initialize schema extractor.
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
    
    def extract_full_schema(self, schema_name: Optional[str] = None) -> DatabaseSchema:
        """
        Extract complete schema from database.
        
        Args:
            schema_name: Optional schema name (for PostgreSQL)
            
        Returns:
            DatabaseSchema object
        """
        inspector = inspect(self.engine)
        
        # Get database name and type
        db_name = self.engine.url.database or "unknown"
        db_type = self.engine.dialect.name
        
        logger.info(f"Extracting schema from {db_type} database: {db_name}")
        
        tables: Dict[str, TableInfo] = {}
        
        # Get all table names
        try:
            table_names = inspector.get_table_names(schema=schema_name)
            logger.info(f"Found {len(table_names)} tables")
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            table_names = []
        
        # Extract each table
        for table_name in table_names:
            try:
                logger.debug(f"Extracting table: {table_name}")
                table_info = self._extract_table_info(inspector, table_name, schema_name)
                tables[table_name] = table_info
            except Exception as e:
                logger.warning(f"Failed to extract table {table_name}: {e}")
        
        schema = DatabaseSchema(
            database_name=db_name,
            schema_name=schema_name,
            tables=tables,
            database_type=db_type
        )
        
        logger.info(f"✅ Schema extraction complete: {len(tables)} tables")
        return schema
    
    def _extract_table_info(
        self,
        inspector: Any,
        table_name: str,
        schema: Optional[str]
    ) -> TableInfo:
        """Extract information for a single table."""
        columns = []
        primary_keys = []
        foreign_keys = []
        indexes = []
        
        # Get columns
        try:
            for col in inspector.get_columns(table_name, schema=schema):
                col_info = ColumnInfo(
                    name=col["name"],
                    data_type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    default_value=str(col.get("default", "")) if col.get("default") else None,
                    comment=col.get("comment")
                )
                columns.append(col_info)
        except Exception as e:
            logger.warning(f"Failed to get columns for {table_name}: {e}")
        
        # Get primary keys
        try:
            pk_constraint = inspector.get_pk_constraint(table_name, schema=schema)
            if pk_constraint and pk_constraint.get("constrained_columns"):
                primary_keys = pk_constraint["constrained_columns"]
                # Mark columns as primary keys
                for col_name in primary_keys:
                    for col in columns:
                        if col.name == col_name:
                            col.is_primary_key = True
        except Exception as e:
            logger.warning(f"Failed to get primary keys for {table_name}: {e}")
        
        # Get foreign keys
        try:
            fk_constraints = inspector.get_foreign_keys(table_name, schema=schema)
            for fk in fk_constraints:
                fk_info = ForeignKeyInfo(
                    constraint_name=fk.get("name", "") or f"fk_{table_name}",
                    table_name=table_name,
                    column_names=fk["constrained_columns"],
                    referenced_table_name=fk["referred_table"],
                    referenced_column_names=fk["referred_columns"]
                )
                foreign_keys.append(fk_info)
                
                # Mark columns as foreign keys
                for col_name in fk["constrained_columns"]:
                    for col in columns:
                        if col.name == col_name:
                            col.is_foreign_key = True
        except Exception as e:
            logger.warning(f"Failed to get foreign keys for {table_name}: {e}")
        
        # Get indexes
        try:
            table_indexes = inspector.get_indexes(table_name, schema=schema)
            for idx in table_indexes:
                if idx.get("name"):
                    idx_info = IndexInfo(
                        name=idx["name"],
                        column_names=idx.get("column_names", []),
                        unique=idx.get("unique", False)
                    )
                    indexes.append(idx_info)
        except Exception as e:
            logger.debug(f"Could not get indexes for {table_name}: {e}")
        
        # Get row count (approximate)
        row_count = 0
        try:
            # Build qualified table name
            if schema:
                # Use quoted identifiers for safety
                full_table_name = f'"{schema}"."{table_name}"'
            else:
                full_table_name = f'"{table_name}"'
            
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {full_table_name}"))
                row_count = result.scalar() or 0
        except Exception as e:
            logger.debug(f"Could not get row count for {table_name}: {e}")
            # Try without quotes as fallback
            try:
                fallback_name = f"{schema}.{table_name}" if schema else table_name
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {fallback_name}"))
                    row_count = result.scalar() or 0
            except Exception as e2:
                logger.debug(f"Fallback row count also failed for {table_name}: {e2}")
        
        # Get table comment
        comment = None
        try:
            table_comment = inspector.get_table_comment(table_name, schema=schema)
            comment = table_comment.get("text") if table_comment else None
        except Exception as e:
            logger.debug(f"Could not get comment for {table_name}: {e}")
        
        return TableInfo(
            name=table_name,
            schema=schema,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            row_count=row_count,
            comment=comment
        )
