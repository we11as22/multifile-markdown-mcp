"""Intelligent markdown chunking with header preservation"""
import hashlib
from typing import Any

import structlog
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logger = structlog.get_logger(__name__)


class MarkdownChunker:
    """Intelligent markdown chunking with header context preservation"""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 200) -> None:
        """
        Initialize markdown chunker.

        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Split by markdown headers first
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4"),
            ],
            strip_headers=False
        )

        # Further split large sections
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        logger.info(
            "markdown_chunker_initialized",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def chunk_markdown(self, content: str, file_path: str) -> list[dict[str, Any]]:
        """
        Split markdown into semantic chunks with header context.

        Args:
            content: Markdown content to chunk
            file_path: Path to the file (for logging)

        Returns:
            List of chunk dictionaries with:
            - content: chunk text
            - header_path: list of header hierarchy
            - section_level: depth in document
            - chunk_index: position in file
            - content_hash: SHA256 hash of content
        """
        try:
            # First split by headers
            header_splits = self.header_splitter.split_text(content)

            chunks = []
            chunk_index = 0

            for doc in header_splits:
                # Extract header metadata
                metadata = doc.metadata
                header_path = [
                    metadata.get('h1', ''),
                    metadata.get('h2', ''),
                    metadata.get('h3', ''),
                    metadata.get('h4', '')
                ]
                # Remove empty strings
                header_path = [h for h in header_path if h]
                section_level = len(header_path)

                chunk_content = doc.page_content

                # If section is large, split further
                if len(chunk_content) > self.chunk_size:
                    sub_chunks = self.text_splitter.split_text(chunk_content)
                    for sub_chunk in sub_chunks:
                        chunks.append({
                            'content': sub_chunk,
                            'header_path': header_path,
                            'section_level': section_level,
                            'chunk_index': chunk_index,
                            'content_hash': self._hash_content(sub_chunk)
                        })
                        chunk_index += 1
                else:
                    chunks.append({
                        'content': chunk_content,
                        'header_path': header_path,
                        'section_level': section_level,
                        'chunk_index': chunk_index,
                        'content_hash': self._hash_content(chunk_content)
                    })
                    chunk_index += 1

            logger.info(
                "markdown_chunked",
                file_path=file_path,
                total_chunks=len(chunks),
                content_size=len(content)
            )

            return chunks

        except Exception as e:
            logger.error(
                "markdown_chunking_failed",
                file_path=file_path,
                error=str(e)
            )
            # Fallback: return whole content as single chunk
            return [{
                'content': content,
                'header_path': [],
                'section_level': 0,
                'chunk_index': 0,
                'content_hash': self._hash_content(content)
            }]

    def _hash_content(self, content: str) -> str:
        """Compute SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
