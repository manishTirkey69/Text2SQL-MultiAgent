"""
Main entry point for Database Reasoning Engine.
"""
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from sqlalchemy import create_engine

from config.settings import get_settings
from core.schema_info import SchemaExtractor
from core.graph_builder import SchemaGraph
from core.schema_embeddings import SchemaEmbeddings
from agents.planner import PlannerAgent
from agents.sql_generator import SQLGeneratorAgent
from agents.sql_critic import SQLCriticAgent
from agents.sql_repair import SQLRepairAgent
from agents.question_suggester import QuestionSuggestionAgent
from memory.query_memory import QueryMemory
from execution.safety import SafetyValidator
from execution.executor import SQLExecutor
from execution.feedback_loop import FeedbackLoopOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseReasoningEngine:
    """Main engine for AI-powered database querying."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Database Reasoning Engine.
        
        Args:
            connection_string: Database connection string
            llm_client: Pre-configured LLM client (optional)
            config: Configuration dictionary (optional)
        """
        logger.info("Initializing Database Reasoning Engine...")
        
        # Load settings
        self.settings = get_settings()
        
        # Initialize LLM client
        if llm_client:
            self.llm_client = llm_client
            self.model = getattr(llm_client, 'model', self.settings.llm.model)
        else:
            import openai
            self.llm_client = openai.OpenAI(api_key=self.settings.llm.api_key)
            self.model = self.settings.llm.model
        
        # Database connection
        if connection_string:
            self.connection_string = connection_string
        else:
            self.connection_string = self.settings.db.get_connection_string()
        
        logger.info(f"Connecting to database: {self.connection_string.split('@')[-1] if '@' in self.connection_string else self.connection_string}")
        
        # Create SQLAlchemy engine
        self.engine = create_engine(
            self.connection_string,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        # Test connection
        try:
            with self.engine.connect() as conn:
                logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
        
        # Extract schema
        logger.info("Extracting database schema...")
        extractor = SchemaExtractor(self.engine)
        self.schema = extractor.extract_full_schema(
            schema_name=self.settings.db.schema_name
        )
        logger.info(f"✅ Schema extracted: {len(self.schema.tables)} tables")
        
        # Build graph
        logger.info("Building schema graph...")
        self.graph = SchemaGraph(self.schema)
        logger.info("✅ Schema graph built")
        
        # Initialize embeddings
        logger.info(f"Loading embedding model: {self.settings.embedding.model_name}")
        self.embeddings = SchemaEmbeddings(
            model_name=self.settings.embedding.model_name,
            device=self.settings.embedding.device
        )
        
        # Generate embeddings
        logger.info("Generating semantic embeddings...")
        self.embeddings.embed_schema(self.schema)
        logger.info("✅ Embeddings generated")
        
        # Initialize agents
        self.planner = PlannerAgent(self.llm_client, self.model)
        self.sql_generator = SQLGeneratorAgent(self.llm_client, self.model)
        self.sql_critic = SQLCriticAgent(self.llm_client, self.model)
        self.sql_repair = SQLRepairAgent(self.llm_client, self.model)
        self.question_suggester = QuestionSuggestionAgent(self.llm_client, self.model)
        
        # Initialize memory
        self.memory = QueryMemory(max_history=self.settings.memory.max_history_turns)
        
        # Initialize safety validator
        self.safety_validator = SafetyValidator(
            enforce_readonly=self.settings.safety.enforce_readonly,
            max_rows=self.settings.safety.max_rows
        )
        
        # Initialize SQL executor
        self.sql_executor = SQLExecutor(
            self.engine,
            safety_validator=self.safety_validator, 
            timeout_seconds=self.settings.safety.timeout_seconds
        )

        
        # Initialize feedback loop orchestrator
        self.feedback_loop = FeedbackLoopOrchestrator(
            sql_executor=self.sql_executor,
            sql_critic=self.sql_critic,
            sql_repair=self.sql_repair,
            max_retries=3
        )
        
        logger.info("=" * 70)
        logger.info("✨ Database Reasoning Engine initialized successfully!")
        logger.info("=" * 70)
    
    def query(
        self,
        query: str,
        enable_critique: bool = True,
        enable_repair: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Execute a natural language query.
        
        Args:
            query: Natural language question
            enable_critique: Enable SQL critique before execution
            enable_repair: Enable automatic error repair
            max_retries: Maximum repair attempts
            
        Returns:
            Dictionary with results and metadata
        """
        logger.info(f"Processing query: {query}")
        
        try:
            # Discover relevant tables
            relevant_results = self.embeddings.find_relevant_tables(
                query,
                top_k=5,
                threshold=0.3
            )
            
            # Extract table names
            relevant_tables = [table_name for table_name, score in relevant_results]
            
            if not relevant_tables:
                # Fallback: use all tables if no relevant ones found
                relevant_tables = list(self.schema.tables.keys())[:5]
            
            logger.info(f"Relevant tables: {relevant_tables}")
            
            # Boost tables based on relevance
            if self.settings.memory.enable_semantic_boosting:
                for table_name, score in relevant_results:
                    if score > 0.5:
                        self.embeddings.boost_table(table_name, factor=1.1)
            
            # Compress schema
            from core.schema_compressor import SchemaCompressor
            compressor = SchemaCompressor(self.schema, self.graph)
            compressed_schema = compressor.compress_relevant_schema(
                table_names=relevant_tables,
                include_neighbors=True,
                detail_level="high"
            )
            
            # Create agent context
            from agents.base_agent import AgentContext
            context = AgentContext(
                query=query,
                schema=compressed_schema,
                relevant_tables=relevant_tables,
                conversation_history=self.memory.get_recent_history(n=3),
                metadata={}
            )
            
            # Plan query
            logger.info("Planning query...")
            plan_response = self.planner.execute(context)
            
            if not plan_response.success:
                return {
                    "success": False,
                    "error": f"Planning failed: {plan_response.error}",
                    "attempts": 1
                }
            
            # Generate SQL
            logger.info("Generating SQL...")
            context.metadata['plan'] = plan_response.output
            sql_response = self.sql_generator.execute(context)
            
            if not sql_response.success:
                return {
                    "success": False,
                    "error": f"SQL generation failed: {sql_response.error}",
                    "attempts": 1
                }
            
            initial_sql = sql_response.output
            
            # Execute with feedback loop
            logger.info("Executing SQL with feedback loop...")
            trace = self.feedback_loop.execute_with_feedback(
                sql=initial_sql,
                schema=compressed_schema,
                original_query=query,
                enable_repair=enable_repair,
                max_retries=max_retries
            )
            
            # Get final result
            final_sql = trace.get_final_sql()
            last_attempt = trace.attempts[-1] if trace.attempts else None
            
            if trace.success and last_attempt and last_attempt.execution_result:
                exec_result = last_attempt.execution_result
                
                # Store in memory
                self.memory.add_turn(
                    query=query,
                    sql=final_sql,
                    success=True,
                    metadata={"row_count": exec_result.row_count}
                )
                
                return {
                    "success": True,
                    "sql": final_sql,
                    "results": exec_result.rows,
                    "row_count": exec_result.row_count,
                    "execution_time_ms": exec_result.execution_time_ms,
                    "attempts": trace.get_total_attempts(),
                    "reasoning_trace": trace.to_dict() if self.settings.enable_reasoning_trace else None
                }
            else:
                error = last_attempt.execution_result.error if last_attempt and last_attempt.execution_result else "Unknown error"
                
                # Store failure in memory
                self.memory.add_turn(
                    query=query,
                    sql=final_sql,
                    success=False,
                    metadata={"error": error}
                )
                
                return {
                    "success": False,
                    "sql": final_sql,
                    "error": error,
                    "attempts": trace.get_total_attempts(),
                    "reasoning_trace": trace.to_dict() if self.settings.enable_reasoning_trace else None
                }
        
        except Exception as e:
            logger.error(f"Query execution error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "attempts": 1
            }
    
    def get_question_suggestions(
        self,
        count: int = 10,
        use_llm: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get suggested questions based on schema.
        
        Args:
            count: Number of suggestions
            use_llm: Use LLM for generation (slower but better quality)
            
        Returns:
            List of question suggestions
        """
        logger.info(f"Generating {count} question suggestions (LLM={use_llm})...")
        
        suggestions = self.question_suggester.generate_suggestions(
            schema=self.schema,
            graph=self.graph,
            count=count,
            use_llm=use_llm
        )
        
        logger.info(f"Generated {len(suggestions)} suggestions")
        return suggestions
    
    def interactive_mode(self):
        """Run in interactive CLI mode."""
        print("=" * 70)
        print("DATABASE REASONING ENGINE - Interactive Mode")
        print("=" * 70)
        print(f"Connected to: {self.schema.database_name}")
        print(f"Tables available: {len(self.schema.tables)}")
        print("\nType your questions in natural language.")
        print("Commands: 'exit' to quit, 'schema' to view tables,")
        print("          'suggest' for question ideas, 'clear' to clear history")
        
        # Show initial suggestions
        print("\n" + "=" * 70)
        print("💡 SUGGESTED QUESTIONS:")
        print("=" * 70)
        try:
            suggestions = self.get_question_suggestions(count=5, use_llm=False)
            for i, suggestion in enumerate(suggestions, 1):
                complexity = suggestion.get('complexity', 'medium')
                emoji = "🟢" if complexity == "low" else "🟡" if complexity == "medium" else "🔴"
                print(f"{i}. {emoji} {suggestion['question']}")
                if suggestion.get('tables'):
                    print(f"   Tables: {', '.join(suggestion['tables'])}")
        except Exception as e:
            logger.warning(f"Could not generate suggestions: {e}")
        print("=" * 70)
        
        while True:
            try:
                query = input("\n💬 Query: ").strip()
                
                if not query:
                    continue
                
                if query.lower() == 'exit':
                    print("Goodbye! 👋")
                    break
                
                if query.lower() == 'schema':
                    print(f"\n📊 Tables ({len(self.schema.tables)}):")
                    for table_name in sorted(self.schema.tables.keys()):
                        table = self.schema.tables[table_name]
                        row_count = f"~{table.row_count:,}" if table.row_count else "unknown"
                        print(f"  - {table_name} ({len(table.columns)} columns, {row_count} rows)")
                    continue
                
                if query.lower() == 'suggest':
                    print("\n💡 Question Suggestions:")
                    print("=" * 70)
                    suggestions = self.get_question_suggestions(count=10, use_llm=False)
                    for i, suggestion in enumerate(suggestions, 1):
                        complexity = suggestion.get('complexity', 'medium')
                        q_type = suggestion.get('type', 'general')
                        emoji = "🟢" if complexity == "low" else "🟡" if complexity == "medium" else "🔴"
                        print(f"\n{i}. {emoji} [{q_type.upper()}] {suggestion['question']}")
                        if suggestion.get('tables'):
                            print(f"   📊 Tables: {', '.join(suggestion['tables'])}")
                    print("=" * 70)
                    continue
                
                if query.lower() == 'clear':
                    self.memory.clear()
                    self.embeddings.reset_boosts()
                    print("✅ Conversation history cleared")
                    continue
                
                # Execute query
                print("🤔 Processing...")
                result = self.query(query)
                
                if result['success']:
                    print(f"\n✅ Success! ({result['attempts']} attempts)")
                    print(f"\n📝 SQL:\n{result['sql']}")
                    print(f"\n📊 {result['row_count']} rows in {result['execution_time_ms']:.2f}ms")
                    
                    # Show first few rows
                    if result['results']:
                        print("\n🔍 First 5 rows:")
                        for i, row in enumerate(result['results'][:5], 1):
                            print(f"  {i}. {row}")
                else:
                    print(f"\n❌ Failed after {result['attempts']} attempts")
                    print(f"Error: {result.get('error', 'Unknown error')}")
            
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                print(f"❌ Error: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Database Reasoning Engine - AI-Powered Text-to-SQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --api                    # Start API server
  python main.py --interactive            # Start interactive CLI
  python main.py --api --connection-string "postgresql://user:pass@localhost/db"
        """
    )
    parser.add_argument("--api", action="store_true", help="Start API server")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode")
    parser.add_argument(
        "--connection-string",
        type=str,
        help="Database connection string (overrides .env)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.api:
            # Start API server
            settings = get_settings()
            import uvicorn
            
            print("=" * 70)
            print("🚀 Starting Database Reasoning Engine API")
            print("=" * 70)
            print(f"📍 Server: http://{settings.api.host}:{settings.api.port}")
            print(f"📚 Docs: http://{settings.api.host}:{settings.api.port}/docs")
            print(f"🔄 Reload: {settings.api.reload}")
            print("=" * 70)
            
            uvicorn.run(
                "api.server:app",
                host=settings.api.host,
                port=settings.api.port,
                reload=settings.api.reload,
                log_level=settings.log_level.lower()
            )
        
        elif args.interactive:
            # Interactive mode
            settings = get_settings()
            connection_string = args.connection_string or settings.db.get_connection_string()
            engine = DatabaseReasoningEngine(connection_string=connection_string)
            engine.interactive_mode()
        
        else:
            # Default: show help
            parser.print_help()
    
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.info("💡 Please check your .env file and ensure all required fields are set")
        print("\n" + "=" * 70)
        print("Required .env variables:")
        print("  - LLM__API_KEY")
        print("  - DB__DATABASE")
        print("  - DB__USERNAME")
        print("  - DB__PASSWORD")
        print("=" * 70)
        exit(1)
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
