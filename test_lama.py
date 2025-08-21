from llama_cpp import Llama
import time

print("Загрузка модели...")

# Оптимизированные настройки для Q2_K на GPU
llm = Llama(
    model_path="model-q2_k.gguf",  # Q2_K версия
    n_ctx=2048,                    # Уменьшенный контекст для экономии памяти
    n_threads=4,                   # Меньше потоков CPU
    n_batch=256,                   # Уменьшенный размер батча
    n_gpu_layers=32,              # Загружаем часть слоев на GPU
    verbose=True                   # Включаем логи для отладки
)

print("Модель загружена")

# Формат промпта для Saiga 2
def format_prompt(message, system_prompt=""):
    if system_prompt:
        return f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{message} [/INST]"
    return f"<s>[INST] {message} [/INST]"

# Тест на документации
test_prompt = """Представь, что ты корпоративный ассистент. Объясни кратко и четко, что такое СОП (стандартная операционная процедура) и зачем он нужен в компании."""

print(f"\nЗапрос: {test_prompt}")
print("Генерация ответа...")

try:
    # Генерация ответа
    prompt = format_prompt(
        test_prompt,
        system_prompt="Ты - эксперт по корпоративной документации. Отвечай кратко и по делу."
    )
    
    response = llm(
        prompt,
        max_tokens=512,            # Уменьшаем для экономии памяти
        temperature=0.1,           # Низкая температура для точных ответов
        top_p=0.95,
        repeat_penalty=1.1,
        top_k=40,
        echo=False                 # Не включаем промпт в ответ
    )
    
    if response and "choices" in response and len(response["choices"]) > 0:
        answer = response["choices"][0]["text"].strip()
        print("\nОтвет модели:")
        print("-" * 50)
        print(answer)
        print("-" * 50)
    else:
        print("\nОшибка: Пустой ответ от модели")
    
except Exception as e:
    print(f"\nОшибка: {str(e)}")
    raise

print("\nТестирование завершено!")