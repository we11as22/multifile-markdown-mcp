"""Main entry point for Agent Memory MCP Server"""
import asyncio
import logging.config
from pathlib import Path

import structlog
from fastmcp import FastMCP

from config.settings import settings
from src.database.connection import DatabaseManager
from src.database.repository import MemoryRepository
from src.database.schema import Base
from src.embeddings.factory import create_embedding_provider
from src.mcp.tools import MemoryTools
from src.search.chunking import MarkdownChunker
from src.search.hybrid_search import HybridSearchEngine
from src.storage.file_manager import FileManager
from src.storage.index_structure import IndexManager
from src.sync.sync_service import FileSyncService

# Configure structured logging
logging.config.dictConfig(settings.get_log_config())
logger = structlog.get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP(settings.mcp_server_name)

# Global state
db_manager: DatabaseManager
memory_tools: MemoryTools


async def initialize_server() -> None:
    """Initialize all server components"""
    global db_manager, memory_tools

    logger.info("initializing_agent_memory_mcp_server", version="0.1.0")

    # Initialize database connection
    db_manager = DatabaseManager(
        database_url=settings.database_url,
        pool_min_size=settings.db_pool_min_size,
        pool_max_size=settings.db_pool_max_size,
    )
    await db_manager.connect()

    # Check database health
    if not await db_manager.health_check():
        raise RuntimeError("Database health check failed")

    # Initialize embedding provider (optional - falls back to fulltext-only mode)
    embedding_provider = None
    if settings.embedding_provider:
        try:
            settings.validate_provider_config()
            embedding_provider = create_embedding_provider(settings)
            logger.info("embedding_provider_created", provider=settings.embedding_provider)
        except Exception as e:
            logger.warning(
                "embedding_provider_initialization_failed_using_fulltext_only",
                error=str(e)
            )
    else:
        logger.info("no_embedding_provider_configured_using_fulltext_only")

    # Initialize file manager
    file_manager = FileManager(settings.memory_files_path_obj)

    # Initialize index manager
    index_manager = IndexManager(settings.main_file_path)

    # Initialize chunker
    chunker = MarkdownChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Initialize repository (we'll create a new session for each request)
    # For now, create one for initial sync
    session = db_manager.get_session()
    pool = await db_manager.get_pool()

    try:
        repository = MemoryRepository(session, pool)

        # Initialize sync service
        sync_service = FileSyncService(
            file_manager=file_manager,
            repository=repository,
            chunker=chunker,
            embedding_provider=embedding_provider,
            batch_size=settings.embedding_batch_size,
        )

        # Perform initial sync
        logger.info("performing_initial_sync")
        await sync_service.sync_all_files()

        # Initialize search engine
        search_engine = HybridSearchEngine(pool, embedding_provider)

        # Initialize memory tools
        memory_tools = MemoryTools(
            file_manager=file_manager,
            index_manager=index_manager,
            repository=repository,
            sync_service=sync_service,
            search_engine=search_engine,
        )

        logger.info("server_initialized_successfully")

    finally:
        await session.close()


async def shutdown_server() -> None:
    """Cleanup on server shutdown"""
    logger.info("shutting_down_server")
    await db_manager.disconnect()
    logger.info("server_shutdown_complete")


# Register MCP Tools
@mcp.tool()
async def create_memory_file(
    title: str,
    category: str,
    content: str,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    """Create a new memory file"""
    return await memory_tools.create_memory_file(title, category, content, tags, metadata)


@mcp.tool()
async def update_memory_file(
    file_path: str,
    content: str,
    update_mode: str = "replace",
) -> dict:
    """Update an existing memory file"""
    return await memory_tools.update_memory_file(file_path, content, update_mode)


@mcp.tool()
async def delete_memory_file(file_path: str) -> dict:
    """Delete a memory file"""
    return await memory_tools.delete_memory_file(file_path)


@mcp.tool()
async def append_to_main_memory(
    content: str,
    section: str = "Recent Notes",
) -> dict:
    """Append content to main.md"""
    return await memory_tools.append_to_main_memory(content, section)


@mcp.tool()
async def update_goals(goal: str, action: str = "add") -> dict:
    """Manage goals in main.md"""
    return await memory_tools.update_goals(goal, action)


@mcp.tool()
async def update_tasks(task: str, action: str = "add") -> dict:
    """Add completed task to main.md"""
    return await memory_tools.update_tasks(task, action)


@mcp.tool()
async def search_memories(
    query: str,
    search_mode: str = "hybrid",
    limit: int = 10,
    category_filter: str | None = None,
    tag_filter: list[str] | None = None,
) -> dict:
    """Search across all memory files"""
    response = await memory_tools.search_memories(query, search_mode, limit, category_filter, tag_filter)
    return response.model_dump()


@mcp.tool()
async def search_within_file(
    file_path: str,
    query: str,
    search_mode: str = "hybrid",
) -> dict:
    """Search within a specific file"""
    response = await memory_tools.search_within_file(file_path, query, search_mode)
    return response.model_dump()


@mcp.tool()
async def list_files(category: str | None = None) -> dict:
    """List all memory files"""
    return await memory_tools.list_files(category)


@mcp.tool()
async def edit_section(
    file_path: str,
    section_header: str,
    new_content: str,
    mode: str = "replace"
) -> dict:
    """Edit a specific section in a file by header"""
    return await memory_tools.edit_section(file_path, section_header, new_content, mode)


@mcp.tool()
async def find_replace(
    file_path: str,
    find: str,
    replace: str,
    regex: bool = False,
    max_replacements: int = -1
) -> dict:
    """Find and replace text in a file"""
    return await memory_tools.find_replace(file_path, find, replace, regex, max_replacements)


@mcp.tool()
async def insert_content(
    file_path: str,
    content: str,
    position: str = "end",
    marker: str | None = None
) -> dict:
    """Insert content at specific position in file"""
    return await memory_tools.insert_content(file_path, content, position, marker)


@mcp.tool()
async def extract_section(
    file_path: str,
    section_header: str
) -> dict:
    """Extract content of a specific section"""
    return await memory_tools.extract_section(file_path, section_header)


@mcp.tool()
async def list_sections(file_path: str) -> dict:
    """List all sections in a file"""
    return await memory_tools.list_sections(file_path)


@mcp.tool()
async def add_tags(file_path: str, tags: list[str]) -> dict:
    """Add tags to a memory file"""
    return await memory_tools.add_tags(file_path, tags)


@mcp.tool()
async def remove_tags(file_path: str, tags: list[str]) -> dict:
    """Remove tags from a memory file"""
    return await memory_tools.remove_tags(file_path, tags)


@mcp.tool()
async def get_tags(file_path: str) -> dict:
    """Get all tags for a memory file"""
    return await memory_tools.get_tags(file_path)


@mcp.tool()
async def batch_create_files(files: list[dict]) -> dict:
    """Create multiple memory files at once"""
    return await memory_tools.batch_create_files(files)


@mcp.tool()
async def batch_add_tags(file_paths: list[str], tags: list[str]) -> dict:
    """Add tags to multiple files at once"""
    return await memory_tools.batch_add_tags(file_paths, tags)


@mcp.tool()
async def batch_remove_tags(file_paths: list[str], tags: list[str]) -> dict:
    """Remove tags from multiple files at once"""
    return await memory_tools.batch_remove_tags(file_paths, tags)


@mcp.tool()
async def rename_file(old_file_path: str, new_title: str) -> dict:
    """Rename a memory file"""
    return await memory_tools.rename_file(old_file_path, new_title)


@mcp.tool()
async def move_file(file_path: str, new_category: str) -> dict:
    """Move a file to a different category"""
    return await memory_tools.move_file(file_path, new_category)


@mcp.tool()
async def copy_file(source_file_path: str, new_title: str, new_category: str | None = None) -> dict:
    """Create a copy of a memory file"""
    return await memory_tools.copy_file(source_file_path, new_title, new_category)


# Register MCP Resources
@mcp.resource("memory://main")
async def get_main_memory() -> str:
    """Get the main agent notes file"""
    result = await memory_tools.get_file_content("main.md")
    return result["content"]


@mcp.resource("memory://file/{file_path:path}")
async def get_memory_file(file_path: str) -> str:
    """Get a specific memory file by path"""
    result = await memory_tools.get_file_content(file_path)
    return result["content"]


# Register MCP Prompts
@mcp.prompt()
async def remember_conversation(topic: str, key_points: str) -> list[dict]:
    """Generate a prompt to save conversation memory"""
    return [
        {
            "role": "user",
            "content": f"""Please create a memory file for this conversation about: {topic}

Key points to remember:
{key_points}

Create a well-structured markdown file with:
1. A clear title
2. Date and context
3. Main discussion points
4. Important decisions or conclusions
5. Follow-up actions if any

Use the create_memory_file tool with category='conversation'."""
        }
    ]


@mcp.prompt()
async def recall_context(topic: str) -> list[dict]:
    """Generate a prompt to recall relevant context"""
    return [
        {
            "role": "user",
            "content": f"""Search my memory for information about: {topic}

Use the search_memories tool with:
- query: "{topic}"
- search_mode: "hybrid"
- limit: 10

Then summarize the relevant findings."""
        }
    ]


async def main() -> None:
    """Main entry point"""
    try:
        # Initialize server components
        await initialize_server()

        # Run MCP server (stdio transport by default)
        logger.info("starting_mcp_server", transport="stdio")
        async with mcp:
            # Server is now running
            await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("received_shutdown_signal")
    except Exception as e:
        logger.error("server_error", error=str(e), exc_info=True)
        raise
    finally:
        await shutdown_server()


if __name__ == "__main__":
    asyncio.run(main())
