"""
Tests for schema introspection.
"""
import pytest
from unittest.mock import Mock, patch
from core.schema_info import (
    SchemaExtractor,
    DatabaseSchema,
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo
)


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine."""
    engine = Mock()
    engine.url.database = "test_db"
    engine.dialect.name = "postgresql"
    return engine


@pytest.fixture
def sample_schema():
    """Sample database schema."""
    columns = [
        ColumnInfo(
            name="user_id",
            data_type="INTEGER",
            nullable=False,
            is_primary_key=True
        ),
        ColumnInfo(
            name="username",
            data_type="VARCHAR(50)",
            nullable=False
        ),
        ColumnInfo(
            name="email",
            data_type="VARCHAR(100)",
            nullable=True
        )
    ]
    
    table = TableInfo(
        name="users",
        schema="public",
        columns=columns,
        primary_keys=["user_id"],
        foreign_keys=[],
        indexes=[],
        row_count=1000
    )
    
    schema = DatabaseSchema(
        database_name="test_db",
        schema_name="public",
        tables={"users": table},
        version_hash="abc123",
        extracted_at="2026-01-10T12:00:00",
        database_type="postgresql"
    )
    
    return schema


def test_schema_to_dict(sample_schema):
    """Test schema serialization."""
    schema_dict = sample_schema.to_dict()
    
    assert schema_dict["database_name"] == "test_db"
    assert "users" in schema_dict["tables"]
    assert len(schema_dict["tables"]["users"]["columns"]) == 3


def test_schema_to_json(sample_schema):
    """Test JSON serialization."""
    json_str = sample_schema.to_json()
    
    assert "test_db" in json_str
    assert "users" in json_str
    assert "user_id" in json_str


def test_schema_from_dict(sample_schema):
    """Test schema deserialization."""
    schema_dict = sample_schema.to_dict()
    restored = DatabaseSchema.from_dict(schema_dict)
    
    assert restored.database_name == sample_schema.database_name
    assert len(restored.tables) == len(sample_schema.tables)
    assert "users" in restored.tables


def test_compute_hash(sample_schema):
    """Test deterministic hash computation."""
    hash1 = sample_schema.compute_hash()
    hash2 = sample_schema.compute_hash()
    
    assert hash1 == hash2
    assert len(hash1) == 16  # SHA256 truncated to 16 chars


def test_hash_changes_with_schema():
    """Test that hash changes when schema changes."""
    schema1 = DatabaseSchema(
        database_name="db",
        schema_name=None,
        tables={
            "users": TableInfo(
                name="users",
                schema=None,
                columns=[ColumnInfo(name="id", data_type="INT", nullable=False)],
                primary_keys=["id"],
                foreign_keys=[],
                indexes=[]
            )
        },
        version_hash="",
        extracted_at="2026-01-10",
        database_type="postgresql"
    )
    
    schema2 = DatabaseSchema(
        database_name="db",
        schema_name=None,
        tables={
            "users": TableInfo(
                name="users",
                schema=None,
                columns=[
                    ColumnInfo(name="id", data_type="INT", nullable=False),
                    ColumnInfo(name="name", data_type="VARCHAR", nullable=True)
                ],
                primary_keys=["id"],
                foreign_keys=[],
                indexes=[]
            )
        },
        version_hash="",
        extracted_at="2026-01-10",
        database_type="postgresql"
    )
    
    hash1 = schema1.compute_hash()
    hash2 = schema2.compute_hash()
    
    assert hash1 != hash2
