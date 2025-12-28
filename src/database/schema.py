"""SQLAlchemy models for database schema"""
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)


class MemoryFileModel(Base):
    """SQLAlchemy model for memory files"""
    __tablename__ = "memory_files"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(512), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(
        String(100),
        nullable=False,
        index=True,
        server_default="other"
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        index=True
    )
    file_hash = Column(String(64), nullable=False)  # SHA256
    word_count = Column(Integer, nullable=False, default=0)
    tags = Column(ARRAY(String), nullable=False, server_default='{}')
    metadata = Column(JSON, nullable=False, server_default='{}')

    # Relationships
    chunks = relationship(
        "MemoryChunkModel",
        back_populates="file",
        cascade="all, delete-orphan"
    )
    sync_status = relationship(
        "SyncStatusModel",
        back_populates="file",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            category.in_(['main', 'project', 'concept', 'conversation', 'preference', 'other']),
            name='valid_category'
        ),
        Index('idx_memory_files_category', 'category'),
        Index('idx_memory_files_updated', 'updated_at'),
        Index('idx_memory_files_tags', 'tags', postgresql_using='gin'),
        Index('idx_memory_files_metadata', 'metadata', postgresql_using='gin'),
    )


class MemoryChunkModel(Base):
    """SQLAlchemy model for memory chunks with embeddings"""
    __tablename__ = "memory_chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey('memory_files.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA256

    # Vector embedding (dimension configurable via settings)
    embedding = Column(Vector(1536), nullable=True)

    # Markdown structure metadata
    header_path = Column(ARRAY(Text), nullable=False, server_default='{}')
    section_level = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    file = relationship("MemoryFileModel", back_populates="chunks")

    # Constraints and indexes
    __table_args__ = (
        Index('idx_chunks_file_chunk', 'file_id', 'chunk_index', unique=True),
        Index('idx_chunks_file_id', 'file_id'),
        # IVFFlat index for vector similarity search
        Index(
            'idx_chunks_embedding_ivfflat',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
        # GIN index for fulltext search (created via computed column in migration)
        Index('idx_chunks_header', 'header_path', postgresql_using='gin'),
    )

    def __repr__(self) -> str:
        return f"<MemoryChunk(id={self.id}, file_id={self.file_id}, chunk_index={self.chunk_index})>"


class SyncStatusModel(Base):
    """SQLAlchemy model for tracking file synchronization status"""
    __tablename__ = "sync_status"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(
        Integer,
        ForeignKey('memory_files.id', ondelete='CASCADE'),
        unique=True,
        nullable=False
    )
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_synced_hash = Column(String(64), nullable=True)
    sync_status = Column(String(20), nullable=False, server_default='pending')
    error_message = Column(Text, nullable=True)

    # Relationship
    file = relationship("MemoryFileModel", back_populates="sync_status")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            sync_status.in_(['pending', 'syncing', 'completed', 'failed']),
            name='valid_sync_status'
        ),
    )

    def __repr__(self) -> str:
        return f"<SyncStatus(file_id={self.file_id}, status={self.sync_status})>"
