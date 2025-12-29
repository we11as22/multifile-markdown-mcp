"""Library interface for using agent memory as a Python library"""
import asyncio
from pathlib import Path
from typing import Any, Optional

import structlog

from config.settings import Settings
from src.database.connection import DatabaseManager
from src.database.repository import MemoryRepository
from src.embeddings.factory import create_embedding_provider
from src.mcp.tools import MemoryTools
from src.search.chunking import MarkdownChunker
from src.search.hybrid_search import HybridSearchEngine
from src.storage.file_manager import FileManager
from src.storage.index_structure import IndexManager, JsonIndexManager
from src.sync.sync_service import FileSyncService

logger = structlog.get_logger(__name__)


class MemoryLibrary:
    """
    Library interface for agent memory management.

    This class provides all memory operations without requiring FastMCP.
    Can be used directly in Python applications or integrated with LangChain.

    Example:
        ```python
        from agent_memory_mcp import MemoryLibrary

        memory = MemoryLibrary(
            memory_files_path="./memory",
            database_url="postgresql://user:pass@localhost/db"
        )
        await memory.initialize()

        # Create a file
        await memory.create_file("test.md", "content")

        # Search
        results = await memory.search("query")
        ```
    """

    def __init__(
        self,
        memory_files_path: str | Path,
        database_url: Optional[str] = None,
        embedding_provider: Optional[str] = None,
        embedding_config: Optional[dict[str, Any]] = None,
        use_database: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize memory library.

        Args:
            memory_files_path: Path to memory files directory
            database_url: Optional PostgreSQL database URL. If None, uses settings from config.
            embedding_provider: Optional embedding provider name (openai, ollama, etc.)
            embedding_config: Optional dict with provider-specific config (API keys, etc.)
            **kwargs: Additional settings (chunk_size, chunk_overlap, etc.)
        """
        self.memory_files_path = Path(memory_files_path)
        self.database_url = database_url
        self.embedding_provider_name = embedding_provider
        self.embedding_config = embedding_config or {}
        # Check use_database from kwargs or environment
        if use_database is None:
            from config.settings import Settings
            settings = Settings()
            self.use_database = settings.use_database
        else:
            self.use_database = use_database
        self.kwargs = kwargs

        # Will be initialized in initialize()
        self.db_manager: Optional[DatabaseManager] = None
        self.memory_tools: Optional[MemoryTools] = None
        self._initialized = False

        logger.info("memory_library_created", path=str(memory_files_path))

    async def initialize(self) -> None:
        """Initialize all components and connect to database if available"""
        if self._initialized:
            logger.warning("library_already_initialized")
            return

        # Initialize file manager
        file_manager = FileManager(self.memory_files_path)

        # Initialize index managers
        main_file_path = self.memory_files_path / "main.md"
        index_manager = IndexManager(main_file_path)
        json_index_path = self.memory_files_path / "files_index.json"
        json_index_manager = JsonIndexManager(json_index_path)

        # Initialize database - always try to connect
        # Use provided URL or fall back to settings
        database_url = self.database_url
        if not database_url:
            # Use settings from config
            settings = Settings()
            database_url = settings.database_url
            logger.info("using_database_url_from_settings")

        repository: Optional[MemoryRepository] = None
        sync_service: Optional[FileSyncService] = None
        search_engine: Optional[HybridSearchEngine] = None

        # Check if database should be used
        if not self.use_database:
            logger.info("database_disabled_using_file_only_mode")
        else:
            try:
                # Initialize database connection
                # Initialize database connection
                self.db_manager = DatabaseManager(
                    database_url=database_url,
                    pool_min_size=self.kwargs.get("db_pool_min_size", 5),
                    pool_max_size=self.kwargs.get("db_pool_max_size", 20),
                )
                await self.db_manager.connect()

                if not await self.db_manager.health_check():
                    raise RuntimeError("Database health check failed")

                # Initialize embedding provider (only if database is enabled)
                embedding_provider = None
                if self.embedding_provider_name:
                    # Create a temporary settings object for provider creation
                    temp_settings = Settings()
                    temp_settings.embedding_provider = self.embedding_provider_name
                    # Update with provided config
                    for key, value in self.embedding_config.items():
                        setattr(temp_settings, key, value)
                    temp_settings.validate_provider_config()
                    embedding_provider = create_embedding_provider(temp_settings)
                else:
                    # Try to use embedding provider from settings
                    settings = Settings()
                    if settings.embedding_provider:
                        try:
                            settings.validate_provider_config()
                            embedding_provider = create_embedding_provider(settings)
                            logger.info("using_embedding_provider_from_settings", provider=settings.embedding_provider)
                        except Exception as e:
                            logger.warning("failed_to_initialize_embedding_from_settings", error=str(e))

                # Initialize chunker
                chunk_size = self.kwargs.get("chunk_size", 800)
                chunk_overlap = self.kwargs.get("chunk_overlap", 200)
                chunker = MarkdownChunker(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )

                # Initialize repository and sync service
                session = self.db_manager.get_session()
                pool = await self.db_manager.get_pool()

                repository = MemoryRepository(session, pool)
                sync_service = FileSyncService(
                    file_manager=file_manager,
                    repository=repository,
                    chunker=chunker,
                    embedding_provider=embedding_provider,
                    batch_size=self.kwargs.get("embedding_batch_size", 100),
                )

                # Initialize search engine (works even without embeddings - uses fulltext)
                search_engine = HybridSearchEngine(pool, embedding_provider)

                logger.info("database_initialized", url=database_url)
            except Exception as e:
                logger.error("database_initialization_failed", error=str(e))
                if self.use_database:
                    # If database is required but failed, raise error
                    raise RuntimeError(
                        f"Failed to initialize database. Database is required when use_database=True. "
                        f"Error: {str(e)}"
                    ) from e
                else:
                    # If database is optional, just log warning
                    logger.warning("database_initialization_failed_continuing_without_db", error=str(e))
                    self.db_manager = None

        # Initialize memory tools (repository, sync_service, search_engine can be None for file-only mode)
        self.memory_tools = MemoryTools(
            file_manager=file_manager,
            index_manager=index_manager,
            json_index_manager=json_index_manager,
            repository=repository,
            sync_service=sync_service,
            search_engine=search_engine,
        )

        # Ensure main.md exists
        if not (self.memory_files_path / "main.md").exists():
            from scripts.init_memory_structure import init_memory_structure
            init_memory_structure(self.memory_files_path)
        
        self._initialized = True
        logger.info("memory_library_initialized")


    async def close(self) -> None:
        """Close connections and cleanup"""
        if self.db_manager:
            await self.db_manager.disconnect()
        self._initialized = False
        logger.info("memory_library_closed")

    # Delegate all methods to memory_tools
    async def create_file(
        self,
        title: str,
        category: str,
        content: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a new memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.create_memory_file(title, category, content, tags, metadata)

    async def update_file(
        self,
        file_path: str,
        content: str,
        update_mode: str = "replace",
    ) -> dict[str, str]:
        """Update an existing memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.update_memory_file(file_path, content, update_mode)

    async def delete_file(self, file_path: str) -> dict[str, str]:
        """Delete a memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.delete_memory_file(file_path)

    async def get_file(self, file_path: str) -> dict[str, str]:
        """Get the content of a memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.get_file_content(file_path)

    async def list_files(self, category: Optional[str] = None) -> dict[str, Any]:
        """List all memory files"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.list_files(category)

    async def search(
        self,
        query: str,
        search_mode: str = "hybrid",
        limit: int = 10,
        file_path: Optional[str] = None,
        category_filter: Optional[str] = None,
        tag_filter: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Search across memory files"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        response = await self.memory_tools.search(
            query, search_mode, limit, file_path, category_filter, tag_filter
        )
        return response.model_dump() if hasattr(response, "model_dump") else response

    async def edit_file(
        self,
        file_path: str,
        edit_type: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Edit a file using universal edit method"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.edit_file(file_path, edit_type, **kwargs)

    async def initialize_memory(self) -> dict[str, Any]:
        """Initialize memory to base state"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.initialize_memory()

    async def reset_memory(self) -> dict[str, Any]:
        """Reset memory to base state"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.reset_memory()

    # Batch operations
    async def batch_create_files(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        """Create multiple memory files at once"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.batch_create_files(files)

    async def batch_update_files(self, updates: list[dict[str, Any]]) -> dict[str, Any]:
        """Update multiple memory files at once"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.batch_update_files(updates)

    async def batch_delete_files(self, file_paths: list[str]) -> dict[str, Any]:
        """Delete multiple memory files at once"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.batch_delete_files(file_paths)

    async def batch_search(self, queries: list[dict[str, Any]]) -> dict[str, Any]:
        """Perform multiple searches at once"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.batch_search(queries)
    
    # Tag management
    async def add_tags(self, file_path: str, tags: list[str]) -> dict[str, Any]:
        """Add tags to a memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.add_tags(file_path, tags)
    
    async def remove_tags(self, file_path: str, tags: list[str]) -> dict[str, Any]:
        """Remove tags from a memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.remove_tags(file_path, tags)
    
    async def get_tags(self, file_path: str) -> dict[str, Any]:
        """Get all tags for a memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.get_tags(file_path)
    
    # Main memory operations
    async def append_to_main(self, content: str, section: str = "Recent Notes") -> dict[str, str]:
        """Append content to a section in main.md"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.append_to_main_memory(content, section)
    
    async def add_goal(self, goal: str) -> dict[str, str]:
        """Add a goal to main.md"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.update_goals(goal, "add")
    
    async def add_task(self, task: str) -> dict[str, str]:
        """Add a task to main.md"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.update_tasks(task, "add")
    
    # File operations
    async def rename_file(self, old_file_path: str, new_title: str) -> dict[str, Any]:
        """Rename a memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.rename_file(old_file_path, new_title)
    
    async def move_file(self, file_path: str, new_category: str) -> dict[str, Any]:
        """Move a file to a different category"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.move_file(file_path, new_category)
    
    async def copy_file(self, source_file_path: str, new_title: str, new_category: Optional[str] = None) -> dict[str, Any]:
        """Create a copy of a memory file"""
        if not self._initialized:
            raise RuntimeError("Library not initialized. Call initialize() first.")
        return await self.memory_tools.copy_file(source_file_path, new_title, new_category)


def get_langchain_tools(memory: MemoryLibrary) -> list[Any]:
    """
    Get LangChain tools from MemoryLibrary instance.

    Args:
        memory: Initialized MemoryLibrary instance

    Returns:
        List of LangChain tools

    Example:
        ```python
        from langchain.agents import Agent
        from agent_memory_mcp import MemoryLibrary, get_langchain_tools

        memory = MemoryLibrary(...)
        await memory.initialize()

        tools = get_langchain_tools(memory)
        agent = Agent(tools=tools)
        ```
    """
    try:
        from langchain.tools import StructuredTool
        from langchain_core.pydantic_v1 import BaseModel, Field
    except ImportError:
        raise ImportError(
            "LangChain is not installed. Install it with: pip install langchain langchain-core"
        )

    # Define tool schemas
    class CreateFileInput(BaseModel):
        title: str = Field(description="Title of the memory file")
        category: str = Field(description="Category: project, concept, conversation, preference, other")
        content: str = Field(description="Markdown content")
        tags: Optional[list[str]] = Field(None, description="Optional tags")
        metadata: Optional[dict[str, Any]] = Field(None, description="Optional metadata")

    class SearchInput(BaseModel):
        query: str = Field(description="Search query text")
        search_mode: str = Field("hybrid", description="Search mode: hybrid, vector, fulltext")
        limit: int = Field(10, description="Maximum results")
        file_path: Optional[str] = Field(None, description="Optional file path filter")
        category_filter: Optional[str] = Field(None, description="Optional category filter")
        tag_filter: Optional[list[str]] = Field(None, description="Optional tag filter")

    # Create tools
    tools = [
        StructuredTool.from_function(
            func=lambda title, category, content, tags=None, metadata=None: asyncio.run(
                memory.create_file(title, category, content, tags, metadata)
            ),
            name="create_memory_file",
            description="Create a new memory file",
            args_schema=CreateFileInput,
        ),
        StructuredTool.from_function(
            func=lambda query, search_mode="hybrid", limit=10, file_path=None, category_filter=None, tag_filter=None: asyncio.run(
                memory.search(query, search_mode, limit, file_path, category_filter, tag_filter)
            ),
            name="search_memory",
            description="Search across memory files",
            args_schema=SearchInput,
        ),
    ]

    return tools

