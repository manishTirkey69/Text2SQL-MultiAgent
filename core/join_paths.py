"""
Join path discovery.
Finds optimal join paths between tables using graph algorithms.
"""
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import logging

from core.graph_builder import SchemaGraph, GraphEdge

logger = logging.getLogger(__name__)


@dataclass
class JoinStep:
    """Single step in a join path."""
    from_table: str
    to_table: str
    join_type: str = "INNER"
    join_columns: Dict[str, str] = field(default_factory=dict)  # {from_col: to_col}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from_table": self.from_table,
            "to_table": self.to_table,
            "join_type": self.join_type,
            "join_columns": self.join_columns
        }


@dataclass
class JoinPath:
    """Complete join path between tables."""
    source_table: str
    target_table: str
    steps: List[JoinStep] = field(default_factory=list)
    total_cost: float = 0.0
    estimated_rows: int = 0
    
    @property
    def path_length(self) -> int:
        """Get number of steps in path."""
        return len(self.steps)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_table": self.source_table,
            "target_table": self.target_table,
            "steps": [step.to_dict() for step in self.steps],
            "total_cost": self.total_cost,
            "estimated_rows": self.estimated_rows,
            "path_length": self.path_length
        }


class JoinPathFinder:
    """Finds optimal join paths between tables."""
    
    def __init__(self, graph: SchemaGraph):
        """
        Initialize join path finder.
        
        Args:
            graph: SchemaGraph instance
        """
        self.graph = graph
    
    def find_path(self, source: str, target: str, max_hops: int = 5) -> Optional[JoinPath]:
        """
        Find join path between two tables.
        
        Args:
            source: Source table name
            target: Target table name
            max_hops: Maximum number of hops
            
        Returns:
            JoinPath or None if no path exists
        """
        if source == target:
            return JoinPath(source_table=source, target_table=target)
        
        # Find shortest path in graph
        path_nodes = self.graph.find_path(source, target, max_hops)
        
        if not path_nodes:
            logger.warning(f"No path found from {source} to {target}")
            return None
        
        # Build join steps
        steps = []
        for i in range(len(path_nodes) - 1):
            from_table = path_nodes[i]
            to_table = path_nodes[i + 1]
            
            # Get edge data
            edge = self.graph.get_edge_data(from_table, to_table)
            if not edge:
                # Try reverse direction
                edge = self.graph.get_edge_data(to_table, from_table)
                if edge:
                    # Reverse the join
                    from_table, to_table = to_table, from_table
            
            if edge:
                # Build join columns mapping
                join_columns = {}
                for fk_col, ref_col in zip(edge.fk_columns, edge.referenced_columns):
                    join_columns[fk_col] = ref_col
                
                step = JoinStep(
                    from_table=from_table,
                    to_table=to_table,
                    join_type="INNER",
                    join_columns=join_columns
                )
                steps.append(step)
        
        # Calculate cost (simple heuristic)
        total_cost = self._calculate_path_cost(path_nodes)
        estimated_rows = self._estimate_rows(path_nodes)
        
        return JoinPath(
            source_table=source,
            target_table=target,
            steps=steps,
            total_cost=total_cost,
            estimated_rows=estimated_rows
        )
    
    def find_paths_for_tables(self, table_names: List[str], max_hops: int = 3) -> Dict[Tuple[str, str], JoinPath]:
        """
        Find join paths connecting multiple tables.
        
        Args:
            table_names: List of table names to connect
            max_hops: Maximum hops per path
            
        Returns:
            Dictionary mapping (source, target) tuples to JoinPath
        """
        paths = {}
        
        # Find paths between all pairs
        for i, source in enumerate(table_names):
            for target in table_names[i + 1:]:
                path = self.find_path(source, target, max_hops)
                if path:
                    paths[(source, target)] = path
                    # Also add reverse
                    reverse_path = self._reverse_path(path)
                    if reverse_path:
                        paths[(target, source)] = reverse_path
        
        return paths
    
    def _reverse_path(self, path: JoinPath) -> Optional[JoinPath]:
        """Reverse a join path."""
        reversed_steps = []
        for step in reversed(path.steps):
            reversed_step = JoinStep(
                from_table=step.to_table,
                to_table=step.from_table,
                join_type=step.join_type,
                join_columns={v: k for k, v in step.join_columns.items()}
            )
            reversed_steps.append(reversed_step)
        
        return JoinPath(
            source_table=path.target_table,
            target_table=path.source_table,
            steps=reversed_steps,
            total_cost=path.total_cost,
            estimated_rows=path.estimated_rows
        )
    
    def _calculate_path_cost(self, path_nodes: List[str]) -> float:
        """Calculate cost of a path (heuristic)."""
        cost = 0.0
        
        for i in range(len(path_nodes) - 1):
            from_table = path_nodes[i]
            to_table = path_nodes[i + 1]
            
            # Base cost per join
            cost += 1.0
            
            # Add cost based on table sizes (if available)
            if from_table in self.graph.schema.tables:
                from_rows = self.graph.schema.tables[from_table].row_count
                if from_rows > 0:
                    cost += min(from_rows / 1000000.0, 1.0)  # Cap at 1.0
        
        return cost
    
    def _estimate_rows(self, path_nodes: List[str]) -> int:
        """Estimate result rows for a path."""
        if not path_nodes:
            return 0
        
        # Simple heuristic: product of table sizes (capped)
        total_rows = 1
        for table_name in path_nodes:
            if table_name in self.graph.schema.tables:
                table_rows = self.graph.schema.tables[table_name].row_count
                if table_rows > 0:
                    total_rows *= min(table_rows, 10000)  # Cap individual tables
        
        return min(total_rows, 1000000)  # Cap total estimate
