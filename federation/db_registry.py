"""
Multi-database registry.
Manages multiple database connections for federated queries.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from core.schema_info import DatabaseSchema
from core.graph_builder import SchemaGraph

logger = logging.getLogger(__name__)


@dataclass
class DatabaseRegistration:
    """Registration information for a database."""
    database_id: str
    connection_string: str
    db_name: str
    schema: DatabaseSchema
    graph: SchemaGraph
    description: Optional[str] = None


class DatabaseRegistry:
    """Manages multiple database registrations."""
    
    def __init__(self):
        """Initialize registry."""
        self.registrations: Dict[str, DatabaseRegistration] = {}
    
    def register_database(
        self,
        database_id: str,
        connection_string: str,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        description: Optional[str] = None
    ):
        """
        Register a database.
        
        Args:
            database_id: Unique identifier
            connection_string: SQLAlchemy connection string
            schema: DatabaseSchema instance
            graph: SchemaGraph instance
            description: Optional description
        """
        registration = DatabaseRegistration(
            database_id=database_id,
            connection_string=connection_string,
            db_name=schema.database_name,
            schema=schema,
            graph=graph,
            description=description
        )
        
        self.registrations[database_id] = registration
        logger.info(f"Registered database: {database_id} ({schema.database_name})")
    
    def get_database(self, database_id: str) -> Optional[DatabaseRegistration]:
        """Get database registration."""
        return self.registrations.get(database_id)
    
    def list_databases(self) -> List[DatabaseRegistration]:
        """List all registered databases."""
        return list(self.registrations.values())
    
    def unregister_database(self, database_id: str):
        """Unregister a database."""
        if database_id in self.registrations:
            del self.registrations[database_id]
            logger.info(f"Unregistered database: {database_id}")
    
    def find_tables(self, table_name: str) -> List[DatabaseRegistration]:
        """Find databases containing a table."""
        results = []
        for reg in self.registrations.values():
            if table_name in reg.schema.tables:
                results.append(reg)
        return results
