"""File manager for markdown memory files"""
import hashlib
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class FileManager:
    """Manages markdown memory files on filesystem"""

    def __init__(self, memory_files_path: Path) -> None:
        """
        Initialize file manager.

        Args:
            memory_files_path: Path to memory files directory
        """
        self.memory_files_path = memory_files_path
        self.memory_files_path.mkdir(parents=True, exist_ok=True)
        logger.info("file_manager_initialized", path=str(memory_files_path))

    def read_file(self, file_path: str) -> str:
        """
        Read markdown file content.

        Args:
            file_path: Relative path to file

        Returns:
            File content as string
        """
        full_path = self.memory_files_path / file_path
        try:
            content = full_path.read_text(encoding='utf-8')
            logger.debug("file_read", file_path=file_path, size=len(content))
            return content
        except FileNotFoundError:
            logger.error("file_not_found", file_path=file_path)
            raise
        except Exception as e:
            logger.error("file_read_failed", file_path=file_path, error=str(e))
            raise

    def write_file(self, file_path: str, content: str) -> None:
        """
        Write content to markdown file.

        Args:
            file_path: Relative path to file
            content: Markdown content to write
        """
        full_path = self.memory_files_path / file_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            full_path.write_text(content, encoding='utf-8')
            logger.info("file_written", file_path=file_path, size=len(content))
        except Exception as e:
            logger.error("file_write_failed", file_path=file_path, error=str(e))
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        Delete markdown file.

        Args:
            file_path: Relative path to file

        Returns:
            True if file was deleted, False if not found
        """
        full_path = self.memory_files_path / file_path
        try:
            if full_path.exists():
                full_path.unlink()
                logger.info("file_deleted", file_path=file_path)
                return True
            else:
                logger.warning("file_not_found_for_deletion", file_path=file_path)
                return False
        except Exception as e:
            logger.error("file_deletion_failed", file_path=file_path, error=str(e))
            raise

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        full_path = self.memory_files_path / file_path
        return full_path.exists()

    def list_all_files(self) -> list[str]:
        """List all markdown files"""
        files = []
        for md_file in self.memory_files_path.rglob("*.md"):
            relative_path = md_file.relative_to(self.memory_files_path)
            files.append(str(relative_path))
        logger.debug("files_listed", count=len(files))
        return files

    def compute_file_hash(self, content: str) -> str:
        """
        Compute SHA256 hash of file content.

        Args:
            content: File content

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def get_word_count(self, content: str) -> int:
        """
        Count words in content.

        Args:
            content: Markdown content

        Returns:
            Word count
        """
        return len(content.split())
