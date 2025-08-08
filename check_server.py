import torch
import psutil
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_system():
    """Проверка системных требований"""
    
    print("\n=== Проверка системных требований ===\n")
    
    # Проверка Python
    python_version = sys.version.split()[0]
    print(f"Python версия: {python_version}")
    
    # Проверка CPU
    cpu_count = psutil.cpu_count()
    cpu_count_physical = psutil.cpu_count(logical=False)
    print(f"CPU ядер: {cpu_count} (физических: {cpu_count_physical})")
    
    # Проверка RAM
    ram = psutil.virtual_memory()
    ram_total = ram.total / (1024 ** 3)  # GB
    ram_available = ram.available / (1024 ** 3)  # GB
    print(f"RAM общая: {ram_total:.1f}GB")
    print(f"RAM доступная: {ram_available:.1f}GB")
    
    # Проверка диска
    disk = psutil.disk_usage('/')
    disk_total = disk.total / (1024 ** 3)  # GB
    disk_free = disk.free / (1024 ** 3)  # GB
    print(f"Диск общий: {disk_total:.1f}GB")
    print(f"Диск свободно: {disk_free:.1f}GB")
    
    # Проверка CUDA
    cuda_available = torch.cuda.is_available()
    print(f"\nCUDA доступна: {cuda_available}")
    
    if cuda_available:
        cuda_version = torch.version.cuda
        gpu_count = torch.cuda.device_count()
        print(f"CUDA версия: {cuda_version}")
        print(f"Количество GPU: {gpu_count}")
        
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            print(f"\nGPU {i}: {gpu_name}")
            print(f"GPU память: {gpu_memory:.1f}GB")
    
    # Проверка необходимых директорий
    required_dirs = ['docs']
    print("\nПроверка директорий:")
    for dir_name in required_dirs:
        exists = os.path.exists(dir_name)
        print(f"{dir_name}: {'✓' if exists else '✗'}")
        if not exists:
            os.makedirs(dir_name)
            print(f"Создана директория {dir_name}")

if __name__ == "__main__":
    check_system() 