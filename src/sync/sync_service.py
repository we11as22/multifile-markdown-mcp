"""File synchronization service"""
from pathlib import Path
from typing import Optional

import structlog

from src.database.repository import MemoryRepository
from src.embeddings.base import EmbeddingProvider
from src.models.chunk import ChunkCreate
from src.models.memory import MemoryCategory
from src.search.chunking import MarkdownChunker
from src.storage.file_manager import FileManager

logger = structlog.get_logger(__name__)


class FileSyncService:
    """Manages bidirectional sync between markdown files and database"""

    def __init__(
        self,
        file_manager: FileManager,
        repository: MemoryRepository,
        chunker: MarkdownChunker,
        embedding_provider: Optional[EmbeddingProvider] = None,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize file sync service.

        Args:
            file_manager: File manager for markdown operations
            repository: Database repository
            chunker: Markdown chunker
            embedding_provider: Embedding provider (optional, fulltext-only mode if None)
            batch_size: Batch size for embedding generation
        """
        self.file_manager = file_manager
        self.repository = repository
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.batch_size = batch_size
        logger.info("file_sync_service_initialized", batch_size=batch_size)

    async def sync_file(self, file_path: str, force: bool = False) -> None:
        """
        Sync a single file to database.

        Args:
            file_path: Relative path to file
            force: Force sync even if hash matches
        """
        logger.info("syncing_file", file_path=file_path, force=force)

        try:
            # Read file content
            content = self.file_manager.read_file(file_path)
            file_hash = self.file_manager.compute_file_hash(content)

            # Check if sync needed
            if not force:
                db_hash = await self.repository.get_file_hash(file_path)
                if db_hash == file_hash:
                    logger.debug("file_unchanged_skipping_sync", file_path=file_path)
                    return

            # Extract metadata
            metadata = self._extract_metadata(file_path, content)

            # Upsert file record
            file_id = await self.repository.upsert_file(
                file_path=file_path,
                title=metadata['title'],
                category=metadata['category'],
                file_hash=file_hash,
                word_count=self.file_manager.get_word_count(content),
                tags=metadata.get('tags', []),
                metadata=metadata.get('extra', {})
            )

            # Delete old chunks
            await self.repository.delete_chunks(file_id)

            # Chunk content
            chunks = self.chunker.chunk_markdown(content, file_path)

            if not chunks:
                logger.warning("no_chunks_generated", file_path=file_path)
                return

            # Generate embeddings in batches (if provider available)
            all_embeddings = []
            if self.embedding_provider is not None:
                chunk_texts = [c['content'] for c in chunks]
                for i in range(0, len(chunk_texts), self.batch_size):
                    batch = chunk_texts[i:i + self.batch_size]
                    embeddings = await self.embedding_provider.embed_batch(batch)
                    all_embeddings.extend(embeddings)
                    logger.debug(
                        "embeddings_generated",
                        batch_start=i,
                        batch_size=len(batch)
                    )
            else:
                # No embeddings - fulltext-only mode
                all_embeddings = [None] * len(chunks)
                logger.info("no_embeddings_provider_fulltext_only_mode")

            # Create chunk objects
            chunk_creates = [
                ChunkCreate(
                    file_id=file_id,
                    chunk_index=chunk['chunk_index'],
                    content=chunk['content'],
                    content_hash=chunk['content_hash'],
                    embedding=embedding,
                    header_path=chunk['header_path'],
                    section_level=chunk['section_level']
                )
                for chunk, embedding in zip(chunks, all_embeddings)
            ]

            # Insert chunks
            await self.repository.insert_chunks(chunk_creates)

            # Update sync status
            await self.repository.update_sync_status(
                file_id=file_id,
                status='completed',
                synced_hash=file_hash
            )

            logger.info(
                "file_synced_successfully",
                file_path=file_path,
                chunks_count=len(chunks)
            )

        except Exception as e:
            logger.error("file_sync_failed", file_path=file_path, error=str(e))
            raise

    async def sync_all_files(self) -> None:
        """Sync all markdown files to database"""
        logger.info("syncing_all_files")

        files = self.file_manager.list_all_files()
        logger.info("files_to_sync", count=len(files))

        for file_path in files:
            try:
                await self.sync_file(file_path)
            except Exception as e:
                logger.error("failed_to_sync_file", file_path=file_path, error=str(e))

        logger.info("all_files_synced", total=len(files))

    def _extract_metadata(self, file_path: str, content: str) -> dict:
        """
        Extract metadata from file path and content.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            Metadata dictionary
        """
        path = Path(file_path)

        # Determine category from parent directory
        parent_dir = path.parent.name if path.parent.name != 'memory_files' else 'other'

        category_map = {
            'projects': MemoryCategory.PROJECT,
            'concepts': MemoryCategory.CONCEPT,
            'conversations': MemoryCategory.CONVERSATION,
            'preferences': MemoryCategory.PREFERENCE,
        }

        category = category_map.get(parent_dir, MemoryCategory.OTHER)

        # Generate title from filename
        title = path.stem.replace('_', ' ').title()

        # TODO: Parse YAML frontmatter if present for additional metadata and tags
        tags = []  # Empty for now, will be extracted from frontmatter later

        return {
            'title': title,
            'category': category,
            'tags': tags,
            'extra': {}
        }
