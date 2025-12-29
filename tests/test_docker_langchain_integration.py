#!/usr/bin/env python3
"""
Тестирование интеграции LangChain агента с режимом без БД
Имитирует работу в Docker (удаленный сервер)
Использует OpenRouter для LLM
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


# OpenRouter API ключ
OPENROUTER_API_KEY = "sk-or-v1-........"


async def test_langchain_agent_file_only_mode():
    """Тестирование LangChain агента с режимом без БД (имитация Docker)"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ LANGCHAIN АГЕНТА С РЕЖИМОМ БЕЗ БД")
    print("Имитация работы в Docker (удаленный сервер)")
    print("=" * 80)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.tools import tool
        from langchain.agents import create_agent
    except ImportError as e:
        print(f"✗ Не установлены зависимости: {e}")
        print("Установите: pip install langchain langchain-openai langchain-core")
        import traceback
        traceback.print_exc()
        return False
    
    # Используем временную директорию (имитация Docker volume)
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Использование временной директории (имитация Docker): {tmpdir}")
        
        # Инициализируем библиотеку в режиме без БД
        print("\nИнициализация библиотеки в режиме без БД...")
        from src.library import MemoryLibrary
        
        memory = MemoryLibrary(
            memory_files_path=tmpdir,
            use_database=False,
        )
        await memory.initialize()
        await memory.initialize_memory()
        print("✓ Библиотека инициализирована (режим без БД)")
        
        # Создаем LangChain инструменты из библиотеки
        print("\nСоздание LangChain инструментов из библиотеки...")
        
        @tool
        async def create_memory_file(title: str, category: str, content: str, tags: list = None) -> str:
            """Создать файл памяти. Всегда работает с одним файлом, но принимает параметры как для массива."""
            result = await memory.create_file(title, category, content, tags or [])
            return f"Файл создан: {result['file_path']}"
        
        @tool
        async def list_memory_files(category: str = None) -> str:
            """Получить список файлов памяти с деревом и описаниями. Возвращает структурированную информацию."""
            result = await memory.list_files(category)
            tree_info = ""
            if 'tree' in result:
                for cat, files in result['tree'].items():
                    tree_info += f"\n{cat}: {len(files)} файлов"
                    for f in files[:3]:  # Первые 3 файла
                        tree_info += f"\n  - {f.get('title')}: {f.get('description', '')[:50]}"
            return f"Всего файлов: {result['total']}.{tree_info}"
        
        @tool
        async def read_memory_file(file_path: str) -> str:
            """Прочитать содержимое файла памяти."""
            result = await memory.get_file(file_path)
            return result['content']
        
        @tool
        async def update_memory_file(file_path: str, content: str, update_mode: str = "replace") -> str:
            """Обновить файл памяти. update_mode: replace, append, prepend."""
            result = await memory.update_file(file_path, content, update_mode)
            return f"Файл обновлен: {result.get('message', 'success')}"
        
        @tool
        async def add_tags_to_file(file_path: str, tags: list) -> str:
            """Добавить теги к файлу памяти."""
            result = await memory.add_tags(file_path, tags)
            return f"Теги добавлены: {result['tags']}"
        
        @tool
        async def get_file_tags(file_path: str) -> str:
            """Получить все теги файла."""
            result = await memory.get_tags(file_path)
            return f"Теги файла: {result['tags']}"
        
        @tool
        async def edit_file_section(file_path: str, section_header: str, new_content: str, mode: str = "replace") -> str:
            """Отредактировать секцию в файле. mode: replace, append, prepend."""
            result = await memory.edit_file(
                file_path,
                "section",
                section_header=section_header,
                new_content=new_content,
                mode=mode
            )
            return f"Секция отредактирована: {result.get('message', 'success')}"
        
        @tool
        async def append_to_main_memory(content: str, section: str = "Recent Notes") -> str:
            """Добавить заметку в main.md в указанную секцию."""
            result = await memory.append_to_main(content, section)
            return f"Заметка добавлена: {result.get('message', 'success')}"
        
        @tool
        async def add_goal_to_main(goal: str) -> str:
            """Добавить цель в main.md."""
            result = await memory.add_goal(goal)
            return f"Цель добавлена: {result.get('message', 'success')}"
        
        tools = [
            create_memory_file,
            list_memory_files,
            read_memory_file,
            update_memory_file,
            add_tags_to_file,
            get_file_tags,
            edit_file_section,
            append_to_main_memory,
            add_goal_to_main,
        ]
        print(f"✓ Создано {len(tools)} инструментов")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:60]}...")
        
        # Создаем LLM с OpenRouter
        print("\nИнициализация LLM (OpenRouter)...")
        llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/we11as22/multifile-markdown-mcp",
                "X-Title": "Agent Memory MCP"
            }
        )
        print("✓ LLM инициализирован (OpenRouter: openai/gpt-4o-mini)")
        
        # Создаем агента (create_agent автоматически создает промпт)
        print("\nСоздание агента...")
        # Используем create_agent - универсальный способ создания агента
        # Он автоматически создает промпт с описанием инструментов
        agent = create_agent(llm, tools)
        print("✓ Агент создан")
        
        # Задачи для агента
        tasks = [
            "Создай файл проекта 'Docker LangChain Integration' с описанием тестирования интеграции LangChain агента с системой памяти в Docker режиме",
            "Создай файл концепции 'File-Only Mode' с описанием режима работы без БД",
            "Получи список всех файлов и покажи структуру дерева с описаниями",
            "Добавь теги 'docker', 'langchain', 'integration', 'file-only' к файлу проекта 'Docker LangChain Integration'",
            "Прочитай содержимое файла проекта 'Docker LangChain Integration'",
            "Отредактируй файл проекта, добавив секцию '## Status' с текстом 'In testing'",
            "Добавь заметку 'Тестирование LangChain интеграции' в main.md в секцию Recent Notes",
            "Добавь цель 'Завершить тестирование интеграции' в main.md",
            "Получи теги файла проекта 'Docker LangChain Integration'",
        ]
        
        print("\n" + "=" * 80)
        print("ЗАПУСК АГЕНТА С ЗАДАЧАМИ")
        print("=" * 80)
        
        results = []
        chat_history = []
        
        for i, task in enumerate(tasks, 1):
            print(f"\n--- Задача {i}/{len(tasks)}: {task} ---")
            try:
                response = await agent.ainvoke({"messages": [("user", task)]})
                output = str(response.get("messages", response))
                results.append({"task": task, "success": True, "result": output})
                print(f"✓ Задача {i} выполнена")
                if output:
                    print(f"Ответ: {output[:200]}...")
            except Exception as e:
                results.append({"task": task, "success": False, "error": str(e)})
                print(f"✗ Задача {i} провалена: {e}")
                import traceback
                traceback.print_exc()
        
        # Проверяем результаты
        print("\n" + "=" * 80)
        print("ПРОВЕРКА РЕЗУЛЬТАТОВ")
        print("=" * 80)
        
        # Проверяем файлы
        files_list = await memory.list_files()
        print(f"Всего файлов в памяти: {files_list['total']}")
        if 'tree' in files_list:
            print(f"Дерево категорий: {list(files_list['tree'].keys())}")
            for category, files in files_list['tree'].items():
                print(f"\n{category}: {len(files)} файлов")
                for f in files:
                    print(f"  - {f.get('title')}: {f.get('description', '')[:60]}")
                    print(f"    Теги: {f.get('tags', [])}")
                    print(f"    Путь: {f.get('file_path')}")
        
        # Проверяем main.md
        main_content = await memory.get_file("main.md")
        has_notes = "Тестирование LangChain интеграции" in main_content['content']
        has_goals = "Завершить тестирование интеграции" in main_content['content']
        print(f"\nmain.md содержит заметку: {has_notes}")
        print(f"main.md содержит цель: {has_goals}")
        
        await memory.close()
        
        # Итоги
        print("\n" + "=" * 80)
        print("ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 80)
        print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        print(f"\nВсего задач: {len(results)}")
        print(f"✓ Успешно: {successful}")
        print(f"✗ Провалено: {failed}")
        print(f"Процент успеха: {(successful / len(results) * 100) if results else 0:.1f}%")
        
        if failed > 0:
            print("\nПроваленные задачи:")
            for r in results:
                if not r["success"]:
                    print(f"  - {r['task']}: {r.get('error', 'Unknown error')}")
        
        # Дополнительные проверки
        print("\n" + "=" * 80)
        print("ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ")
        print("=" * 80)
        print(f"✓ Файлов создано: {files_list['total']}")
        print(f"✓ Дерево файлов работает: {'tree' in files_list}")
        print(f"✓ Описания в дереве: {any('description' in f for files in files_list.get('tree', {}).values() for f in files)}")
        print(f"✓ main.md обновлен: {has_notes and has_goals}")
        
        print("=" * 80)
        
        return failed == 0


async def main():
    """Главная функция"""
    success = await test_langchain_agent_file_only_mode()
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
