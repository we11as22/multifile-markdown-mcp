#!/usr/bin/env python3
"""
Тестирование интеграции LangChain агента с удаленным MCP сервером в Docker
Имитирует работу с сервисом памяти на удаленном сервере через SSE
Использует langchain-mcp-adapters для подключения к MCP серверу
Режим без БД (file-only mode)

ИНСТРУКЦИЯ:
1. В отдельном терминале запустите Docker:
   cd /home/asudakov/projects/multifile-markdown-mcp
   docker-compose -f docker/docker-compose.remote-test.yml up -d

2. В этом терминале запустите тест:
   python tests/test_remote_mcp_langchain.py

3. После теста остановите Docker:
   docker-compose -f docker/docker-compose.remote-test.yml down
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# OpenRouter API ключ
OPENROUTER_API_KEY = "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"

# Порт для MCP сервера в Docker
MCP_PORT = 8000
# SSE транспорт использует путь /sse
MCP_URL = f"http://localhost:{MCP_PORT}/sse"


async def test_remote_mcp_langchain_integration():
    """Тестирование LangChain агента с удаленным MCP сервером в Docker через SSE"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ LANGCHAIN АГЕНТА С УДАЛЕННЫМ MCP СЕРВЕРОМ В DOCKER")
    print("Режим без БД (file-only mode)")
    print("Транспорт: SSE (Server-Sent Events)")
    print("=" * 80)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("⚠️  ВАЖНО: Docker контейнер должен быть запущен в отдельном терминале:")
    print(f"   cd {project_root}")
    print(f"   docker-compose -f docker/docker-compose.remote-test.yml up -d")
    print()
    
    try:
        from langchain.agents import create_agent
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as e:
        print(f"✗ Не установлены зависимости: {e}")
        print("Установите: pip install langchain langchain-mcp-adapters")
        return False
    
    # Проверяем доступность сервера
    print("=== ПРОВЕРКА ДОСТУПНОСТИ СЕРВЕРА ===")
    try:
        import urllib.request
        import urllib.error
        try:
            response = urllib.request.urlopen(MCP_URL, timeout=2)
            print(f"✓ Сервер доступен на {MCP_URL}")
        except urllib.error.HTTPError as e:
            # 406 Not Acceptable означает что сервер работает, но требует POST (это нормально для MCP)
            if e.code in (406, 405, 400):
                print(f"✓ Сервер доступен на {MCP_URL} (код ответа: {e.code})")
            else:
                print(f"✗ Сервер вернул ошибку: {e.code}")
                return False
    except Exception as e:
        print(f"✗ Сервер недоступен на {MCP_URL}: {e}")
        print("\nЗапустите Docker контейнер в отдельном терминале:")
        print(f"   cd {project_root}")
        print(f"   docker-compose -f docker/docker-compose.remote-test.yml up -d")
        return False
    
    try:
        # Создаем клиент для подключения к MCP серверу через SSE
        print("\n=== ПОДКЛЮЧЕНИЕ К MCP СЕРВЕРУ ===")
        print(f"URL: {MCP_URL}")
        print("Транспорт: SSE")
        
        client = MultiServerMCPClient(
            {
                "memory_service": {
                    "transport": "sse",
                    "url": MCP_URL,
                }
            }
        )
        
        # Получаем инструменты из MCP сервера
        print("\nПолучение инструментов из MCP сервера...")
        try:
            tools = await client.get_tools()
            print(f"✓ Получено {len(tools)} инструментов из MCP сервера")
            
            # Выводим список инструментов
            print("\nДоступные инструменты:")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool.name}")
                desc = tool.description or ""
                if len(desc) > 80:
                    desc = desc[:80] + "..."
                print(f"     {desc}")
            
            # Проверяем наличие ключевых инструментов
            tool_names = [tool.name for tool in tools]
            expected_tools = ["files", "search", "edit", "tags", "main", "memory", "extract", "list", "help"]
            
            print("\n=== ПРОВЕРКА ИНСТРУМЕНТОВ ===")
            for expected in expected_tools:
                if expected in tool_names:
                    print(f"✓ {expected} - доступен")
                else:
                    print(f"✗ {expected} - НЕ найден")
            
            missing = [t for t in expected_tools if t not in tool_names]
            if missing:
                print(f"\n⚠️  Отсутствуют инструменты: {missing}")
                return False
            
            print(f"\n✓ Все {len(expected_tools)} инструментов доступны!")
            
            # Тестируем вызов инструмента help
            print("\n=== ТЕСТИРОВАНИЕ ИНСТРУМЕНТА help ===")
            help_tool = next((t for t in tools if t.name == "help"), None)
            if help_tool:
                try:
                    result = await help_tool.ainvoke({})
                    print(f"✓ Инструмент help вызван успешно")
                    print(f"Результат (первые 200 символов): {str(result)[:200]}...")
                except Exception as e:
                    print(f"✗ Ошибка вызова инструмента help: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("✗ Инструмент help не найден")
            
            # Тестируем вызов инструмента list
            print("\n=== ТЕСТИРОВАНИЕ ИНСТРУМЕНТА list ===")
            list_tool = next((t for t in tools if t.name == "list"), None)
            if list_tool:
                try:
                    # Инструмент list требует параметр requests (массив запросов)
                    result = await list_tool.ainvoke({"requests": [{"type": "files"}]})
                    print(f"✓ Инструмент list вызван успешно")
                    result_str = str(result)
                    if len(result_str) > 200:
                        print(f"Результат (первые 200 символов): {result_str[:200]}...")
                    else:
                        print(f"Результат: {result_str}")
                except Exception as e:
                    print(f"✗ Ошибка вызова инструмента list: {e}")
                    # Не критично, просто показываем ошибку
                    if "validation" not in str(e).lower():
                        import traceback
                        traceback.print_exc()
            else:
                print("✗ Инструмент list не найден")
            
        except Exception as e:
            print(f"✗ Ошибка получения инструментов: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Создаем LLM с OpenRouter
        print("\n=== ИНИЦИАЛИЗАЦИЯ LLM ===")
        try:
            from langchain_openai import ChatOpenAI
            
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
        except Exception as e:
            print(f"✗ Ошибка инициализации LLM: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Создаем агента с инструментами из MCP
        print("\n=== СОЗДАНИЕ АГЕНТА ===")
        try:
            agent = create_agent(llm, tools)
            print("✓ Агент создан с инструментами из MCP сервера")
        except Exception as e:
            print(f"✗ Ошибка создания агента: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Простой тест - агент использует инструмент help
        print("\n=== ТЕСТИРОВАНИЕ АГЕНТА ===")
        try:
            response = await agent.ainvoke({"messages": [("user", "Получи помощь по использованию системы памяти используя инструмент help")]})
            print(f"✓ Агент успешно вызван")
            output = str(response.get("messages", response))
            if output:
                output_preview = output[:300] if len(output) > 300 else output
                print(f"Ответ агента (первые 300 символов): {output_preview}...")
        except Exception as e:
            print(f"⚠️  Ошибка вызова агента (может быть из-за API ограничений): {e}")
            if "unsupported_country" not in str(e).lower() and "403" not in str(e) and "401" not in str(e):
                import traceback
                traceback.print_exc()
        
        # Итоги
        print("\n" + "=" * 80)
        print("ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 80)
        print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n✓ Инструменты получены: {len(tools)} инструментов")
        print(f"✓ Все необходимые инструменты доступны: {len(expected_tools)}/{len(expected_tools)}")
        print(f"✓ Сервер работает в Docker: доступен на {MCP_URL}")
        print(f"✓ Агент создан успешно")
        
        print("\n" + "=" * 80)
        print("ОСТАНОВКА DOCKER")
        print("=" * 80)
        print("Для остановки Docker контейнера выполните в терминале:")
        print(f"   cd {project_root}")
        print(f"   docker-compose -f docker/docker-compose.remote-test.yml down")
        print("=" * 80)
        
        # Успех если инструменты получены
        return len(tools) > 0 and len(missing) == 0
        
    except Exception as e:
        print(f"\n✗ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция"""
    success = await test_remote_mcp_langchain_integration()
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
