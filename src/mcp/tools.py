"""MCP tools for agent memory operations"""
from typing import Any, Literal, Optional

import structlog

from src.database.repository import MemoryRepository
from src.models.memory import MemoryCategory
from src.models.search import SearchMode, SearchRequest, SearchResponse
from src.search.hybrid_search import HybridSearchEngine
from src.storage.file_manager import FileManager
from src.storage.index_structure import IndexManager
from src.sync.sync_service import FileSyncService
from src.utils.file_editor import MarkdownEditor

logger = structlog.get_logger(__name__)


class MemoryTools:
    """MCP tools for memory operations"""

    def __init__(
        self,
        file_manager: FileManager,
        index_manager: IndexManager,
        repository: MemoryRepository,
        sync_service: FileSyncService,
        search_engine: HybridSearchEngine,
    ) -> None:
        """Initialize memory tools"""
        self.file_manager = file_manager
        self.index_manager = index_manager
        self.repository = repository
        self.sync_service = sync_service
        self.search_engine = search_engine
        logger.info("memory_tools_initialized")

    async def create_memory_file(
        self,
        title: str,
        category: Literal["project", "concept", "conversation", "preference", "other"],
        content: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Create a new memory file.

        Args:
            title: Title of the memory file
            category: Category (project, concept, conversation, preference, other)
            content: Markdown content
            tags: Optional tags for categorization
            metadata: Optional additional metadata

        Returns:
            Dictionary with file_path and file_id
        """
        # Generate file path
        file_name = title.lower().replace(' ', '_') + '.md'
        file_path = f"{category}s/{file_name}"

        # Write file
        self.file_manager.write_file(file_path, content)

        # Sync to database
        await self.sync_service.sync_file(file_path)

        # Update index
        self.index_manager.update_file_index(
            file_path=file_path,
            description=title,
            category=f"{category}s"
        )

        logger.info("memory_file_created", file_path=file_path, title=title)

        return {
            "file_path": file_path,
            "title": title,
            "category": category,
            "message": f"Memory file created successfully at {file_path}"
        }

    async def update_memory_file(
        self,
        file_path: str,
        content: str,
        update_mode: Literal["replace", "append", "prepend"] = "replace",
    ) -> dict[str, str]:
        """
        Update an existing memory file.

        Args:
            file_path: Path to the file
            content: New content
            update_mode: How to update (replace, append, prepend)

        Returns:
            Status message
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if update_mode == "replace":
            self.file_manager.write_file(file_path, content)
        elif update_mode == "append":
            existing = self.file_manager.read_file(file_path)
            self.file_manager.write_file(file_path, existing + "\n\n" + content)
        elif update_mode == "prepend":
            existing = self.file_manager.read_file(file_path)
            self.file_manager.write_file(file_path, content + "\n\n" + existing)

        # Sync to database
        await self.sync_service.sync_file(file_path, force=True)

        logger.info("memory_file_updated", file_path=file_path, mode=update_mode)

        return {
            "file_path": file_path,
            "message": f"File updated successfully using {update_mode} mode"
        }

    async def delete_memory_file(self, file_path: str) -> dict[str, str]:
        """Delete a memory file"""
        # Get file ID first
        file_record = await self.repository.get_file_by_path(file_path)
        if not file_record:
            raise FileNotFoundError(f"File not found in database: {file_path}")

        # Delete from database (cascades to chunks)
        await self.repository.delete_file(file_record.id)

        # Delete file from filesystem
        self.file_manager.delete_file(file_path)

        logger.info("memory_file_deleted", file_path=file_path)

        return {
            "file_path": file_path,
            "message": "File deleted successfully"
        }

    async def append_to_main_memory(
        self,
        content: str,
        section: Literal["Recent Notes", "Current Goals", "Future Plans", "Quick Reference"] = "Recent Notes",
    ) -> dict[str, str]:
        """Append content to a section in main.md"""
        self.index_manager.append_to_section(section, content)

        # Sync main.md
        await self.sync_service.sync_file("main.md", force=True)

        logger.info("main_memory_updated", section=section)

        return {
            "section": section,
            "message": f"Content appended to {section} section"
        }

    async def update_main_index(
        self,
        file_path: str,
        description: str,
    ) -> dict[str, str]:
        """Update file index in main.md"""
        # Determine category from file path
        category = file_path.split('/')[0] if '/' in file_path else "other"

        self.index_manager.update_file_index(
            file_path=file_path,
            description=description,
            category=category
        )

        await self.sync_service.sync_file("main.md", force=True)

        return {"message": "Index updated successfully"}

    async def update_goals(
        self,
        goal: str,
        action: Literal["add", "complete", "remove"] = "add",
    ) -> dict[str, str]:
        """Manage goals in main.md"""
        if action == "add":
            self.index_manager.add_goal(goal)
            message = f"Goal added: {goal}"
        elif action == "complete":
            self.index_manager.complete_goal(goal)
            message = f"Goal completed: {goal}"
        else:
            # Remove not implemented yet
            message = "Remove action not yet implemented"

        await self.sync_service.sync_file("main.md", force=True)

        return {"message": message}

    async def update_tasks(
        self,
        task: str,
        action: Literal["add"] = "add",
    ) -> dict[str, str]:
        """Add completed task to main.md"""
        self.index_manager.add_task(task)
        await self.sync_service.sync_file("main.md", force=True)

        return {"message": f"Task added: {task}"}

    async def search_memories(
        self,
        query: str,
        search_mode: Literal["hybrid", "vector", "fulltext"] = "hybrid",
        limit: int = 10,
        category_filter: Optional[str] = None,
        tag_filter: Optional[list[str]] = None,
    ) -> SearchResponse:
        """
        Search across all memory files.

        Args:
            query: Search query
            search_mode: Search algorithm (hybrid, vector, fulltext)
            limit: Maximum results
            category_filter: Optional category filter
            tag_filter: Optional tag filter (files must have ALL specified tags)

        Returns:
            Search response with results
        """
        mode_map = {
            "hybrid": SearchMode.HYBRID,
            "vector": SearchMode.VECTOR,
            "fulltext": SearchMode.FULLTEXT,
        }

        search_mode_enum = mode_map[search_mode]

        results = await self.search_engine.search(
            query=query,
            search_mode=search_mode_enum,
            limit=limit,
            category_filter=category_filter,
            tag_filter=tag_filter,
        )

        logger.info(
            "memories_searched",
            query=query,
            mode=search_mode,
            results_count=len(results)
        )

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_mode=search_mode_enum,
        )

    async def search_within_file(
        self,
        file_path: str,
        query: str,
        search_mode: Literal["hybrid", "vector", "fulltext"] = "hybrid",
    ) -> SearchResponse:
        """Search within a specific file"""
        mode_map = {
            "hybrid": SearchMode.HYBRID,
            "vector": SearchMode.VECTOR,
            "fulltext": SearchMode.FULLTEXT,
        }

        search_mode_enum = mode_map[search_mode]

        results = await self.search_engine.search(
            query=query,
            search_mode=search_mode_enum,
            limit=100,
            file_filter=file_path,
        )

        logger.info(
            "file_searched",
            file_path=file_path,
            query=query,
            results_count=len(results)
        )

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_mode=search_mode_enum,
        )

    async def get_file_content(self, file_path: str) -> dict[str, str]:
        """Get the content of a memory file"""
        content = self.file_manager.read_file(file_path)
        return {
            "file_path": file_path,
            "content": content,
        }

    async def list_files(
        self,
        category: Optional[Literal["project", "concept", "conversation", "preference", "other"]] = None,
    ) -> dict[str, Any]:
        """List all memory files, optionally filtered by category"""
        if category:
            category_enum = MemoryCategory(category)
            files = await self.repository.get_all_files(category=category_enum)
        else:
            files = await self.repository.get_all_files()

        return {
            "files": [
                {
                    "file_path": f.file_path,
                    "title": f.title,
                    "category": f.category,
                    "tags": f.tags,
                    "updated_at": f.updated_at.isoformat(),
                    "word_count": f.word_count,
                }
                for f in files
            ],
            "total": len(files),
        }

    # =============================
    # Advanced Editing Operations
    # =============================

    async def edit_section(
        self,
        file_path: str,
        section_header: str,
        new_content: str,
        mode: Literal["replace", "append", "prepend"] = "replace",
    ) -> dict[str, str]:
        """
        Edit a specific section in a file by header.

        Args:
            file_path: Path to file
            section_header: Section header (e.g., "## Goals" or "Goals")
            new_content: New content for section
            mode: How to update (replace/append/prepend)

        Returns:
            Success message
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self.file_manager.read_file(file_path)
        updated_content = MarkdownEditor.edit_section(content, section_header, new_content, mode)
        self.file_manager.write_file(file_path, updated_content)

        # Sync to database
        await self.sync_service.sync_file(file_path, force=True)

        return {
            "file_path": file_path,
            "section": section_header,
            "mode": mode,
            "message": f"Section '{section_header}' updated successfully"
        }

    async def find_replace(
        self,
        file_path: str,
        find: str,
        replace: str,
        regex: bool = False,
        max_replacements: int = -1,
    ) -> dict[str, Any]:
        """
        Find and replace text in a file.

        Args:
            file_path: Path to file
            find: Text or regex pattern to find
            replace: Replacement text
            regex: Whether find is regex pattern
            max_replacements: Max number of replacements (-1 for all)

        Returns:
            Result with number of replacements made
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self.file_manager.read_file(file_path)
        updated_content, num_replacements = MarkdownEditor.find_and_replace(
            content, find, replace, regex, max_replacements
        )

        if num_replacements > 0:
            self.file_manager.write_file(file_path, updated_content)
            await self.sync_service.sync_file(file_path, force=True)

        return {
            "file_path": file_path,
            "replacements_made": num_replacements,
            "message": f"Made {num_replacements} replacement(s)"
        }

    async def insert_content(
        self,
        file_path: str,
        content: str,
        position: Literal["start", "end", "after_marker"] = "end",
        marker: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Insert content at specific position in file.

        Args:
            file_path: Path to file
            content: Content to insert
            position: Where to insert (start/end/after_marker)
            marker: Marker text to insert after (required for after_marker)

        Returns:
            Success message
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        existing_content = self.file_manager.read_file(file_path)
        updated_content = MarkdownEditor.insert_at_position(
            existing_content, content, position, marker
        )
        self.file_manager.write_file(file_path, updated_content)

        await self.sync_service.sync_file(file_path, force=True)

        return {
            "file_path": file_path,
            "position": position,
            "message": f"Content inserted at {position}"
        }

    async def extract_section(
        self,
        file_path: str,
        section_header: str,
    ) -> dict[str, Optional[str]]:
        """
        Extract content of a specific section.

        Args:
            file_path: Path to file
            section_header: Section header to extract

        Returns:
            Section content or None
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self.file_manager.read_file(file_path)
        section_content = MarkdownEditor.extract_section(content, section_header)

        return {
            "file_path": file_path,
            "section_header": section_header,
            "content": section_content,
            "found": section_content is not None,
        }

    async def list_sections(self, file_path: str) -> dict[str, Any]:
        """
        List all sections in a file.

        Args:
            file_path: Path to file

        Returns:
            List of sections with headers
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self.file_manager.read_file(file_path)
        sections = MarkdownEditor.list_sections(content)

        return {
            "file_path": file_path,
            "sections": sections,
            "total": len(sections),
        }

    # =============================
    # Tag Management Operations
    # =============================

    async def add_tags(
        self,
        file_path: str,
        tags: list[str],
    ) -> dict[str, Any]:
        """
        Add tags to a memory file.

        Args:
            file_path: Path to file
            tags: Tags to add

        Returns:
            Updated tags list
        """
        # Get current file record
        file_record = await self.repository.get_file_by_path(file_path)
        if not file_record:
            raise FileNotFoundError(f"File not found in database: {file_path}")

        # Merge tags (avoid duplicates)
        current_tags = set(file_record.tags)
        new_tags = current_tags.union(set(tags))
        updated_tags = list(new_tags)

        # Update database directly
        from sqlalchemy import update
        from src.database.schema import MemoryFileModel

        await self.repository.session.execute(
            update(MemoryFileModel)
            .where(MemoryFileModel.file_path == file_path)
            .values(tags=updated_tags)
        )
        await self.repository.session.commit()

        logger.info("tags_added", file_path=file_path, tags=tags)

        return {
            "file_path": file_path,
            "tags": updated_tags,
            "message": f"Tags added successfully: {', '.join(tags)}"
        }

    async def remove_tags(
        self,
        file_path: str,
        tags: list[str],
    ) -> dict[str, Any]:
        """
        Remove tags from a memory file.

        Args:
            file_path: Path to file
            tags: Tags to remove

        Returns:
            Updated tags list
        """
        # Get current file record
        file_record = await self.repository.get_file_by_path(file_path)
        if not file_record:
            raise FileNotFoundError(f"File not found in database: {file_path}")

        # Remove tags
        current_tags = set(file_record.tags)
        updated_tags = list(current_tags.difference(set(tags)))

        # Update database directly
        from sqlalchemy import update
        from src.database.schema import MemoryFileModel

        await self.repository.session.execute(
            update(MemoryFileModel)
            .where(MemoryFileModel.file_path == file_path)
            .values(tags=updated_tags)
        )
        await self.repository.session.commit()

        logger.info("tags_removed", file_path=file_path, tags=tags)

        return {
            "file_path": file_path,
            "tags": updated_tags,
            "message": f"Tags removed successfully: {', '.join(tags)}"
        }

    async def get_tags(self, file_path: str) -> dict[str, Any]:
        """
        Get all tags for a file.

        Args:
            file_path: Path to file

        Returns:
            Tags list
        """
        file_record = await self.repository.get_file_by_path(file_path)
        if not file_record:
            raise FileNotFoundError(f"File not found in database: {file_path}")

        return {
            "file_path": file_path,
            "tags": file_record.tags,
            "total": len(file_record.tags)
        }

    # =============================
    # Bulk Operations
    # =============================

    async def batch_create_files(
        self,
        files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Create multiple memory files at once.

        Args:
            files: List of file definitions with keys: title, category, content, tags (optional), metadata (optional)

        Returns:
            Results with created files and any errors
        """
        created = []
        errors = []

        for file_def in files:
            try:
                result = await self.create_memory_file(
                    title=file_def["title"],
                    category=file_def["category"],
                    content=file_def["content"],
                    tags=file_def.get("tags"),
                    metadata=file_def.get("metadata"),
                )
                created.append(result)
            except Exception as e:
                errors.append({
                    "title": file_def.get("title", "unknown"),
                    "error": str(e)
                })

        logger.info("batch_create_completed", created=len(created), errors=len(errors))

        return {
            "created": created,
            "errors": errors,
            "total": len(files),
            "success_count": len(created),
            "error_count": len(errors)
        }

    async def batch_add_tags(
        self,
        file_paths: list[str],
        tags: list[str],
    ) -> dict[str, Any]:
        """
        Add tags to multiple files at once.

        Args:
            file_paths: List of file paths
            tags: Tags to add to all files

        Returns:
            Results with updated files and any errors
        """
        updated = []
        errors = []

        for file_path in file_paths:
            try:
                result = await self.add_tags(file_path, tags)
                updated.append(result)
            except Exception as e:
                errors.append({
                    "file_path": file_path,
                    "error": str(e)
                })

        logger.info("batch_add_tags_completed", updated=len(updated), errors=len(errors))

        return {
            "updated": updated,
            "errors": errors,
            "total": len(file_paths),
            "success_count": len(updated),
            "error_count": len(errors)
        }

    async def batch_remove_tags(
        self,
        file_paths: list[str],
        tags: list[str],
    ) -> dict[str, Any]:
        """
        Remove tags from multiple files at once.

        Args:
            file_paths: List of file paths
            tags: Tags to remove from all files

        Returns:
            Results with updated files and any errors
        """
        updated = []
        errors = []

        for file_path in file_paths:
            try:
                result = await self.remove_tags(file_path, tags)
                updated.append(result)
            except Exception as e:
                errors.append({
                    "file_path": file_path,
                    "error": str(e)
                })

        logger.info("batch_remove_tags_completed", updated=len(updated), errors=len(errors))

        return {
            "updated": updated,
            "errors": errors,
            "total": len(file_paths),
            "success_count": len(updated),
            "error_count": len(errors)
        }

    # =============================
    # File Operations
    # =============================

    async def rename_file(
        self,
        old_file_path: str,
        new_title: str,
    ) -> dict[str, Any]:
        """
        Rename a memory file (updates filesystem and database).

        Args:
            old_file_path: Current file path
            new_title: New title for the file

        Returns:
            New file path and status
        """
        if not self.file_manager.file_exists(old_file_path):
            raise FileNotFoundError(f"File not found: {old_file_path}")

        # Get current file record for category
        file_record = await self.repository.get_file_by_path(old_file_path)
        if not file_record:
            raise FileNotFoundError(f"File not found in database: {old_file_path}")

        # Generate new path from new title
        from pathlib import Path
        old_path = Path(old_file_path)
        category_dir = old_path.parent
        new_file_name = new_title.lower().replace(' ', '_') + '.md'
        new_file_path = str(category_dir / new_file_name)

        # Read content
        content = self.file_manager.read_file(old_file_path)

        # Write to new path
        self.file_manager.write_file(new_file_path, content)

        # Delete old file
        self.file_manager.delete_file(old_file_path)

        # Sync new file to database
        await self.sync_service.sync_file(new_file_path, force=True)

        # Delete old file from database
        await self.repository.delete_file(file_record.id)

        logger.info("file_renamed", old_path=old_file_path, new_path=new_file_path)

        return {
            "old_file_path": old_file_path,
            "new_file_path": new_file_path,
            "new_title": new_title,
            "message": f"File renamed successfully from {old_file_path} to {new_file_path}"
        }

    async def move_file(
        self,
        file_path: str,
        new_category: Literal["project", "concept", "conversation", "preference", "other"],
    ) -> dict[str, Any]:
        """
        Move a file to a different category.

        Args:
            file_path: Current file path
            new_category: New category for the file

        Returns:
            New file path and status
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get current file record
        file_record = await self.repository.get_file_by_path(file_path)
        if not file_record:
            raise FileNotFoundError(f"File not found in database: {file_path}")

        # Generate new path
        from pathlib import Path
        old_path = Path(file_path)
        file_name = old_path.name
        new_file_path = f"{new_category}s/{file_name}"

        # Read content
        content = self.file_manager.read_file(file_path)

        # Write to new path
        self.file_manager.write_file(new_file_path, content)

        # Delete old file
        self.file_manager.delete_file(file_path)

        # Sync new file to database
        await self.sync_service.sync_file(new_file_path, force=True)

        # Delete old file from database
        await self.repository.delete_file(file_record.id)

        # Update main.md index
        self.index_manager.update_file_index(
            file_path=new_file_path,
            description=file_record.title,
            category=f"{new_category}s"
        )
        await self.sync_service.sync_file("main.md", force=True)

        logger.info("file_moved", old_path=file_path, new_path=new_file_path)

        return {
            "old_file_path": file_path,
            "new_file_path": new_file_path,
            "new_category": new_category,
            "message": f"File moved successfully from {file_path} to {new_file_path}"
        }

    async def copy_file(
        self,
        source_file_path: str,
        new_title: str,
        new_category: Optional[Literal["project", "concept", "conversation", "preference", "other"]] = None,
    ) -> dict[str, Any]:
        """
        Create a copy of a memory file.

        Args:
            source_file_path: Source file path
            new_title: Title for the new copy
            new_category: Optional new category (defaults to same as source)

        Returns:
            New file path and status
        """
        if not self.file_manager.file_exists(source_file_path):
            raise FileNotFoundError(f"File not found: {source_file_path}")

        # Get source file record
        file_record = await self.repository.get_file_by_path(source_file_path)
        if not file_record:
            raise FileNotFoundError(f"File not found in database: {source_file_path}")

        # Determine category
        if new_category is None:
            # Use same category as source
            from pathlib import Path
            source_path = Path(source_file_path)
            category = source_path.parent.name.rstrip('s')  # Remove trailing 's'
        else:
            category = new_category

        # Read source content
        content = self.file_manager.read_file(source_file_path)

        # Create new file using create_memory_file
        result = await self.create_memory_file(
            title=new_title,
            category=category,
            content=content,
            tags=file_record.tags,
            metadata=file_record.metadata,
        )

        logger.info("file_copied", source=source_file_path, destination=result["file_path"])

        return {
            "source_file_path": source_file_path,
            "new_file_path": result["file_path"],
            "new_title": new_title,
            "message": f"File copied successfully from {source_file_path} to {result['file_path']}"
        }
