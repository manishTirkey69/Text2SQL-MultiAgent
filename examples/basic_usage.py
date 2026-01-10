"""
Basic usage examples for Database Reasoning Engine.
"""
from main import DatabaseReasoningEngine


def main():
    # Initialize engine with connection string
    connection_string = "postgresql://dbuser:dbpass@localhost:5432/testdb"
    engine = DatabaseReasoningEngine(connection_string)
    
    print("=" * 70)
    print("Database Reasoning Engine - Basic Examples")
    print("=" * 70)
    
    # Example 1: Simple query
    print("\n[Example 1] Simple SELECT query")
    result = engine.query("Show me all users")
    print(f"Success: {result['success']}")
    print(f"SQL: {result['sql']}")
    print(f"Rows: {result['row_count']}")
    
    # Example 2: Aggregation query
    print("\n[Example 2] Aggregation query")
    result = engine.query("How many orders has each user placed?")
    print(f"Success: {result['success']}")
    print(f"SQL: {result['sql']}")
    if result['success']:
        print(f"Results: {result['results'][:3]}")  # First 3 rows
    
    # Example 3: Join query
    print("\n[Example 3] Join query")
    result = engine.query("Show me the products in order 1")
    print(f"Success: {result['success']}")
    print(f"SQL: {result['sql']}")
    
    # Example 4: Complex query with multiple tables
    print("\n[Example 4] Complex multi-table query")
    result = engine.query(
        "What are the top 5 products by total revenue?"
    )
    print(f"Success: {result['success']}")
    print(f"SQL: {result['sql']}")
    print(f"Attempts: {result['attempts']}")
    
    # Example 5: Conversational follow-up
    print("\n[Example 5] Conversational follow-up")
    result1 = engine.query("Show me all electronics products")
    print(f"Query 1 - Rows: {result1['row_count']}")
    
    result2 = engine.query("Which of those have more than 50 in stock?")
    print(f"Query 2 - SQL: {result2['sql']}")
    print(f"Query 2 - Rows: {result2['row_count']}")


if __name__ == "__main__":
    main()
