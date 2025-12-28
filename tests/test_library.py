"""Tests for library usage"""
import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from src.library import MemoryLibrary


# Skip tests if database is not available
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("POSTGRES_HOST"),
    reason="Database connection required for tests"
)


@pytest.mark.asyncio
async def test_library_initialization():
    """Test basic library initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use database URL from environment or settings
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            # Try to construct from individual env vars
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Check that main.md and files_index.json were created
        assert (Path(tmpdir) / "main.md").exists()
        assert (Path(tmpdir) / "files_index.json").exists()

        await memory.close()


@pytest.mark.asyncio
async def test_create_file():
    """Test creating a memory file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create a file
        result = await memory.create_file(
            title="Test File",
            category="project",
            content="# Test File\n\nThis is a test.",
            tags=["test"],
        )

        assert result["file_path"] == "projects/test_file.md"
        assert result["title"] == "Test File"

        # Check file exists
        assert (Path(tmpdir) / "projects" / "test_file.md").exists()

        await memory.close()


@pytest.mark.asyncio
async def test_get_file():
    """Test getting file content"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create a file
        await memory.create_file(
            title="Test File",
            category="project",
            content="# Test File\n\nThis is a test.",
        )

        # Get file content
        result = await memory.get_file("projects/test_file.md")

        assert result["file_path"] == "projects/test_file.md"
        assert "Test File" in result["content"]

        await memory.close()


@pytest.mark.asyncio
async def test_list_files():
    """Test listing files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create multiple files
        await memory.create_file(
            title="Project 1",
            category="project",
            content="# Project 1",
        )
        await memory.create_file(
            title="Concept 1",
            category="concept",
            content="# Concept 1",
        )

        # List all files
        result = await memory.list_files()
        assert result["total"] >= 2

        # List by category
        result = await memory.list_files(category="project")
        assert result["total"] >= 1

        await memory.close()


@pytest.mark.asyncio
async def test_batch_create_files():
    """Test batch file creation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create multiple files at once
        files = [
            {
                "title": "File 1",
                "category": "project",
                "content": "# File 1",
            },
            {
                "title": "File 2",
                "category": "concept",
                "content": "# File 2",
            },
        ]

        result = await memory.batch_create_files(files)

        assert result["success_count"] == 2
        assert result["error_count"] == 0
        assert len(result["created"]) == 2

        await memory.close()


@pytest.mark.asyncio
async def test_initialize_memory():
    """Test memory initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Initialize memory (should create base structure)
        result = await memory.initialize_memory()

        assert result["message"] == "Memory initialized successfully"
        assert "main.md" in result["main_file"]
        assert "files_index.json" in result["index_file"]

        await memory.close()


@pytest.mark.asyncio
async def test_reset_memory():
    """Test memory reset"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create some files
        await memory.create_file(
            title="Test File",
            category="project",
            content="# Test",
        )

        # Reset memory
        result = await memory.reset_memory()

        assert result["message"] == "Memory reset to base state"
        assert result["deleted_files"] >= 1

        # Check that only main.md and files_index.json remain
        files = list(Path(tmpdir).rglob("*.md"))
        md_files = [f for f in files if f.name != "main.md"]
        assert len(md_files) == 0

        await memory.close()


@pytest.mark.asyncio
async def test_update_file():
    """Test updating a file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create a file
        await memory.create_file(
            title="Test File",
            category="project",
            content="# Original",
        )

        # Update the file
        result = await memory.update_file(
            file_path="projects/test_file.md",
            content="# Updated",
            update_mode="replace",
        )

        assert "updated successfully" in result["message"].lower()

        # Check content
        file_result = await memory.get_file("projects/test_file.md")
        assert "Updated" in file_result["content"]

        await memory.close()


@pytest.mark.asyncio
async def test_delete_file():
    """Test deleting a file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create a file
        await memory.create_file(
            title="Test File",
            category="project",
            content="# Test",
        )

        # Delete the file
        result = await memory.delete_file("projects/test_file.md")

        assert "deleted successfully" in result["message"].lower()

        # Check file doesn't exist
        assert not (Path(tmpdir) / "projects" / "test_file.md").exists()

        await memory.close()


@pytest.mark.asyncio
async def test_edit_file_section():
    """Test editing a file section"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create a file with sections
        await memory.create_file(
            title="Test File",
            category="project",
            content="# Test\n\n## Section 1\n\nOld content",
        )

        # Edit section
        result = await memory.edit_file(
            file_path="projects/test_file.md",
            edit_type="section",
            section_header="Section 1",
            new_content="New content",
            mode="replace",
        )

        assert "updated successfully" in result["message"].lower()

        await memory.close()


@pytest.mark.asyncio
async def test_batch_update_files():
    """Test batch file updates"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create files
        await memory.create_file(
            title="File 1",
            category="project",
            content="# Original 1",
        )
        await memory.create_file(
            title="File 2",
            category="project",
            content="# Original 2",
        )

        # Batch update
        updates = [
            {
                "file_path": "projects/file_1.md",
                "content": "# Updated 1",
                "update_mode": "replace",
            },
            {
                "file_path": "projects/file_2.md",
                "content": "# Updated 2",
                "update_mode": "replace",
            },
        ]

        result = await memory.batch_update_files(updates)

        assert result["success_count"] == 2
        assert result["error_count"] == 0

        await memory.close()


@pytest.mark.asyncio
async def test_batch_delete_files():
    """Test batch file deletion"""
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from config.settings import Settings
            settings = Settings()
            database_url = settings.database_url

        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        await memory.initialize()

        # Create files
        await memory.create_file(
            title="File 1",
            category="project",
            content="# File 1",
        )
        await memory.create_file(
            title="File 2",
            category="project",
            content="# File 2",
        )

        # Batch delete
        result = await memory.batch_delete_files([
            "projects/file_1.md",
            "projects/file_2.md",
        ])

        assert result["success_count"] == 2
        assert result["error_count"] == 0

        await memory.close()

