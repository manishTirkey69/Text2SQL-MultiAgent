"""
Schema embeddings for semantic search.
Generates embeddings for tables and columns for similarity matching.
"""
from typing import List, Tuple, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

from core.schema_info import DatabaseSchema, TableInfo

logger = logging.getLogger(__name__)


class SchemaEmbeddings:
    """Manages semantic embeddings for schema elements."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", device: str = "cpu"):
        """
        Initialize embeddings model.
        
        Args:
            model_name: SentenceTransformer model name
            device: Device to run on ('cpu' or 'cuda')
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        self.model_name = model_name
        
        # Storage for embeddings
        self.table_embeddings: Dict[str, np.ndarray] = {}
        self.table_boost_scores: Dict[str, float] = {}
    
    def embed_schema(self, schema: DatabaseSchema):
        """
        Generate embeddings for all tables in schema.
        
        Args:
            schema: DatabaseSchema to embed
        """
        logger.info(f"Generating embeddings for {len(schema.tables)} tables...")
        
        for table_name, table_info in schema.tables.items():
            self.embed_table(table_info)
        
        logger.info("Schema embedding complete")
    
    def embed_table(self, table: TableInfo):
        """
        Generate embedding for a single table.
        
        Args:
            table: TableInfo to embed
        """
        # Create text representation
        text_parts = [f"Table: {table.name}"]
        
        if table.comment:
            text_parts.append(table.comment)
        
        # Add column names and types
        col_descriptions = []
        for col in table.columns:
            col_desc = f"{col.name} {col.data_type}"
            if col.is_primary_key:
                col_desc += " primary key"
            if col.is_foreign_key:
                col_desc += " foreign key"
            col_descriptions.append(col_desc)
        
        text_parts.append("Columns: " + ", ".join(col_descriptions))
        
        # Generate embedding
        text = " ".join(text_parts)
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        self.table_embeddings[table.name] = embedding
        self.table_boost_scores[table.name] = 1.0  # Default boost
    
    def find_relevant_tables(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """
        Find tables most relevant to a query.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (table_name, similarity_score) tuples
        """
        if not self.table_embeddings:
            logger.warning("No table embeddings available")
            return []
        
        # Encode query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        # Calculate similarities
        similarities = []
        for table_name, table_embedding in self.table_embeddings.items():
            similarity = self._cosine_similarity(query_embedding, table_embedding)
            
            # Apply boost score
            boost = self.table_boost_scores.get(table_name, 1.0)
            similarity *= boost
            
            if similarity >= threshold:
                similarities.append((table_name, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def boost_table(self, table_name: str, factor: float = 1.1):
        """
        Boost a table's relevance score.
        
        Args:
            table_name: Table to boost
            factor: Boost factor (default 1.1 = 10% increase)
        """
        current_boost = self.table_boost_scores.get(table_name, 1.0)
        self.table_boost_scores[table_name] = current_boost * factor
        logger.debug(f"Boosted {table_name}: {current_boost} -> {self.table_boost_scores[table_name]}")
    
    def reset_boosts(self):
        """Reset all boost scores to 1.0."""
        for table_name in self.table_boost_scores:
            self.table_boost_scores[table_name] = 1.0
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
