"""Database repository for CRUD operations"""
from datetime import datetime
from typing import Any, Optional

import asyncpg
import structlog
from pgvector.asyncpg import register_vector
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.schema import MemoryChunkModel, MemoryFileModel, SyncStatusModel
from src.models.chunk import Chunk, ChunkCreate
from src.models.memory import MemoryCategory, MemoryFile

logger = structlog.get_logger(__name__)


class MemoryRepository:
    """Repository for memory file and chunk operations"""

    def __init__(self, session: AsyncSession, pool: asyncpg.Pool) -> None:
        """
        Initialize repository.

        Args:
            session: SQLAlchemy async session
            pool: asyncpg connection pool for raw SQL
        """
        self.session = session
        self.pool = pool

    # ======================
    # Memory Files
    # ======================

    async def create_file(
        self,
        file_path: str,
        title: str,
        category: MemoryCategory,
        file_hash: str,
        word_count: int,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> MemoryFile:
        """Create a new memory file"""
        file_model = MemoryFileModel(
            file_path=file_path,
            title=title,
            category=category.value,
            file_hash=file_hash,
            word_count=word_count,
            tags=tags,
            metadata=metadata,
        )

        self.session.add(file_model)
        await self.session.commit()
        await self.session.refresh(file_model)

        logger.info("memory_file_created", file_id=file_model.id, file_path=file_path)
        # Convert file_metadata to dict - handle both dict and JSON types
        if hasattr(file_model.file_metadata, '__dict__'):
            metadata_dict = {}
        elif isinstance(file_model.file_metadata, dict):
            metadata_dict = file_model.file_metadata
        else:
            # Try to convert JSON/other types to dict
            try:
                import json
                if hasattr(file_model.file_metadata, 'copy'):
                    metadata_dict = file_model.file_metadata.copy()
                else:
                    metadata_dict = dict(file_model.file_metadata) if file_model.file_metadata else {}
            except (TypeError, AttributeError):
                metadata_dict = {}
        file_dict = {
            "id": file_model.id,
            "file_path": file_model.file_path,
            "title": file_model.title,
            "category": file_model.category,
            "created_at": file_model.created_at,
            "updated_at": file_model.updated_at,
            "file_hash": file_model.file_hash,
            "word_count": file_model.word_count,
            "tags": file_model.tags or [],
            "metadata": metadata_dict,
        }
        return MemoryFile.model_validate(file_dict)

    async def get_file_by_id(self, file_id: int) -> Optional[MemoryFile]:
        """Get memory file by ID"""
        result = await self.session.execute(
            select(MemoryFileModel).where(MemoryFileModel.id == file_id)
        )
        file_model = result.scalar_one_or_none()
        if file_model:
            metadata_dict = file_model.file_metadata if isinstance(file_model.file_metadata, dict) else {}
            file_dict = {
                "id": file_model.id,
                "file_path": file_model.file_path,
                "title": file_model.title,
                "category": file_model.category,
                "created_at": file_model.created_at,
                "updated_at": file_model.updated_at,
                "file_hash": file_model.file_hash,
                "word_count": file_model.word_count,
                "tags": file_model.tags or [],
                "metadata": metadata_dict,
            }
            return MemoryFile.model_validate(file_dict)
        return None

    async def get_file_by_path(self, file_path: str) -> Optional[MemoryFile]:
        """Get memory file by path"""
        result = await self.session.execute(
            select(MemoryFileModel).where(MemoryFileModel.file_path == file_path)
        )
        file_model = result.scalar_one_or_none()
        if file_model:
            # Convert file_metadata to dict - handle both dict and JSON types
            if isinstance(file_model.file_metadata, dict):
                metadata_dict = file_model.file_metadata
            else:
                try:
                    metadata_dict = dict(file_model.file_metadata) if file_model.file_metadata else {}
                except (TypeError, AttributeError):
                    metadata_dict = {}
            # Create dict for validation
            file_dict = {
                "id": file_model.id,
                "file_path": file_model.file_path,
                "title": file_model.title,
                "category": file_model.category,
                "created_at": file_model.created_at,
                "updated_at": file_model.updated_at,
                "file_hash": file_model.file_hash,
                "word_count": file_model.word_count,
                "tags": file_model.tags or [],
                "metadata": metadata_dict,
            }
            return MemoryFile.model_validate(file_dict)
        return None

    async def get_all_files(self, category: Optional[MemoryCategory] = None) -> list[MemoryFile]:
        """Get all memory files, optionally filtered by category"""
        query = select(MemoryFileModel)
        if category:
            query = query.where(MemoryFileModel.category == category.value)

        result = await self.session.execute(query.order_by(MemoryFileModel.updated_at.desc()))
        files = result.scalars().all()
        result_files = []
        for f in files:
            metadata_dict = f.file_metadata if isinstance(f.file_metadata, dict) else {}
            file_dict = {
                "id": f.id,
                "file_path": f.file_path,
                "title": f.title,
                "category": f.category,
                "created_at": f.created_at,
                "updated_at": f.updated_at,
                "file_hash": f.file_hash,
                "word_count": f.word_count,
                "tags": f.tags or [],
                "metadata": metadata_dict,
            }
            result_files.append(MemoryFile.model_validate(file_dict))
        return result_files

    async def upsert_file(
        self,
        file_path: str,
        title: str,
        category: MemoryCategory,
        file_hash: str,
        word_count: int,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> int:
        """Create or update a memory file, return file_id"""
        # Check if file exists
        existing = await self.get_file_by_path(file_path)

        if existing:
            # Update existing file
            await self.session.execute(
                update(MemoryFileModel)
                .where(MemoryFileModel.file_path == file_path)
                .values(
                    title=title,
                    category=category.value,
                    file_hash=file_hash,
                    word_count=word_count,
                    tags=tags,
                    file_metadata=metadata,
                    updated_at=datetime.utcnow(),
                )
            )
            await self.session.commit()
            logger.info("memory_file_updated", file_id=existing.id, file_path=file_path)
            return existing.id
        else:
            # Create new file
            file = await self.create_file(file_path, title, category, file_hash, word_count, tags, metadata)
            return file.id

    async def delete_file(self, file_id: int) -> bool:
        """Delete a memory file and all its chunks"""
        result = await self.session.execute(
            delete(MemoryFileModel).where(MemoryFileModel.id == file_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("memory_file_deleted", file_id=file_id)
        return deleted

    async def get_file_hash(self, file_path: str) -> Optional[str]:
        """Get file hash for change detection"""
        result = await self.session.execute(
            select(MemoryFileModel.file_hash).where(MemoryFileModel.file_path == file_path)
        )
        return result.scalar_one_or_none()

    # ======================
    # Memory Chunks
    # ======================

    async def create_chunk(self, chunk: ChunkCreate) -> Chunk:
        """Create a new memory chunk"""
        chunk_model = MemoryChunkModel(
            file_id=chunk.file_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=chunk.content_hash,
            embedding=chunk.embedding,
            header_path=chunk.header_path,
            section_level=chunk.section_level,
        )

        self.session.add(chunk_model)
        await self.session.commit()
        await self.session.refresh(chunk_model)

        return Chunk.model_validate(chunk_model)

    async def insert_chunks(self, chunks: list[ChunkCreate]) -> None:
        """Batch insert multiple chunks"""
        chunk_models = [
            MemoryChunkModel(
                file_id=chunk.file_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                embedding=chunk.embedding,
                header_path=chunk.header_path,
                section_level=chunk.section_level,
            )
            for chunk in chunks
        ]

        self.session.add_all(chunk_models)
        await self.session.commit()
        logger.info("chunks_inserted", count=len(chunks))

    async def delete_chunks(self, file_id: int) -> int:
        """Delete all chunks for a file"""
        result = await self.session.execute(
            delete(MemoryChunkModel).where(MemoryChunkModel.file_id == file_id)
        )
        await self.session.commit()
        deleted_count = result.rowcount
        logger.info("chunks_deleted", file_id=file_id, count=deleted_count)
        return deleted_count

    async def get_chunks_by_file(self, file_id: int) -> list[Chunk]:
        """Get all chunks for a file"""
        result = await self.session.execute(
            select(MemoryChunkModel)
            .where(MemoryChunkModel.file_id == file_id)
            .order_by(MemoryChunkModel.chunk_index)
        )
        chunks = result.scalars().all()
        return [Chunk.model_validate(c) for c in chunks]

    # ======================
    # Sync Status
    # ======================

    async def create_sync_status(self, file_id: int) -> None:
        """Create sync status for a file"""
        sync_model = SyncStatusModel(
            file_id=file_id,
            sync_status='pending'
        )
        self.session.add(sync_model)
        await self.session.commit()

    async def update_sync_status(
        self,
        file_id: int,
        status: str,
        synced_hash: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update sync status for a file"""
        values: dict[str, Any] = {
            'sync_status': status,
        }

        if status == 'completed':
            values['last_synced_at'] = datetime.utcnow()
            values['last_synced_hash'] = synced_hash
            values['error_message'] = None
        elif status == 'failed':
            values['error_message'] = error_message

        await self.session.execute(
            update(SyncStatusModel)
            .where(SyncStatusModel.file_id == file_id)
            .values(**values)
        )
        await self.session.commit()
        logger.info("sync_status_updated", file_id=file_id, status=status)

    async def get_sync_status(self, file_id: int) -> Optional[dict[str, Any]]:
        """Get sync status for a file"""
        result = await self.session.execute(
            select(SyncStatusModel).where(SyncStatusModel.file_id == file_id)
        )
        sync = result.scalar_one_or_none()
        if not sync:
            return None

        return {
            'file_id': sync.file_id,
            'last_synced_at': sync.last_synced_at,
            'last_synced_hash': sync.last_synced_hash,
            'sync_status': sync.sync_status,
            'error_message': sync.error_message,
        }
