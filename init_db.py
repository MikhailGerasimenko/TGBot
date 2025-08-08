import asyncio
from database import init_db, populate_test_data

async def main():
    print("Инициализация базы данных...")
    if await init_db():
        print("База данных успешно создана")
        
        print("\nДобавление тестовых данных...")
        if await populate_test_data():
            print("Тестовые данные успешно добавлены")
        else:
            print("Ошибка при добавлении тестовых данных")
    else:
        print("Ошибка при создании базы данных")

if __name__ == "__main__":
    asyncio.run(main()) 