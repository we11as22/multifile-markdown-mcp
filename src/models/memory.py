"""Pydantic models for memory files"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    """Categories for memory files"""
    MAIN = "main"
    PROJECT = "project"
    CONCEPT = "concept"
    CONVERSATION = "conversation"
    PREFERENCE = "preference"
    OTHER = "other"


class MemoryFileCreate(BaseModel):
    """Model for creating a memory file"""
    file_path: str = Field(..., description="Relative path to the memory file")
    title: str = Field(..., description="Title of the memory file")
    category: MemoryCategory = Field(..., description="Category of the memory file")
    content: str = Field(..., description="Markdown content")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization and search")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MemoryFileUpdate(BaseModel):
    """Model for updating a memory file"""
    content: Optional[str] = Field(None, description="Updated markdown content")
    title: Optional[str] = Field(None, description="Updated title")
    category: Optional[MemoryCategory] = Field(None, description="Updated category")
    tags: Optional[list[str]] = Field(None, description="Updated tags")
    metadata: Optional[dict[str, Any]] = Field(None, description="Updated metadata")


class MemoryFile(BaseModel):
    """Model for a memory file with metadata"""
    id: int
    file_path: str
    title: str
    category: MemoryCategory
    created_at: datetime
    updated_at: datetime
    file_hash: str
    word_count: int
    tags: list[str]
    metadata: dict[str, Any]

    class Config:
        from_attributes = True


class MemoryFileWithContent(MemoryFile):
    """Memory file model including the actual content"""
    content: str
