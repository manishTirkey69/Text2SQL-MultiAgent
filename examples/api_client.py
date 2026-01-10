"""
Example API client for Database Reasoning Engine.
"""
import requests
import json


class DBReasoningClient:
    """Client for DB Reasoning Engine API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def health_check(self):
        """Check API health."""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def query(self, query: str, enable_repair: bool = True):
        """Execute natural language query."""
        payload = {
            "query": query,
            "enable_critique": True,
            "enable_repair": enable_repair,
            "max_retries": 3
        }
        
        response = requests.post(
            f"{self.base_url}/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
    
    def register_database(self, db_config: dict):
        """Register a new database."""
        response = requests.post(
            f"{self.base_url}/databases/register",
            json=db_config
        )
        return response.json()
    
    def list_databases(self):
        """List all registered databases."""
        response = requests.get(f"{self.base_url}/databases")
        return response.json()
    
    def get_schema(self, database_id: str = "default"):
        """Get schema information."""
        payload = {
            "database_id": database_id,
            "detail_level": "medium"
        }
        
        response = requests.post(
            f"{self.base_url}/schema",
            json=payload
        )
        return response.json()


def main():
    """Example usage."""
    client = DBReasoningClient()
    
    # Health check
    print("Health Check:")
    health = client.health_check()
    print(json.dumps(health, indent=2))
    
    # Execute query
    print("\n" + "=" * 70)
    print("Executing Query...")
    result = client.query("Show me the top 10 customers by order count")
    
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"SQL: {result['sql']}")
        print(f"Rows: {result['row_count']}")
        print(f"Execution Time: {result['execution_time_ms']:.2f}ms")
        
        if result.get('reasoning_trace'):
            print(f"Attempts: {result['reasoning_trace']['total_attempts']}")
    else:
        print(f"Error: {result.get('error')}")
    
    # Get schema info
    print("\n" + "=" * 70)
    print("Schema Information:")
    schema = client.get_schema()
    if schema['success']:
        print(f"Tables: {', '.join(schema['tables'])}")


if __name__ == "__main__":
    main()
