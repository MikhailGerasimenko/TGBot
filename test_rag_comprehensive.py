 #!/usr/bin/env python3
"""
Комплексный тест RAG функций
Проверяет индексацию, поиск, генерацию с контекстом
"""

import requests
import time
import json
from datetime import datetime

# Конфигурация
MODEL_SERVICE_URL = "http://localhost:8000"

def test_health():
    """Проверка здоровья сервиса"""
    print("🔍 Проверка здоровья сервиса...")
    try:
        response = requests.get(f"{MODEL_SERVICE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Сервис работает")
            print(f"   Корпус: {data.get('corpus_size', 0)} документов")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_index_documents():
    """Тест индексации документов"""
    print(f"\n📚 Тест индексации документов...")
    
    # Тестовые документы
    test_docs = [
        "Для получения отпуска сотрудник должен подать заявление за 2 недели до начала отпуска. Заявление подается руководителю отдела.",
        "Руководитель рассматривает заявление в течение 3 рабочих дней. При положительном решении издается приказ о предоставлении отпуска.",
        "Больничный лист оформляется в медицинском учреждении. Сотрудник должен представить больничный лист в отдел кадров в течение 3 дней после выхода на работу.",
        "СОП (Стандартная Операционная Процедура) - это документ, описывающий стандартные методы выполнения задач в компании.",
        "Для повышения по службе необходимо подать заявление на имя руководителя с обоснованием причин повышения."
    ]
    
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/index",
            json={"documents": test_docs},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Индексация успешна")
            print(f"   Проиндексировано: {data.get('indexed', 0)} документов")
            return True
        else:
            print(f"❌ Ошибка индексации: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_search(query, top_k=3):
    """Тест поиска"""
    print(f"\n🔍 Тест поиска: '{query}'")
    
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('hits', [])
            print(f"✅ Найдено результатов: {len(results)}")
            
            for i, result in enumerate(results, 1):
                print(f"   {i}. Схожесть: {result.get('score', 0):.3f}")
                print(f"      Текст: {result.get('text', '')[:100]}...")
            
            return results
        else:
            print(f"❌ Ошибка поиска: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def test_generation_with_context(query, context, max_tokens=150):
    """Тест генерации с контекстом"""
    print(f"\n📝 Тест генерации с контекстом: '{query}'")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/generate",
            json={
                "query": query,
                "context": context,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        generation_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', '')
            tokens = data.get('completion_tokens', 0)
            
            print(f"✅ Успешно ({generation_time:.2f}с)")
            print(f"   Токенов: {tokens}")
            print(f"   Ответ: {response_text[:200]}...")
            
            return {
                'success': True,
                'response': response_text,
                'time': generation_time,
                'tokens': tokens
            }
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            return {'success': False}
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {'success': False}

def test_search_v2(query, top_k=3):
    """Тест улучшенного поиска v2"""
    print(f"\n⚡ Тест поиска v2: '{query}'")
    
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/search_v2",
            json={"query": query, "top_k": top_k},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('hits', [])
            print(f"✅ Найдено результатов: {len(results)}")
            
            for i, result in enumerate(results, 1):
                print(f"   {i}. Схожесть: {result.get('score', 0):.3f}")
                print(f"      Текст: {result.get('text', '')[:100]}...")
            
            return results
        else:
            print(f"❌ Ошибка поиска v2: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def test_rag_workflow():
    """Тест полного RAG workflow"""
    print(f"\n🔄 Тест полного RAG workflow...")
    
    # 1. Индексация
    if not test_index_documents():
        print("❌ Не удалось проиндексировать документы")
        return False
    
    time.sleep(2)
    
    # 2. Поиск
    search_results = test_search("отпуск документы", top_k=2)
    if not search_results:
        print("❌ Поиск не дал результатов")
        return False
    
    time.sleep(2)
    
    # 3. Генерация с контекстом
    context = "\n".join([result['text'] for result in search_results])
    generation_result = test_generation_with_context(
        "Какие документы нужны для отпуска?",
        context,
        max_tokens=200
    )
    
    if not generation_result.get('success'):
        print("❌ Генерация с контекстом не удалась")
        return False
    
    time.sleep(2)
    
    # 4. Тест поиска v2
    test_search_v2("больничный лист", top_k=2)
    
    return True

def main():
    """Главная функция тестирования"""
    print("🧠 Комплексный тест RAG функций")
    print("=" * 50)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Проверка здоровья
    if not test_health():
        print("❌ Сервис недоступен. Завершение теста.")
        return
    
    # 2. Тест RAG workflow
    if test_rag_workflow():
        print(f"\n🎉 RAG тестирование завершено успешно!")
    else:
        print(f"\n❌ RAG тестирование завершено с ошибками!")
    
    print(f"Время окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 