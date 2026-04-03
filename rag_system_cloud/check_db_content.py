# check_db_content.py
"""Скрипт для проверки содержимого векторных БД и статистики по загруженным документам."""
import os
from langchain_community.vectorstores import Chroma
from config import (
    PERSIST_DIRECTORY_TECHNIC, PERSIST_DIRECTORY_WORK_PLAN, PERSIST_DIRECTORY_ALL_DOCS,
    PERSIST_DIRECTORY_EMPLOYEES, PERSIST_DIRECTORY_SUBDIVISIONS,
    PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES, PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES
)
import app_state

def check_vectorstore(persist_directory: str, name: str):
    """Проверяет содержимое векторной БД и выводит статистику."""
    print(f"\n{'='*60}")
    print(f"Проверка: {name}")
    print(f"Путь: {persist_directory}")
    print(f"{'='*60}")
    
    if not os.path.exists(persist_directory):
        print(f"❌ Директория не существует!")
        return
    
    try:
        # Подключаемся к векторной БД
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=app_state.embedding_model
        )
        
        # Получаем все документы
        collection = vectorstore._collection
        count = collection.count()
        
        if count == 0:
            print(f"❌ Коллекция пуста!")
            return
        
        print(f"✅ Всего чанков: {count}")
        
        # Получаем все документы с метаданными
        results = collection.get(include=['metadatas', 'documents'])
        
        # Собираем уникальные источники (файлы)
        sources = set()
        md_files = set()
        docx_files = set()
        subdivisions = set()
        
        for metadata in results['metadatas']:
            source = metadata.get('source', 'unknown')
            sources.add(source)
            
            if source.endswith('.md'):
                md_files.add(os.path.basename(source))
            elif source.endswith('.docx'):
                docx_files.add(os.path.basename(source))
            
            # Проверяем метаданные подразделений
            if 'subdivision' in metadata:
                subdivisions.add(metadata['subdivision'])
        
        print(f"\n📁 Уникальных источников: {len(sources)}")
        print(f"   - MD файлов: {len(md_files)}")
        print(f"   - DOCX файлов: {len(docx_files)}")
        
        if subdivisions:
            print(f"\n🏢 Подразделения в метаданных: {len(subdivisions)}")
            for sub in sorted(subdivisions):
                print(f"   - {sub}")
        
        # Выводим список MD файлов
        if md_files:
            print(f"\n📄 MD файлы:")
            for f in sorted(md_files):
                print(f"   - {f}")
        
        # Выводим список DOCX файлов
        if docx_files:
            print(f"\n📄 DOCX файлы:")
            for f in sorted(docx_files):
                print(f"   - {f}")
        
        # Показываем пример содержимого первого чанка
        if results['documents']:
            print(f"\n📝 Пример содержимого первого чанка:")
            print(f"   {results['documents'][0][:200]}...")
            print(f"\n📋 Метаданные первого чанка:")
            for key, value in results['metadatas'][0].items():
                print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Проверяет все векторные БД."""
    print("🔍 Проверка содержимого векторных БД")
    print("="*60)
    
    # Проверяем все коллекции
    check_vectorstore(PERSIST_DIRECTORY_TECHNIC, "Техника (list_technic)")
    check_vectorstore(PERSIST_DIRECTORY_WORK_PLAN, "План работ (work_plan)")
    check_vectorstore(PERSIST_DIRECTORY_ALL_DOCS, "Все документы (all_docs)")
    check_vectorstore(PERSIST_DIRECTORY_EMPLOYEES, "Сотрудники (employees)")
    check_vectorstore(PERSIST_DIRECTORY_SUBDIVISIONS, "Подразделения (subdivisions)")
    check_vectorstore(PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES, "Примеры сотрудников (employees_examples)")
    check_vectorstore(PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES, "Примеры подразделений (subdivisions_examples)")
    
    print(f"\n{'='*60}")
    print("✅ Проверка завершена")
    print("="*60)

if __name__ == "__main__":
    main()
