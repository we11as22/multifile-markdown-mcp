"""Hybrid search engine with RRF (Reciprocal Rank Fusion)"""
from typing import Any, Optional

import asyncpg
import structlog
from pgvector.asyncpg import register_vector

from src.embeddings.base import EmbeddingProvider
from src.models.search import SearchMode, SearchResult

logger = structlog.get_logger(__name__)


class HybridSearchEngine:
    """RRF-based hybrid search combining vector and fulltext"""

    def __init__(self, db_pool: asyncpg.Pool, embedding_provider: Optional[EmbeddingProvider] = None) -> None:
        """
        Initialize hybrid search engine.

        Args:
            db_pool: asyncpg connection pool
            embedding_provider: Embedding provider for query vectorization (optional, falls back to fulltext-only)
        """
        self.db_pool = db_pool
        self.embedding_provider = embedding_provider
        self.has_embeddings = embedding_provider is not None
        logger.info("hybrid_search_engine_initialized", has_embeddings=self.has_embeddings)

    async def search(
        self,
        query: str,
        search_mode: SearchMode = SearchMode.HYBRID,
        limit: int = 20,
        rrf_k: int = 60,
        category_filter: Optional[str] = None,
        file_filter: Optional[str] = None,
        tag_filter: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """
        Perform search with specified mode.

        Args:
            query: Search query
            search_mode: Search algorithm to use
            limit: Maximum number of results
            rrf_k: RRF k parameter for hybrid search
            category_filter: Filter by category
            file_filter: Filter by specific file path
            tag_filter: Filter by tags (files must have ALL specified tags)

        Returns:
            List of search results sorted by relevance
        """
        # Graceful degradation: fallback to fulltext if no embeddings
        if not self.has_embeddings and search_mode in (SearchMode.HYBRID, SearchMode.VECTOR):
            logger.warning(
                "no_embeddings_available_fallback_to_fulltext",
                requested_mode=search_mode.value
            )
            search_mode = SearchMode.FULLTEXT

        if search_mode == SearchMode.HYBRID:
            return await self._hybrid_search(query, limit, rrf_k, category_filter, file_filter, tag_filter)
        elif search_mode == SearchMode.VECTOR:
            return await self._vector_search(query, limit, category_filter, file_filter, tag_filter)
        elif search_mode == SearchMode.FULLTEXT:
            return await self._fulltext_search(query, limit, category_filter, file_filter, tag_filter)
        else:
            raise ValueError(f"Unsupported search mode: {search_mode}")

    async def _hybrid_search(
        self,
        query: str,
        limit: int,
        rrf_k: int,
        category_filter: Optional[str],
        file_filter: Optional[str],
        tag_filter: Optional[list[str]],
    ) -> list[SearchResult]:
        """Execute hybrid RRF search"""
        logger.info("executing_hybrid_search", query=query, limit=limit)

        # Generate query embedding
        query_embedding = await self.embedding_provider.embed_text(query)

        async with self.db_pool.acquire() as conn:
            await register_vector(conn)

            # Build filter clauses
            filter_clause = ""
            params: list[Any] = [query, query_embedding, limit, rrf_k]
            param_num = 5

            if category_filter:
                filter_clause += f" AND mf.category = ${param_num}"
                params.append(category_filter)
                param_num += 1

            if file_filter:
                filter_clause += f" AND mf.file_path = ${param_num}"
                params.append(file_filter)
                param_num += 1

            if tag_filter:
                filter_clause += f" AND mf.tags @> ${param_num}"
                params.append(tag_filter)
                param_num += 1

            # Execute hybrid search query
            query_sql = f"""
                WITH vector_search AS (
                    SELECT
                        mc.id,
                        mc.file_id,
                        mc.content,
                        mc.header_path,
                        mf.file_path,
                        mf.title,
                        mf.category,
                        ROW_NUMBER() OVER (ORDER BY mc.embedding <=> $2) AS rank
                    FROM memory_chunks mc
                    JOIN memory_files mf ON mc.file_id = mf.id
                    WHERE mc.embedding IS NOT NULL {filter_clause}
                    ORDER BY mc.embedding <=> $2
                    LIMIT $3
                ),
                fulltext_search AS (
                    SELECT
                        mc.id,
                        mc.file_id,
                        mc.content,
                        mc.header_path,
                        mf.file_path,
                        mf.title,
                        mf.category,
                        ROW_NUMBER() OVER (
                            ORDER BY ts_rank(mc.content_tsvector, websearch_to_tsquery('english', $1)) DESC
                        ) AS rank
                    FROM memory_chunks mc
                    JOIN memory_files mf ON mc.file_id = mf.id
                    WHERE mc.content_tsvector @@ websearch_to_tsquery('english', $1) {filter_clause}
                    ORDER BY ts_rank(mc.content_tsvector, websearch_to_tsquery('english', $1)) DESC
                    LIMIT $3
                ),
                combined AS (
                    SELECT
                        COALESCE(v.id, f.id) AS chunk_id,
                        COALESCE(v.file_path, f.file_path) AS file_path,
                        COALESCE(v.title, f.title) AS title,
                        COALESCE(v.category, f.category) AS category,
                        COALESCE(v.content, f.content) AS content,
                        COALESCE(v.header_path, f.header_path) AS header_path,
                        rrf_score(v.rank, $4) + rrf_score(f.rank, $4) AS rrf_score
                    FROM vector_search v
                    FULL OUTER JOIN fulltext_search f ON v.id = f.id
                )
                SELECT *
                FROM combined
                ORDER BY rrf_score DESC
                LIMIT $3;
            """

            results = await conn.fetch(query_sql, *params)

            search_results = [
                SearchResult(
                    chunk_id=r['chunk_id'],
                    file_path=r['file_path'],
                    file_title=r['title'],
                    file_category=r['category'],
                    content=r['content'],
                    header_path=r['header_path'] or [],
                    score=float(r['rrf_score']),
                    search_mode=SearchMode.HYBRID
                )
                for r in results
            ]

            logger.info("hybrid_search_completed", results_count=len(search_results))
            return search_results

    async def _vector_search(
        self,
        query: str,
        limit: int,
        category_filter: Optional[str],
        file_filter: Optional[str],
        tag_filter: Optional[list[str]],
    ) -> list[SearchResult]:
        """Execute vector-only search"""
        logger.info("executing_vector_search", query=query, limit=limit)

        query_embedding = await self.embedding_provider.embed_text(query)

        async with self.db_pool.acquire() as conn:
            await register_vector(conn)

            filter_clause = ""
            params: list[Any] = [query_embedding, limit]
            param_num = 3

            if category_filter:
                filter_clause += f" AND mf.category = ${param_num}"
                params.append(category_filter)
                param_num += 1

            if file_filter:
                filter_clause += f" AND mf.file_path = ${param_num}"
                params.append(file_filter)
                param_num += 1

            if tag_filter:
                filter_clause += f" AND mf.tags @> ${param_num}"
                params.append(tag_filter)
                param_num += 1

            results = await conn.fetch(f"""
                SELECT
                    mc.id as chunk_id,
                    mf.file_path,
                    mf.title,
                    mf.category,
                    mc.content,
                    mc.header_path,
                    1 - (mc.embedding <=> $1) as similarity
                FROM memory_chunks mc
                JOIN memory_files mf ON mc.file_id = mf.id
                WHERE mc.embedding IS NOT NULL {filter_clause}
                ORDER BY mc.embedding <=> $1
                LIMIT $2
            """, *params)

            search_results = [
                SearchResult(
                    chunk_id=r['chunk_id'],
                    file_path=r['file_path'],
                    file_title=r['title'],
                    file_category=r['category'],
                    content=r['content'],
                    header_path=r['header_path'] or [],
                    score=float(r['similarity']),
                    search_mode=SearchMode.VECTOR
                )
                for r in results
            ]

            logger.info("vector_search_completed", results_count=len(search_results))
            return search_results

    async def _fulltext_search(
        self,
        query: str,
        limit: int,
        category_filter: Optional[str],
        file_filter: Optional[str],
        tag_filter: Optional[list[str]],
    ) -> list[SearchResult]:
        """Execute fulltext-only search"""
        logger.info("executing_fulltext_search", query=query, limit=limit)

        async with self.db_pool.acquire() as conn:
            filter_clause = ""
            params: list[Any] = [query, limit]
            param_num = 3

            if category_filter:
                filter_clause += f" AND mf.category = ${param_num}"
                params.append(category_filter)
                param_num += 1

            if file_filter:
                filter_clause += f" AND mf.file_path = ${param_num}"
                params.append(file_filter)
                param_num += 1

            if tag_filter:
                filter_clause += f" AND mf.tags @> ${param_num}"
                params.append(tag_filter)
                param_num += 1

            results = await conn.fetch(f"""
                SELECT
                    mc.id as chunk_id,
                    mf.file_path,
                    mf.title,
                    mf.category,
                    mc.content,
                    mc.header_path,
                    ts_rank(mc.content_tsvector, websearch_to_tsquery('english', $1)) as rank
                FROM memory_chunks mc
                JOIN memory_files mf ON mc.file_id = mf.id
                WHERE mc.content_tsvector @@ websearch_to_tsquery('english', $1) {filter_clause}
                ORDER BY rank DESC
                LIMIT $2
            """, *params)

            search_results = [
                SearchResult(
                    chunk_id=r['chunk_id'],
                    file_path=r['file_path'],
                    file_title=r['title'],
                    file_category=r['category'],
                    content=r['content'],
                    header_path=r['header_path'] or [],
                    score=float(r['rank']),
                    search_mode=SearchMode.FULLTEXT
                )
                for r in results
            ]

            logger.info("fulltext_search_completed", results_count=len(search_results))
            return search_results
