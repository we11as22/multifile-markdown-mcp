#!/usr/bin/env python3
"""
Тестирование режима без БД в Docker
Проверяет работу MCP сервера в контейнере
"""
import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_docker_container():
    """Проверка, что контейнер запущен"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=agent-memory-mcp-file-only", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            check=True
        )
        status = result.stdout.strip()
        if status and "Up" in status:
            print(f"✓ Контейнер запущен: {status}")
            return True
        else:
            print(f"✗ Контейнер не запущен: {status}")
            return False
    except Exception as e:
        print(f"✗ Ошибка проверки контейнера: {e}")
        return False


def check_docker_logs():
    """Проверка логов контейнера"""
    try:
        result = subprocess.run(
            ["docker", "logs", "agent-memory-mcp-file-only", "--tail", "20"],
            capture_output=True,
            text=True,
            check=True
        )
        logs = result.stdout
        print("\n=== ЛОГИ КОНТЕЙНЕРА ===")
        print(logs)
        
        # Проверяем ключевые сообщения
        has_file_only = "database_disabled_using_file_only_mode" in logs or "file-only" in logs.lower()
        has_initialized = "server_initialized" in logs or "initialized" in logs.lower()
        
        print(f"\n✓ Режим без БД: {has_file_only}")
        print(f"✓ Сервер инициализирован: {has_initialized}")
        
        return has_file_only and has_initialized
    except Exception as e:
        print(f"✗ Ошибка чтения логов: {e}")
        return False


def test_memory_files():
    """Проверка файлов памяти в контейнере"""
    try:
        # Проверяем, что директория memory_files существует
        memory_path = project_root / "memory_files"
        if not memory_path.exists():
            memory_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Создана директория: {memory_path}")
        
        # Проверяем, что файлы доступны
        main_file = memory_path / "main.md"
        index_file = memory_path / "files_index.json"
        
        print(f"\n=== ПРОВЕРКА ФАЙЛОВ ===")
        print(f"main.md существует: {main_file.exists()}")
        print(f"files_index.json существует: {index_file.exists()}")
        
        if main_file.exists():
            content = main_file.read_text(encoding='utf-8')
            print(f"main.md размер: {len(content)} байт")
            print(f"main.md содержит 'Agent Memory': {'Agent Memory' in content}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка проверки файлов: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_container_exec():
    """Тестирование выполнения команд в контейнере"""
    try:
        print("\n=== ТЕСТИРОВАНИЕ В КОНТЕЙНЕРЕ ===")
        
        # Проверяем Python окружение
        result = subprocess.run(
            ["docker", "exec", "agent-memory-mcp-file-only", "python", "-c", "import sys; print(sys.version)"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Python версия: {result.stdout.strip()}")
        
        # Проверяем импорт модулей
        result = subprocess.run(
            ["docker", "exec", "agent-memory-mcp-file-only", "python", "-c", "from config.settings import Settings; s = Settings(); print(f'USE_DATABASE={s.use_database}')"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ USE_DATABASE: {result.stdout.strip()}")
        
        # Проверяем структуру директорий
        result = subprocess.run(
            ["docker", "exec", "agent-memory-mcp-file-only", "ls", "-la", "/app/memory_files"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Содержимое /app/memory_files:")
        print(result.stdout)
        
        return True
    except Exception as e:
        print(f"✗ Ошибка выполнения команд: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_library_in_container():
    """Тестирование библиотеки внутри контейнера"""
    try:
        print("\n=== ТЕСТИРОВАНИЕ БИБЛИОТЕКИ В КОНТЕЙНЕРЕ ===")
        
        # Создаем тестовый скрипт
        test_script = """
import asyncio
import sys
sys.path.insert(0, '/app')

from src.library import MemoryLibrary

async def test():
    try:
        memory = MemoryLibrary(
            memory_files_path="/app/memory_files",
            use_database=False
        )
        await memory.initialize()
        await memory.initialize_memory()
        
        # Создаем файл
        result = await memory.create_file(
            "Docker Test Project",
            "project",
            "# Docker Test Project\\n\\nТестовый проект из Docker",
            tags=["docker", "test"]
        )
        print(f"✓ Файл создан: {result['file_path']}")
        
        # Список файлов
        files = await memory.list_files()
        print(f"✓ Всего файлов: {files['total']}")
        print(f"✓ Дерево файлов: {list(files.get('tree', {}).keys())}")
        
        # Чтение файла
        content = await memory.get_file(result['file_path'])
        print(f"✓ Файл прочитан: {len(content['content'])} байт")
        
        # Теги
        tags = await memory.get_tags(result['file_path'])
        print(f"✓ Теги: {tags['tags']}")
        
        await memory.close()
        print("✓ Все тесты пройдены")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
"""
        
        # Записываем скрипт во временный файл
        script_path = project_root / "tests" / "docker_test_temp.py"
        script_path.write_text(test_script, encoding='utf-8')
        
        try:
            # Копируем скрипт в контейнер
            subprocess.run(
                ["docker", "cp", str(script_path), "agent-memory-mcp-file-only:/tmp/test.py"],
                check=True
            )
            
            # Запускаем скрипт
            result = subprocess.run(
                ["docker", "exec", "agent-memory-mcp-file-only", "python", "/tmp/test.py"],
                capture_output=True,
                text=True,
                check=True
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result.returncode == 0
        finally:
            # Удаляем временный файл
            if script_path.exists():
                script_path.unlink()
        
    except Exception as e:
        print(f"✗ Ошибка тестирования библиотеки: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция тестирования"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ РЕЖИМА БЕЗ БД В DOCKER")
    print("=" * 80)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Тест 1: Проверка контейнера
    print("\n" + "=" * 80)
    print("ТЕСТ 1: Проверка контейнера")
    print("=" * 80)
    results.append(("Проверка контейнера", check_docker_container()))
    
    # Тест 2: Проверка логов
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Проверка логов")
    print("=" * 80)
    results.append(("Проверка логов", check_docker_logs()))
    
    # Тест 3: Проверка файлов
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Проверка файлов памяти")
    print("=" * 80)
    results.append(("Проверка файлов", test_memory_files()))
    
    # Тест 4: Выполнение команд
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Выполнение команд в контейнере")
    print("=" * 80)
    results.append(("Выполнение команд", test_container_exec()))
    
    # Тест 5: Тестирование библиотеки
    print("\n" + "=" * 80)
    print("ТЕСТ 5: Тестирование библиотеки в контейнере")
    print("=" * 80)
    results.append(("Тестирование библиотеки", await test_library_in_container()))
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nВсего тестов: {total}")
    print(f"✓ Успешно: {passed}")
    print(f"✗ Провалено: {total - passed}")
    print(f"Процент успеха: {(passed / total * 100) if total > 0 else 0:.1f}%")
    
    print("\nДетали:")
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    if passed < total:
        print("\nПроваленные тесты:")
        for name, result in results:
            if not result:
                print(f"  - {name}")
    
    print("=" * 80)
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nТесты прерваны пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

