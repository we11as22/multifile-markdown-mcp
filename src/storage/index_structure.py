"""Manage main.md index structure and JSON file index"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class IndexManager:
    """Manages the File Index section in main.md"""

    def __init__(self, main_file_path: Path) -> None:
        """
        Initialize index manager.

        Args:
            main_file_path: Path to main.md file
        """
        self.main_file_path = main_file_path
        logger.info("index_manager_initialized", path=str(main_file_path))

    def read_main_file(self) -> str:
        """Read main.md content"""
        if not self.main_file_path.exists():
            raise FileNotFoundError(f"Main file not found: {self.main_file_path}")
        return self.main_file_path.read_text(encoding='utf-8')

    def write_main_file(self, content: str) -> None:
        """Write content to main.md"""
        self.main_file_path.write_text(content, encoding='utf-8')
        logger.info("main_file_updated")

    def update_file_index(self, file_path: str, description: str, category: str) -> None:
        """
        Add or update file reference in the File Index section.

        Args:
            file_path: Path to the memory file
            description: Description of the file
            category: Category (projects, concepts, conversations, preferences)
        """
        content = self.read_main_file()

        # Find the appropriate category section
        category_header = f"### {category.title()}"
        link = f"- [{Path(file_path).stem.replace('_', ' ').title()}](/memory_files/{file_path}) - {description}"

        # Check if category section exists
        if category_header not in content:
            logger.warning("category_not_found_in_index", category=category)
            return

        # Replace the section
        pattern = rf"({re.escape(category_header)}.*?)(\n###|\n---|\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section_content = match.group(1)

            # Check if file already exists in section
            file_pattern = rf"- \[.*?\]\(/memory_files/{re.escape(file_path)}\)"
            if re.search(file_pattern, section_content):
                # Update existing entry
                new_section = re.sub(file_pattern, link, section_content)
            else:
                # Add new entry (remove comment if exists)
                new_section = section_content.replace("<!-- Add", link + "\n<!-- Add")

            content = content.replace(section_content, new_section)
            self.write_main_file(content)
            logger.info("file_index_updated", file_path=file_path, category=category)

    def append_to_section(self, section_name: str, content_to_add: str) -> None:
        """
        Append content to a specific section in main.md.

        Args:
            section_name: Name of the section (e.g., "Recent Notes", "Current Goals")
            content_to_add: Content to append
        """
        content = self.read_main_file()

        # Find section header
        section_pattern = rf"(## {re.escape(section_name)}.*?)(\n##|\Z)"
        match = re.search(section_pattern, content, re.DOTALL)

        if not match:
            logger.warning("section_not_found", section=section_name)
            return

        section_content = match.group(1)

        # Append content before next section or end
        # Insert after section header and any existing content
        new_section = section_content.rstrip() + "\n\n" + content_to_add + "\n"

        content = content.replace(section_content, new_section)

        # Update "Last Updated" timestamp
        content = re.sub(
            r"Last Updated: .*",
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}",
            content
        )

        self.write_main_file(content)
        logger.info("section_appended", section=section_name)

    def add_goal(self, goal: str) -> None:
        """Add a goal to Current Goals section"""
        self.append_to_section("Current Goals", f"- [ ] {goal}")

    def complete_goal(self, goal: str) -> None:
        """Move goal from Current Goals to Completed Tasks"""
        content = self.read_main_file()

        # Find and remove from Current Goals
        goal_pattern = rf"- \[ \] {re.escape(goal)}"
        content = re.sub(goal_pattern, "", content)

        # Add to Completed Tasks
        completed_entry = f"- [x] {goal} (completed {datetime.now().strftime('%Y-%m-%d')})"
        self.write_main_file(content)
        self.append_to_section("Completed Tasks", completed_entry)

        logger.info("goal_completed", goal=goal)

    def add_task(self, task: str) -> None:
        """Add task to Completed Tasks section"""
        entry = f"- [x] {task} (completed {datetime.now().strftime('%Y-%m-%d')})"
        self.append_to_section("Completed Tasks", entry)

    def add_future_plan(self, plan: str) -> None:
        """Add to Future Plans section"""
        self.append_to_section("Future Plans", f"- {plan}")
    
    def add_plan(self, plan: str) -> None:
        """Add a plan to Plans section"""
        self.append_to_section("Plans", f"- [ ] {plan}")
    
    def complete_plan(self, plan: str) -> None:
        """Mark plan as completed"""
        content = self.read_main_file()
        
        # Find and remove from Plans
        plan_pattern = rf"- \[ \] {re.escape(plan)}"
        content = re.sub(plan_pattern, f"- [x] {plan}", content)
        
        self.write_main_file(content)
        logger.info("plan_completed", plan=plan)


class JsonIndexManager:
    """Manages the files_index.json file with complete file metadata"""

    def __init__(self, json_index_path: Path) -> None:
        """
        Initialize JSON index manager.

        Args:
            json_index_path: Path to files_index.json file
        """
        self.json_index_path = json_index_path
        logger.info("json_index_manager_initialized", path=str(json_index_path))

    def read_index(self) -> dict[str, Any]:
        """
        Read the JSON index file.

        Returns:
            Dictionary with index data
        """
        if not self.json_index_path.exists():
            return {
                "version": "1.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "files": []
            }

        try:
            content = self.json_index_path.read_text(encoding='utf-8')
            data = json.loads(content)
            logger.debug("json_index_read", files_count=len(data.get("files", [])))
            return data
        except (json.JSONDecodeError, Exception) as e:
            logger.error("json_index_read_failed", error=str(e))
            # Return default structure if file is corrupted
            return {
                "version": "1.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "files": []
            }

    def write_index(self, data: dict[str, Any]) -> None:
        """
        Write data to JSON index file.

        Args:
            data: Dictionary with index data
        """
        # Update last_updated timestamp
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

        try:
            # Ensure parent directory exists
            self.json_index_path.parent.mkdir(parents=True, exist_ok=True)

            # Write with pretty formatting
            content = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_index_path.write_text(content, encoding='utf-8')
            logger.info("json_index_written", files_count=len(data.get("files", [])))
        except Exception as e:
            logger.error("json_index_write_failed", error=str(e))
            raise

    def add_or_update_file(
        self,
        file_path: str,
        title: str,
        category: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        word_count: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """
        Add or update a file entry in the JSON index.

        Args:
            file_path: Path to the file
            title: File title
            category: File category
            description: Optional description
            tags: Optional tags list
            metadata: Optional metadata dict
            word_count: Word count
            created_at: Creation timestamp (defaults to now)
            updated_at: Update timestamp (defaults to now)
        """
        data = self.read_index()

        # Prepare file entry
        now = datetime.now(timezone.utc)
        file_entry = {
            "file_path": file_path,
            "title": title,
            "category": category,
            "description": description or title,
            "tags": tags or [],
            "metadata": metadata or {},
            "word_count": word_count,
            "created_at": (created_at or now).isoformat(),
            "updated_at": (updated_at or now).isoformat(),
        }

        # Find existing entry
        files = data.get("files", [])
        existing_index = None
        for i, f in enumerate(files):
            if f.get("file_path") == file_path:
                existing_index = i
                break

        if existing_index is not None:
            # Update existing entry, preserve created_at
            existing = files[existing_index]
            file_entry["created_at"] = existing.get("created_at", file_entry["created_at"])
            files[existing_index] = file_entry
            logger.debug("json_index_file_updated", file_path=file_path)
        else:
            # Add new entry
            files.append(file_entry)
            logger.debug("json_index_file_added", file_path=file_path)

        data["files"] = files
        self.write_index(data)

    def remove_file(self, file_path: str) -> None:
        """
        Remove a file entry from the JSON index.

        Args:
            file_path: Path to the file to remove
        """
        data = self.read_index()
        files = data.get("files", [])

        # Filter out the file
        original_count = len(files)
        files = [f for f in files if f.get("file_path") != file_path]

        if len(files) < original_count:
            data["files"] = files
            self.write_index(data)
            logger.info("json_index_file_removed", file_path=file_path)
        else:
            logger.warning("json_index_file_not_found", file_path=file_path)

    def get_file(self, file_path: str) -> Optional[dict[str, Any]]:
        """
        Get a file entry from the JSON index.

        Args:
            file_path: Path to the file

        Returns:
            File entry dict or None if not found
        """
        data = self.read_index()
        files = data.get("files", [])

        for f in files:
            if f.get("file_path") == file_path:
                return f

        return None

    def get_all_files(self) -> list[dict[str, Any]]:
        """
        Get all file entries from the JSON index.

        Returns:
            List of file entry dicts
        """
        data = self.read_index()
        return data.get("files", [])

    def clear_all_files(self) -> None:
        """Clear all file entries from the JSON index (keep structure)"""
        data = self.read_index()
        data["files"] = []
        self.write_index(data)
        logger.info("json_index_cleared")
