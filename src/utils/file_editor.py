"""Advanced file editing utilities for markdown memory files"""
import re
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class MarkdownEditor:
    """Advanced markdown file editing utilities"""

    @staticmethod
    def edit_section(
        content: str,
        section_header: str,
        new_section_content: str,
        mode: str = "replace"
    ) -> str:
        """
        Edit a specific section in markdown by header.

        Args:
            content: Full markdown content
            section_header: Header to find (e.g., "## Goals" or "Goals")
            new_section_content: New content for the section
            mode: 'replace', 'append', 'prepend'

        Returns:
            Updated content
        """
        # Normalize header (add ## if not present)
        if not section_header.startswith('#'):
            section_header = f"## {section_header}"

        # Find section boundaries
        pattern = rf"({re.escape(section_header)}.*?)(\n##|\n#|\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            logger.warning("section_not_found", header=section_header)
            # Append new section at the end
            return content.rstrip() + f"\n\n{section_header}\n\n{new_section_content}\n"

        section_content = match.group(1)
        section_end = match.group(2)

        if mode == "replace":
            new_section = f"{section_header}\n\n{new_section_content}"
        elif mode == "append":
            existing_text = section_content.replace(section_header, "").strip()
            new_section = f"{section_header}\n\n{existing_text}\n\n{new_section_content}"
        elif mode == "prepend":
            existing_text = section_content.replace(section_header, "").strip()
            new_section = f"{section_header}\n\n{new_section_content}\n\n{existing_text}"
        else:
            raise ValueError(f"Invalid mode: {mode}")

        updated_content = content.replace(
            section_content,
            new_section
        )

        logger.info("section_edited", header=section_header, mode=mode)
        return updated_content

    @staticmethod
    def find_and_replace(
        content: str,
        pattern: str,
        replacement: str,
        regex: bool = False,
        count: int = -1
    ) -> tuple[str, int]:
        """
        Find and replace text or pattern in content.

        Args:
            content: Content to search
            pattern: Text or regex pattern to find
            replacement: Replacement text
            regex: Whether pattern is regex
            count: Max replacements (-1 for all)

        Returns:
            (updated_content, number_of_replacements)
        """
        if regex:
            updated, num_subs = re.subn(pattern, replacement, content, count=count if count > 0 else 0)
        else:
            if count == -1:
                updated = content.replace(pattern, replacement)
                num_subs = content.count(pattern)
            else:
                updated = content.replace(pattern, replacement, count)
                num_subs = min(content.count(pattern), count)

        logger.info(
            "find_and_replace_executed",
            replacements=num_subs,
            regex=regex
        )
        return updated, num_subs

    @staticmethod
    def insert_at_position(
        content: str,
        insert_content: str,
        position: str = "end",
        marker: Optional[str] = None
    ) -> str:
        """
        Insert content at specific position.

        Args:
            content: Existing content
            insert_content: Content to insert
            position: 'start', 'end', or 'after_marker'
            marker: Marker text to insert after (when position='after_marker')

        Returns:
            Updated content
        """
        if position == "start":
            return insert_content + "\n\n" + content

        elif position == "end":
            return content.rstrip() + "\n\n" + insert_content

        elif position == "after_marker":
            if not marker:
                raise ValueError("Marker required for 'after_marker' position")

            if marker not in content:
                logger.warning("marker_not_found_appending_to_end", marker=marker)
                return content.rstrip() + "\n\n" + insert_content

            parts = content.split(marker, 1)
            return parts[0] + marker + "\n\n" + insert_content + "\n\n" + parts[1]

        else:
            raise ValueError(f"Invalid position: {position}")

    @staticmethod
    def extract_section(content: str, section_header: str) -> Optional[str]:
        """
        Extract content of a specific section.

        Args:
            content: Full markdown content
            section_header: Section header to extract

        Returns:
            Section content or None if not found
        """
        # Normalize header
        if not section_header.startswith('#'):
            section_header = f"## {section_header}"

        pattern = rf"{re.escape(section_header)}(.*?)(\n##|\n#|\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section_content = match.group(1).strip()
            return section_content

        return None

    @staticmethod
    def list_sections(content: str) -> list[dict[str, str]]:
        """
        List all sections in markdown.

        Returns:
            List of {level, header, content}
        """
        sections = []
        pattern = r"(#{1,6})\s+(.+?)(?=\n#|\Z)"

        for match in re.finditer(pattern, content, re.DOTALL):
            level = len(match.group(1))
            header = match.group(2).strip().split('\n')[0]  # First line is header
            sections.append({
                'level': level,
                'header': header,
                'full_header': match.group(1) + ' ' + header
            })

        return sections

    @staticmethod
    def merge_content(
        existing: str,
        new: str,
        strategy: str = "append"
    ) -> str:
        """
        Merge two markdown contents.

        Args:
            existing: Existing content
            new: New content to merge
            strategy: 'append', 'prepend', 'smart_merge' (merge by sections)

        Returns:
            Merged content
        """
        if strategy == "append":
            return existing.rstrip() + "\n\n---\n\n" + new

        elif strategy == "prepend":
            return new.rstrip() + "\n\n---\n\n" + existing

        elif strategy == "smart_merge":
            # TODO: Implement smart section-based merging
            logger.warning("smart_merge_not_yet_implemented_using_append")
            return existing.rstrip() + "\n\n---\n\n" + new

        else:
            raise ValueError(f"Invalid strategy: {strategy}")
