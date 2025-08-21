#!/usr/bin/env python3
"""
Тестирование GigaChat-20B-A3B-instruct модели
"""

from llama_cpp import Llama
import time
import os

def test_gigachat():
    print("🧠 Тестирование GigaChat-20B-A3B-instruct модели")
    print("=" * 60)
    
               # Проверяем наличие модели
           model_path = "models/model-gigachat_20b_q8_0.gguf"
    if not os.path.exists(model_path):
        print(f"❌ Модель не найдена: {model_path}")
                       print("📥 Скачайте модель: ./download_model.sh gigachat_20b_q8_0")
        return
    
    print(f"✅ Модель найдена: {model_path}")
    
    # Настройки для GigaChat-20B
    print("\n⚙️  Загружаем модель с оптимизированными настройками...")
    llm = Llama(
        model_path=model_path,
        n_ctx=8192,                    # Увеличенный контекст
        n_threads=12,                  # Больше потоков
        n_batch=1024,                  # Увеличенный батч
        n_gpu_layers=40,               # Больше слоев на GPU
        verbose=True
    )
    
    print("✅ Модель загружена успешно!")
    
    # Тестовые промпты для корпоративного бота
    test_prompts = [
        {
            "name": "Корпоративный ассистент",
            "prompt": "Представь, что ты корпоративный ассистент. Объясни кратко и четко, что такое СОП (стандартная операционная процедура) и зачем он нужен в компании."
        },
        {
            "name": "Анализ документа",
            "prompt": "Проанализируй следующий текст и выдели основные пункты: 'Для получения отпуска сотрудник должен подать заявление за 2 недели до начала отпуска. Заявление подается руководителю отдела. Руководитель рассматривает заявление в течение 3 рабочих дней.'"
        },
        {
            "name": "Ответ на вопрос сотрудника",
            "prompt": "Сотрудник спрашивает: 'Как мне оформить больничный лист? Какие документы нужны и куда их подавать?' Дай четкий пошаговый ответ."
        }
    ]
    
    print(f"\n🧪 Запускаем {len(test_prompts)} тестов...")
    
    for i, test in enumerate(test_prompts, 1):
        print(f"\n📝 Тест {i}: {test['name']}")
        print(f"Вопрос: {test['prompt']}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # GigaChat использует специальный chat template
            response = llm(
                f"<|im_start|>user\n{test['prompt']}<|im_end|>\n<|im_start|>assistant\n",
                max_tokens=512,
                temperature=0.1,
                top_p=0.95,
                repeat_penalty=1.1,
                top_k=40,
                echo=False
            )
            
            generation_time = time.time() - start_time
            
            if response and "choices" in response and len(response["choices"]) > 0:
                answer = response["choices"][0]["text"].strip()
                print(f"Ответ ({generation_time:.2f}с):")
                print(answer)
                
                # Статистика токенов
                if "usage" in response:
                    usage = response["usage"]
                    print(f"\n📊 Токены: {usage.get('completion_tokens', 'N/A')} (ответ)")
                else:
                    print(f"\n📊 Время генерации: {generation_time:.2f} секунд")
                    
            else:
                print("❌ Пустой ответ от модели")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        print("=" * 60)
    
    print("\n🎉 Тестирование завершено!")
    print("\n💡 Рекомендации:")
    print("• Если ответы качественные - модель готова к использованию")
    print("• Если медленно - уменьшите n_gpu_layers или используйте q4_k_m")
    print("• Если ошибки - проверьте GPU память и драйверы")

if __name__ == "__main__":
    test_gigachat() 