# Agent Memory MCP Server

Multi-file markdown MCP server with hybrid search (vector + fulltext + RRF) for agent memory management. Can be used as MCP server or Python library.

## Features

- **Persistent Memory**: Store agent memories in human-readable markdown files
- **Hybrid Search**: Combines vector (semantic) and fulltext (keyword) search with RRF ranking
- **Multiple Embedding Providers**: OpenAI, Cohere, Ollama, HuggingFace, LiteLLM
- **Intelligent Chunking**: Markdown-aware chunking with header context preservation
- **Automatic Sync**: File changes automatically sync to PostgreSQL + pgvector
- **MCP Integration**: Full MCP support via FastMCP (tools, resources, prompts)
- **Python Library**: Use as standalone Python library with LangChain integration
- **Batch Operations**: Efficient batch create/update/delete/search operations
- **JSON Index**: Complete file metadata in `files_index.json` for fast access
- **Memory Management**: Initialize and reset memory to base state
- **Structured Memory**: Organized by categories (projects, concepts, conversations, preferences)
- **Goal & Task Tracking**: Built-in support for current goals and completed tasks

## Architecture

```
MCP Client (Claude) ↔ FastMCP Server ↔ Memory Manager
                                           ├─ File Manager (Markdown CRUD)
                                           ├─ Search Engine (Hybrid RRF)
                                           ├─ JSON Index Manager
                                           └─ Sync Service (File ↔ DB)
                                               ↓
                                        PostgreSQL + pgvector
```

## Installation

### As Python Library (Recommended)

Install via pip:

```bash
pip install agent-memory-mcp
```

Or install from source:

```bash
git clone https://github.com/we11as22/multifile-markdown-mcp.git
cd multifile-markdown-mcp
pip install -e .
```

### As MCP Server (Docker)

1. Clone the repository:
```bash
git clone https://github.com/we11as22/multifile-markdown-mcp.git
cd multifile-markdown-mcp
```

2. Copy environment template:
```bash
cp .env.example .env
```

3. Edit `.env` and configure your embedding provider:
```bash
# For OpenAI
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# OR for Ollama (local, free)
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
```

4. Start services:
```bash
cd docker
docker-compose up -d
```

5. Check logs:
```bash
docker-compose logs -f mcp-server
```

## Usage

### As Python Library

```python
import asyncio
from agent_memory_mcp import MemoryLibrary

async def main():
    # Initialize library
    memory = MemoryLibrary(
        memory_files_path="./memory",
        database_url="postgresql+asyncpg://user:pass@localhost/agent_memory"
    )
    await memory.initialize()

    # Create a memory file
    result = await memory.create_file(
        title="My Project",
        category="project",
        content="# My Project\n\nProject description...",
        tags=["important", "active"]
    )

    # Search memories
    results = await memory.search(
        query="project details",
        search_mode="hybrid",
        limit=10
    )

    # Batch operations
    files = [
        {"title": "File 1", "category": "project", "content": "# File 1"},
        {"title": "File 2", "category": "concept", "content": "# File 2"},
    ]
    await memory.batch_create_files(files)

    # Cleanup
    await memory.close()

asyncio.run(main())
```

### LangChain Integration

```python
from agent_memory_mcp import MemoryLibrary, get_langchain_tools
from langchain.agents import Agent

# Initialize memory
memory = MemoryLibrary(...)
await memory.initialize()

# Get LangChain tools
tools = get_langchain_tools(memory)

# Use in agent
agent = Agent(tools=tools)
```

### Memory Initialization and Reset

```python
# Initialize memory to base state (creates main.md and files_index.json)
await memory.initialize_memory()

# Reset memory (deletes all files except main.md and files_index.json)
await memory.reset_memory()
```

## Configuration

### Environment Variables

Set `MEMORY_FILES_PATH` to specify memory directory:

```bash
export MEMORY_FILES_PATH=/path/to/memory
```

Or use in code:

```python
memory = MemoryLibrary(
    memory_files_path="/path/to/memory",
    database_url="..."
)
```

### Embedding Providers

#### OpenAI (Recommended)
```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # or text-embedding-3-large
EMBEDDING_DIMENSION=1536  # 3072 for large
```

