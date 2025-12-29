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
from src.mcp.tools_unified import UnifiedMemoryTools
from src.search.chunking import MarkdownChunker
from src.search.hybrid_search import HybridSearchEngine
from src.storage.file_manager import FileManager
from src.storage.index_structure import IndexManager, JsonIndexManager
from src.sync.sync_service import FileSyncService

# Configure structured logging
logging.config.dictConfig(settings.get_log_config())
logger = structlog.get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP(settings.mcp_server_name)

# Global state
db_manager: DatabaseManager
memory_tools: MemoryTools
unified_tools: UnifiedMemoryTools


async def initialize_server() -> None:
    """Initialize all server components"""
    global db_manager, memory_tools, unified_tools

    logger.info("initializing_agent_memory_mcp_server", version="0.1.0")

    # Initialize database connection (if enabled)
    db_manager = None
    repository = None
    sync_service = None
    search_engine = None
    
    if settings.use_database:
        db_manager = DatabaseManager(
            database_url=settings.database_url,
            pool_min_size=settings.db_pool_min_size,
            pool_max_size=settings.db_pool_max_size,
        )
        await db_manager.connect()

        # Check database health
        if not await db_manager.health_check():
            raise RuntimeError("Database health check failed")
    else:
        logger.info("database_disabled_using_file_only_mode")

    # Initialize embedding provider (only if database is enabled)
    embedding_provider = None
    if settings.use_database and settings.embedding_provider:
        try:
            settings.validate_provider_config()
            embedding_provider = create_embedding_provider(settings)
            logger.info("embedding_provider_created", provider=settings.embedding_provider)
        except Exception as e:
            logger.warning(
                "embedding_provider_initialization_failed_using_fulltext_only",
                error=str(e)
            )
    elif not settings.use_database:
        logger.info("database_disabled_embedding_provider_not_used")

    # Initialize file manager
    file_manager = FileManager(settings.memory_files_path_obj)

    # Initialize index managers
    index_manager = IndexManager(settings.main_file_path)
    json_index_path = settings.memory_files_path_obj / "files_index.json"
    json_index_manager = JsonIndexManager(json_index_path)

    # Initialize chunker (only if database is enabled)
    chunker = None
    if settings.use_database:
        chunker = MarkdownChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    # Initialize repository and sync service (only if database is enabled)
    if settings.use_database and db_manager:
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
        finally:
            await session.close()

    # Initialize memory tools
    memory_tools = MemoryTools(
        file_manager=file_manager,
        index_manager=index_manager,
        json_index_manager=json_index_manager,
        repository=repository,
        sync_service=sync_service,
        search_engine=search_engine,
    )
    
    # Initialize unified tools
    unified_tools = UnifiedMemoryTools(memory_tools)

    logger.info("server_initialized_successfully", use_database=settings.use_database)


async def shutdown_server() -> None:
    """Cleanup on server shutdown"""
    logger.info("shutting_down_server")
    if db_manager:
        await db_manager.disconnect()
    logger.info("server_shutdown_complete")


# Register MCP Tools - 9 универсальных инструментов

@mcp.tool()
async def files(
    operation: str,
    items: list[dict],
) -> dict:
    """
    Универсальное управление файлами. Всегда работает с массивом операций.
    
    Args:
        operation: Тип операции (create, read, update, delete, move, copy, rename, list)
        items: Массив элементов для обработки
        
    Returns:
        Результаты операций с успешными и неудачными
    """
    return await unified_tools.files(operation, items)


@mcp.tool()
async def search(queries: list[dict]) -> dict:
    """
    Универсальный поиск. Всегда работает с массивом запросов.
    
    Args:
        queries: Массив запросов, каждый содержит:
            - query: Текст запроса
            - search_mode: hybrid/vector/fulltext (default: hybrid)
            - limit: Максимум результатов (default: 10)
            - file_path: Опциональный путь файла
            - category_filter: Опциональный фильтр категории
            - tag_filter: Опциональный массив тегов
            
    Returns:
        Результаты поиска для каждого запроса
    """
    return await unified_tools.search(queries)


