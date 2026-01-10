"""
Tests for graph builder.
"""
import pytest
from core.schema_info import DatabaseSchema, TableInfo, ColumnInfo, ForeignKeyInfo
from core.graph_builder import SchemaGraph


@pytest.fixture
def sample_schema_with_fks():
    """Create schema with foreign key relationships."""
    users_table = TableInfo(
        name="users",
        schema=None,
        columns=[
            ColumnInfo(name="user_id", data_type="INT", nullable=False, is_primary_key=True)
        ],
        primary_keys=["user_id"],
        foreign_keys=[],
        indexes=[],
        row_count=100
    )
    
    orders_table = TableInfo(
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
    
    schema = DatabaseSchema(
        database_name="test_db",
        schema_name=None,
        tables={"users": users_table, "orders": orders_table},
        version_hash="test",
        extracted_at="2026-01-10",
        database_type="postgresql"
    )
    
    return schema


def test_graph_creation(sample_schema_with_fks):
    """Test graph construction."""
    graph = SchemaGraph(sample_schema_with_fks)
    
    assert graph.graph.number_of_nodes() == 2
    assert graph.graph.number_of_edges() == 1


def test_get_neighbors(sample_schema_with_fks):
    """Test neighbor retrieval."""
    graph = SchemaGraph(sample_schema_with_fks)
    
    # Orders has outgoing edge to users
    neighbors_out = graph.get_neighbors("orders", direction="out")
    assert "users" in neighbors_out
    
    # Users has incoming edge from orders
    neighbors_in = graph.get_neighbors("users", direction="in")
    assert "orders" in neighbors_in


def test_get_edge_data(sample_schema_with_fks):
    """Test edge metadata retrieval."""
    graph = SchemaGraph(sample_schema_with_fks)
    
    edge = graph.get_edge_data("orders", "users")
    
    assert edge is not None
    assert edge.source_table == "orders"
    assert edge.target_table == "users"
    assert "user_id" in edge.fk_columns