#### Ollama (Free, Local)
```bash
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

First, pull the model:
```bash
ollama pull nomic-embed-text
```

#### Cohere
```bash
EMBEDDING_PROVIDER=cohere
COHERE_API_KEY=your-key
COHERE_EMBEDDING_MODEL=embed-english-v3.0
```

#### HuggingFace (API or Local)
```bash
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2
HUGGINGFACE_USE_LOCAL=true  # Use local model
HUGGINGFACE_DEVICE=cpu  # or cuda
```

#### LiteLLM (Universal Proxy)
```bash
EMBEDDING_PROVIDER=litellm
LITELLM_MODEL=text-embedding-3-small
# Set provider-specific API keys as needed
```

### Search Configuration

```bash
CHUNK_SIZE=800              # Max chunk size in characters
CHUNK_OVERLAP=200           # Overlap between chunks
SEARCH_LIMIT=20             # Default result limit
RRF_K=60                    # RRF k parameter (higher = less ranking difference)
```

## MCP Tools

### Memory Management

#### `create_memory_file`
Create a new memory file.
```python
{
  "title": "Project Alpha",
  "category": "project",  # project, concept, conversation, preference, other
  "content": "# Project Alpha\n\n...",
  "tags": ["important"],  # optional
  "metadata": {}  # optional
}
```

#### `update_memory_file`
Update existing file.
```python
{
  "file_path": "projects/project_alpha.md",
  "content": "Updated content...",
  "update_mode": "replace"  # replace, append, prepend
}
```

#### `delete_memory_file`
Delete a memory file.
```python
{
  "file_path": "projects/old_project.md"
}
```

#### `get_file_content`
Get file content.
```python
{
  "file_path": "projects/project_alpha.md"
}
```

#### `list_files`
List all memory files.
```python
{
  "category": "project"  # optional filter
}
```

### Search

#### `search` (Unified Search)
Unified search method that replaces `search_memories` and `search_within_file`.

Search across all files or within specific files with flexible filtering:

```python
{
  "query": "machine learning concepts",
  "search_mode": "hybrid",  # hybrid, vector, fulltext
  "limit": 10,
  "file_path": "concepts/ml_concepts.md",  # optional: search within file
  "category_filter": "concept",  # optional: filter by category
  "tag_filter": ["important", "active"]  # optional: filter by tags (ALL must match)
}
```

**Search Modes:**
- `hybrid` (recommended): Combines vector and fulltext search with RRF ranking
- `vector`: Semantic similarity search using embeddings
- `fulltext`: Keyword-based search using PostgreSQL fulltext

**Examples:**
```python
# Search across all files
search("machine learning", search_mode="hybrid", limit=20)

# Search within specific file
search("neural networks", file_path="concepts/ml_concepts.md")

# Search with category filter
search("project status", category_filter="project")

