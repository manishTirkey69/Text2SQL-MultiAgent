"""
Federated query planner.
Plans queries across multiple databases.
"""
from typing import List, Dict, Any, Optional
import logging

from federation.db_registry import DatabaseRegistry

logger = logging.getLogger(__name__)


class FederatedPlanner:
    """Plans queries across multiple databases."""
    
    def __init__(self, registry: DatabaseRegistry):
        """
        Initialize federated planner.
        
        Args:
            registry: DatabaseRegistry instance
        """
        self.registry = registry
    
    def plan_federated_query(
        self,
        query: str,
        tables: List[str]
    ) -> Dict[str, Any]:
        """
        Plan a federated query.
        
        Args:
            query: Natural language query
            tables: Required tables
            
        Returns:
            Federated query plan
        """
        # Find which databases contain the tables
        table_mapping = {}
        for table_name in tables:
            dbs = self.registry.find_tables(table_name)
            if dbs:
                table_mapping[table_name] = dbs[0].database_id
        
        # Group tables by database
        db_groups: Dict[str, List[str]] = {}
        for table, db_id in table_mapping.items():
            if db_id not in db_groups:
                db_groups[db_id] = []
            db_groups[db_id].append(table)
        
        return {
            "strategy": "federated" if len(db_groups) > 1 else "single",
            "database_groups": db_groups,
            "requires_merge": len(db_groups) > 1
        }
