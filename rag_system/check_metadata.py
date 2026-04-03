# check_metadata.py
"""Скрипт для проверки метаданных в векторных БД."""
import os
from langchain_community.vectorstores import Chroma
import app_state
from config import PERSIST_DIRECTORY_EMPLOYEES, PERSIST_DIRECTORY_TECHNIC

def check_subdivision_metadata(persist_directory: str, name: str):
    """Проверяет метаданные подразделений в коллекции."""
    print(f"\n{'='*60}")
    print(f"Проверка метаданных: {name}")
    print(f"Путь: {persist_directory}")
    print(f"{'='*60}")
    
    if not os.path.exists(persist_directory):
        print(f"❌ Директория не существует!")
        return
    
    try:
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=app_state.embedding_model
        )
        
        collection = vectorstore._collection
        count = collection.count()
        
        if count == 0:
            print(f"❌ Коллекция пуста!")
            return
        
        # Получаем все документы с метаданными
        results = collection.get(include=['metadatas'])
        
        # Собираем уникальные подразделения
        subdivisions = {}
        for metadata in results['metadatas']:
            subdivision = metadata.get('subdivision', 'NO_SUBDIVISION')
            source = metadata.get('source', 'unknown')
            
            if subdivision not in subdivisions:
                subdivisions[subdivision] = {'count': 0, 'sources': set()}
            subdivisions[subdivision]['count'] += 1
            subdivisions[subdivision]['sources'].add(os.path.basename(source))
        
        print(f"\n📊 Всего чанков: {count}")
        print(f"🏢 Уникальных подразделений: {len(subdivisions)}")
        
        # Сортируем по количеству чанков
        sorted_subdivisions = sorted(subdivisions.items(), key=lambda x: x[1]['count'], reverse=True)
        
        print(f"\n📋 Подразделения:")
        for sub, data in sorted_subdivisions:
            print(f"   {sub}: {data['count']} чанков")
            if sub != 'NO_SUBDIVISION':
                # Показываем первые 3 источника
                sources = list(data['sources'])[:3]
                print(f"      Источники: {', '.join(sources)}")
        
        # Проверяем конкретное подразделение
        target = 'ЦУТСС'
        if target in subdivisions:
            print(f"\n✅ Подразделение {target} найдено:")
            print(f"   Чанков: {subdivisions[target]['count']}")
            print(f"   Источники: {', '.join(subdivisions[target]['sources'])}")
        else:
            print(f"\n❌ Подразделение {target} НЕ найдено!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Проверяет метаданные во всех коллекциях."""
    print("🔍 Проверка метаданных подразделений")
    print("="*60)
    
    # Инициализируем embedding модель
    print("\n📦 Инициализация embedding модели...")
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from config import EMBEDDING_MODEL_NAME
    app_state.embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    print("✅ Embedding модель инициализирована")
    
    check_subdivision_metadata(PERSIST_DIRECTORY_EMPLOYEES, "Сотрудники (employees)")
    check_subdivision_metadata(PERSIST_DIRECTORY_TECHNIC, "Техника (technic)")
    
    print(f"\n{'='*60}")
    print("✅ Проверка завершена")
    print("="*60)

if __name__ == "__main__":
    main()
