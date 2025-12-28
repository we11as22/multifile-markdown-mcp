"""Pydantic models for memory chunks"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChunkCreate(BaseModel):
    """Model for creating a chunk"""
    file_id: int = Field(..., description="ID of the parent memory file")
    chunk_index: int = Field(..., description="Position of chunk in the file")
    content: str = Field(..., description="Chunk text content")
    content_hash: str = Field(..., description="SHA256 hash of content")
    embedding: Optional[list[float]] = Field(None, description="Embedding vector")
    header_path: list[str] = Field(default_factory=list, description="Markdown header hierarchy")
    section_level: int = Field(0, description="Depth in document structure")


class Chunk(BaseModel):
    """Model for a chunk with all fields"""
    id: int
    file_id: int
    chunk_index: int
    content: str
    content_hash: str
    embedding: Optional[list[float]]
    header_path: list[str]
    section_level: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChunkWithFile(Chunk):
    """Chunk model including parent file information"""
    file_path: str
    file_title: str
    file_category: str
