"""
Schema snapshot storage for evolution tracking.
Maintains historical schema versions for diff detection.
"""
from typing import Dict, List, Optional
from pathlib import Path
import json
import logging

from core.schema_info import DatabaseSchema

logger = logging.getLogger(__name__)


class SchemaSnapshotManager:
    """Manages schema snapshots."""
    
    def __init__(self, storage_dir: str = "./data/schema_snapshots"):
        """
        Initialize snapshot manager.
        
        Args:
            storage_dir: Directory to store snapshots
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots: Dict[str, DatabaseSchema] = {}
    
    def save_snapshot(self, schema: DatabaseSchema, label: Optional[str] = None):
        """
        Save schema snapshot.
        
        Args:
            schema: DatabaseSchema to snapshot
            label: Optional label (defaults to version_hash)
        """
        label = label or schema.version_hash
        
        # Save to memory
        self.snapshots[label] = schema
        
        # Save to disk
        filepath = self.storage_dir / f"{label}.json"
        with open(filepath, 'w') as f:
            f.write(schema.to_json())
        
        logger.info(f"Saved schema snapshot: {label}")
    
    def load_snapshot(self, label: str) -> Optional[DatabaseSchema]:
        """
        Load schema snapshot.
        
        Args:
            label: Snapshot label
            
        Returns:
            DatabaseSchema or None
        """
        # Check memory first
        if label in self.snapshots:
            return self.snapshots[label]
        
        # Load from disk
        filepath = self.storage_dir / f"{label}.json"
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
            schema = DatabaseSchema.from_dict(data)
            self.snapshots[label] = schema
            return schema
        
        logger.warning(f"Snapshot not found: {label}")
        return None
    
    def list_snapshots(self) -> List[str]:
        """List all available snapshots."""
        snapshots = set(self.snapshots.keys())
        
        # Add disk snapshots
        for filepath in self.storage_dir.glob("*.json"):
            snapshots.add(filepath.stem)
        
        return sorted(snapshots)
    
    def get_latest_snapshot(self) -> Optional[DatabaseSchema]:
        """Get the most recent snapshot."""
        snapshots = self.list_snapshots()
        if snapshots:
            return self.load_snapshot(snapshots[-1])
        return None
