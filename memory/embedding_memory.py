"""
Semantic memory using embeddings.
Stores and retrieves past successful queries based on semantic similarity.
"""
from typing import List, Tuple, Optional, Any
import numpy as np
import logging

from memory.query_memory import QueryTurn

logger = logging.getLogger(__name__)


class EmbeddingMemory:
    """Semantic memory for query patterns."""
    
    def __init__(self, embedding_model: Any):
        """
        Initialize with embedding model.
        
        Args:
            embedding_model: SentenceTransformer model
        """
        self.model = embedding_model
        self.query_embeddings: List[Tuple[QueryTurn, np.ndarray]] = []
    
    def add_successful_query(self, turn: QueryTurn):
        """
        Add a successful query to semantic memory.
        
        Args:
            turn: QueryTurn object
        """
        if not turn.success:
            logger.warning("Attempted to add unsuccessful query to memory")
            return
        
        # Generate embedding
        embedding = self.model.encode(turn.query, convert_to_numpy=True)
        self.query_embeddings.append((turn, embedding))
        
        logger.debug(f"Added query to semantic memory: {turn.query[:50]}...")
    
    def find_similar_queries(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.6
    ) -> List[Tuple[QueryTurn, float]]:
        """
        Find semantically similar past queries.
        
        Args:
            query: Query to match
            top_k: Number of results
            threshold: Minimum similarity
            
        Returns:
            List of (QueryTurn, similarity_score) tuples
        """
        if not self.query_embeddings:
            return []
        
        # Encode query
        query_emb = self.model.encode(query, convert_to_numpy=True)
        
        # Calculate similarities
        similarities = []
        for turn, emb in self.query_embeddings:
            similarity = self._cosine_similarity(query_emb, emb)
            if similarity >= threshold:
                similarities.append((turn, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def clear(self):
        """Clear semantic memory."""
        self.query_embeddings.clear()
        logger.info("Semantic memory cleared")
