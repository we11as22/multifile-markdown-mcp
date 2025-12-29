#!/usr/bin/env python3
"""
Тестирование режима работы без БД (file-only mode)
Все операции работают через файловую систему и JSON index
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


class FileOnlyTestRunner:
    """Тестирование режима без БД"""
    
    def __init__(self):
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
        print("ТЕСТИРОВАНИЕ РЕЖИМА БЕЗ БД (FILE-ONLY MODE)")
        print("=" * 80)
        print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        await self.test_1_initialization()
        await self.test_2_create_files()
        await self.test_3_list_files_with_tree()
        await self.test_4_read_files()
        await self.test_5_update_files()
        await self.test_6_edit_files()
        await self.test_7_tags_management()
        await self.test_8_main_operations()
        await self.test_9_file_operations()
        await self.test_10_search_not_available()
        
        self.print_summary()
        return self.tests_failed == 0
    
    async def test_1_initialization(self):
        """Тест 1: Инициализация без БД"""
        print("\n" + "=" * 80)
        print("ТЕСТ 1: Инициализация без БД")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Проверка базовых файлов
                main_exists = (Path(tmpdir) / "main.md").exists()
                index_exists = (Path(tmpdir) / "files_index.json").exists()
                
                self.log_test("Инициализация без БД", True)
                self.log_test("Создание main.md", main_exists, None if main_exists else "Файл не создан")
                self.log_test("Создание files_index.json", index_exists, None if index_exists else "Файл не создан")
                self.log_test("БД не подключена", memory.db_manager is None)
                
                await memory.close()
            except Exception as e:
                self.log_test("Инициализация без БД", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_2_create_files(self):
        """Тест 2: Создание файлов"""
        print("\n" + "=" * 80)
        print("ТЕСТ 2: Создание файлов")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Создаем файлы
                result1 = await memory.create_file(
                    "Test Project",
                    "project",
                    "# Test Project\n\nОписание тестового проекта",
                    tags=["test", "important"]
                )
                result2 = await memory.create_file(
                    "Test Concept",
                    "concept",
                    "# Test Concept\n\nОписание тестовой концепции"
                )
                
                self.log_test("Создание файла проекта", "file_path" in result1)
                self.log_test("Создание файла концепции", "file_path" in result2)
                
                # Проверяем, что файлы созданы
                file1_exists = (Path(tmpdir) / result1["file_path"]).exists()
                file2_exists = (Path(tmpdir) / result2["file_path"]).exists()
                
                self.log_test("Файл проекта существует", file1_exists)
                self.log_test("Файл концепции существует", file2_exists)
                
                await memory.close()
            except Exception as e:
                self.log_test("Создание файлов", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_3_list_files_with_tree(self):
        """Тест 3: Список файлов с деревом"""
        print("\n" + "=" * 80)
        print("ТЕСТ 3: Список файлов с деревом и описаниями")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Создаем файлы
                await memory.create_file("Project 1", "project", "# Project 1\n\nОписание проекта 1", tags=["active"])
                await memory.create_file("Project 2", "project", "# Project 2\n\nОписание проекта 2")
                await memory.create_file("Concept 1", "concept", "# Concept 1\n\nОписание концепции 1")
                
                # Получаем список файлов
                all_files = await memory.list_files()
                
                self.log_test("Получение списка файлов", "files" in all_files)
                self.log_test("Наличие дерева", "tree" in all_files, None, f"Всего файлов: {all_files.get('total', 0)}")
                
                # Проверяем структуру дерева
                tree = all_files.get("tree", {})
                has_projects = "projects" in tree
                has_concepts = "concepts" in tree
                
                self.log_test("Дерево содержит projects", has_projects, None, f"Файлов в projects: {len(tree.get('projects', []))}")
                self.log_test("Дерево содержит concepts", has_concepts, None, f"Файлов в concepts: {len(tree.get('concepts', []))}")
                
                # Проверяем, что у файлов есть описания
                if tree.get("projects"):
                    first_project = tree["projects"][0]
                    has_description = "description" in first_project and first_project["description"]
                    self.log_test("Файлы имеют описания", has_description, None, f"Описание: {first_project.get('description', 'нет')}")
                
                # Фильтр по категории
                project_files = await memory.list_files(category="project")
                self.log_test("Фильтр по категории", project_files.get("total", 0) >= 2, None, f"Найдено проектов: {project_files.get('total', 0)}")
                
                await memory.close()
            except Exception as e:
                self.log_test("Список файлов с деревом", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_4_read_files(self):
        """Тест 4: Чтение файлов"""
        print("\n" + "=" * 80)
        print("ТЕСТ 4: Чтение файлов")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Создаем файл
                result = await memory.create_file("Read Test", "project", "# Read Test\n\nContent for reading")
                
                # Читаем файл
                file_content = await memory.get_file(result["file_path"])
                
                self.log_test("Чтение файла", "content" in file_content)
                self.log_test("Содержимое корректно", "Read Test" in file_content["content"])
                
                await memory.close()
            except Exception as e:
                self.log_test("Чтение файлов", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_5_update_files(self):
        """Тест 5: Обновление файлов"""
        print("\n" + "=" * 80)
        print("ТЕСТ 5: Обновление файлов")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Создаем файл
                result = await memory.create_file("Update Test", "project", "# Update Test\n\nOld content")
                
                # Обновляем файл
                await memory.update_file(result["file_path"], "# Update Test\n\nNew content", "replace")
                
                # Проверяем обновление
                file_content = await memory.get_file(result["file_path"])
                has_new = "New content" in file_content["content"]
                has_old = "Old content" in file_content["content"]
                
                self.log_test("Обновление файла", has_new and not has_old)
                
                # Append mode
                await memory.update_file(result["file_path"], "\n\nAppended content", "append")
                file_content = await memory.get_file(result["file_path"])
                has_appended = "Appended content" in file_content["content"]
                
                self.log_test("Добавление контента", has_appended)
                
                await memory.close()
            except Exception as e:
                self.log_test("Обновление файлов", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_6_edit_files(self):
        """Тест 6: Редактирование файлов"""
        print("\n" + "=" * 80)
        print("ТЕСТ 6: Редактирование файлов")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Создаем файл с секциями
                result = await memory.create_file(
                    "Edit Test",
                    "project",
                    "# Edit Test\n\n## Section 1\n\nOld content"
                )
                
                # Редактируем секцию
                await memory.edit_file(
                    result["file_path"],
                    "section",
                    section_header="## Section 1",
                    new_content="New content",
                    mode="replace"
                )
                
                # Проверяем результат
                file_content = await memory.get_file(result["file_path"])
                has_new = "New content" in file_content["content"]
                
                self.log_test("Редактирование секции", has_new)
                
                # Insert
                await memory.edit_file(
                    result["file_path"],
                    "insert",
                    content="\n\n## Section 2\n\nInserted",
                    position="end"
                )
                
                file_content = await memory.get_file(result["file_path"])
                has_section2 = "Section 2" in file_content["content"]
                
                self.log_test("Вставка контента", has_section2)
                
                await memory.close()
            except Exception as e:
                self.log_test("Редактирование файлов", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_7_tags_management(self):
        """Тест 7: Управление тегами"""
        print("\n" + "=" * 80)
        print("ТЕСТ 7: Управление тегами")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Создаем файл с тегами
                result = await memory.create_file(
                    "Tags Test",
                    "project",
                    "# Tags Test",
                    tags=["initial"]
                )
                
                # Добавляем теги
                add_result = await memory.add_tags(result["file_path"], ["important", "active"])
                tags_after_add = add_result.get("tags", [])
                has_important = "important" in tags_after_add
                has_active = "active" in tags_after_add
                
                self.log_test("Добавление тегов", has_important and has_active, None, f"Тегов: {len(tags_after_add)}")
                
                # Получаем теги
                get_result = await memory.get_tags(result["file_path"])
                tags_count = get_result.get("total", 0)
                
                self.log_test("Получение тегов", tags_count >= 3, None, f"Тегов: {tags_count}")
                
                # Удаляем теги
                remove_result = await memory.remove_tags(result["file_path"], ["initial"])
                tags_after_remove = remove_result.get("tags", [])
                no_initial = "initial" not in tags_after_remove
                
                self.log_test("Удаление тегов", no_initial, None, f"Тегов после удаления: {len(tags_after_remove)}")
                
                await memory.close()
            except Exception as e:
                self.log_test("Управление тегами", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_8_main_operations(self):
        """Тест 8: Операции с main.md"""
        print("\n" + "=" * 80)
        print("ТЕСТ 8: Операции с main.md")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Добавляем заметку
                await memory.append_to_main("Test note", "Recent Notes")
                
                # Добавляем цель
                await memory.add_goal("Test goal")
                
                # Добавляем задачу
                await memory.add_task("Test task")
                
                # Проверяем main.md
                main_content = await memory.get_file("main.md")
                has_note = "Test note" in main_content["content"]
                has_goal = "Test goal" in main_content["content"]
                has_task = "Test task" in main_content["content"]
                
                self.log_test("Добавление заметки", has_note)
                self.log_test("Добавление цели", has_goal)
                self.log_test("Добавление задачи", has_task)
                
                await memory.close()
            except Exception as e:
                self.log_test("Операции с main.md", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_9_file_operations(self):
        """Тест 9: Операции с файлами (move, copy, rename)"""
        print("\n" + "=" * 80)
        print("ТЕСТ 9: Операции с файлами")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Создаем файл
                result = await memory.create_file("File Ops Test", "project", "# File Ops Test")
                
                # Переименовываем
                rename_result = await memory.rename_file(result["file_path"], "Renamed File")
                self.log_test("Переименование файла", "new_file_path" in rename_result)
                
                # Копируем
                copy_result = await memory.copy_file(rename_result["new_file_path"], "Copied File")
                self.log_test("Копирование файла", "new_file_path" in copy_result)
                
                # Перемещаем
                move_result = await memory.move_file(copy_result["new_file_path"], "concept")
                self.log_test("Перемещение файла", "new_file_path" in move_result)
                self.log_test("Проверка категории", "concepts" in move_result["new_file_path"])
                
                await memory.close()
            except Exception as e:
                self.log_test("Операции с файлами", False, str(e))
                import traceback
                traceback.print_exc()
    
    async def test_10_search_not_available(self):
        """Тест 10: Поиск недоступен без БД"""
        print("\n" + "=" * 80)
        print("ТЕСТ 10: Поиск недоступен без БД")
        print("=" * 80)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                memory = MemoryLibrary(
                    memory_files_path=tmpdir,
                    use_database=False,
                )
                await memory.initialize()
                await memory.initialize_memory()
                
                # Попытка поиска должна вызвать ошибку
                try:
                    await memory.search("test")
                    self.log_test("Поиск недоступен", False, "Поиск не должен работать без БД")
                except RuntimeError as e:
                    if "not available" in str(e) or "database" in str(e).lower():
                        self.log_test("Поиск недоступен", True, None, "Ошибка корректна")
                    else:
                        self.log_test("Поиск недоступен", False, f"Неожиданная ошибка: {e}")
                
                await memory.close()
            except Exception as e:
                self.log_test("Проверка поиска", False, str(e))
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
    runner = FileOnlyTestRunner()
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

