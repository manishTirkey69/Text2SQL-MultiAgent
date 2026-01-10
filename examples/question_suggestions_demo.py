"""
Demo script for question suggestion feature.
"""
from main import DatabaseReasoningEngine


def main():
    # Initialize engine
    connection_string = "postgresql://dbuser:dbpass@localhost:5432/testdb"
    engine = DatabaseReasoningEngine(connection_string)
    
    print("=" * 80)
    print("QUESTION SUGGESTION AGENT - Demo")
    print("=" * 80)
    
    # Example 1: Template-based suggestions (fast, no LLM cost)
    print("\n[Example 1] Template-based suggestions (Fast)")
    print("-" * 80)
    suggestions = engine.get_question_suggestions(count=10, use_llm=False)
    
    for i, suggestion in enumerate(suggestions, 1):
        complexity = suggestion['complexity']
        q_type = suggestion['type']
        tables = suggestion.get('tables', [])
        
        emoji = "🟢" if complexity == "low" else "🟡" if complexity == "medium" else "🔴"
        
        print(f"\n{i}. {emoji} [{q_type.upper()}]")
        print(f"   {suggestion['question']}")
        if tables:
            print(f"   📊 Tables: {', '.join(tables)}")
        print(f"   🎯 Complexity: {complexity}")
    
    # Example 2: LLM-based suggestions (slower, higher quality)
    print("\n\n[Example 2] LLM-based suggestions (High Quality)")
    print("-" * 80)
    print("Generating with LLM... (this may take a few seconds)")
    
    suggestions = engine.get_question_suggestions(count=5, use_llm=True)
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['question']}")
        print(f"   Tables: {', '.join(suggestion.get('tables', []))}")
        print(f"   Type: {suggestion.get('type', 'general')}")
    
    # Example 3: Use a suggestion to query
    print("\n\n[Example 3] Using a suggestion")
    print("-" * 80)
    
    if suggestions:
        sample_question = suggestions[0]['question']
        print(f"Executing: {sample_question}")
        
        result = engine.query(sample_question)
        
        if result['success']:
            print(f"\n✓ Success!")
            print(f"SQL: {result['sql']}")
            print(f"Rows: {result['row_count']}")
        else:
            print(f"\n✗ Failed: {result.get('error')}")


if __name__ == "__main__":
    main()