# Search with tag filter
search("important notes", tag_filter=["important", "active"])
```

### Editing

#### `edit_file` (Unified Editing)
Universal editing method that replaces `edit_section`, `find_replace`, and `insert_content`.

Supports three edit types:

**1. Section Editing:**
```python
{
  "file_path": "projects/my_project.md",
  "edit_type": "section",
  "section_header": "## Status",
  "new_content": "In progress",
  "mode": "replace"  # replace, append, prepend
}
```

**2. Find and Replace:**
```python
{
  "file_path": "notes.md",
  "edit_type": "find_replace",
  "find": "old text",
  "replace": "new text",
  "regex": false,  # optional: use regex pattern
  "max_replacements": -1  # optional: -1 for all
}
```

**3. Content Insertion:**
```python
{
  "file_path": "notes.md",
  "edit_type": "insert",
  "content": "New note",
  "position": "end",  # start, end, after_marker
  "marker": "<!-- insert here -->"  # required for after_marker
}
```

### Batch Operations

All CRUD operations support batch processing for efficiency:

#### `batch_create_files`
Create multiple files at once.
```python
{
  "files": [
    {
      "title": "File 1",
      "category": "project",
      "content": "# File 1",
      "tags": ["tag1"],
      "metadata": {}
    },
    {
      "title": "File 2",
      "category": "concept",
      "content": "# File 2"
    }
  ]
}
```

#### `batch_update_files`
Update multiple files at once.
```python
{
  "updates": [
    {
      "file_path": "projects/file1.md",
      "content": "Updated content",
      "update_mode": "replace"
    },
    {
      "file_path": "projects/file2.md",
      "content": "More content",
      "update_mode": "append"
    }
  ]
}
```

#### `batch_delete_files`
Delete multiple files at once.
```python
{
  "file_paths": [
    "projects/file1.md",
    "projects/file2.md"
  ]
}
```

#### `batch_search`
Perform multiple searches at once.
```python
{
  "queries": [
    {
      "query": "machine learning",
      "search_mode": "hybrid",
      "limit": 10
    },
    {
      "query": "neural networks",
      "file_path": "concepts/ml.md",
      "limit": 5
    }
  ]
}
```

### Memory Management

#### `initialize_memory`
Initialize memory to base state (creates `main.md` and `files_index.json`).
```python
{}
```

#### `reset_memory`
Reset memory to base state (deletes all files except `main.md` and `files_index.json`, clears database).
```python
{}
```

### Main Memory File Operations

#### `append_to_main_memory`
Add to main.md sections.
```python
{
  "content": "Important note...",
  "section": "Recent Notes"  # Recent Notes, Current Goals, Future Plans, Quick Reference
}
```

#### `update_goals`
Manage goals in main.md.
```python
{
  "goal": "Complete agent memory implementation",
  "action": "add"  # add, complete, remove
}
```

#### `update_tasks`
Add completed tasks.
```python
{
  "task": "Implemented hybrid search with RRF"
}
```

### Tag Management

#### `add_tags`
Add tags to a file.
```python
{
  "file_path": "projects/my_project.md",
  "tags": ["important", "active"]
}
```

#### `remove_tags`
Remove tags from a file.
```python
{
  "file_path": "projects/my_project.md",
  "tags": ["old-tag"]
}
```

#### `get_tags`
Get all tags for a file.
```python
{
  "file_path": "projects/my_project.md"
}
```

### File Operations

#### `rename_file`
Rename a memory file.
```python
{
  "old_file_path": "projects/old_name.md",
  "new_title": "New Name"
}
```

#### `move_file`
Move a file to a different category.
```python
{
  "file_path": "projects/my_project.md",
  "new_category": "concept"
}
```

#### `copy_file`
Create a copy of a memory file.
```python
{
  "source_file_path": "projects/original.md",
  "new_title": "Copy of Original",
  "new_category": "concept"  # optional
}
```

## MCP Resources

Access memory files directly:

- `memory://main` - Main agent notes
- `memory://file/{file_path}` - Specific memory file

## MCP Prompts

Enhanced prompts with detailed instructions:

- `remember_conversation(topic, key_points)` - Save conversation memory with structured format
- `recall_context(topic)` - Search and recall context with search tips
- `memory_usage_guide()` - Comprehensive guide on using the memory system
- `active_memory_usage()` - Prompt encouraging active memory usage

**Important:** Agents should actively use the memory system throughout conversations to maintain context and provide better assistance.

## Memory Structure

```
memory_files/
├── main.md                    # Central hub with index and goals
├── files_index.json          # JSON index with complete file metadata
├── projects/
│   ├── project_alpha.md
│   └── project_beta.md
├── concepts/
│   ├── technical_concepts.md
│   └── domain_knowledge.md
├── conversations/
│   └── conversation_2025_01.md
└── preferences/
    └── user_preferences.md
```

### Base State

The base state consists of:
- `main.md` - Main memory file with index and goals
- `files_index.json` - JSON file with complete metadata for all files

Use `initialize_memory()` to create base state and `reset_memory()` to restore it.

### main.md Structure

```markdown
# Agent Memory - Main Notes

Last Updated: 2025-01-15

## File Index

This section maintains an index of all specialized memory files with descriptions.

### Projects
- [Project Alpha](/memory_files/projects/project_alpha.md) - Description

### Concepts
- [Technical Concepts](/memory_files/concepts/technical_concepts.md) - Description

## Current Goals
- [ ] Goal 1
- [ ] Goal 2

## Completed Tasks
- [x] Task 1 (completed 2025-01-15)

## Future Plans
- Plan 1

## Recent Notes
### 2025-01-15 - Session Notes
- Note 1

## Quick Reference
- Key info
```

