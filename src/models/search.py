"""Pydantic models for search operations"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    """Search modes available"""
    HYBRID = "hybrid"      # RRF combination of vector + fulltext
    VECTOR = "vector"      # Semantic similarity only
    FULLTEXT = "fulltext"  # Keyword/BM25 only
    DIRECT = "direct"      # Direct file path lookup


class SearchRequest(BaseModel):
    """Model for search request"""
    query: str = Field(..., description="Search query")
    search_mode: SearchMode = Field(SearchMode.HYBRID, description="Search algorithm to use")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")
    category_filter: Optional[str] = Field(None, description="Filter by category")
    file_filter: Optional[str] = Field(None, description="Filter by specific file path")
    rrf_k: int = Field(60, ge=1, description="RRF k parameter for hybrid search")


class SearchResult(BaseModel):
    """Model for a single search result"""
    chunk_id: int = Field(..., description="ID of the matching chunk")
    file_path: str = Field(..., description="Path to the memory file")
    file_title: str = Field(..., description="Title of the memory file")
    file_category: str = Field(..., description="Category of the memory file")
    content: str = Field(..., description="Matching chunk content")
    header_path: list[str] = Field(..., description="Markdown header hierarchy")
    score: float = Field(..., description="Relevance score")
    search_mode: SearchMode = Field(..., description="Search mode used")


class SearchResponse(BaseModel):
    """Model for search response"""
    query: str = Field(..., description="Original query")
    results: list[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Number of results returned")
    search_mode: SearchMode = Field(..., description="Search mode used")
