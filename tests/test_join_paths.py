"""
Tests for join path discovery.
"""
import pytest
from core.schema_info import DatabaseSchema, TableInfo, ColumnInfo, ForeignKeyInfo
from core.graph_builder import SchemaGraph
from core.join_paths import JoinPathFinder


@pytest.fixture
def multi_table_schema():
    """Create schema with multiple related tables."""
    users = TableInfo(
        name="users",
        schema=None,
        columns=[ColumnInfo(name="user_id", data_type="INT", nullable=False, is_primary_key=True)],
        primary_keys=["user_id"],
        foreign_keys=[],
        indexes=[],
        row_count=100
    )
    
    orders = TableInfo(
        name="orders",
        schema=None,
        columns=[
            ColumnInfo(name="order_id", data_type="INT", nullable=False, is_primary_key=True),
            ColumnInfo(name="user_id", data_type="INT", nullable=False, is_foreign_key=True)
        ],
        primary_keys=["order_id"],
        foreign_keys=[
            ForeignKeyInfo(
                constraint_name="fk_orders_users",
                table_name="orders",
                column_names=["user_id"],
                referenced_table_name="users",
                referenced_column_names=["user_id"]
            )
        ],
        indexes=[],
        row_count=500
    )
    
    order_items = TableInfo(
        name="order_items",
        schema=None,
        columns=[
            ColumnInfo(name="item_id", data_type="INT", nullable=False, is_primary_key=True),
            ColumnInfo(name="order_id", data_type="INT", nullable=False, is_foreign_key=True)
        ],
        primary_keys=["item_id"],
        foreign_keys=[
            ForeignKeyInfo(
                constraint_name="fk_items_orders",
                table_name="order_items",
                column_names=["order_id"],
                referenced_table_name="orders",
                referenced_column_names=["order_id"]
            )
        ],
        indexes=[],
        row_count=1000
    )
    
    schema = DatabaseSchema(
        database_name="test_db",
        schema_name=None,
        tables={"users": users, "orders": orders, "order_items": order_items},
        version_hash="test",
        extracted_at="2026-01-10",
        database_type="postgresql"
    )
    
    return schema


def test_find_direct_path(multi_table_schema):
    """Test finding direct join path."""
    graph = SchemaGraph(multi_table_schema)
    finder = JoinPathFinder(graph)
    
    path = finder.find_path("orders", "users")
    
    assert path is not None
    assert path.source_table == "orders"
    assert path.target_table == "users"
    assert len(path.steps) == 1


def test_find_multi_hop_path(multi_table_schema):
    """Test finding multi-hop join path."""
    graph = SchemaGraph(multi_table_schema)
    finder = JoinPathFinder(graph)
    
    path = finder.find_path("order_items", "users", max_hops=5)
    
    assert path is not None
    assert path.source_table == "order_items"
    assert path.target_table == "users"
    assert len(path.steps) == 2  # order_items -> orders -> users
