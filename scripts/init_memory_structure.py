"""Initialize memory file structure"""
from pathlib import Path


def init_memory_structure(base_path: Path = Path("./memory_files")) -> None:
    """
    Create initial memory file structure.

    Args:
        base_path: Base path for memory files
    """
    base_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    subdirs = ["projects", "concepts", "conversations", "preferences"]
    for subdir in subdirs:
        (base_path / subdir).mkdir(exist_ok=True)

    # Create main.md if it doesn't exist
    main_file = base_path / "main.md"
    if not main_file.exists():
        main_content = """# Agent Memory - Main Notes

Last Updated: 2025-12-28

## File Index

This section maintains an index of all specialized memory files with descriptions.

### Projects
<!-- Add project files here -->

### Concepts
<!-- Add concept files here -->

### Conversations
<!-- Add conversation files here -->

### Preferences
<!-- Add preference files here -->

---

## Current Goals

<!-- Active goals that the agent is working towards -->

---

## Completed Tasks

<!-- Tasks that have been completed with dates -->

---

## Future Plans

<!-- Long-term plans and ideas for the future -->

---

## Recent Notes

<!-- Recent session notes and important observations -->

---

## Quick Reference

<!-- Quick access to frequently needed information -->
"""
        main_file.write_text(main_content, encoding='utf-8')
        print(f"Created {main_file}")

    print(f"Memory structure initialized at {base_path}")
    print(f"Subdirectories: {', '.join(subdirs)}")


if __name__ == "__main__":
    init_memory_structure()
