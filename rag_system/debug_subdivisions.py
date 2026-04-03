# debug_subdivisions.py
"""Отладочный скрипт для проверки индексации подразделений."""
import os
from config import DOCS_FOLDER_SUBDIVISIONS

print("🔍 Проверка папки subdivisions")
print("="*60)
print(f"Папка: {DOCS_FOLDER_SUBDIVISIONS}")
print(f"Существует: {os.path.exists(DOCS_FOLDER_SUBDIVISIONS)}")

if os.path.exists(DOCS_FOLDER_SUBDIVISIONS):
    # Ищем файлы .docx и .md
    doc_files = []
    # Сначала файлы в корне
    for f in os.listdir(DOCS_FOLDER_SUBDIVISIONS):
        if os.path.isfile(os.path.join(DOCS_FOLDER_SUBDIVISIONS, f)) and (f.endswith('.docx') or f.endswith('.md')):
            doc_files.append(os.path.join(DOCS_FOLDER_SUBDIVISIONS, f))
    # Затем файлы в подпапках
    for root, dirs, files in os.walk(DOCS_FOLDER_SUBDIVISIONS):
        # Пропускаем корневую директорию (уже обработали)
        if root == DOCS_FOLDER_SUBDIVISIONS:
            continue
        for f in files:
            if f.endswith('.docx') or f.endswith('.md'):
                doc_files.append(os.path.join(root, f))
    
    print(f"\n📄 Найдено файлов: {len(doc_files)}")
    
    if doc_files:
        print("\nПервые 10 файлов:")
        for f in doc_files[:10]:
            print(f"  - {os.path.relpath(f, DOCS_FOLDER_SUBDIVISIONS)}")
    else:
        print("\n❌ Файлы не найдены!")
else:
    print("\n❌ Папка не существует!")
