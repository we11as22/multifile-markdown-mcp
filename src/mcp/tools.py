"""MCP tools for agent memory operations"""
from typing import Any, Literal, Optional

import structlog

from src.database.repository import MemoryRepository
from src.models.memory import MemoryCategory
from src.models.search import SearchMode, SearchRequest, SearchResponse
from src.search.hybrid_search import HybridSearchEngine
from src.storage.file_manager import FileManager
from src.storage.index_structure import IndexManager, JsonIndexManager
from src.sync.sync_service import FileSyncService
from src.utils.file_editor import MarkdownEditor

logger = structlog.get_logger(__name__)


class MemoryTools:
    """MCP tools for memory operations"""

    def __init__(
        self,
        file_manager: FileManager,
        index_manager: IndexManager,
        json_index_manager: JsonIndexManager,
        repository: Optional[MemoryRepository],
        sync_service: Optional[FileSyncService],
        search_engine: Optional[HybridSearchEngine],
    ) -> None:
        """Initialize memory tools"""
        self.file_manager = file_manager
        self.index_manager = index_manager
        self.json_index_manager = json_index_manager
        self.repository = repository
        self.sync_service = sync_service
        self.search_engine = search_engine
        logger.info("memory_tools_initialized", has_db=repository is not None)

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

        # Sync to database if available
        if self.sync_service:
            await self.sync_service.sync_file(file_path)

        # Get file record from database for complete metadata (if available)
        file_record = None
        if self.repository:
            file_record = await self.repository.get_file_by_path(file_path)

        # Update markdown index
        self.index_manager.update_file_index(
            file_path=file_path,
            description=title,
            category=f"{category}s"
        )

        # Update JSON index
        if file_record:
            # Use database record if available
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=file_record.title,
                category=file_record.category.value,
                description=title,
                tags=file_record.tags,
                metadata=file_record.metadata,
                word_count=file_record.word_count,
                created_at=file_record.created_at,
                updated_at=file_record.updated_at,
            )
        else:
            # Use file-only mode - calculate word count from content
            word_count = len(content.split())
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=title,
                category=f"{category}s",
                description=title,
                tags=tags or [],
                metadata=metadata or {},
                word_count=word_count,
                created_at=now,
                updated_at=now,
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

        # Sync to database if available
        if self.sync_service:
            await self.sync_service.sync_file(file_path, force=True)

        # Update JSON index
        if self.repository:
            file_record = await self.repository.get_file_by_path(file_path)
            if file_record:
                self.json_index_manager.add_or_update_file(
                    file_path=file_path,
                    title=file_record.title,
                    category=file_record.category.value,
                    description=file_record.title,
                    tags=file_record.tags,
                    metadata=file_record.metadata,
                    word_count=file_record.word_count,
                    created_at=file_record.created_at,
                    updated_at=file_record.updated_at,
                )
        else:
            # File-only mode - update JSON index from file content
            from pathlib import Path
            from datetime import datetime, timezone
            file_path_obj = Path(file_path)
            category = file_path_obj.parent.name
            title = file_path_obj.stem.replace('_', ' ').title()
            word_count = len(content.split())
            now = datetime.now(timezone.utc)
            
            # Get existing entry to preserve created_at and tags
            existing = self.json_index_manager.get_file(file_path)
            created_at = existing.get("created_at", now) if existing else now
            tags = existing.get("tags", []) if existing else []
            metadata = existing.get("metadata", {}) if existing else {}
            
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=title,
                category=category,
                description=title,
                tags=tags,
                metadata=metadata,
                word_count=word_count,
                created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                updated_at=now,
            )

        logger.info("memory_file_updated", file_path=file_path, mode=update_mode)

        return {
            "file_path": file_path,
            "message": f"File updated successfully using {update_mode} mode"
        }

    async def delete_memory_file(self, file_path: str) -> dict[str, str]:
        """Delete a memory file"""
        # Check if file exists in filesystem
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Delete from database if available
        if self.repository:
            file_record = await self.repository.get_file_by_path(file_path)
            if file_record:
                await self.repository.delete_file(file_record.id)

        # Delete file from filesystem
        self.file_manager.delete_file(file_path)

        # Remove from JSON index
        self.json_index_manager.remove_file(file_path)

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

        # Sync main.md if available
        if self.sync_service:
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

        if self.sync_service:
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

        if self.sync_service:
            await self.sync_service.sync_file("main.md", force=True)

        return {"message": message}

    async def update_tasks(
        self,
        task: str,
        action: Literal["add"] = "add",
    ) -> dict[str, str]:
        """Add completed task to main.md"""
        self.index_manager.add_task(task)
        if self.sync_service:
            await self.sync_service.sync_file("main.md", force=True)

        return {"message": f"Task added: {task}"}

    async def search(
        self,
        query: str,
        search_mode: Literal["hybrid", "vector", "fulltext"] = "hybrid",
        limit: int = 10,
        file_path: Optional[str] = None,
        category_filter: Optional[str] = None,
        tag_filter: Optional[list[str]] = None,
    ) -> SearchResponse:
        """
        Search across memory files. Requires database connection.
        In file-only mode, search is not available.
        """
        """
        Search across memory files with flexible filtering options.

        This unified search method can search:
        - Across all files (default)
        - Within a specific file (use file_path parameter)
        - Filtered by category (use category_filter parameter)
        - Filtered by tags (use tag_filter parameter - files must have ALL specified tags)

        Args:
            query: Search query text
            search_mode: Search algorithm to use:
                - "hybrid": Combines vector (semantic) and fulltext (keyword) search with RRF ranking (recommended)
                - "vector": Semantic similarity search using embeddings
                - "fulltext": Keyword-based search using PostgreSQL fulltext search
            limit: Maximum number of results to return (default: 10, max: 100)
            file_path: Optional path to search within a specific file only (e.g., "projects/my_project.md")
            category_filter: Optional category to filter by (project, concept, conversation, preference, other)
            tag_filter: Optional list of tags - files must have ALL specified tags to match

        Returns:
            SearchResponse with results containing:
            - query: The search query used
            - results: List of search results with file_path, content, score, etc.
            - total_results: Number of results found
            - search_mode: The search mode used

        Examples:
            # Search across all files
            results = await search("machine learning", search_mode="hybrid", limit=20)

            # Search within a specific file
            results = await search("neural networks", file_path="concepts/ml_concepts.md")

            # Search with category filter
            results = await search("project status", category_filter="project")

            # Search with tag filter
            results = await search("important notes", tag_filter=["important", "active"])
        """
        mode_map = {
            "hybrid": SearchMode.HYBRID,
            "vector": SearchMode.VECTOR,
            "fulltext": SearchMode.FULLTEXT,
        }

        search_mode_enum = mode_map[search_mode]

        # If file_path is specified, use it as file_filter and increase limit
        file_filter = file_path
        if file_path:
            limit = min(limit, 100)  # Cap at 100 for file-specific searches

        if not self.search_engine:
            raise RuntimeError(
                "Search engine not available. Database connection is required for search functionality."
            )

        results = await self.search_engine.search(
            query=query,
            search_mode=search_mode_enum,
            limit=limit,
            file_filter=file_filter,
            category_filter=category_filter,
            tag_filter=tag_filter,
        )

        logger.info(
            "memory_searched",
            query=query,
            mode=search_mode,
            file_path=file_path,
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
        """
        List all memory files, optionally filtered by category.
        Uses database if available, otherwise uses JSON index.
        Returns tree structure with descriptions.
        """
        if self.repository:
            # Use database
            if category:
                category_enum = MemoryCategory(category)
                files = await self.repository.get_all_files(category=category_enum)
            else:
                files = await self.repository.get_all_files()

            files_list = [
                {
                    "file_path": f.file_path,
                    "title": f.title,
                    "category": f.category.value if hasattr(f.category, 'value') else str(f.category),
                    "description": f.title,  # Use title as description if not available
                    "tags": f.tags,
                    "updated_at": f.updated_at.isoformat() if hasattr(f.updated_at, 'isoformat') else str(f.updated_at),
                    "word_count": f.word_count,
                }
                for f in files
            ]
        else:
            # Use JSON index (file-only mode)
            all_files = self.json_index_manager.get_all_files()
            
            # Filter by category if specified
            if category:
                category_key = f"{category}s"  # Convert "project" to "projects"
                files_list = [
                    {
                        "file_path": f.get("file_path", ""),
                        "title": f.get("title", ""),
                        "category": f.get("category", ""),
                        "description": f.get("description", f.get("title", "")),
                        "tags": f.get("tags", []),
                        "updated_at": f.get("updated_at", ""),
                        "word_count": f.get("word_count", 0),
                    }
                    for f in all_files
                    if f.get("category", "").rstrip('s') == category  # Match "projects" with "project"
                ]
            else:
                files_list = [
                    {
                        "file_path": f.get("file_path", ""),
                        "title": f.get("title", ""),
                        "category": f.get("category", ""),
                        "description": f.get("description", f.get("title", "")),
                        "tags": f.get("tags", []),
                        "updated_at": f.get("updated_at", ""),
                        "word_count": f.get("word_count", 0),
                    }
                    for f in all_files
                ]
        
        # Build tree structure
        tree = {}
        for file_info in files_list:
            file_path = file_info["file_path"]
            category = file_info["category"]
            
            # Initialize category if not exists
            if category not in tree:
                tree[category] = []
            
            # Add file to category
            tree[category].append({
                "file_path": file_path,
                "title": file_info["title"],
                "description": file_info["description"],
                "tags": file_info["tags"],
                "updated_at": file_info["updated_at"],
                "word_count": file_info["word_count"],
            })
        
        return {
            "files": files_list,
            "tree": tree,  # Tree structure by category
            "total": len(files_list),
        }

    # =============================
    # Advanced Editing Operations
    # =============================

    async def edit_file(
        self,
        file_path: str,
        edit_type: Literal["section", "find_replace", "insert"],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Universal file editing method supporting multiple edit operations.

        This method unifies all file editing operations into a single interface:
        - Section editing (edit_section)
        - Find and replace (find_replace)
        - Content insertion (insert_content)

        Args:
            file_path: Path to the file to edit
            edit_type: Type of edit operation:
                - "section": Edit a specific section by header
                - "find_replace": Find and replace text/regex patterns
                - "insert": Insert content at specific position
            **kwargs: Additional parameters depending on edit_type:
                For "section":
                    - section_header: Section header (e.g., "## Goals" or "Goals")
                    - new_content: New content for section
                    - mode: How to update (replace/append/prepend, default: "replace")
                For "find_replace":
                    - find: Text or regex pattern to find
                    - replace: Replacement text
                    - regex: Whether find is regex pattern (default: False)
                    - max_replacements: Max number of replacements (-1 for all, default: -1)
                For "insert":
                    - content: Content to insert
                    - position: Where to insert (start/end/after_marker, default: "end")
                    - marker: Marker text to insert after (required for after_marker)

        Returns:
            Dictionary with operation results

        Examples:
            # Edit a section
            await edit_file(
                "projects/my_project.md",
                edit_type="section",
                section_header="## Status",
                new_content="In progress",
                mode="replace"
            )

            # Find and replace
            await edit_file(
                "notes.md",
                edit_type="find_replace",
                find="old text",
                replace="new text",
                regex=False
            )

            # Insert content
            await edit_file(
                "notes.md",
                edit_type="insert",
                content="New note",
                position="end"
            )
        """
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self.file_manager.read_file(file_path)
        updated_content = content
        result_info: dict[str, Any] = {"file_path": file_path}

        if edit_type == "section":
            section_header = kwargs.get("section_header")
            new_content = kwargs.get("new_content")
            mode = kwargs.get("mode", "replace")

            if not section_header or new_content is None:
                raise ValueError("section_header and new_content are required for section edit")

            updated_content = MarkdownEditor.edit_section(content, section_header, new_content, mode)
            result_info.update({
                "section": section_header,
                "mode": mode,
                "message": f"Section '{section_header}' updated successfully"
            })

        elif edit_type == "find_replace":
            find = kwargs.get("find")
            replace = kwargs.get("replace")
            regex = kwargs.get("regex", False)
            max_replacements = kwargs.get("max_replacements", -1)

            if not find or replace is None:
                raise ValueError("find and replace are required for find_replace edit")

            updated_content, num_replacements = MarkdownEditor.find_and_replace(
                content, find, replace, regex, max_replacements
            )
            result_info.update({
                "replacements_made": num_replacements,
                "message": f"Made {num_replacements} replacement(s)"
            })

        elif edit_type == "insert":
            insert_content = kwargs.get("content")
            position = kwargs.get("position", "end")
            marker = kwargs.get("marker")

            if not insert_content:
                raise ValueError("content is required for insert edit")

            updated_content = MarkdownEditor.insert_at_position(
                content, insert_content, position, marker
            )
            result_info.update({
                "position": position,
                "message": f"Content inserted at {position}"
            })

        else:
            raise ValueError(f"Unknown edit_type: {edit_type}")

        # Write updated content
        self.file_manager.write_file(file_path, updated_content)

        # Sync to database if available
        if self.sync_service:
            await self.sync_service.sync_file(file_path, force=True)

        # Update JSON index
        if self.repository:
            file_record = await self.repository.get_file_by_path(file_path)
            if file_record:
                self.json_index_manager.add_or_update_file(
                    file_path=file_path,
                    title=file_record.title,
                    category=file_record.category.value,
                    description=file_record.title,
                    tags=file_record.tags,
                    metadata=file_record.metadata,
                    word_count=file_record.word_count,
                    created_at=file_record.created_at,
                    updated_at=file_record.updated_at,
                )
        else:
            # File-only mode - update JSON index from file content
            from pathlib import Path
            from datetime import datetime, timezone
            file_path_obj = Path(file_path)
            category = file_path_obj.parent.name.rstrip('s')  # Remove trailing 's'
            title = file_path_obj.stem.replace('_', ' ').title()
            word_count = len(content.split())
            now = datetime.now(timezone.utc)
            
            # Get existing entry to preserve created_at
            existing = self.json_index_manager.get_file(file_path)
            created_at = existing.get("created_at", now) if existing else now
            
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=title,
                category=file_path_obj.parent.name,
                description=title,
                tags=existing.get("tags", []) if existing else [],
                metadata=existing.get("metadata", {}) if existing else {},
                word_count=word_count,
                created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                updated_at=now,
            )

        logger.info("file_edited", file_path=file_path, edit_type=edit_type)

        return result_info

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
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get current tags
        if self.repository:
            # Use database
            file_record = await self.repository.get_file_by_path(file_path)
            if not file_record:
                raise FileNotFoundError(f"File not found in database: {file_path}")
            
            current_tags = file_record.tags
            new_tags = set(current_tags).union(set(tags))
            updated_tags = list(new_tags)

            # Update database
            from sqlalchemy import update
            from src.database.schema import MemoryFileModel

            await self.repository.session.execute(
                update(MemoryFileModel)
                .where(MemoryFileModel.file_path == file_path)
                .values(tags=updated_tags)
            )
            await self.repository.session.commit()

            # Update JSON index
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=file_record.title,
                category=file_record.category.value,
                description=file_record.title,
                tags=updated_tags,
                metadata=file_record.metadata,
                word_count=file_record.word_count,
                created_at=file_record.created_at,
                updated_at=file_record.updated_at,
            )
        else:
            # File-only mode - use JSON index
            existing = self.json_index_manager.get_file(file_path)
            if not existing:
                raise FileNotFoundError(f"File not found: {file_path}")
            
            current_tags = existing.get("tags", [])
            new_tags = set(current_tags).union(set(tags))
            updated_tags = list(new_tags)
            
            # Update JSON index
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            created_at = existing.get("created_at", now)
            
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=existing.get("title", ""),
                category=existing.get("category", ""),
                description=existing.get("description", existing.get("title", "")),
                tags=updated_tags,
                metadata=existing.get("metadata", {}),
                word_count=existing.get("word_count", 0),
                created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                updated_at=now,
            )

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
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get current tags
        if self.repository:
            # Use database
            file_record = await self.repository.get_file_by_path(file_path)
            if not file_record:
                raise FileNotFoundError(f"File not found in database: {file_path}")
            
            current_tags = file_record.tags
            updated_tags = list(set(current_tags).difference(set(tags)))

            # Update database
            from sqlalchemy import update
            from src.database.schema import MemoryFileModel

            await self.repository.session.execute(
                update(MemoryFileModel)
                .where(MemoryFileModel.file_path == file_path)
                .values(tags=updated_tags)
            )
            await self.repository.session.commit()

            # Update JSON index
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=file_record.title,
                category=file_record.category.value,
                description=file_record.title,
                tags=updated_tags,
                metadata=file_record.metadata,
                word_count=file_record.word_count,
                created_at=file_record.created_at,
                updated_at=file_record.updated_at,
            )
        else:
            # File-only mode - use JSON index
            existing = self.json_index_manager.get_file(file_path)
            if not existing:
                raise FileNotFoundError(f"File not found: {file_path}")
            
            current_tags = existing.get("tags", [])
            updated_tags = list(set(current_tags).difference(set(tags)))
            
            # Update JSON index
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            created_at = existing.get("created_at", now)
            
            self.json_index_manager.add_or_update_file(
                file_path=file_path,
                title=existing.get("title", ""),
                category=existing.get("category", ""),
                description=existing.get("description", existing.get("title", "")),
                tags=updated_tags,
                metadata=existing.get("metadata", {}),
                word_count=existing.get("word_count", 0),
                created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                updated_at=now,
            )

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
        if not self.file_manager.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if self.repository:
            # Use database
            file_record = await self.repository.get_file_by_path(file_path)
            if not file_record:
                raise FileNotFoundError(f"File not found in database: {file_path}")
            
            return {
                "file_path": file_path,
                "tags": file_record.tags,
                "total": len(file_record.tags)
            }
        else:
            # File-only mode - use JSON index
            existing = self.json_index_manager.get_file(file_path)
            if not existing:
                raise FileNotFoundError(f"File not found: {file_path}")
            
            tags = existing.get("tags", [])
            return {
                "file_path": file_path,
                "tags": tags,
                "total": len(tags)
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

    async def batch_update_files(
        self,
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Update multiple memory files at once.

        Args:
            updates: List of update definitions with keys:
                - file_path: Path to file (required)
                - content: New content (required)
                - update_mode: How to update (replace/append/prepend, default: "replace")

        Returns:
            Results with updated files and any errors
        """
        updated = []
        errors = []

        for update_def in updates:
            try:
                result = await self.update_memory_file(
                    file_path=update_def["file_path"],
                    content=update_def["content"],
                    update_mode=update_def.get("update_mode", "replace"),
                )
                updated.append(result)
            except Exception as e:
                errors.append({
                    "file_path": update_def.get("file_path", "unknown"),
                    "error": str(e)
                })

        logger.info("batch_update_completed", updated=len(updated), errors=len(errors))

        return {
            "updated": updated,
            "errors": errors,
            "total": len(updates),
            "success_count": len(updated),
            "error_count": len(errors)
        }

    async def batch_delete_files(
        self,
        file_paths: list[str],
    ) -> dict[str, Any]:
        """
        Delete multiple memory files at once.

        Args:
            file_paths: List of file paths to delete

        Returns:
            Results with deleted files and any errors
        """
        deleted = []
        errors = []

        for file_path in file_paths:
            try:
                result = await self.delete_memory_file(file_path)
                deleted.append(result)
            except Exception as e:
                errors.append({
                    "file_path": file_path,
                    "error": str(e)
                })

        logger.info("batch_delete_completed", deleted=len(deleted), errors=len(errors))

        return {
            "deleted": deleted,
            "errors": errors,
            "total": len(file_paths),
            "success_count": len(deleted),
            "error_count": len(errors)
        }

    async def batch_search(
        self,
        queries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Perform multiple searches at once.

        Args:
            queries: List of search query definitions with keys:
                - query: Search query text (required)
                - search_mode: Search mode (hybrid/vector/fulltext, default: "hybrid")
                - limit: Maximum results (default: 10)
                - file_path: Optional file path filter
                - category_filter: Optional category filter
                - tag_filter: Optional tag filter list

        Returns:
            Results with search results for each query
        """
        results = []
        errors = []

        for query_def in queries:
            try:
                result = await self.search(
                    query=query_def["query"],
                    search_mode=query_def.get("search_mode", "hybrid"),
                    limit=query_def.get("limit", 10),
                    file_path=query_def.get("file_path"),
                    category_filter=query_def.get("category_filter"),
                    tag_filter=query_def.get("tag_filter"),
                )
                results.append({
                    "query": query_def["query"],
                    "result": result.model_dump() if hasattr(result, "model_dump") else result,
                })
            except Exception as e:
                errors.append({
                    "query": query_def.get("query", "unknown"),
                    "error": str(e)
                })

        logger.info("batch_search_completed", results_count=len(results), errors=len(errors))

        return {
            "results": results,
            "errors": errors,
            "total": len(queries),
            "success_count": len(results),
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

        # Get current file record for category (if available)
        file_record = None
        if self.repository:
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

        # Update JSON index before syncing
        from pathlib import Path
        from datetime import datetime, timezone
        file_path_obj = Path(new_file_path)
        category = file_path_obj.parent.name
        word_count = len(content.split())
        now = datetime.now(timezone.utc)
        
        # Get old entry to preserve created_at and metadata
        old_entry = self.json_index_manager.get_file(old_file_path)
        created_at = old_entry.get("created_at", now) if old_entry else now
        tags = old_entry.get("tags", []) if old_entry else []
        metadata = old_entry.get("metadata", {}) if old_entry else {}
        
        if file_record:
            # Use database record if available
            self.json_index_manager.add_or_update_file(
                file_path=new_file_path,
                title=new_title,
                category=file_record.category.value,
                description=new_title,
                tags=file_record.tags,
                metadata=file_record.metadata,
                word_count=file_record.word_count,
                created_at=file_record.created_at,
                updated_at=file_record.updated_at,
            )
        else:
            # File-only mode
            self.json_index_manager.add_or_update_file(
                file_path=new_file_path,
                title=new_title,
                category=category,
                description=new_title,
                tags=tags,
                metadata=metadata,
                word_count=word_count,
                created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                updated_at=now,
            )
        
        # Remove old file from JSON index
        self.json_index_manager.remove_file(old_file_path)
        
        # Sync new file to database if available
        if self.sync_service:
            await self.sync_service.sync_file(new_file_path, force=True)

        # Delete old file from database if available
        if self.repository and file_record:
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

        # Get current file record (if available)
        file_record = None
        if self.repository:
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

        # Sync new file to database if available
        if self.sync_service:
            await self.sync_service.sync_file(new_file_path, force=True)

        # Delete old file from database if available
        if self.repository and file_record:
            await self.repository.delete_file(file_record.id)

        # Update main.md index
        title = file_record.title if file_record else Path(new_file_path).stem.replace('_', ' ').title()
        self.index_manager.update_file_index(
            file_path=new_file_path,
            description=title,
            category=f"{new_category}s"
        )
        if self.sync_service:
            await self.sync_service.sync_file("main.md", force=True)
        
        # Update JSON index
        if file_record:
            # Use database record
            self.json_index_manager.add_or_update_file(
                file_path=new_file_path,
                title=file_record.title,
                category=f"{new_category}s",
                description=file_record.title,
                tags=file_record.tags,
                metadata=file_record.metadata,
                word_count=file_record.word_count,
                created_at=file_record.created_at,
                updated_at=file_record.updated_at,
            )
        else:
            # File-only mode
            from datetime import datetime, timezone
            file_path_obj = Path(new_file_path)
            title = file_path_obj.stem.replace('_', ' ').title()
            word_count = len(content.split())
            now = datetime.now(timezone.utc)
            
            # Get old entry to preserve created_at
            old_entry = self.json_index_manager.get_file(file_path)
            created_at = old_entry.get("created_at", now) if old_entry else now
            
            self.json_index_manager.add_or_update_file(
                file_path=new_file_path,
                title=title,
                category=f"{new_category}s",
                description=title,
                tags=old_entry.get("tags", []) if old_entry else [],
                metadata=old_entry.get("metadata", {}) if old_entry else {},
                word_count=word_count,
                created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                updated_at=now,
            )
        
        # Remove old file from JSON index
        self.json_index_manager.remove_file(file_path)

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

        # Get source file record (if available)
        file_record = None
        tags = []
        metadata = {}
        if self.repository:
            file_record = await self.repository.get_file_by_path(source_file_path)
            if file_record:
                tags = file_record.tags
                metadata = file_record.metadata
        else:
            # File-only mode - get from JSON index
            existing = self.json_index_manager.get_file(source_file_path)
            if existing:
                tags = existing.get("tags", [])
                metadata = existing.get("metadata", {})

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
            tags=tags,
            metadata=metadata,
        )

        logger.info("file_copied", source=source_file_path, destination=result["file_path"])

        return {
            "source_file_path": source_file_path,
            "new_file_path": result["file_path"],
            "new_title": new_title,
            "message": f"File copied successfully from {source_file_path} to {result['file_path']}"
        }

    # =============================
    # Initialization and Reset
    # =============================

    async def initialize_memory(self) -> dict[str, Any]:
        """
        Initialize memory to base state (main.md + files_index.json).
        Creates the base structure if it doesn't exist.

        Returns:
            Status message with initialization details
        """
        from scripts.init_memory_structure import init_memory_structure

        # Initialize file structure
        init_memory_structure(self.file_manager.memory_files_path)

        # Ensure main.md exists
        if not self.file_manager.file_exists("main.md"):
            raise RuntimeError("Failed to create main.md during initialization")

        # Ensure files_index.json exists
        if not self.json_index_manager.json_index_path.exists():
            # Create empty index
            self.json_index_manager.write_index({
                "version": "1.0",
                "last_updated": "",
                "files": []
            })

        # Sync main.md to database if available
        if self.sync_service:
            try:
                await self.sync_service.sync_file("main.md", force=True)
            except Exception as e:
                logger.warning("failed_to_sync_main_to_db", error=str(e))

        logger.info("memory_initialized", path=str(self.file_manager.memory_files_path))

        return {
            "message": "Memory initialized successfully",
            "memory_path": str(self.file_manager.memory_files_path),
            "main_file": "main.md",
            "index_file": "files_index.json"
        }

    async def reset_memory(self) -> dict[str, Any]:
        """
        Reset memory to base state.
        Deletes all files except main.md and files_index.json, clears database.

        Returns:
            Status message with reset details
        """
        # Get all files
        all_files = self.file_manager.list_all_files()

        # Filter out main.md and files_index.json
        files_to_delete = [
            f for f in all_files
            if f != "main.md" and not f.endswith("files_index.json")
        ]

        deleted_count = 0
        errors = []

        # Delete files
        for file_path in files_to_delete:
            try:
                # Delete from database if available
                if self.repository:
                    file_record = await self.repository.get_file_by_path(file_path)
                    if file_record:
                        await self.repository.delete_file(file_record.id)

                # Delete from filesystem
                self.file_manager.delete_file(file_path)

                # Remove from JSON index
                self.json_index_manager.remove_file(file_path)

                deleted_count += 1
            except Exception as e:
                errors.append({"file_path": file_path, "error": str(e)})
                logger.warning("failed_to_delete_file", file_path=file_path, error=str(e))

        # Clear JSON index (keep structure)
        self.json_index_manager.clear_all_files()

        # Reset main.md to base state
        from scripts.init_memory_structure import init_memory_structure
        init_memory_structure(self.file_manager.memory_files_path)

        # Sync main.md if available
        if self.sync_service:
            try:
                await self.sync_service.sync_file("main.md", force=True)
            except Exception as e:
                logger.warning("failed_to_sync_main_after_reset", error=str(e))

        logger.info("memory_reset", deleted_count=deleted_count, errors=len(errors))

        return {
            "message": "Memory reset to base state",
            "deleted_files": deleted_count,
            "errors": errors,
            "remaining_files": ["main.md", "files_index.json"]
        }
