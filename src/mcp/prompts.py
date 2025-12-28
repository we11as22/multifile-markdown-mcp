"""Enhanced MCP prompts with detailed instructions"""
from typing import Any


def get_memory_usage_prompt() -> str:
    """
    Get a comprehensive prompt about memory usage for agents.

    Returns:
        Detailed prompt text
    """
    return """# Agent Memory System - Usage Guide

You have access to a powerful memory system that allows you to store, retrieve, and manage information across sessions. **You should actively use this memory system** to maintain context and improve your responses.

## Core Principles

1. **Always use memory for important information**: When the user shares important details, preferences, project information, or decisions, save them to memory.
2. **Search before answering**: Before providing answers, search your memory for relevant context.
3. **Update memory regularly**: Keep memory files up-to-date as projects evolve and new information emerges.
4. **Use batch operations**: When working with multiple items, use batch operations for efficiency.

## Available Tools

### File Management

- **create_memory_file**: Create a new memory file with title, category, content, tags, and metadata
- **update_memory_file**: Update existing file content (replace/append/prepend modes)
- **delete_memory_file**: Delete a memory file
- **get_file_content**: Read a file's content
- **list_files**: List all files, optionally filtered by category

### Search

- **search**: Unified search across all files or within specific files
  - Use `file_path` parameter to search within a specific file
  - Use `category_filter` to filter by category
  - Use `tag_filter` to find files with specific tags
  - Search modes: "hybrid" (recommended), "vector", "fulltext"

### Editing

- **edit_file**: Universal editing method supporting:
  - `edit_type="section"`: Edit a section by header (requires: section_header, new_content, mode)
  - `edit_type="find_replace"`: Find and replace text (requires: find, replace, optional: regex)
  - `edit_type="insert"`: Insert content at position (requires: content, optional: position, marker)

### Batch Operations

- **batch_create_files**: Create multiple files at once
- **batch_update_files**: Update multiple files at once
- **batch_delete_files**: Delete multiple files at once
- **batch_search**: Perform multiple searches at once

### Memory Management

- **initialize_memory**: Initialize memory to base state (main.md + files_index.json)
- **reset_memory**: Reset memory to base state (deletes all files except main.md and files_index.json)

### Main Memory File

- **append_to_main_memory**: Add content to main.md sections (Recent Notes, Current Goals, Future Plans, Quick Reference)
- **update_goals**: Manage goals in main.md (add/complete actions)
- **update_tasks**: Add completed tasks to main.md

## Usage Scenarios

### Scenario 1: Starting a New Project

1. Create a project file: `create_memory_file(title="Project Name", category="project", content="...")`
2. Add initial goals: `update_goals(goal="Complete project setup", action="add")`
3. Search for related information: `search(query="similar projects", category_filter="project")`

### Scenario 2: Retrieving Context

1. Search for relevant information: `search(query="user preferences", tag_filter=["important"])`
2. Read specific files: `get_file_content(file_path="preferences/user_prefs.md")`
3. Update with new information: `update_memory_file(file_path="...", content="...")`

### Scenario 3: Organizing Information

1. List all files: `list_files(category="project")`
2. Add tags for better organization: Use tag management tools
3. Use batch operations for multiple updates

### Scenario 4: Maintaining Goals and Tasks

1. Add goals: `update_goals(goal="New goal", action="add")`
2. Complete goals: `update_goals(goal="Completed goal", action="complete")`
3. Add tasks: `update_tasks(task="Completed task")`

## Best Practices

1. **Use descriptive titles**: Make file titles clear and searchable
2. **Add relevant tags**: Tag files for easy filtering and search
3. **Keep main.md updated**: Regularly update goals, tasks, and notes
4. **Search before creating**: Check if information already exists before creating new files
5. **Use batch operations**: When working with multiple items, use batch operations
6. **Update metadata**: Include relevant metadata for better organization

## Important Notes

- Memory files are stored in markdown format for human readability
- All operations automatically sync to the database for search
- The JSON index (files_index.json) maintains complete file metadata
- Search supports hybrid (semantic + keyword) search for best results
- Batch operations are more efficient than individual operations

**Remember: Actively use the memory system to maintain context and provide better assistance!**
"""


def remember_conversation_prompt(topic: str, key_points: str) -> list[dict[str, Any]]:
    """
    Generate a prompt to save conversation memory.

    Args:
        topic: Conversation topic
        key_points: Key points to remember

    Returns:
        List of prompt messages
    """
    return [
        {
            "role": "user",
            "content": f"""Please create a memory file for this conversation about: {topic}

Key points to remember:
{key_points}

**Instructions:**
1. Use the `create_memory_file` tool with category='conversation'
2. Create a well-structured markdown file with:
   - A clear title based on the topic
   - Date and context of the conversation
   - Main discussion points
   - Important decisions or conclusions
   - Follow-up actions if any
   - Relevant tags for easy retrieval

3. If this relates to an existing project or concept, search for related files first using the `search` tool
4. Consider adding this to main.md's Recent Notes section using `append_to_main_memory`

**Example structure:**
```markdown
# {topic}

**Date:** [current date]
**Context:** [brief context]

## Discussion Points
- [point 1]
- [point 2]

## Decisions
- [decision 1]

## Actions
- [ ] Action item 1
- [ ] Action item 2
```

Use the create_memory_file tool now."""
        }
    ]


def recall_context_prompt(topic: str) -> list[dict[str, Any]]:
    """
    Generate a prompt to recall relevant context.

    Args:
        topic: Topic to search for

    Returns:
        List of prompt messages
    """
    return [
        {
            "role": "user",
            "content": f"""Search my memory for information about: {topic}

**Instructions:**
1. Use the `search` tool with:
   - query: "{topic}"
   - search_mode: "hybrid" (recommended for best results)
   - limit: 10 (or more if needed)

2. Review the search results and identify the most relevant information

3. If you find relevant files, you can:
   - Read full file content using `get_file_content` if needed
   - Update the information if it's outdated using `update_memory_file`
   - Add related information to main.md if it's important

4. Summarize the relevant findings and use them to provide better assistance

**Search tips:**
- Try different search queries if initial results aren't helpful
- Use `category_filter` to narrow down by category (project, concept, conversation, etc.)
- Use `tag_filter` to find files with specific tags
- Use `file_path` to search within a specific file

Start by searching for: "{topic}"
"""
        }
    ]


def active_memory_usage_prompt() -> str:
    """
    Get a prompt encouraging active memory usage.

    Returns:
        Prompt text
    """
    return """**IMPORTANT: Actively Use Memory System**

You should actively use the memory system throughout our conversation:

1. **Before answering questions**: Search memory for relevant context
2. **When receiving new information**: Save important details to memory
3. **When making decisions**: Update goals and tasks in main.md
4. **When organizing work**: Use tags and categories effectively
5. **When working with multiple items**: Use batch operations

The memory system helps you:
- Maintain context across sessions
- Provide more accurate and personalized responses
- Track goals and tasks
- Organize information efficiently

Don't hesitate to use memory tools - they're designed to make you more helpful!"""

