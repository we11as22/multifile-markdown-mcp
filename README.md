# Agent Memory MCP Server

Multi-file markdown MCP server with hybrid search (vector + fulltext + RRF) for agent memory management.

## Features

- **Persistent Memory**: Store agent memories in human-readable markdown files
- **Hybrid Search**: Combines vector (semantic) and fulltext (keyword) search with RRF ranking
- **Multiple Embedding Providers**: OpenAI, Cohere, Ollama, HuggingFace, LiteLLM
- **Intelligent Chunking**: Markdown-aware chunking with header context preservation
- **Automatic Sync**: File changes automatically sync to PostgreSQL + pgvector
- **MCP Integration**: Full MCP support via FastMCP (tools, resources, prompts)
- **Structured Memory**: Organized by categories (projects, concepts, conversations, preferences)
- **Goal & Task Tracking**: Built-in support for current goals and completed tasks

## Architecture

```
MCP Client (Claude) ↔ FastMCP Server ↔ Memory Manager
                                           ├─ File Manager (Markdown CRUD)
                                           ├─ Search Engine (Hybrid RRF)
                                           └─ Sync Service (File ↔ DB)
                                               ↓
                                        PostgreSQL + pgvector
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) API keys for embedding providers (OpenAI, Cohere, HuggingFace)

### Installation

1. Clone the repository:
```bash
cd /workspace/work/multifile-markdown-mcp
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

### Running Locally (Development)

1. Install dependencies with UV:
```bash
pip install uv
uv pip install -e .
```

2. Start PostgreSQL:
```bash
docker-compose up -d postgres
```

3. Run MCP server:
```bash
python -m src.main
```

## Configuration

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
  "content": "# Project Alpha\n\n..."
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

#### `append_to_main_memory`
Add to main.md sections.
```python
{
  "content": "Important note...",
  "section": "Recent Notes"  # Recent Notes, Current Goals, Future Plans, Quick Reference
}
```

### Goal & Task Management

#### `update_goals`
Manage goals.
```python
{
  "goal": "Complete agent memory implementation",
  "action": "add"  # add, complete
}
```

#### `update_tasks`
Add completed tasks.
```python
{
  "task": "Implemented hybrid search with RRF"
}
```

### Search

#### `search_memories`
Search across all memories.
```python
{
  "query": "machine learning concepts",
  "search_mode": "hybrid",  # hybrid, vector, fulltext
  "limit": 10,
  "category_filter": "concept"  # optional
}
```

#### `search_within_file`
Search within specific file.
```python
{
  "file_path": "concepts/ml_concepts.md",
  "query": "neural networks",
  "search_mode": "hybrid"
}
```

#### `list_files`
List all memory files.
```python
{
  "category": "project"  # optional filter
}
```

## MCP Resources

Access memory files directly:

- `memory://main` - Main agent notes
- `memory://file/{file_path}` - Specific memory file

## MCP Prompts

- `remember_conversation(topic, key_points)` - Save conversation memory
- `recall_context(topic)` - Search and recall context

## Memory Structure

```
memory_files/
├── main.md                    # Central hub with index and goals
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

### main.md Structure

```markdown
# Agent Memory - Main Notes

## File Index
### Projects
- [Project Alpha](/memory_files/projects/project_alpha.md) - Description

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

## Database Schema

### Tables

**memory_files** - File metadata
- id, file_path, title, category
- created_at, updated_at, file_hash
- word_count, metadata (JSONB)

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

## Development

### Project Structure

```
src/
├── main.py                # FastMCP entry point
├── models/                # Pydantic models
├── storage/               # File management
├── database/              # PostgreSQL + SQLAlchemy
├── embeddings/            # Provider implementations
├── search/                # Chunking + hybrid search
├── sync/                  # File ↔ DB sync
└── mcp/                   # MCP tools/resources/prompts
```

## Performance

- **Batch Embedding**: 100 chunks per batch
- **Connection Pool**: 5-20 connections
- **Vector Index**: IVFFlat (100 lists)
- **Fulltext Index**: GIN (tsvector)

## Troubleshooting

### Database connection fails
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

### Embedding provider errors

**OpenAI**: Verify API key and credits
**Ollama**: Ensure model is pulled (`ollama pull nomic-embed-text`)
**Cohere**: Check API key and quotas

### Search returns no results

1. Check files are synced: `docker-compose logs mcp-server | grep sync`
2. Verify embeddings generated: Check `memory_chunks` table has `embedding` values
3. Try different search modes (vector, fulltext, hybrid)

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

For issues: https://github.com/we11as22/multifile-markdown-mcp/issues