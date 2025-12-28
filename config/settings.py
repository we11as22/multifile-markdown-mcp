"""Application settings using Pydantic Settings"""
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings"""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    # ===================================
    # Server Configuration
    # ===================================
    mcp_server_name: str = Field(default="agent-memory", description="MCP server name")
    log_level: str = Field(default="INFO", description="Logging level")

    # ===================================
    # Storage Configuration
    # ===================================
    memory_files_path: str = Field(default="./memory_files", description="Path to memory files directory")
    main_file_name: str = Field(default="main.md", description="Name of the main memory file")

    # ===================================
    # Database Configuration
    # ===================================
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="agent_memory", description="PostgreSQL database name")
    postgres_user: str = Field(default="memory_user", description="PostgreSQL user")
    postgres_password: str = Field(default="change_me_in_production", description="PostgreSQL password")

    db_pool_min_size: int = Field(default=5, description="Minimum database connection pool size")
    db_pool_max_size: int = Field(default=20, description="Maximum database connection pool size")

    # ===================================
    # Embedding Provider Configuration
    # ===================================
    embedding_provider: Literal["openai", "cohere", "ollama", "huggingface", "litellm"] = Field(
        default="openai",
        description="Embedding provider to use"
    )
    embedding_dimension: int = Field(default=1536, description="Embedding vector dimension")

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model"
    )

    # Cohere
    cohere_api_key: str = Field(default="", description="Cohere API key")
    cohere_embedding_model: str = Field(
        default="embed-english-v3.0",
        description="Cohere embedding model"
    )
    cohere_input_type: str = Field(
        default="search_document",
        description="Cohere input type (search_document, search_query, classification)"
    )

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model"
    )

    # HuggingFace
    huggingface_api_key: str = Field(default="", description="HuggingFace API token")
    huggingface_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model name"
    )
    huggingface_use_local: bool = Field(
        default=False,
        description="Use local model instead of API"
    )
    huggingface_device: str = Field(default="cpu", description="Device for local model (cpu, cuda)")

    # LiteLLM
    litellm_model: str = Field(
        default="text-embedding-3-small",
        description="LiteLLM model identifier"
    )

    # ===================================
    # Search Configuration
    # ===================================
    chunk_size: int = Field(default=800, description="Maximum chunk size in characters")
    chunk_overlap: int = Field(default=200, description="Chunk overlap in characters")
    search_limit: int = Field(default=20, ge=1, le=100, description="Default search result limit")
    rrf_k: int = Field(default=60, ge=1, description="RRF k parameter for hybrid search")

    # ===================================
    # Sync Configuration
    # ===================================
    file_watch_enabled: bool = Field(default=True, description="Enable file watching for auto-sync")
    sync_interval_seconds: int = Field(
        default=60,
        ge=10,
        description="Interval for periodic sync in seconds"
    )

    # ===================================
    # Advanced Configuration
    # ===================================
    embedding_batch_size: int = Field(
        default=100,
        ge=1,
        description="Batch size for embedding generation"
    )
    max_retries: int = Field(default=3, ge=0, description="Maximum retries for API calls")
    retry_backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        description="Exponential backoff factor for retries"
    )

    # ===================================
    # Computed Properties
    # ===================================

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Construct synchronous PostgreSQL connection URL (for Alembic)"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def memory_files_path_obj(self) -> Path:
        """Get memory files path as Path object"""
        return Path(self.memory_files_path)

    @computed_field
    @property
    def main_file_path(self) -> Path:
        """Get full path to main memory file"""
        return self.memory_files_path_obj / self.main_file_name

    def validate_provider_config(self) -> None:
        """Validate that required configuration for selected provider is present"""
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        elif self.embedding_provider == "cohere" and not self.cohere_api_key:
            raise ValueError("COHERE_API_KEY is required when using Cohere provider")
        elif self.embedding_provider == "huggingface":
            if not self.huggingface_use_local and not self.huggingface_api_key:
                raise ValueError(
                    "HUGGINGFACE_API_KEY is required when using HuggingFace API"
                )

    def get_log_config(self) -> dict:
        """Get structured logging configuration"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "structlog.stdlib.ProcessorFormatter",
                    "processor": "structlog.processors.JSONRenderer",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": self.log_level,
            },
        }


# Global settings instance
settings = Settings()
