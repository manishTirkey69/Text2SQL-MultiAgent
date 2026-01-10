"""
Example API client for question suggestions.
"""
import requests
import json


def main():
    base_url = "http://localhost:8000"
    
    print("=" * 80)
    print("Question Suggestions API Demo")
    print("=" * 80)
    
    # Get suggestions
    print("\n1. Getting 10 question suggestions...")
    response = requests.post(
        f"{base_url}/suggestions",
        json={
            "count": 10,
            "use_llm": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Got {data['count']} suggestions\n")
        
        for i, suggestion in enumerate(data['suggestions'], 1):
            print(f"{i}. [{suggestion['type'].upper()}] {suggestion['question']}")
            print(f"   Complexity: {suggestion['complexity']}")
            print(f"   Tables: {', '.join(suggestion['tables'])}\n")
    else:
        print(f"✗ Error: {response.text}")
    
    # Refresh suggestions
    print("\n2. Refreshing suggestions (GET endpoint)...")
    response = requests.get(f"{base_url}/suggestions/refresh?count=5")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Refreshed with {data['count']} new suggestions\n")
        
        for i, suggestion in enumerate(data['suggestions'], 1):
            print(f"{i}. {suggestion['question']}")
    
    # Filter by complexity
    print("\n3. Getting only 'low' complexity questions...")
    response = requests.post(
        f"{base_url}/suggestions",
        json={
            "count": 20,
            "use_llm": False,
            "complexity_filter": "low"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Got {data['count']} low-complexity suggestions\n")
        
        for suggestion in data['suggestions'][:5]:
            print(f"  • {suggestion['question']}")
    
    # Execute a suggestion
    if response.status_code == 200 and data['suggestions']:
        print("\n4. Executing a suggested question...")
        sample_question = data['suggestions'][0]['question']
        
        query_response = requests.post(
            f"{base_url}/query",
            json={
                "query": sample_question,
                "enable_repair": True
            }
        )
        
        if query_response.status_code == 200:
            result = query_response.json()
            print(f"Question: {sample_question}")
            print(f"Success: {result['success']}")
            if result['success']:
                print(f"Rows returned: {result['row_count']}")
                print(f"SQL: {result['sql']}")


if __name__ == "__main__":
    main()
