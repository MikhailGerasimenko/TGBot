#!/usr/bin/env python3
"""
Расширенный тест модели GigaChat-20B-A3B-instruct
Проверяет генерацию, поиск, эмбеддинги и производительность
"""

import requests
import time
import json
import statistics
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
            print(f"   Модель: {data.get('model_path', 'N/A')}")
            print(f"   GPU слои: {data.get('gpu_layers', 'N/A')}")
            print(f"   Контекст: {data.get('ctx', 'N/A')}")
            print(f"   Эмбеддинги: {data.get('embedding_model', 'N/A')}")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_generation(prompt, max_tokens=100, expected_time=10):
    """Тест генерации текста"""
    print(f"\n📝 Тест генерации: {prompt[:50]}...")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/generate",
            json={"query": prompt, "max_tokens": max_tokens},
            timeout=60
        )
        generation_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', '')
            tokens = data.get('completion_tokens', 0)
            
            print(f"✅ Успешно ({generation_time:.2f}с)")
            print(f"   Токенов: {tokens}")
            print(f"   Скорость: {tokens/generation_time:.1f} токенов/сек")
            print(f"   Ответ: {response_text[:200]}...")
            
            return {
                'success': True,
                'time': generation_time,
                'tokens': tokens,
                'speed': tokens/generation_time
            }
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return {'success': False}
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {'success': False}

def test_embeddings(text):
    """Тест создания эмбеддингов"""
    print(f"\n🔢 Тест эмбеддингов: {text[:30]}...")
    
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/embeddings",
            json={"text": text},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            embedding = data.get('embedding', [])
            print(f"✅ Успешно")
            print(f"   Размер: {len(embedding)} измерений")
            print(f"   Первые 5 значений: {embedding[:5]}")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_search(query, top_k=5):
    """Тест поиска"""
    print(f"\n🔍 Тест поиска: {query}")
    
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Найдено результатов: {len(results)}")
            
            for i, result in enumerate(results[:3], 1):
                print(f"   {i}. Схожесть: {result.get('score', 0):.3f}")
                print(f"      Текст: {result.get('text', '')[:100]}...")
            
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_performance():
    """Тест производительности"""
    print(f"\n⚡ Тест производительности...")
    
    test_prompts = [
        "Объясни простыми словами, что такое искусственный интеллект",
        "Напиши короткое стихотворение про кота",
        "Какие основные принципы здорового питания?",
        "Опиши процесс фотосинтеза",
        "Что такое блокчейн и как он работает?"
    ]
    
    results = []
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Тест {i}/{len(test_prompts)} ---")
        result = test_generation(prompt, max_tokens=80)
        if result.get('success'):
            results.append(result)
        time.sleep(2)  # Пауза между запросами
    
    if results:
        times = [r['time'] for r in results]
        speeds = [r['speed'] for r in results]
        
        print(f"\n📊 Статистика производительности:")
        print(f"   Среднее время: {statistics.mean(times):.2f}с")
        print(f"   Мин. время: {min(times):.2f}с")
        print(f"   Макс. время: {max(times):.2f}с")
        print(f"   Средняя скорость: {statistics.mean(speeds):.1f} токенов/сек")
        print(f"   Мин. скорость: {min(speeds):.1f} токенов/сек")
        print(f"   Макс. скорость: {max(speeds):.1f} токенов/сек")

def test_corporate_scenarios():
    """Тест корпоративных сценариев"""
    print(f"\n🏢 Тест корпоративных сценариев...")
    
    corporate_prompts = [
        "Как правильно оформить больничный лист?",
        "Какие документы нужны для получения отпуска?",
        "Объясни, что такое СОП и зачем он нужен",
        "Как подать заявление на повышение?",
        "Какие льготы положены сотрудникам с детьми?"
    ]
    
    for i, prompt in enumerate(corporate_prompts, 1):
        print(f"\n--- Корпоративный тест {i}/{len(corporate_prompts)} ---")
        test_generation(prompt, max_tokens=120)
        time.sleep(2)

def main():
    """Главная функция тестирования"""
    print("🧠 Расширенный тест модели GigaChat-20B-A3B-instruct")
    print("=" * 60)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Проверка здоровья
    if not test_health():
        print("❌ Сервис недоступен. Завершение теста.")
        return
    
    # 2. Тест эмбеддингов
    test_embeddings("Это тестовый текст для проверки эмбеддингов")
    
    # 3. Тест поиска
    test_search("отпуск документы")
    
    # 4. Тест производительности
    test_performance()
    
    # 5. Тест корпоративных сценариев
    test_corporate_scenarios()
    
    print(f"\n🎉 Тестирование завершено!")
    print(f"Время окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 