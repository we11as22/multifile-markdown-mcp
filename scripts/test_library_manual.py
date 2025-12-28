#!/usr/bin/env python3
"""
Manual test script for library mode
Tests all functionality without pytest
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.library import MemoryLibrary


async def test_library():
    """Run comprehensive library tests"""
    print("=" * 60)
    print("Testing Agent Memory MCP Library Mode")
    print("=" * 60)

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        from config.settings import Settings
        settings = Settings()
        database_url = settings.database_url
        print(f"Using database URL from settings: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")

    # Test 1: Initialization
    print("\n[TEST 1] Library Initialization")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )

        try:
            await memory.initialize()
            print("✓ Library initialized successfully")

            # Check files
            assert (Path(tmpdir) / "main.md").exists(), "main.md not created"
            assert (Path(tmpdir) / "files_index.json").exists(), "files_index.json not created"
            print("✓ Base files created (main.md, files_index.json)")

        except Exception as e:
            print(f"✗ Initialization failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 2: Create File
    print("\n[TEST 2] Create Memory File")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            result = await memory.create_file(
                title="Test Project",
                category="project",
                content="# Test Project\n\nThis is a test project.",
                tags=["test", "example"],
            )
            print(f"✓ File created: {result['file_path']}")
            assert result["title"] == "Test Project"
            assert (Path(tmpdir) / result["file_path"]).exists()
        except Exception as e:
            print(f"✗ Create file failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 3: Get File
    print("\n[TEST 3] Get File Content")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            # Create file first
            create_result = await memory.create_file(
                title="Test File",
                category="concept",
                content="# Test File\n\nContent here.",
            )

            # Get file
            file_result = await memory.get_file(create_result["file_path"])
            print(f"✓ File retrieved: {file_result['file_path']}")
            assert "Test File" in file_result["content"]
            assert "Content here" in file_result["content"]
        except Exception as e:
            print(f"✗ Get file failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 4: Update File
    print("\n[TEST 4] Update File")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            # Create file
            create_result = await memory.create_file(
                title="Update Test",
                category="project",
                content="# Original",
            )

            # Update file
            update_result = await memory.update_file(
                file_path=create_result["file_path"],
                content="# Updated Content",
                update_mode="replace",
            )
            print(f"✓ File updated: {update_result['file_path']}")

            # Verify update
            file_result = await memory.get_file(create_result["file_path"])
            assert "Updated Content" in file_result["content"]
        except Exception as e:
            print(f"✗ Update file failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 5: List Files
    print("\n[TEST 5] List Files")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            # Create multiple files
            await memory.create_file("File 1", "project", "# File 1")
            await memory.create_file("File 2", "concept", "# File 2")
            await memory.create_file("File 3", "project", "# File 3")

            # List all
            all_files = await memory.list_files()
            print(f"✓ Listed {all_files['total']} files")
            assert all_files["total"] >= 3

            # List by category
            project_files = await memory.list_files(category="project")
            print(f"✓ Listed {project_files['total']} project files")
            assert project_files["total"] >= 2
        except Exception as e:
            print(f"✗ List files failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 6: Search
    print("\n[TEST 6] Search Functionality")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            # Create files with searchable content
            await memory.create_file(
                "Machine Learning",
                "concept",
                "# Machine Learning\n\nMachine learning is a subset of AI.",
            )
            await memory.create_file(
                "Deep Learning",
                "concept",
                "# Deep Learning\n\nDeep learning uses neural networks.",
            )

            # Search
            results = await memory.search("machine learning", limit=10)
            print(f"✓ Search returned {results.get('total_results', len(results.get('results', [])))} results")
            assert results.get("total_results", 0) > 0 or len(results.get("results", [])) > 0
        except Exception as e:
            print(f"✗ Search failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 7: Batch Operations
    print("\n[TEST 7] Batch Operations")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            # Batch create
            files = [
                {"title": "Batch 1", "category": "project", "content": "# Batch 1"},
                {"title": "Batch 2", "category": "project", "content": "# Batch 2"},
            ]
            batch_result = await memory.batch_create_files(files)
            print(f"✓ Batch created {batch_result['success_count']} files")
            assert batch_result["success_count"] == 2

            # Batch update
            updates = [
                {
                    "file_path": "projects/batch_1.md",
                    "content": "# Updated Batch 1",
                    "update_mode": "replace",
                },
                {
                    "file_path": "projects/batch_2.md",
                    "content": "# Updated Batch 2",
                    "update_mode": "replace",
                },
            ]
            batch_update_result = await memory.batch_update_files(updates)
            print(f"✓ Batch updated {batch_update_result['success_count']} files")
            assert batch_update_result["success_count"] == 2

            # Batch delete
            file_paths = ["projects/batch_1.md", "projects/batch_2.md"]
            batch_delete_result = await memory.batch_delete_files(file_paths)
            print(f"✓ Batch deleted {batch_delete_result['success_count']} files")
            assert batch_delete_result["success_count"] == 2
        except Exception as e:
            print(f"✗ Batch operations failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 8: Initialize and Reset
    print("\n[TEST 8] Initialize and Reset Memory")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            # Create some files
            await memory.create_file("Test 1", "project", "# Test 1")
            await memory.create_file("Test 2", "concept", "# Test 2")

            # Reset
            reset_result = await memory.reset_memory()
            print(f"✓ Memory reset: deleted {reset_result['deleted_files']} files")
            assert reset_result["deleted_files"] >= 2

            # Verify only base files remain
            files = list(Path(tmpdir).rglob("*.md"))
            md_files = [f for f in files if f.name != "main.md"]
            assert len(md_files) == 0, "Files should be deleted after reset"
        except Exception as e:
            print(f"✗ Initialize/Reset failed: {e}")
            raise
        finally:
            await memory.close()

    # Test 9: Edit File
    print("\n[TEST 9] Edit File Operations")
    print("-" * 60)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            database_url=database_url,
        )
        await memory.initialize()

        try:
            # Create file with sections
            await memory.create_file(
                "Edit Test",
                "project",
                "# Edit Test\n\n## Section 1\n\nOld content",
            )

            # Edit section
            edit_result = await memory.edit_file(
                "projects/edit_test.md",
                edit_type="section",
                section_header="Section 1",
                new_content="New content",
                mode="replace",
            )
            print(f"✓ Section edited: {edit_result.get('message', 'success')}")

            # Verify edit
            file_result = await memory.get_file("projects/edit_test.md")
            assert "New content" in file_result["content"]
        except Exception as e:
            print(f"✗ Edit file failed: {e}")
            raise
        finally:
            await memory.close()

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_library())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

