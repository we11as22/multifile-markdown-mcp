#!/usr/bin/env python3
"""
Тестирование сервиса как инструментов для LLM агента через MCP протокол
Использует инструменты напрямую из FastMCP и создает агента одной строкой
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_agent_with_mcp_tools():
    """Тестирование агента с MCP инструментами"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ LLM АГЕНТА С MCP ИНСТРУМЕНТАМИ")
    print("=" * 80)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # OpenAI API ключ
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-proj-.....")
    
    if not openai_api_key:
        print("✗ OPENAI_API_KEY не установлен")
        return False
    
    try:
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI
        from langchain_core.tools import StructuredTool
    except ImportError as e:
        print(f"✗ Не установлены зависимости: {e}")
        print("Установите: pip install langchain langchain-openai")
        return False
    
    # Инициализируем MCP сервер
    print("Инициализация MCP сервера...")
    from src.main import initialize_server, shutdown_server, mcp
    await initialize_server()
    print("✓ MCP сервер инициализирован")
    
    # Получаем инструменты напрямую из MCP и преобразуем в LangChain tools
    print("\nПолучение MCP инструментов...")
    mcp_tools_dict = await mcp.get_tools()
    print(f"✓ Получено {len(mcp_tools_dict)} MCP инструментов из сервера")
    
    # Преобразуем MCP tools в LangChain tools
    tools = []
    for tool_name, mcp_tool in mcp_tools_dict.items():
        # Получаем функцию из FunctionTool
        tool_func = mcp_tool.func if hasattr(mcp_tool, 'func') else None
        if tool_func:
            tool = StructuredTool.from_function(
                func=tool_func,
                name=tool_name,
                description=mcp_tool.description or f"MCP tool: {tool_name}",
            )
            tools.append(tool)
            print(f"  - {tool_name}")
    
    # Создаем LLM
    print("\nИнициализация LLM...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=openai_api_key)
    print("✓ LLM инициализирован (gpt-4o-mini)")
    
    # СОЗДАЕМ АГЕНТА С MCP ИНСТРУМЕНТАМИ ОДНОЙ СТРОЧКОЙ
    print("\nСоздание агента с MCP инструментами...")
    agent = create_agent(llm, tools)
    print("✓ Агент создан с MCP инструментами")
    
    # Задачи для агента
    tasks = [
        "Получи помощь по использованию системы памяти используя инструмент help",
        "Создай 2 файла памяти используя инструмент files: один проект 'Test Project' с описанием тестового проекта, и одну концепцию 'Test Concept' с описанием тестовой концепции",
        "Выполни поиск по запросу 'test' используя инструмент search",
        "Прочитай созданные файлы используя инструмент files с операцией read",
        "Отредактируй файл проекта, добавив секцию '## Progress' с текстом 'In progress' используя инструмент edit",
        "Добавь теги 'important' и 'test' к файлу проекта используя инструмент tags",
        "Добавь заметку в main.md используя инструмент main с операцией append",
        "Добавь цель в main.md используя инструмент main с операцией goal",
        "Добавь план в main.md используя инструмент main с операцией plan",
        "Извлеки секцию из файла проекта используя инструмент extract",
        "Получи список всех файлов используя инструмент list",
    ]
    
    print("\n" + "=" * 80)
    print("ЗАПУСК АГЕНТА С MCP ИНСТРУМЕНТАМИ")
    print("=" * 80)
    
    results = []
    for i, task in enumerate(tasks, 1):
        print(f"\n--- Задача {i}/{len(tasks)}: {task} ---")
        
        try:
            response = await agent.ainvoke({"messages": task})
            results.append({
                "task": task,
                "success": True,
                "result": str(response.get("messages", response))
            })
            print(f"✓ Задача {i} выполнена")
        except Exception as e:
            results.append({"task": task, "success": False, "error": str(e)})
            print(f"✗ Задача {i} провалена: {e}")
            import traceback
            traceback.print_exc()
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    print(f"Всего задач: {len(results)}")
    print(f"✓ Успешно: {successful}")
    print(f"✗ Провалено: {failed}")
    print(f"Процент успеха: {(successful / len(results) * 100) if results else 0:.1f}%")
    
    if failed > 0:
        print("\nПроваленные задачи:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['task']}: {r.get('error', 'Unknown error')}")
    
    # Завершаем работу
    await shutdown_server()
    
    return failed == 0


async def main():
    """Главная функция"""
    success = await test_agent_with_mcp_tools()
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
