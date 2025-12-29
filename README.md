# Agent Memory MCP Server

Multi-file markdown MCP server with hybrid search (vector + fulltext + RRF) for agent memory management. Can be used as MCP server or Python library.

## 🚀 Возможности

**9 универсальных MCP инструментов** - все операции работают с массивами, без дублирования:
- 📁 **files** - Управление файлами (create, read, update, delete, move, copy, rename, list)
- 🔍 **search** - Поиск с гибридным алгоритмом (vector + fulltext + RRF)
- ✏️ **edit** - Редактирование (секции, поиск/замена, вставка)
- 🏷️ **tags** - Управление тегами (add, remove, get)
- 🎯 **main** - Операции с main.md (append, goal, task, plan)
- 🔧 **memory** - Управление памятью (initialize, reset)
- 📄 **extract** - Извлечение секций из файлов
- 📋 **list** - Списки файлов и секций
- 💡 **help** - Помощь, рекомендации, гайды и примеры использования

**Все инструменты всегда работают с массивами** - нет разделения на batch и не-batch версии!

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

#### С БД (полный функционал с поиском)

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

#### Без БД (file-only mode)

Для работы без БД (без поиска, но со всеми остальными операциями):

**Вариант 1: Использовать специальный compose файл (рекомендуется)**
```bash
cd docker
docker-compose -f docker-compose.file-only.yml up -d
```

**Вариант 2: Использовать основной compose с переменной окружения**
```bash
cd docker

# Установить переменную окружения
export USE_DATABASE=false

# Запустить только MCP сервер (без postgres и ollama)
docker-compose up -d mcp-server
```

**Вариант 3: Через .env файл**
```bash
cd docker

# Создать/отредактировать .env
echo "USE_DATABASE=false" >> .env

# Запустить только MCP сервер
docker-compose up -d mcp-server
```

**Проверка работы:**
```bash
# Проверить логи
docker-compose logs -f mcp-server

# Должно быть сообщение: "database_disabled_using_file_only_mode"
```

**Преимущества режима без БД:**
- ✅ Не требует PostgreSQL
- ✅ Быстрый старт (не нужно ждать инициализации БД)
- ✅ Все операции с файлами работают
- ✅ Управление тегами через JSON index
- ✅ Список файлов с деревом и описаниями
- ✅ Операции с main.md работают
- ❌ Поиск недоступен (требует БД)

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

### File-Only Mode (Без БД)

Сервис может работать **без базы данных** в режиме только файлов. В этом режиме:
- ✅ Все операции с файлами работают (create, read, update, delete, move, copy, rename)
- ✅ Управление тегами работает через JSON index
- ✅ Операции с main.md работают
- ✅ Список файлов возвращает дерево с описаниями
- ❌ Поиск недоступен (требует БД)

**Включение режима без БД:**

Через переменную окружения:
```bash
export USE_DATABASE=false
```

Или в коде:
```python
memory = MemoryLibrary(
    memory_files_path="./memory",
    use_database=False  # Включает режим без БД
)
await memory.initialize()
```

**Список файлов с деревом:**
```python
result = await memory.list_files()
# result содержит:
# {
#   "files": [...],  # Плоский список всех файлов
#   "tree": {         # Дерево по категориям
#     "projects": [
#       {
#         "file_path": "projects/project_1.md",
#         "title": "Project 1",
#         "description": "Описание проекта",
#         "tags": ["important"],
#         "updated_at": "2025-12-29T...",
#         "word_count": 150
#       }
#     ],
#     "concepts": [...]
#   },
#   "total": 10
# }
```

### Environment Variables

Set `MEMORY_FILES_PATH` to specify memory directory:

```bash
export MEMORY_FILES_PATH=/path/to/memory
```

Or use in code:

```python
memory = MemoryLibrary(
    memory_files_path="/path/to/memory",
    database_url="..."  # Опционально, если use_database=True
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

Сервис предоставляет **9 универсальных MCP инструментов**. Все операции работают с массивами - нет дублирования между batch и не-batch версиями.

### 📁 1. files - Управление файлами

**Всегда работает с массивом операций.** Поддерживает операции: `create`, `read`, `update`, `delete`, `move`, `copy`, `rename`, `list`.

```python
# Создание нескольких файлов
files(operation="create", items=[
    {"title": "Project 1", "category": "project", "content": "# Project 1", "tags": ["important"]},
    {"title": "Concept 1", "category": "concept", "content": "# Concept 1"},
])

