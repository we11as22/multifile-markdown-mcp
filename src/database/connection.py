"""Database connection management with asyncpg"""
import asyncpg
import structlog
from pgvector.asyncpg import register_vector
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, database_url: str, pool_min_size: int = 5, pool_max_size: int = 20) -> None:
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL
            pool_min_size: Minimum number of connections in pool
            pool_max_size: Maximum number of connections in pool
        """
        self.database_url = database_url
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self.pool: asyncpg.Pool | None = None
        self.engine: AsyncEngine | None = None
        self.async_session_maker: sessionmaker | None = None

    async def connect(self) -> None:
        """Establish database connections"""
        logger.info(
            "connecting_to_database",
            pool_min=self.pool_min_size,
            pool_max=self.pool_max_size
        )

        # Create asyncpg connection pool for raw SQL queries
        self.pool = await asyncpg.create_pool(
            self.database_url.replace('+asyncpg', ''),
            min_size=self.pool_min_size,
            max_size=self.pool_max_size,
            command_timeout=60,
        )

        # Register pgvector extension
        async with self.pool.acquire() as conn:
            await register_vector(conn)

        logger.info("asyncpg_pool_created")

        # Create SQLAlchemy async engine for ORM operations
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=pool_min_size,
            max_overflow=pool_max_size - pool_min_size,
        )

        # Create async session maker
        self.async_session_maker = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("sqlalchemy_engine_created")

    async def disconnect(self) -> None:
        """Close database connections"""
        logger.info("disconnecting_from_database")

        if self.pool:
            await self.pool.close()
            logger.info("asyncpg_pool_closed")

        if self.engine:
            await self.engine.dispose()
            logger.info("sqlalchemy_engine_disposed")

    async def get_pool(self) -> asyncpg.Pool:
        """Get asyncpg connection pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        return self.pool

    def get_session(self) -> AsyncSession:
        """Get SQLAlchemy async session"""
        if not self.async_session_maker:
            raise RuntimeError("Session maker not initialized. Call connect() first.")
        return self.async_session_maker()

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False
