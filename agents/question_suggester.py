"""
Question suggestion agent.
Generates relevant natural language questions based on database schema.
"""
from typing import List, Dict, Any, Optional
import random
import logging
from collections import defaultdict

from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from core.schema_info import DatabaseSchema, TableInfo
from core.graph_builder import SchemaGraph

logger = logging.getLogger(__name__)


class QuestionSuggestionAgent(BaseAgent):
    """Agent that suggests relevant questions based on schema."""
    
    def __init__(self, llm_client: Any, model: Optional[str] = None):
        """Initialize question suggester."""
        super().__init__(llm_client, model)
        self.template_cache: List[str] = []
    
    def get_system_prompt(self) -> str:
        """Get system prompt for question generation."""
        return """You are an expert at generating relevant, insightful database questions.

Given a database schema with tables and columns, generate 10 natural language questions that would be valuable for data analysis.

Requirements:
- Questions should be realistic and business-oriented
- Mix different complexity levels (simple, aggregations, joins, time-series)
- Cover different tables in the schema
- Include various analysis types: counts, sums, trends, comparisons, rankings
- Make questions specific to the actual column names and tables
- Avoid generic questions - be specific to this schema

Output as JSON array:
[
  {
    "question": "What are the top 5 customers by total order value?",
    "complexity": "medium",
    "tables": ["customers", "orders"],
    "type": "aggregation"
  },
  ...
]

Question types:
- "simple": Single table, basic filtering
- "aggregation": COUNT, SUM, AVG, etc.
- "join": Multiple tables
- "time_series": Trends over time
- "comparison": Comparing groups
- "ranking": TOP N queries"""
    
    def generate_suggestions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        count: int = 10,
        use_llm: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate question suggestions.
        
        Args:
            schema: Database schema
            graph: Schema graph
            count: Number of suggestions
            use_llm: Use LLM for generation (True) or templates (False)
            
        Returns:
            List of question suggestions
        """
        if use_llm:
            return self._generate_with_llm(schema, graph, count)
        else:
            return self._generate_with_templates(schema, graph, count)
    
    def _generate_with_llm(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate questions using LLM."""
        # Prepare schema summary
        schema_summary = self._create_schema_summary(schema, graph)
        
        # Create context
        context = AgentContext(
            query=f"Generate {count} insightful questions for this database",
            schema=schema_summary,
            relevant_tables=list(schema.tables.keys())[:10],  # Limit to 10 tables
            metadata={"task": "generate_questions", "count": count}
        )
        
        try:
            response = self.execute(context)
            
            if response.success:
                return response.output
            else:
                logger.warning(f"LLM generation failed, falling back to templates: {response.error}")
                return self._generate_with_templates(schema, graph, count)
        
        except Exception as e:
            logger.error(f"Error generating with LLM: {e}")
            return self._generate_with_templates(schema, graph, count)
    
    def _generate_with_templates(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate questions using templates (no LLM needed)."""
        suggestions = []
        tables = list(schema.tables.values())
        
        if not tables:
            return []
        
        # Analyze schema for smart suggestions
        analysis = self._analyze_schema(schema, graph)
        
        # Generate different types of questions
        generators = [
            self._generate_simple_questions,
            self._generate_aggregation_questions,
            self._generate_join_questions,
            self._generate_time_series_questions,
            self._generate_ranking_questions,
            self._generate_comparison_questions,
            self._generate_statistical_questions,
        ]
        
        # Distribute questions across types
        questions_per_type = max(1, count // len(generators))
        
        for generator in generators:
            try:
                questions = generator(schema, graph, analysis, questions_per_type)
                suggestions.extend(questions)
            except Exception as e:
                logger.error(f"Error in {generator.__name__}: {e}")
        
        # Shuffle and limit
        random.shuffle(suggestions)
        return suggestions[:count]
    
    def _create_schema_summary(self, schema: DatabaseSchema, graph: SchemaGraph) -> str:
        """Create concise schema summary for LLM."""
        lines = [f"Database: {schema.database_name}"]
        lines.append(f"Total tables: {len(schema.tables)}\n")
        
        # Prioritize tables with relationships
        hub_tables = [name for name, _ in graph.get_hub_tables(top_n=10)]
        
        for table_name in hub_tables[:10]:  # Limit to 10 tables
            if table_name not in schema.tables:
                continue
            
            table = schema.tables[table_name]
            lines.append(f"\nTable: {table_name} (~{table.row_count:,} rows)")
            
            # Key columns
            key_cols = []
            for col in table.columns[:8]:  # Limit columns
                col_desc = f"{col.name}:{col.data_type}"
                if col.is_primary_key:
                    col_desc += "[PK]"
                if col.is_foreign_key:
                    col_desc += "[FK]"
                key_cols.append(col_desc)
            
            lines.append(f"  Columns: {', '.join(key_cols)}")
            
            # FKs
            if table.foreign_keys:
                fk_desc = [f"{fk.column_names[0]}→{fk.referenced_table_name}" 
                          for fk in table.foreign_keys[:3]]
                lines.append(f"  Relationships: {', '.join(fk_desc)}")
        
        return "\n".join(lines)
    
    def _analyze_schema(self, schema: DatabaseSchema, graph: SchemaGraph) -> Dict[str, Any]:
        """Analyze schema for question generation."""
        analysis = {
            "has_time_columns": [],
            "has_amount_columns": [],
            "has_quantity_columns": [],
            "has_status_columns": [],
            "fact_tables": [],
            "dimension_tables": [],
            "relationships": [],
            "metrics": []
        }
        
        for table_name, table in schema.tables.items():
            in_degree, out_degree = graph.get_table_degree(table_name)
            
            # Classify tables
            if out_degree > 0 and in_degree == 0:
                analysis["fact_tables"].append(table_name)
            elif out_degree == 0 and in_degree > 0:
                analysis["dimension_tables"].append(table_name)
            
            # Analyze columns
            for col in table.columns:
                col_lower = col.name.lower()
                
                # Time columns
                if any(x in col_lower for x in ['date', 'time', 'created', 'updated', 'timestamp']):
                    analysis["has_time_columns"].append((table_name, col.name))
                
                # Amount columns
                if any(x in col_lower for x in ['amount', 'price', 'cost', 'revenue', 'total', 'value']):
                    if 'decimal' in col.data_type.lower() or 'numeric' in col.data_type.lower():
                        analysis["has_amount_columns"].append((table_name, col.name))
                        analysis["metrics"].append((table_name, col.name, "amount"))
                
                # Quantity columns
                if any(x in col_lower for x in ['quantity', 'count', 'num', 'qty']):
                    analysis["has_quantity_columns"].append((table_name, col.name))
                    analysis["metrics"].append((table_name, col.name, "quantity"))
                
                # Status columns
                if any(x in col_lower for x in ['status', 'state', 'type', 'category']):
                    analysis["has_status_columns"].append((table_name, col.name))
            
            # Capture relationships
            for fk in table.foreign_keys:
                analysis["relationships"].append({
                    "from": table_name,
                    "to": fk.referenced_table_name,
                    "on": fk.column_names[0] if fk.column_names else ""
                })
        
        return analysis
    
    def _generate_simple_questions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        analysis: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate simple single-table questions."""
        questions = []
        
        tables = list(schema.tables.values())[:count * 2]
        
        templates = [
            "Show me all {table}",
            "List all {table} records",
            "What {table} are in the database?",
            "Display the {table} table",
            "Retrieve all entries from {table}",
        ]
        
        for table in tables[:count]:
            template = random.choice(templates)
            question = template.format(table=table.name)
            
            questions.append({
                "question": question,
                "complexity": "low",
                "tables": [table.name],
                "type": "simple",
                "estimated_rows": table.row_count
            })
        
        return questions[:count]
    
    def _generate_aggregation_questions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        analysis: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate aggregation questions."""
        questions = []
        
        # Questions about metrics
        for table, col, metric_type in analysis["metrics"][:count]:
            templates = [
                f"What is the total {col} in {table}?",
                f"Calculate the sum of {col} from {table}",
                f"What is the average {col} in {table}?",
                f"Show me the total {col} by category",
                f"How much {col} do we have in total?",
            ]
            
            question = random.choice(templates)
            
            questions.append({
                "question": question,
                "complexity": "medium",
                "tables": [table],
                "type": "aggregation",
                "metric": col
            })
        
        # Count questions
        for table_name in list(schema.tables.keys())[:count]:
            questions.append({
                "question": f"How many {table_name} are there?",
                "complexity": "low",
                "tables": [table_name],
                "type": "aggregation"
            })
        
        return questions[:count]
    
    def _generate_join_questions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        analysis: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate questions requiring joins."""
        questions = []
        
        # Use relationships
        for rel in analysis["relationships"][:count]:
            from_table = rel["from"]
            to_table = rel["to"]
            
            templates = [
                f"Show me {from_table} with their {to_table} information",
                f"List all {to_table} and their related {from_table}",
                f"Which {to_table} have {from_table}?",
                f"Show {from_table} grouped by {to_table}",
                f"How many {from_table} does each {to_table} have?",
            ]
            
            question = random.choice(templates)
            
            questions.append({
                "question": question,
                "complexity": "medium",
                "tables": [from_table, to_table],
                "type": "join"
            })
        
        return questions[:count]
    
    def _generate_time_series_questions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        analysis: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate time-based questions."""
        questions = []
        
        for table, time_col in analysis["has_time_columns"][:count]:
            templates = [
                f"Show {table} created in the last 30 days",
                f"What is the trend of {table} over time?",
                f"How many {table} were created each month?",
                f"Show {table} grouped by {time_col}",
                f"What are the most recent {table}?",
            ]
            
            question = random.choice(templates)
            
            questions.append({
                "question": question,
                "complexity": "medium",
                "tables": [table],
                "type": "time_series",
                "time_column": time_col
            })
        
        return questions[:count]
    
    def _generate_ranking_questions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        analysis: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate ranking/TOP N questions."""
        questions = []
        
        # Top by metric
        for table, col, metric_type in analysis["metrics"][:count]:
            n = random.choice([5, 10, 20])
            
            templates = [
                f"What are the top {n} {table} by {col}?",
                f"Show me the {n} highest {col} in {table}",
                f"Rank {table} by {col} (top {n})",
                f"Which {table} have the most {col}?",
            ]
            
            question = random.choice(templates)
            
            questions.append({
                "question": question,
                "complexity": "medium",
                "tables": [table],
                "type": "ranking",
                "metric": col,
                "limit": n
            })
        
        return questions[:count]
    
    def _generate_comparison_questions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        analysis: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate comparison questions."""
        questions = []
        
        # Compare by status/category
        for table, status_col in analysis["has_status_columns"][:count]:
            templates = [
                f"Compare {table} by {status_col}",
                f"Show the distribution of {table} across different {status_col}",
                f"How many {table} are in each {status_col}?",
                f"Break down {table} by {status_col}",
            ]
            
            question = random.choice(templates)
            
            questions.append({
                "question": question,
                "complexity": "medium",
                "tables": [table],
                "type": "comparison",
                "group_by": status_col
            })
        
        return questions[:count]
    
    def _generate_statistical_questions(
        self,
        schema: DatabaseSchema,
        graph: SchemaGraph,
        analysis: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate statistical questions."""
        questions = []
        
        for table, col, metric_type in analysis["metrics"][:count]:
            templates = [
                f"What is the average {col} in {table}?",
                f"Show the distribution of {col} across {table}",
                f"What are the min and max {col} in {table}?",
                f"Calculate statistics for {col} in {table}",
            ]
            
            question = random.choice(templates)
            
            questions.append({
                "question": question,
                "complexity": "medium",
                "tables": [table],
                "type": "statistical",
                "metric": col
            })
        
        return questions[:count]
    
    def process_response(self, response: str, context: AgentContext) -> List[Dict[str, Any]]:
        """Process LLM response into question list."""
        import json
        
        # Try to extract JSON
        questions = self._extract_json(response)
        
        if not questions:
            try:
                questions = json.loads(response)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse question response: {response}")
                return []
        
        # Validate structure
        if not isinstance(questions, list):
            logger.error("Response is not a list")
            return []
        
        # Ensure all questions have required fields
        validated = []
        for q in questions:
            if isinstance(q, dict) and "question" in q:
                q.setdefault("complexity", "medium")
                q.setdefault("tables", [])
                q.setdefault("type", "general")
                validated.append(q)
        
        return validated