@mcp.tool()
async def edit(operations: list[dict]) -> dict:
    """
    Универсальное редактирование. Всегда работает с массивом операций.
    
    Args:
        operations: Массив операций редактирования, каждая содержит:
            - file_path: Путь к файлу
            - edit_type: section/find_replace/insert
            - ... остальные параметры зависят от edit_type
            
    Returns:
        Результаты редактирования
    """
    return await unified_tools.edit(operations)


@mcp.tool()
async def tags(
    operation: str,
    items: list[dict],
) -> dict:
    """
    Универсальное управление тегами. Всегда работает с массивом файлов.
    
    Args:
        operation: Тип операции (add, remove, get)
        items: Массив элементов, каждый содержит:
            - file_path: Путь к файлу
            - tags: Массив тегов (для add/remove)
            
    Returns:
        Результаты операций
    """
    return await unified_tools.tags(operation, items)


@mcp.tool()
async def main(
    operation: str,
    items: list[dict],
) -> dict:
    """
    Универсальные операции с main.md. Всегда работает с массивом операций.
    
    Args:
        operation: Тип операции (append, goal, task, plan)
        items: Массив элементов для обработки
        
    Returns:
        Результаты операций
    """
    return await unified_tools.main(operation, items)


@mcp.tool()
async def memory(operation: str) -> dict:
    """
    Управление памятью (инициализация и сброс).
    
    Args:
        operation: Тип операции (initialize, reset)
        
    Returns:
        Результат операции
    """
    return await unified_tools.memory(operation)


@mcp.tool()
async def extract(requests: list[dict]) -> dict:
    """
    Извлечение секций из файлов. Всегда работает с массивом запросов.
    
    Args:
        requests: Массив запросов, каждый содержит:
            - file_path: Путь к файлу
            - section_header: Заголовок секции
            
    Returns:
        Результаты извлечения
    """
    return await unified_tools.extract(requests)


@mcp.tool()
async def list(requests: list[dict]) -> dict:
    """
    Получение списков файлов или секций. Всегда работает с массивом запросов.
    
    Args:
        requests: Массив запросов, каждый содержит:
            - type: "files" или "sections"
            - category: Опциональная категория (для files)
            - file_path: Путь к файлу (для sections)
            
    Returns:
        Результаты списков
    """
    return await unified_tools.list(requests)


@mcp.tool()
async def help(topic: str | None = None) -> dict:
    """
    Единый инструмент для получения помощи, рекомендаций, гайдов и примеров использования.
    
    Args:
        topic: Опциональная тема для конкретной помощи:
            - None или "all": Полный гайд
            - "files": Управление файлами
            - "search": Поиск
            - "edit": Редактирование
            - "tags": Теги
            - "main": Операции с main.md
            - "memory": Управление памятью
            - "examples": Примеры использования
            
    Returns:
        Полный гайд с рекомендациями и примерами
    """
    return await unified_tools.help(topic)


# Register MCP Resources
@mcp.resource("memory://main")
async def get_main_memory() -> str:
    """Get the main agent notes file"""
    result = await memory_tools.get_file_content("main.md")
    return result["content"]


@mcp.resource("memory://file/{file_path}")
async def get_memory_file(file_path: str) -> str:
    """Get a specific memory file by path"""
    result = await memory_tools.get_file_content(file_path)
    return result["content"]


# Register MCP Prompts
@mcp.prompt()
async def remember_conversation(topic: str, key_points: str):
    """Generate a prompt to save conversation memory with detailed instructions"""
    from src.mcp.prompts import remember_conversation_prompt
    return remember_conversation_prompt(topic, key_points)


@mcp.prompt()
async def recall_context(topic: str):
    """Generate a prompt to recall relevant context with search instructions"""
    from src.mcp.prompts import recall_context_prompt
    return recall_context_prompt(topic)


@mcp.prompt()
async def memory_usage_guide() -> str:
    """Get comprehensive guide on using the memory system"""
    from src.mcp.prompts import get_memory_usage_prompt
    return get_memory_usage_prompt()


@mcp.prompt()
async def active_memory_usage() -> str:
    """Get prompt encouraging active memory usage"""
    from src.mcp.prompts import active_memory_usage_prompt
    return active_memory_usage_prompt()


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


def cli_main() -> None:
    """CLI entry point for pip installation"""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
