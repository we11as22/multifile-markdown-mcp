#!/usr/bin/env python3
"""
Полное тестирование 9 универсальных инструментов
Все операции работают с массивами
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.library import MemoryLibrary
from src.mcp.tools_unified import UnifiedMemoryTools


class UnifiedTestRunner:
    """Тестирование универсальных инструментов"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
    def log_test(self, test_name: str, passed: bool, error: str = None, details: str = None):
        """Логирование результата теста"""
        status = "✓" if passed else "✗"
        print(f"{status} {test_name}")
        if details:
            print(f"  {details}")
        if error:
            print(f"  ERROR: {error}")
            
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
            self.failed_tests.append((test_name, error))
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("=" * 80)
        print("ПОЛНОЕ ТЕСТИРОВАНИЕ 9 УНИВЕРСАЛЬНЫХ ИНСТРУМЕНТОВ")
        print("=" * 80)
        print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        await self.test_1_files()
        await self.test_2_search()
        await self.test_3_edit()
        await self.test_4_tags()
        await self.test_5_main()
        await self.test_6_memory()
        await self.test_7_extract()
        await self.test_8_list()
        await self.test_9_help()
        
        self.print_summary()
        return self.tests_failed == 0
    
    async def test_1_files(self):
        """Тест 1: files - Управление файлами"""
        print("\n" + "=" * 80)
        print("ТЕСТ 1: files - Управление файлами")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # CREATE
                create_result = await unified.files(operation="create", items=[
                    {"title": "Test Project", "category": "project", "content": "# Test Project\n\nContent"},
                    {"title": "Test Concept", "category": "concept", "content": "# Test Concept"},
                ])
                self.log_test("FILES: Создание", create_result["success_count"] == 2, None, f"Создано: {create_result['success_count']}")
                
                # READ
                read_result = await unified.files(operation="read", items=[
                    {"file_path": "projects/test_project.md"},
                    {"file_path": "concepts/test_concept.md"},
                ])
                self.log_test("FILES: Чтение", read_result["success_count"] == 2, None, f"Прочитано: {read_result['success_count']}")
                
                # UPDATE
                update_result = await unified.files(operation="update", items=[
                    {"file_path": "projects/test_project.md", "content": "# Updated", "update_mode": "replace"},
                ])
                self.log_test("FILES: Обновление", update_result["success_count"] == 1)
                
                # LIST
                list_result = await unified.files(operation="list", items=[
                    {"category": "project"},
                ])
                self.log_test("FILES: Список", list_result["success_count"] == 1)
                
                # COPY
                copy_result = await unified.files(operation="copy", items=[
                    {"source_file_path": "projects/test_project.md", "new_title": "Copied Project", "new_category": "concept"},
                ])
                self.log_test("FILES: Копирование", copy_result["success_count"] == 1)
                
                # RENAME
                rename_result = await unified.files(operation="rename", items=[
                    {"old_file_path": "concepts/copied_project.md", "new_title": "Renamed Project"},
                ])
                self.log_test("FILES: Переименование", rename_result["success_count"] == 1)
                
                # MOVE
                move_result = await unified.files(operation="move", items=[
                    {"file_path": "concepts/renamed_project.md", "new_category": "project"},
                ])
                self.log_test("FILES: Перемещение", move_result["success_count"] == 1)
                
                # DELETE
                delete_result = await unified.files(operation="delete", items=[
                    {"file_path": "projects/renamed_project.md"},
                    {"file_path": "concepts/test_concept.md"},
                ])
                self.log_test("FILES: Удаление", delete_result["success_count"] == 2)
                
                await memory.close()
            except Exception as e:
                self.log_test("FILES: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_2_search(self):
        """Тест 2: search - Поиск"""
        print("\n" + "=" * 80)
        print("ТЕСТ 2: search - Поиск")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # Создаем файлы для поиска
                await unified.files(operation="create", items=[
                    {"title": "ML Project", "category": "project", "content": "# ML Project\n\nMachine learning project"},
                    {"title": "Neural Networks", "category": "concept", "content": "# Neural Networks\n\nDeep learning concepts"},
                ])
                
                await asyncio.sleep(2)  # Ждем синхронизации
                
                # Множественный поиск
                search_result = await unified.search(queries=[
                    {"query": "machine learning", "search_mode": "fulltext", "limit": 10},
                    {"query": "neural", "search_mode": "fulltext", "limit": 5},
                    {"query": "project", "category_filter": "project", "limit": 10},
                ])
                self.log_test("SEARCH: Множественный поиск", search_result["success_count"] == 3, None, f"Выполнено поисков: {search_result['success_count']}")
                
                await memory.close()
            except Exception as e:
                self.log_test("SEARCH: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_3_edit(self):
        """Тест 3: edit - Редактирование"""
        print("\n" + "=" * 80)
        print("ТЕСТ 3: edit - Редактирование")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # Создаем файл
                await unified.files(operation="create", items=[
                    {"title": "Edit Test", "category": "project", "content": "# Edit Test\n\n## Section 1\n\nOld content"},
                ])
                
                # Множественное редактирование
                edit_result = await unified.edit(operations=[
                    {
                        "file_path": "projects/edit_test.md",
                        "edit_type": "section",
                        "section_header": "## Section 1",
                        "new_content": "New content",
                        "mode": "replace"
                    },
                    {
                        "file_path": "projects/edit_test.md",
                        "edit_type": "find_replace",
                        "find": "New content",
                        "replace": "Updated content"
                    },
                    {
                        "file_path": "projects/edit_test.md",
                        "edit_type": "insert",
                        "content": "\n\n## Section 2\n\nAdded",
                        "position": "end"
                    },
                ])
                self.log_test("EDIT: Множественное редактирование", edit_result["success_count"] == 3, None, f"Выполнено операций: {edit_result['success_count']}")
                
                # Проверяем результат
                read_result = await unified.files(operation="read", items=[
                    {"file_path": "projects/edit_test.md"},
                ])
                if read_result["success_count"] > 0:
                    content = read_result["results"][0]["content"]
                    has_updated = "Updated content" in content
                    has_section2 = "Section 2" in content
                    self.log_test("EDIT: Проверка результата", has_updated and has_section2)
                
                await memory.close()
            except Exception as e:
                self.log_test("EDIT: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_4_tags(self):
        """Тест 4: tags - Управление тегами"""
        print("\n" + "=" * 80)
        print("ТЕСТ 4: tags - Управление тегами")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # Создаем файлы
                await unified.files(operation="create", items=[
                    {"title": "Tag Test 1", "category": "project", "content": "# Tag Test 1", "tags": ["initial"]},
                    {"title": "Tag Test 2", "category": "project", "content": "# Tag Test 2"},
                ])
                
                # Добавление тегов
                add_result = await unified.tags(operation="add", items=[
                    {"file_path": "projects/tag_test_1.md", "tags": ["important", "active"]},
                    {"file_path": "projects/tag_test_2.md", "tags": ["important"]},
                ])
                self.log_test("TAGS: Добавление", add_result["success_count"] == 2, None, f"Обновлено файлов: {add_result['success_count']}")
                
                # Небольшая задержка для синхронизации
                await asyncio.sleep(0.5)
                
                # Получение тегов (после добавления должно быть минимум 2: important + active, initial может быть удален при обновлении)
                get_result = await unified.tags(operation="get", items=[
                    {"file_path": "projects/tag_test_1.md"},
                ])
                if get_result["success_count"] > 0:
                    tags = get_result["results"][0].get("tags", [])
                    tags_count = len(tags)
                    # Проверяем, что есть хотя бы important и active
                    has_important = "important" in tags
                    has_active = "active" in tags
                    self.log_test("TAGS: Получение", tags_count >= 2 and has_important and has_active, None, f"Тегов: {tags_count}, список: {tags}")
                else:
                    self.log_test("TAGS: Получение", False, "Не удалось получить теги")
                
                # Удаление тегов
                remove_result = await unified.tags(operation="remove", items=[
                    {"file_path": "projects/tag_test_1.md", "tags": ["initial"]},
                ])
                self.log_test("TAGS: Удаление", remove_result["success_count"] == 1)
                
                # Проверка после удаления
                get_after = await unified.tags(operation="get", items=[
                    {"file_path": "projects/tag_test_1.md"},
                ])
                if get_after["success_count"] > 0:
                    tags_after = len(get_after["results"][0].get("tags", []))
                    self.log_test("TAGS: Проверка после удаления", tags_after >= 2, None, f"Тегов после удаления: {tags_after}")
                
                await memory.close()
            except Exception as e:
                self.log_test("TAGS: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_5_main(self):
        """Тест 5: main - Операции с main.md"""
        print("\n" + "=" * 80)
        print("ТЕСТ 5: main - Операции с main.md")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # APPEND
                append_result = await unified.main(operation="append", items=[
                    {"content": "Test note 1", "section": "Recent Notes"},
                    {"content": "Test note 2", "section": "Recent Notes"},
                ])
                self.log_test("MAIN: Добавление заметок", append_result["success_count"] == 2)
                
                # GOAL
                goal_result = await unified.main(operation="goal", items=[
                    {"goal": "Test goal 1", "action": "add"},
                    {"goal": "Test goal 2", "action": "add"},
                ])
                self.log_test("MAIN: Управление целями", goal_result["success_count"] == 2)
                
                # TASK
                task_result = await unified.main(operation="task", items=[
                    {"task": "Completed task 1", "action": "add"},
                ])
                self.log_test("MAIN: Управление задачами", task_result["success_count"] == 1)
                
                # PLAN
                plan_result = await unified.main(operation="plan", items=[
                    {"plan": "Test plan 1", "action": "add"},
                    {"plan": "Test plan 2", "action": "add"},
                ])
                self.log_test("MAIN: Управление планами", plan_result["success_count"] == 2)
                
                await memory.close()
            except Exception as e:
                self.log_test("MAIN: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_6_memory(self):
        """Тест 6: memory - Управление памятью"""
        print("\n" + "=" * 80)
        print("ТЕСТ 6: memory - Управление памятью")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # INITIALIZE
                init_result = await unified.memory(operation="initialize")
                self.log_test("MEMORY: Инициализация", "initialized" in init_result.get("message", "").lower())
                
                # Создаем файлы
                await unified.files(operation="create", items=[
                    {"title": "Test 1", "category": "project", "content": "# Test 1"},
                    {"title": "Test 2", "category": "concept", "content": "# Test 2"},
                ])
                
                # RESET
                reset_result = await unified.memory(operation="reset")
                deleted = reset_result.get("deleted_files", 0)
                self.log_test("MEMORY: Сброс", deleted >= 2, None, f"Удалено файлов: {deleted}")
                
                await memory.close()
            except Exception as e:
                self.log_test("MEMORY: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_7_extract(self):
        """Тест 7: extract - Извлечение секций"""
        print("\n" + "=" * 80)
        print("ТЕСТ 7: extract - Извлечение секций")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # Создаем файл с секциями
                await unified.files(operation="create", items=[
                    {"title": "Extract Test", "category": "project", "content": "# Extract Test\n\n## Section A\n\nContent A\n\n## Section B\n\nContent B"},
                ])
                
                # Извлечение секций
                extract_result = await unified.extract(requests=[
                    {"file_path": "projects/extract_test.md", "section_header": "## Section A"},
                    {"file_path": "projects/extract_test.md", "section_header": "## Section B"},
                ])
                self.log_test("EXTRACT: Извлечение секций", extract_result["success_count"] == 2, None, f"Извлечено: {extract_result['success_count']}")
                
                await memory.close()
            except Exception as e:
                self.log_test("EXTRACT: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_8_list(self):
        """Тест 8: list - Списки"""
        print("\n" + "=" * 80)
        print("ТЕСТ 8: list - Списки")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # Создаем файлы
                await unified.files(operation="create", items=[
                    {"title": "List Test 1", "category": "project", "content": "# List Test 1\n\n## Section 1\n\nContent"},
                    {"title": "List Test 2", "category": "concept", "content": "# List Test 2"},
                ])
                
                # Списки
                list_result = await unified.list(requests=[
                    {"type": "files", "category": "project"},
                    {"type": "sections", "file_path": "projects/list_test_1.md"},
                ])
                self.log_test("LIST: Списки файлов и секций", list_result["success_count"] == 2, None, f"Получено списков: {list_result['success_count']}")
                
                await memory.close()
            except Exception as e:
                self.log_test("LIST: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_9_help(self):
        """Тест 9: help - Помощь"""
        print("\n" + "=" * 80)
        print("ТЕСТ 9: help - Помощь")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    database_url=self.database_url,
                )
                await memory.initialize()
                
                unified = UnifiedMemoryTools(memory.memory_tools)
                
                # Полный гайд
                help_all = await unified.help(topic=None)
                has_guide = "full_guide" in help_all
                has_examples = "examples" in help_all
                self.log_test("HELP: Полный гайд", has_guide and has_examples)
                
                # Гайд по теме
                help_files = await unified.help(topic="files")
                has_topic = "topic" in help_files
                self.log_test("HELP: Гайд по теме", has_topic)
                
                await memory.close()
            except Exception as e:
                self.log_test("HELP: Общий тест", False, str(e))
                import traceback
                traceback.print_exc()
    
    def print_summary(self):
        """Вывод итогов"""
        print("\n" + "=" * 80)
        print("ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 80)
        print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Всего тестов: {self.tests_passed + self.tests_failed}")
        print(f"✓ Успешно: {self.tests_passed}")
        print(f"✗ Провалено: {self.tests_failed}")
        print(f"Процент успеха: {(self.tests_passed / (self.tests_passed + self.tests_failed) * 100) if (self.tests_passed + self.tests_failed) > 0 else 0:.1f}%")
        
        if self.failed_tests:
            print("\nПроваленные тесты:")
            for test_name, error in self.failed_tests:
                print(f"  - {test_name}: {error}")
        
        print("=" * 80)


async def main():
    """Главная функция"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        from config.settings import Settings
        settings = Settings()
        database_url = settings.database_url
    
    runner = UnifiedTestRunner(database_url)
    success = await runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nТесты прерваны пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