# Чтение нескольких файлов
files(operation="read", items=[
    {"file_path": "projects/project_1.md"},
    {"file_path": "concepts/concept_1.md"},
])

# Обновление файлов
files(operation="update", items=[
    {"file_path": "projects/project_1.md", "content": "# Updated", "update_mode": "replace"},
    {"file_path": "concepts/concept_1.md", "content": "# More content", "update_mode": "append"},
])

# Удаление файлов
files(operation="delete", items=[
    {"file_path": "projects/old_project.md"},
])

# Перемещение файлов
files(operation="move", items=[
    {"file_path": "projects/project.md", "new_category": "concept"},
])

# Копирование файлов
files(operation="copy", items=[
    {"source_file_path": "projects/original.md", "new_title": "Copy", "new_category": "concept"},
])

# Переименование файлов
files(operation="rename", items=[
    {"old_file_path": "projects/old_name.md", "new_title": "New Name"},
])

# Список файлов
files(operation="list", items=[
    {"category": "project"},  # опционально
])
```

### 🔍 2. search - Поиск

**Всегда работает с массивом запросов.** Поддерживает режимы: `hybrid` (рекомендуется), `vector`, `fulltext`.

```python
# Множественный поиск
search(queries=[
    {
        "query": "machine learning",
        "search_mode": "hybrid",
        "limit": 10,
        "category_filter": "concept",  # опционально
        "tag_filter": ["important"],  # опционально
    },
    {
        "query": "neural networks",
        "file_path": "concepts/ml.md",  # поиск внутри файла
        "limit": 5,
    },
])
```

**Режимы поиска:**
- `hybrid` (рекомендуется): Комбинация векторного и полнотекстового поиска с ранжированием RRF
- `vector`: Семантический поиск по схожести с использованием embeddings
- `fulltext`: Поиск по ключевым словам с использованием PostgreSQL fulltext

### ✏️ 3. edit - Редактирование

**Всегда работает с массивом операций.** Поддерживает типы: `section`, `find_replace`, `insert`.

```python
# Множественное редактирование
edit(operations=[
    {
        "file_path": "projects/project.md",
        "edit_type": "section",
        "section_header": "## Status",
        "new_content": "In progress",
        "mode": "replace"  # replace, append, prepend
    },
    {
        "file_path": "notes.md",
        "edit_type": "find_replace",
        "find": "old text",
        "replace": "new text",
        "regex": false,  # опционально
        "max_replacements": -1  # опционально, -1 для всех
    },
    {
        "file_path": "notes.md",
        "edit_type": "insert",
        "content": "New note",
        "position": "end",  # start, end, after_marker
        "marker": "<!-- insert here -->"  # для after_marker
    },
])
```

### 🏷️ 4. tags - Управление тегами

**Всегда работает с массивом файлов.** Поддерживает операции: `add`, `remove`, `get`.

```python
# Добавление тегов к нескольким файлам
tags(operation="add", items=[
    {"file_path": "projects/project1.md", "tags": ["important", "active"]},
    {"file_path": "projects/project2.md", "tags": ["important"]},
])

# Удаление тегов
tags(operation="remove", items=[
    {"file_path": "projects/project1.md", "tags": ["old-tag"]},
])

# Получение тегов
tags(operation="get", items=[
    {"file_path": "projects/project1.md"},
])
```

### 🎯 5. main - Операции с main.md

**Всегда работает с массивом операций.** Поддерживает операции: `append`, `goal`, `task`, `plan`.

```python
# Добавление заметок в секции
main(operation="append", items=[
    {"content": "Important note", "section": "Recent Notes"},  # Recent Notes, Current Goals, Future Plans, Plans, Quick Reference
])

# Управление целями
main(operation="goal", items=[
    {"goal": "Complete project", "action": "add"},  # add, complete, remove
    {"goal": "Test system", "action": "add"},
])

# Управление задачами
main(operation="task", items=[
    {"task": "Completed task 1", "action": "add"},
])

# Управление планами
main(operation="plan", items=[
    {"plan": "Implement feature X", "action": "add"},  # add, complete
])
```

### 🔧 6. memory - Управление памятью

Поддерживает операции: `initialize`, `reset`.

```python
# Инициализация памяти
memory(operation="initialize")