### files_index.json Structure

```json
{
  "version": "1.0",
  "last_updated": "2025-01-15T10:00:00Z",
  "files": [
    {
      "file_path": "projects/project_alpha.md",
      "title": "Project Alpha",
      "category": "project",
      "description": "Main project description",
      "tags": ["important", "active"],
      "metadata": {},
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z",
      "word_count": 1500
    }
  ]
}
```

## Database Schema

### Tables

**memory_files** - File metadata
- id, file_path, title, category
- created_at, updated_at, file_hash
- word_count, tags (array), metadata (JSONB)

**memory_chunks** - Text chunks with embeddings
- id, file_id, chunk_index, content
- embedding (vector), header_path, section_level
- content_tsvector (fulltext index)

**sync_status** - Sync tracking
- file_id, last_synced_at, sync_status

### Hybrid Search Algorithm

Uses **Reciprocal Rank Fusion (RRF)**:

```
RRF_score = sum(1/(rank_vector + k)) + sum(1/(rank_fulltext + k))
```

Where:
- `rank_vector`: Position in semantic similarity results
- `rank_fulltext`: Position in keyword (BM25) results
- `k`: Constant (default 60) to reduce rank difference impact

## Testing

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (requires PostgreSQL)
pytest tests/ -v

# Run library tests specifically
pytest tests/test_library.py -v
```

### Manual Testing Script

```bash
# Start PostgreSQL
cd docker
docker-compose up -d postgres

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=agent_memory
export POSTGRES_USER=memory_user
export POSTGRES_PASSWORD=change_me_in_production

# Run manual test script
python scripts/test_library_manual.py
```

## Development

### Project Structure

```
src/
├── main.py                # FastMCP entry point
├── library.py             # Python library interface
├── models/                # Pydantic models
├── storage/               # File management + JSON index
├── database/              # PostgreSQL + SQLAlchemy
├── embeddings/            # Provider implementations
├── search/                # Chunking + hybrid search
├── sync/                  # File ↔ DB sync
└── mcp/                   # MCP tools/resources/prompts
```

### Running Locally (Development)

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Start PostgreSQL:
```bash
cd docker
docker-compose up -d postgres
```

3. Run MCP server:
```bash
python -m src.main
```

4. Or use as library:
```python
from agent_memory_mcp import MemoryLibrary

memory = MemoryLibrary(...)
await memory.initialize()
```

## Performance

- **Batch Embedding**: 100 chunks per batch
- **Connection Pool**: 5-20 connections
- **Vector Index**: IVFFlat (100 lists)
- **Fulltext Index**: GIN (tsvector)
- **Batch Operations**: Process multiple items efficiently

## Best Practices

1. **Use batch operations** when working with multiple files
2. **Search before creating** to avoid duplicates
3. **Use descriptive titles and tags** for better organization
4. **Keep main.md updated** with goals and tasks
5. **Actively use memory** throughout conversations
6. **Use hybrid search mode** for best results
7. **Initialize memory** before first use
8. **Reset memory** when starting fresh

## Troubleshooting

### Database connection fails
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Verify connection string
echo $DATABASE_URL
```

### Embedding provider errors

**OpenAI**: Verify API key and credits
**Ollama**: Ensure model is pulled (`ollama pull nomic-embed-text`)
**Cohere**: Check API key and quotas
**HuggingFace**: Verify API key or local model path

### Search returns no results

1. Check files are synced: `docker-compose logs mcp-server | grep sync`
2. Verify embeddings generated: Check `memory_chunks` table has `embedding` values
3. Try different search modes (vector, fulltext, hybrid)
4. Check database connection is active

### Library initialization fails

1. Verify database URL is correct
2. Check PostgreSQL is running and accessible
3. Ensure database exists and user has permissions
4. Check environment variables are set correctly

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

For issues: https://github.com/we11as22/multifile-markdown-mcp/issues
