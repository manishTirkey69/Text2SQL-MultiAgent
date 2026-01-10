"""
Base agent abstraction for all LLM-powered agents.
Provides common interface and utilities for specialized agents.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to agents during execution."""
    query: str
    schema: str
    relevant_tables: List[str]
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "schema": self.schema,
            "relevant_tables": self.relevant_tables,
            "conversation_history": self.conversation_history,
            "metadata": self.metadata
        }


@dataclass
class AgentResponse:
    """Response from agent execution."""
    success: bool
    output: Any
    reasoning: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "reasoning": self.reasoning,
            "error": self.error,
            "metadata": self.metadata
        }


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(
        self, 
        llm_client: Any, 
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048
    ):
        """
        Initialize agent.
        
        Args:
            llm_client: LLM client (OpenAI, Anthropic, etc.)
            model: Model name override
            temperature: Sampling temperature
            max_tokens: Maximum tokens for completion
        """
        self.llm_client = llm_client
        self.model = model or getattr(llm_client, 'model', 'gpt-4o-mini')
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.name = self.__class__.__name__
        
        logger.info(f"[{self.name}] Initialized with model: {self.model}")
    
    def _is_o1_model(self) -> bool:
        """
        Check if model is o1-series (requires max_completion_tokens).
        
        Returns:
            True if o1/o3 model, False otherwise
        """
        model_lower = self.model.lower()
        
        # ONLY o1 and o3 models use max_completion_tokens
        o1_models = ['o1-preview', 'o1-mini', 'o3-mini']
        
        return any(o1_model in model_lower for o1_model in o1_models)
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent."""
        pass
    
    @abstractmethod
    def process_response(self, response: str, context: AgentContext) -> Any:
        """Process LLM response into structured output."""
        pass
    
    def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute agent with given context.
        
        Args:
            context: Execution context
            
        Returns:
            AgentResponse
        """
        logger.info(f"[{self.name}] Executing...")
        
        try:
            # Build messages
            messages = self._build_messages(context)
            
            # Call LLM
            llm_response = self._call_llm(messages)
            
            # Process response
            output = self.process_response(llm_response, context)
            
            logger.info(f"[{self.name}] Success")
            
            return AgentResponse(
                success=True,
                output=output,
                reasoning=llm_response,
                metadata={"agent": self.name, "model": self.model}
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                output=None,
                error=str(e),
                metadata={"agent": self.name, "model": self.model}
            )
    
    def _build_messages(self, context: AgentContext) -> List[Dict[str, str]]:
        """Build message list for LLM."""
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        
        # Add conversation history if available
        for turn in context.conversation_history[-3:]:  # Last 3 turns
            # Handle both dict and QueryTurn object
            if hasattr(turn, 'query'):
                # It's a QueryTurn object (from memory)
                messages.append({"role": "user", "content": turn.query})
                if hasattr(turn, 'sql') and turn.sql:
                    messages.append({"role": "assistant", "content": f"SQL: {turn.sql}"})
            elif isinstance(turn, dict):
                # It's a dictionary
                if "query" in turn:
                    messages.append({"role": "user", "content": turn["query"]})
                if "sql" in turn:
                    messages.append({"role": "assistant", "content": f"SQL: {turn['sql']}"})
        
        # Add current query with schema
        user_message = self._format_user_message(context)
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _format_user_message(self, context: AgentContext) -> str:
        """Format user message with context."""
        parts = [
            f"Query: {context.query}",
            f"\nDatabase Schema:\n{context.schema}"
        ]
        
        if context.relevant_tables:
            parts.append(f"\nMost Relevant Tables: {', '.join(context.relevant_tables)}")
        
        if context.metadata:
            for key, value in context.metadata.items():
                if key not in ["schema", "relevant_tables"]:
                    parts.append(f"\n{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(parts)
    
    def _call_llm(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None
    ) -> str:
        """
        Call LLM and return response text.
        
        Args:
            messages: List of message dicts
            temperature: Override default temperature
            
        Returns:
            Response text from LLM
        """
        temp = temperature if temperature is not None else self.temperature
        
        # Build base parameters
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
        }
        
        # Add token parameter based on model type
        # ONLY o1/o3 models use max_completion_tokens
        # ALL other models (gpt-4o, gpt-5, gpt-4-turbo, etc.) use max_tokens
        if self._is_o1_model():
            request_params["max_completion_tokens"] = self.max_tokens
            token_param_name = "max_completion_tokens"
        else:
            request_params["max_tokens"] = self.max_tokens
            token_param_name = "max_tokens"
        
        try:
            logger.debug(
                f"[{self.name}] Calling LLM: model={self.model}, "
                f"{token_param_name}={self.max_tokens}, temp={temp}"
            )
            
            response = self.llm_client.chat.completions.create(**request_params)
            
            content = response.choices[0].message.content
            
            if not content:
                raise ValueError("Empty response from LLM")
            
            logger.debug(f"[{self.name}] LLM response received ({len(content)} chars)")
            
            return content
            
        except Exception as e:
            logger.error(f"[{self.name}] LLM call failed: {e}")
            raise
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text."""
        import re
        
        # Try to find JSON in code blocks first
        json_match = re.search(r'```json\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON code block
        json_match = re.search(r'```\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find raw JSON object or array
        json_match = re.search(r'(\[.*?\]|\{.*?\})', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"[{self.name}] Could not extract JSON from response")
        return None
    
    def _extract_code_block(self, text: str, language: str = "sql") -> Optional[str]:
        """
        Extract code block from markdown response.
        
        Args:
            text: Response text
            language: Language identifier (sql, python, etc.)
            
        Returns:
            Extracted code or None
        """
        import re
        
        # Try language-specific code block
        pattern = rf'```{language}\s*(.*?)\s*```'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try generic code block
        pattern = r'```\s*(.*?)\s*```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return None
