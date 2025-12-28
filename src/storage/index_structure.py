"""Manage main.md index structure"""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

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
