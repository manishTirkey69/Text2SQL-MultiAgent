"""
Query memory for conversational context.
Maintains history of queries and results for multi-turn interactions.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueryTurn:
    """Single query-response turn."""
    turn_id: int
    query: str
    sql: str
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "turn_id": self.turn_id,
            "query": self.query,
            "sql": self.sql,
            "success": self.success,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class QueryMemory:
    """Manages conversational query history."""
    
    def __init__(self, max_history: int = 10):
        """
        Initialize query memory.
        
        Args:
            max_history: Maximum number of turns to retain
        """
        self.max_history = max_history
        self.history: List[QueryTurn] = []
        self.turn_counter = 0
    
    def add_turn(
        self,
        query: str,
        sql: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueryTurn:
        """
        Add a new query turn.
        
        Args:
            query: Natural language query
            sql: Generated SQL
            success: Whether execution succeeded
            metadata: Additional metadata
            
        Returns:
            QueryTurn object
        """
        self.turn_counter += 1
        
        turn = QueryTurn(
            turn_id=self.turn_counter,
            query=query,
            sql=sql,
            success=success,
            metadata=metadata or {}
        )
        
        self.history.append(turn)
        
        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        logger.debug(f"Added turn {turn.turn_id} to memory")
        
        return turn
    
    def get_recent_history(self, n: int = 3) -> List[QueryTurn]:
        """
        Get N most recent turns.
        
        Args:
            n: Number of turns to retrieve
            
        Returns:
            List of QueryTurn objects
        """
        return self.history[-n:] if self.history else []
    
    def get_all_history(self) -> List[QueryTurn]:
        """Get all history."""
        return self.history.copy()
    
    def find_similar_queries(self, query: str, limit: int = 3) -> List[QueryTurn]:
        """
        Find similar previous queries (simple string matching).
        
        Args:
            query: Query to match
            limit: Maximum results
            
        Returns:
            List of similar QueryTurn objects
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored = []
        for turn in self.history:
            turn_words = set(turn.query.lower().split())
            # Simple Jaccard similarity
            intersection = len(query_words & turn_words)
            union = len(query_words | turn_words)
            score = intersection / union if union > 0 else 0
            
            if score > 0.3:  # Threshold
                scored.append((score, turn))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [turn for _, turn in scored[:limit]]
    
    def get_last_successful_query(self) -> Optional[QueryTurn]:
        """Get the most recent successful query."""
        for turn in reversed(self.history):
            if turn.success:
                return turn
        return None
    
    def clear(self):
        """Clear all history."""
        self.history.clear()
        self.turn_counter = 0
        logger.info("Query memory cleared")
    
    def save(self, filepath: str):
        """Save memory to file."""
        data = {
            "turn_counter": self.turn_counter,
            "history": [turn.to_dict() for turn in self.history]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Memory saved to {filepath}")
    
    def load(self, filepath: str):
        """Load memory from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.turn_counter = data["turn_counter"]
        self.history = [
            QueryTurn(**turn_data) for turn_data in data["history"]
        ]
        
        logger.info(f"Memory loaded from {filepath}: {len(self.history)} turns")
