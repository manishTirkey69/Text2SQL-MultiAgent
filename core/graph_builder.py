"""
Schema graph builder.
Constructs graph representation of foreign key relationships.
"""
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import networkx as nx
import logging

from core.schema_info import DatabaseSchema, ForeignKeyInfo

logger = logging.getLogger(__name__)


@dataclass
class GraphEdge:
    """Represents an edge in the schema graph."""
    source_table: str
    target_table: str
    fk_columns: List[str]
    referenced_columns: List[str]
    constraint_name: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "source_table": self.source_table,
            "target_table": self.target_table,
            "fk_columns": self.fk_columns,
            "referenced_columns": self.referenced_columns,
            "constraint_name": self.constraint_name
        }


class SchemaGraph:
    """Graph representation of database schema relationships."""
    
    def __init__(self, schema: DatabaseSchema):
        """
        Initialize schema graph.
        
        Args:
            schema: DatabaseSchema to build graph from
        """
        self.schema = schema
        self.graph = nx.DiGraph()
        self._build_graph()
    
    def _build_graph(self):
        """Build graph from schema."""
        # Add all tables as nodes
        for table_name in self.schema.tables.keys():
            self.graph.add_node(table_name)
        
        # Add edges from foreign keys
        for table_name, table_info in self.schema.tables.items():
            for fk in table_info.foreign_keys:
                edge = GraphEdge(
                    source_table=table_name,
                    target_table=fk.referenced_table_name,
                    fk_columns=fk.column_names,
                    referenced_columns=fk.referenced_column_names,
                    constraint_name=fk.constraint_name
                )
                
                # Add edge with metadata
                self.graph.add_edge(
                    table_name,
                    fk.referenced_table_name,
                    edge_data=edge
                )
        
        logger.info(f"Built graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def get_neighbors(self, table_name: str, direction: str = "both") -> List[str]:
        """
        Get neighboring tables.
        
        Args:
            table_name: Table name
            direction: 'in', 'out', or 'both'
            
        Returns:
            List of neighbor table names
        """
        if table_name not in self.graph:
            return []
        
        neighbors = set()
        
        if direction in ("out", "both"):
            neighbors.update(self.graph.successors(table_name))
        
        if direction in ("in", "both"):
            neighbors.update(self.graph.predecessors(table_name))
        
        return list(neighbors)
    
    def get_edge_data(self, source: str, target: str) -> Optional[GraphEdge]:
        """Get edge data between two tables."""
        if not self.graph.has_edge(source, target):
            return None
        
        return self.graph[source][target].get("edge_data")
    
    def get_table_degree(self, table_name: str) -> Tuple[int, int]:
        """
        Get in-degree and out-degree of a table.
        
        Returns:
            Tuple of (in_degree, out_degree)
        """
        if table_name not in self.graph:
            return (0, 0)
        
        return (self.graph.in_degree(table_name), self.graph.out_degree(table_name))
    
    def get_hub_tables(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Get tables with most connections (hubs).
        
        Args:
            top_n: Number of top hubs to return
            
        Returns:
            List of (table_name, degree) tuples
        """
        degrees = [
            (node, self.graph.in_degree(node) + self.graph.out_degree(node))
            for node in self.graph.nodes()
        ]
        degrees.sort(key=lambda x: x[1], reverse=True)
        return degrees[:top_n]
    
    def get_root_tables(self) -> List[str]:
        """Get tables with no outgoing foreign keys (roots)."""
        return [node for node in self.graph.nodes() if self.graph.out_degree(node) == 0]
    
    def get_leaf_tables(self) -> List[str]:
        """Get tables with no incoming foreign keys (leaves)."""
        return [node for node in self.graph.nodes() if self.graph.in_degree(node) == 0]
    
    def find_path(self, source: str, target: str, max_hops: int = 5) -> Optional[List[str]]:
        """
        Find shortest path between two tables.
        
        Args:
            source: Source table name
            target: Target table name
            max_hops: Maximum path length
            
        Returns:
            List of table names in path, or None if no path exists
        """
        if source not in self.graph or target not in self.graph:
            return None
        
        try:
            path = nx.shortest_path(self.graph, source, target)
            if len(path) - 1 > max_hops:
                return None
            return path
        except nx.NetworkXNoPath:
            return None
    
    def has_cycle(self) -> bool:
        """Check if graph has cycles."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return len(cycles) > 0
        except:
            return False
