"""Unified MCP tools - все операции работают с массивами"""
from typing import Any, Literal, Optional
import structlog

from src.mcp.tools import MemoryTools

logger = structlog.get_logger(__name__)


class UnifiedMemoryTools:
    """Универсальные инструменты - все операции работают с массивами"""
    
    def __init__(self, memory_tools: MemoryTools) -> None:
        """Инициализация с использованием существующих MemoryTools"""
        self.tools = memory_tools

    # =============================
    # 1. FILES - Управление файлами
    # =============================
    
    async def files(
        self,
        operation: Literal["create", "read", "update", "delete", "move", "copy", "rename", "list"],
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Универсальное управление файлами. Всегда работает с массивом операций.
        
        Args:
            operation: Тип операции (create, read, update, delete, move, copy, rename, list)
            items: Массив элементов для обработки
            
        Returns:
            Результаты операций с успешными и неудачными
        """
        results = []
        errors = []
        
        for item in items:
            try:
                if operation == "create":
                    result = await self.tools.create_memory_file(
                        title=item["title"],
                        category=item["category"],
                        content=item["content"],
                        tags=item.get("tags"),
                        metadata=item.get("metadata"),
                    )
                elif operation == "read":
                    result = await self.tools.get_file_content(item["file_path"])
                elif operation == "update":
                    result = await self.tools.update_memory_file(
                        file_path=item["file_path"],
                        content=item["content"],
                        update_mode=item.get("update_mode", "replace"),
                    )
                elif operation == "delete":
                    result = await self.tools.delete_memory_file(item["file_path"])
                elif operation == "move":
                    result = await self.tools.move_file(
                        file_path=item["file_path"],
                        new_category=item["new_category"],
                    )
                elif operation == "copy":
                    result = await self.tools.copy_file(
                        source_file_path=item["source_file_path"],
                        new_title=item["new_title"],
                        new_category=item.get("new_category"),
                    )
                elif operation == "rename":
                    result = await self.tools.rename_file(
                        old_file_path=item["old_file_path"],
                        new_title=item["new_title"],
                    )
                elif operation == "list":
                    result = await self.tools.list_files(item.get("category"))
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                
                results.append(result)
            except Exception as e:
                errors.append({
                    "item": item,
                    "error": str(e)
                })
        
        return {
            "operation": operation,
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    # =============================
    # 2. SEARCH - Поиск
    # =============================
    
    async def search(
        self,
        queries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Универсальный поиск. Всегда работает с массивом запросов.
        
        Args:
            queries: Массив запросов, каждый содержит:
                - query: Текст запроса
                - search_mode: hybrid/vector/fulltext (default: hybrid)
                - limit: Максимум результатов (default: 10)
                - file_path: Опциональный путь файла
                - category_filter: Опциональный фильтр категории
                - tag_filter: Опциональный массив тегов
                
        Returns:
            Результаты поиска для каждого запроса
        """
        results = []
        errors = []
        
        for query_def in queries:
            try:
                result = await self.tools.search(
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
        
        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    # =============================
    # 3. EDIT - Редактирование
    # =============================
    
    async def edit(
        self,
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Универсальное редактирование. Всегда работает с массивом операций.
        
        Args:
            operations: Массив операций редактирования, каждая содержит:
                - file_path: Путь к файлу
                - edit_type: section/find_replace/insert
                - ... остальные параметры зависят от edit_type
                
        Returns:
            Результаты редактирования
        """
        results = []
        errors = []
        
        for op in operations:
            try:
                result = await self.tools.edit_file(
                    file_path=op["file_path"],
                    edit_type=op["edit_type"],
                    **{k: v for k, v in op.items() if k not in ["file_path", "edit_type"]}
                )
                results.append(result)
            except Exception as e:
                errors.append({
                    "operation": op,
                    "error": str(e)
                })
        
        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    # =============================
    # 4. TAGS - Управление тегами
    # =============================
    
    async def tags(
        self,
        operation: Literal["add", "remove", "get"],
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Универсальное управление тегами. Всегда работает с массивом файлов.
        
        Args:
            operation: Тип операции (add, remove, get)
            items: Массив элементов, каждый содержит:
                - file_path: Путь к файлу
                - tags: Массив тегов (для add/remove)
                
        Returns:
            Результаты операций
        """
        results = []
        errors = []
        
        for item in items:
            try:
                if operation == "add":
                    result = await self.tools.add_tags(item["file_path"], item["tags"])
                elif operation == "remove":
                    result = await self.tools.remove_tags(item["file_path"], item["tags"])
                elif operation == "get":
                    result = await self.tools.get_tags(item["file_path"])
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                
                results.append(result)
            except Exception as e:
                errors.append({
                    "item": item,
                    "error": str(e)
                })
        
        return {
            "operation": operation,
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    # =============================
    # 5. MAIN - Операции с main.md
    # =============================
    
    async def main(
        self,
        operation: Literal["append", "goal", "task", "plan"],
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Универсальные операции с main.md. Всегда работает с массивом операций.
        
        Args:
            operation: Тип операции (append, goal, task, plan)
            items: Массив элементов для обработки
            
        Returns:
            Результаты операций
        """
        results = []
        errors = []
        
        for item in items:
            try:
                if operation == "append":
                    result = await self.tools.append_to_main_memory(
                        content=item["content"],
                        section=item.get("section", "Recent Notes"),
                    )
                elif operation == "goal":
                    result = await self.tools.update_goals(
                        goal=item["goal"],
                        action=item.get("action", "add"),
                    )
                elif operation == "task":
                    result = await self.tools.update_tasks(
                        task=item["task"],
                        action=item.get("action", "add"),
                    )
                elif operation == "plan":
                    # Новая операция для планов
                    result = await self._update_plan(
                        plan=item["plan"],
                        action=item.get("action", "add"),
                    )
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                
                results.append(result)
            except Exception as e:
                errors.append({
                    "item": item,
                    "error": str(e)
                })
        
        return {
            "operation": operation,
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }
    
    async def _update_plan(self, plan: str, action: str = "add"):
        """Управление планами в секции Plans"""
        if action == "add":
            self.tools.index_manager.add_plan(plan)
            message = f"Plan added: {plan}"
        elif action == "complete":
            self.tools.index_manager.complete_plan(plan)
            message = f"Plan completed: {plan}"
        else:
            message = f"Action '{action}' not yet implemented for plans"
        
        if self.tools.sync_service:
            await self.tools.sync_service.sync_file("main.md", force=True)
        
        return {"message": message}

    # =============================
    # 6. MEMORY - Управление памятью
    # =============================
    
    async def memory(
        self,
        operation: Literal["initialize", "reset"],
    ) -> dict[str, Any]:
        """
        Управление памятью (инициализация и сброс).
        
        Args:
            operation: Тип операции (initialize, reset)
            
        Returns:
            Результат операции
        """
        if operation == "initialize":
            return await self.tools.initialize_memory()
        elif operation == "reset":
            return await self.tools.reset_memory()
        else:
            raise ValueError(f"Unknown operation: {operation}")

    # =============================
    # 7. EXTRACT - Извлечение секций
    # =============================
    
    async def extract(
        self,
        requests: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Извлечение секций из файлов. Всегда работает с массивом запросов.
        
        Args:
            requests: Массив запросов, каждый содержит:
                - file_path: Путь к файлу
                - section_header: Заголовок секции
                
        Returns:
            Результаты извлечения
        """
        results = []
        errors = []
        
        for req in requests:
            try:
                result = await self.tools.extract_section(
                    file_path=req["file_path"],
                    section_header=req["section_header"],
                )
                results.append(result)
            except Exception as e:
                errors.append({
                    "request": req,
                    "error": str(e)
                })
        
        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    # =============================
    # 8. LIST - Список файлов/секций
    # =============================
    
    async def list(
        self,
        requests: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Получение списков файлов или секций. Всегда работает с массивом запросов.
        
        Args:
            requests: Массив запросов, каждый содержит:
                - type: "files" или "sections"
                - category: Опциональная категория (для files)
                - file_path: Путь к файлу (для sections)
                
        Returns:
            Результаты списков
        """
        results = []
        errors = []
        
        for req in requests:
            try:
                if req["type"] == "files":
                    result = await self.tools.list_files(req.get("category"))
                elif req["type"] == "sections":
                    result = await self.tools.list_sections(req["file_path"])
                else:
                    raise ValueError(f"Unknown list type: {req.get('type')}")
                
                results.append(result)
            except Exception as e:
                errors.append({
                    "request": req,
                    "error": str(e)
                })
        
        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    # =============================
    # 9. HELP - Помощь и рекомендации
    # =============================
    
    async def help(
        self,
        topic: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Единый инструмент для получения помощи, рекомендаций, гайдов и примеров использования.
        
        Args:
            topic: Опциональная тема для конкретной помощи:
                - None или "all": Полный гайд
                - "files": Управление файлами
                - "search": Поиск
                - "edit": Редактирование
                - "tags": Теги
                - "main": Операции с main.md
                - "memory": Управление памятью
                - "examples": Примеры использования
                
        Returns:
            Полный гайд с рекомендациями и примерами
        """
        from src.mcp.prompts import get_memory_usage_prompt
        
        full_guide = get_memory_usage_prompt()
        
        # Добавляем примеры использования
        examples = """
## Примеры использования инструментов

### 1. Управление файлами (files)

```python
# Создание нескольких файлов
files(operation="create", items=[
    {"title": "Project 1", "category": "project", "content": "# Project 1"},
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
])
```

### 2. Поиск (search)

```python
# Множественный поиск
search(queries=[
    {"query": "machine learning", "search_mode": "hybrid", "limit": 10},
    {"query": "neural networks", "category_filter": "concept", "limit": 5},
])
```

### 3. Редактирование (edit)

```python
# Множественное редактирование
edit(operations=[
    {
        "file_path": "projects/project.md",
        "edit_type": "section",
        "section_header": "## Status",
        "new_content": "In progress",
        "mode": "replace"
    },
    {
        "file_path": "notes.md",
        "edit_type": "find_replace",
        "find": "old",
        "replace": "new"
    },
])
```

### 4. Управление тегами (tags)

```python
# Добавление тегов к нескольким файлам
tags(operation="add", items=[
    {"file_path": "projects/project1.md", "tags": ["important", "active"]},
    {"file_path": "projects/project2.md", "tags": ["important"]},
])
```

### 5. Операции с main.md (main)

```python
# Добавление целей и задач
main(operation="goal", items=[
    {"goal": "Complete project", "action": "add"},
    {"goal": "Test system", "action": "add"},
])

# Добавление планов
main(operation="plan", items=[
    {"plan": "Implement feature X", "action": "add"},
])
```

### 6. Управление памятью (memory)

```python
# Инициализация
memory(operation="initialize")

# Сброс
memory(operation="reset")
```

### 7. Извлечение секций (extract)

```python
# Извлечение секций из нескольких файлов
extract(requests=[
    {"file_path": "projects/project.md", "section_header": "## Status"},
    {"file_path": "concepts/concept.md", "section_header": "## Details"},
])
```

### 8. Списки (list)

```python
# Получение списков файлов и секций
list(requests=[
    {"type": "files", "category": "project"},
    {"type": "sections", "file_path": "projects/project.md"},
])
```
"""
        
        guide_by_topic = {
            "files": "Управление файлами: создание, чтение, обновление, удаление, перемещение, копирование, переименование, список - все операции работают с массивом элементов.",
            "search": "Поиск: гибридный (hybrid), векторный (vector), полнотекстовый (fulltext) - всегда работает с массивом запросов.",
            "edit": "Редактирование: секции, поиск/замена, вставка - всегда работает с массивом операций.",
            "tags": "Теги: добавление, удаление, получение - всегда работает с массивом файлов.",
            "main": "Операции с main.md: добавление заметок, управление целями, задачами и планами - всегда работает с массивом операций.",
            "memory": "Управление памятью: инициализация и сброс.",
            "extract": "Извлечение секций из файлов - всегда работает с массивом запросов.",
            "list": "Получение списков файлов или секций - всегда работает с массивом запросов.",
        }
        
        if topic and topic != "all" and topic in guide_by_topic:
            return {
                "topic": topic,
                "guide": guide_by_topic[topic],
                "full_guide": full_guide,
                "examples": examples,
            }
        
        return {
            "topic": "all",
            "full_guide": full_guide,
            "examples": examples,
            "topics": list(guide_by_topic.keys()),
        }
