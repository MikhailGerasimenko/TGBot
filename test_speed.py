#!/usr/bin/env python3
"""
Скрипт для тестирования скорости модели
"""

import requests
import time
import json
from datetime import datetime

def test_generation_speed(prompt, max_tokens=100, iterations=3):
    """Тестирует скорость генерации"""
    print(f"🧪 Тестируем скорость генерации...")
    print(f"Промпт: {prompt[:50]}...")
    print(f"Максимум токенов: {max_tokens}")
    print(f"Итераций: {iterations}")
    print("-" * 50)
    
    speeds = []
    times = []
    tokens = []
    
    for i in range(iterations):
        print(f"Итерация {i+1}/{iterations}...")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                "http://localhost:8000/generate",
                json={
                    "query": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "top_p": 0.9
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                end_time = time.time()
                
                generation_time = result['generation_time']
                completion_tokens = result['completion_tokens']
                
                # Рассчитываем скорость
                speed = completion_tokens / generation_time
                speeds.append(speed)
                times.append(generation_time)
                tokens.append(completion_tokens)
                
                print(f"  ⏱️ Время: {generation_time:.2f} сек")
                print(f"  📊 Токенов: {completion_tokens}")
                print(f"  ⚡ Скорость: {speed:.1f} т/с")
                print(f"  📝 Ответ: {result['response'][:100]}...")
                
            else:
                print(f"  ❌ Ошибка HTTP: {response.status_code}")
                print(f"  📄 Ответ: {response.text}")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
    
    print("-" * 50)
    
    if speeds:
        avg_speed = sum(speeds) / len(speeds)
        avg_time = sum(times) / len(times)
        avg_tokens = sum(tokens) / len(tokens)
        
        print(f"📊 РЕЗУЛЬТАТЫ:")
        print(f"  Средняя скорость: {avg_speed:.1f} т/с")
        print(f"  Среднее время: {avg_time:.2f} сек")
        print(f"  Среднее токенов: {avg_tokens:.0f}")
        print(f"  Минимальная скорость: {min(speeds):.1f} т/с")
        print(f"  Максимальная скорость: {max(speeds):.1f} т/с")
        
        return avg_speed
    else:
        print("❌ Не удалось получить результаты")
        return 0

def test_embeddings_speed(texts, iterations=3):
    """Тестирует скорость эмбеддингов"""
    print(f"\n🧪 Тестируем скорость эмбеддингов...")
    print(f"Текстов: {len(texts)}")
    print(f"Итераций: {iterations}")
    print("-" * 50)
    
    times = []
    
    for i in range(iterations):
        print(f"Итерация {i+1}/{iterations}...")
        
        try:
            response = requests.post(
                "http://localhost:8000/embeddings",
                json={"texts": texts},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                embedding_time = result['embedding_time']
                times.append(embedding_time)
                
                print(f"  ⏱️ Время: {embedding_time:.3f} сек")
                print(f"  📊 Эмбеддингов: {len(result['embeddings'])}")
                print(f"  📏 Размерность: {len(result['embeddings'][0])}")
                
            else:
                print(f"  ❌ Ошибка HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
    
    print("-" * 50)
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"📊 РЕЗУЛЬТАТЫ ЭМБЕДДИНГОВ:")
        print(f"  Среднее время: {avg_time:.3f} сек")
        print(f"  Минимальное время: {min(times):.3f} сек")
        print(f"  Максимальное время: {max(times):.3f} сек")
        
        return avg_time
    else:
        print("❌ Не удалось получить результаты")
        return 0

def test_search_speed(query, iterations=3):
    """Тестирует скорость поиска"""
    print(f"\n🧪 Тестируем скорость поиска...")
    print(f"Запрос: {query}")
    print(f"Итераций: {iterations}")
    print("-" * 50)
    
    times = []
    
    for i in range(iterations):
        print(f"Итерация {i+1}/{iterations}...")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                "http://localhost:8000/search",
                json={"query": query, "top_k": 5},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                end_time = time.time()
                search_time = end_time - start_time
                times.append(search_time)
                
                print(f"  ⏱️ Время: {search_time:.3f} сек")
                print(f"  📊 Результатов: {len(result['hits'])}")
                if result['hits']:
                    print(f"  🎯 Лучший результат: {result['hits'][0]['text'][:100]}...")
                
            else:
                print(f"  ❌ Ошибка HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
    
    print("-" * 50)
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"📊 РЕЗУЛЬТАТЫ ПОИСКА:")
        print(f"  Среднее время: {avg_time:.3f} сек")
        print(f"  Минимальное время: {min(times):.3f} сек")
        print(f"  Максимальное время: {max(times):.3f} сек")
        
        return avg_time
    else:
        print("❌ Не удалось получить результаты")
        return 0

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ СКОРОСТИ МОДЕЛИ")
    print("=" * 50)
    
    # Проверяем health
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Сервис не отвечает")
            return
        print("✅ Сервис работает")
    except Exception as e:
        print(f"❌ Не удалось подключиться к сервису: {e}")
        return
    
    # Тест генерации
    gen_speed = test_generation_speed(
        "Объясни простыми словами, что такое искусственный интеллект и как он используется в современном мире?",
        max_tokens=150,
        iterations=3
    )
    
    # Тест эмбеддингов
    emb_time = test_embeddings_speed([
        "Искусственный интеллект - это технология машинного обучения",
        "Машинное обучение позволяет компьютерам учиться на данных",
        "Нейронные сети имитируют работу человеческого мозга",
        "Глубокое обучение использует многослойные нейронные сети",
        "Компьютерное зрение позволяет машинам видеть и понимать изображения"
    ], iterations=3)
    
    # Тест поиска
    search_time = test_search_speed(
        "искусственный интеллект машинное обучение",
        iterations=3
    )
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    print(f"Генерация: {gen_speed:.1f} т/с")
    print(f"Эмбеддинги: {emb_time:.3f} сек")
    print(f"Поиск: {search_time:.3f} сек")
    
    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ:")
    
    if gen_speed < 15:
        print("  - Увеличить LLAMA_GPU_LAYERS до 80-120")
        print("  - Увеличить LLAMA_BATCH до 2048")
        print("  - Уменьшить LLAMA_CTX до 4096")
        print("  - Попробовать более легкую модель (q4_k_m)")
    
    if emb_time > 0.1:
        print("  - Эмбеддинги работают медленно, проверить GPU")
    
    if search_time > 0.05:
        print("  - Поиск работает медленно, оптимизировать индекс")

if __name__ == "__main__":
    main() 