# Сброс памяти
memory(operation="reset")
```

### 📄 7. extract - Извлечение секций

**Всегда работает с массивом запросов.**

```python
# Извлечение секций из нескольких файлов
extract(requests=[
    {"file_path": "projects/project.md", "section_header": "## Status"},
    {"file_path": "concepts/concept.md", "section_header": "## Details"},
])
```

### 📋 8. list - Списки файлов и секций

**Всегда работает с массивом запросов.** Поддерживает типы: `files`, `sections`.

**Список файлов возвращает дерево с описаниями:**
```python
list(requests=[{"type": "files", "category": "project"}])
# Возвращает:
# {
#   "results": [{
#     "files": [...],  # Плоский список
#     "tree": {        # Дерево по категориям
#       "projects": [
#         {
#           "file_path": "projects/project_1.md",
#           "title": "Project 1",
#           "description": "Описание проекта",
#           "tags": ["important"],
#           "updated_at": "2025-12-29T...",
#           "word_count": 150
#         }
#       ]
#     },
#     "total": 5
#   }]
# }
```

```python
# Получение списков файлов и секций
list(requests=[
    {"type": "files", "category": "project"},  # опционально
    {"type": "sections", "file_path": "projects/project.md"},
])
```

### 💡 9. help - Помощь и рекомендации

**Единый инструмент для получения помощи, рекомендаций, гайдов и примеров использования.**

```python
# Полный гайд
help(topic=None)  # или help(topic="all")

# Гайд по конкретной теме
help(topic="files")  # files, search, edit, tags, main, memory, extract, list, examples
```

## MCP Resources

Прямой доступ к файлам памяти через ресурсы:

- **`memory://main`** - Главный файл заметок агента (main.md)
- **`memory://file/{file_path}`** - Конкретный файл памяти по пути

**Примеры:**
- `memory://main` - получить main.md
- `memory://file/projects/my_project.md` - получить конкретный файл проекта

## MCP Prompts

Расширенные промпты с детальными инструкциями:

### `remember_conversation(topic, key_points)`
Сохранить память о разговоре в структурированном формате.
```python
{
  "topic": "Обсуждение проекта",
  "key_points": "Основные моменты разговора..."
}
```
Создает файл категории `conversation` с датой, контекстом, ключевыми моментами, решениями и действиями.

### `recall_context(topic)`
Поиск и восстановление контекста с советами по поиску.
```python
{
  "topic": "информация о проекте"
}
```
Выполняет поиск по теме и предоставляет инструкции по использованию результатов.

### `memory_usage_guide()`
Полное руководство по использованию системы памяти.
Возвращает детальное описание всех инструментов, сценариев использования и лучших практик.

### `active_memory_usage()`
Промпт, поощряющий активное использование памяти.
Напоминает агенту о необходимости использовать систему памяти на протяжении всего разговора.

**Важно:** Агенты должны активно использовать систему памяти на протяжении всего разговора для поддержания контекста и предоставления лучшей помощи.

## Полный список инструментов

### Всего доступно 9 универсальных MCP инструментов:

1. **`files`** - Управление файлами (create, read, update, delete, move, copy, rename, list)
2. **`search`** - Поиск (hybrid, vector, fulltext)
3. **`edit`** - Редактирование (section, find_replace, insert)
4. **`tags`** - Управление тегами (add, remove, get)
5. **`main`** - Операции с main.md (append, goal, task, plan)
6. **`memory`** - Управление памятью (initialize, reset)
7. **`extract`** - Извлечение секций
8. **`list`** - Списки файлов и секций
9. **`help`** - Помощь, рекомендации, гайды и примеры

**Все инструменты всегда работают с массивами** - нет разделения на batch и не-batch версии!

**Ресурсы (2):**
- `memory://main` - Главный файл
- `memory://file/{path}` - Файл по пути

**Промпты (4):**
- `remember_conversation` - Сохранить разговор
- `recall_context` - Восстановить контекст
- `memory_usage_guide` - Руководство
- `active_memory_usage` - Активное использование

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

1. **Все операции работают с массивами** - используйте массивы даже для одного элемента
2. **Search before creating** - ищите перед созданием, чтобы избежать дубликатов
3. **Use descriptive titles and tags** - используйте описательные заголовки и теги
4. **Keep main.md updated** - обновляйте цели, задачи и планы в main.md
5. **Actively use memory** - активно используйте память на протяжении разговора
6. **Use hybrid search mode** - используйте гибридный режим поиска для лучших результатов
7. **Initialize memory** - инициализируйте память перед первым использованием
8. **Use help tool** - используйте инструмент help для получения рекомендаций и примеров

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
