"""
Configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM configuration."""
    
    provider: str = Field(default="openai", description="LLM provider")
    model: str = Field(default="gpt-4-turbo-preview", description="Model name")
    api_key: str = Field(default="", description="API key")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=128000)
    timeout: int = Field(default=60, ge=10, le=300)
    
    model_config = SettingsConfigDict(
        env_prefix="LLM__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    
    type: Literal["postgresql", "mysql", "oracle", "sqlite"] = Field(
        default="postgresql",
        description="Database type"
    )
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="", description="Database name")
    username: str = Field(default="", description="Database username")
    password: str = Field(default="", description="Database password")
    schema_name: Optional[str] = Field(default="public", description="Schema name")
    
    model_config = SettingsConfigDict(
        env_prefix="DB__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def get_connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        if self.type == "sqlite":
            return f"sqlite:///{self.database}"
        
        return (
            f"{self.type}://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


class SafetySettings(BaseSettings):
    """Safety and security settings."""
    
    enforce_readonly: bool = Field(default=True, description="Enforce read-only mode")
    max_rows: int = Field(default=10000, ge=1, le=1000000)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    allow_ddl: bool = Field(default=False, description="Allow DDL operations")
    allow_dml: bool = Field(default=False, description="Allow DML operations")
    
    model_config = SettingsConfigDict(
        env_prefix="SAFETY__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""
    
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence transformer model name"
    )
    device: str = Field(default="cpu", description="Device: cpu or cuda")
    batch_size: int = Field(default=32, ge=1, le=512)
    
    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=()
    )


class MemorySettings(BaseSettings):
    """Memory and context configuration."""
    
    enable_query_memory: bool = Field(default=True)
    max_history_turns: int = Field(default=10, ge=1, le=100)
    enable_semantic_boosting: bool = Field(default=True)
    embedding_similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    
    model_config = SettingsConfigDict(
        env_prefix="MEMORY__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class FederationSettings(BaseSettings):
    """Multi-database federation settings."""
    
    enable_federation: bool = Field(default=False)
    max_federated_databases: int = Field(default=5, ge=1, le=50)
    parallel_execution: bool = Field(default=True)
    
    model_config = SettingsConfigDict(
        env_prefix="FEDERATION__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class APISettings(BaseSettings):
    """API server configuration."""
    
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    workers: int = Field(default=1, ge=1, le=32)
    enable_cors: bool = Field(default=True)
    
    model_config = SettingsConfigDict(
        env_prefix="API__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class Settings(BaseSettings):
    """Main application settings."""
    
    # Nested settings - these will be automatically populated
    llm: LLMSettings = Field(default_factory=LLMSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    federation: FederationSettings = Field(default_factory=FederationSettings)
    api: APISettings = Field(default_factory=APISettings)
    
    # General settings
    log_level: str = Field(default="INFO")
    enable_reasoning_trace: bool = Field(default=True)
    data_dir: str = Field(default="./data")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def model_post_init(self, __context):
        """Post-initialization validation."""
        # Re-initialize nested settings to ensure they load from environment
        self.llm = LLMSettings()
        self.db = DatabaseSettings()
        self.safety = SafetySettings()
        self.embedding = EmbeddingSettings()
        self.memory = MemorySettings()
        self.federation = FederationSettings()
        self.api = APISettings()
    
    def validate_required_fields(self) -> None:
        """Validate that required fields are set."""
        errors = []
        
        if not self.llm.api_key:
            errors.append("LLM__API_KEY is required")
        
        if not self.db.database:
            errors.append("DB__DATABASE is required")
        
        if not self.db.username:
            errors.append("DB__USERNAME is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Singleton pattern for settings
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    
    if _settings is None:
        _settings = Settings()
        _settings.validate_required_fields()
    
    return _settings


def reload_settings() -> Settings:
    """Force reload settings from environment."""
    global _settings
    _settings = None
    return get_settings()
