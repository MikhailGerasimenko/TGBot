#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений
"""

import requests
import json
import time

def test_generation():
    """Тест генерации с очисткой артефактов"""
    print("🧪 Тестируем генерацию...")
    
    url = "http://localhost:8000/generate"
    data = {
        "query": "Что такое ИИ?",
        "max_tokens": 50
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            
            print(f"⚡ Скорость: {result['completion_tokens'] / result['generation_time']:.1f} т/с")
            print(f"⏱️ Время: {result['generation_time']:.2f} сек")
            print(f"📊 Токенов: {result['completion_tokens']}")
            print(f"\n📝 Ответ:")
            print(result['response'])
            
            # Проверяем на артефакты
            if '[/SYS]' in result['response'] or '[/INST]' in result['response']:
                print("❌ Артефакты все еще есть!")
                return False
            else:
                print("✅ Артефакты убраны!")
                return True
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_embeddings():
    """Тест эмбеддингов"""
    print("\n🧪 Тестируем эмбеддинги...")
    
    url = "http://localhost:8000/embeddings"
    data = {
        "texts": ["тестовый текст", "второй текст"]
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            
            print(f"📊 Создано эмбеддингов: {len(result['embeddings'])}")
            print(f"📏 Размерность: {len(result['embeddings'][0])}")
            print(f"⏱️ Время: {result['embedding_time']:.3f} сек")
            print("✅ Эмбеддинги работают!")
            return True
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_health():
    """Тест health check"""
    print("🏥 Проверяем health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Сервис работает")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Сервис не отвечает: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Тестируем исправления...")
    
    # Проверяем health
    if not test_health():
        print("❌ Сервис не работает!")
        exit(1)
    
    # Тестируем генерацию
    gen_ok = test_generation()
    
    # Тестируем эмбеддинги
    emb_ok = test_embeddings()
    
    print(f"\n📊 Результаты:")
    print(f"Генерация: {'✅' if gen_ok else '❌'}")
    print(f"Эмбеддинги: {'✅' if emb_ok else '❌'}")
    
    if gen_ok and emb_ok:
        print("🎉 Все исправления работают!")
    else:
        print("⚠️ Есть проблемы, нужно доработать") 