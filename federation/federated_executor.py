"""
Federated query executor.
Executes queries across multiple databases and merges results.
"""
from typing import List, Dict, Any, Optional
import logging

from federation.db_registry import DatabaseRegistry
from main import DatabaseReasoningEngine

logger = logging.getLogger(__name__)


class FederatedExecutor:
    """Executes queries across multiple databases."""
    
    def __init__(self, registry: DatabaseRegistry):
        """
        Initialize federated executor.
        
        Args:
            registry: DatabaseRegistry instance
        """
        self.registry = registry
        self.engines: Dict[str, DatabaseReasoningEngine] = {}
    
    def get_engine(self, database_id: str) -> DatabaseReasoningEngine:
        """Get or create engine for database."""
        if database_id not in self.engines:
            registration = self.registry.get_database(database_id)
            if not registration:
                raise ValueError(f"Database {database_id} not found")
            
            engine = DatabaseReasoningEngine(registration.connection_string)
            self.engines[database_id] = engine
        
        return self.engines[database_id]
    
    def execute_federated(
        self,
        query: str,
        database_groups: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Execute federated query.
        
        Args:
            query: Natural language query
            database_groups: Mapping of database_id to table lists
            
        Returns:
            Merged results
        """
        results = []
        
        for db_id, tables in database_groups.items():
            try:
                engine = self.get_engine(db_id)
                result = engine.query(query)
                
                if result['success']:
                    results.append({
                        'database_id': db_id,
                        'results': result.get('results', []),
                        'row_count': result.get('row_count', 0)
                    })
            except Exception as e:
                logger.error(f"Error executing on {db_id}: {e}")
        
        # Merge results (simple union for now)
        merged_results = []
        for r in results:
            merged_results.extend(r['results'])
        
        total_rows = sum(r['row_count'] for r in results)
        
        return {
            'success': len(results) > 0,
            'results': merged_results,
            'row_count': total_rows,
            'databases_queried': list(database_groups.keys())
        }
