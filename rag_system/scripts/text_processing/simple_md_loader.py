# simple_md_loader.py
"""Простой загрузчик MD файлов без зависимости от unstructured."""
import os
from typing import List
from langchain.schema import Document

class SimpleMarkdownLoader:
    """Простой загрузчик Markdown файлов."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> List[Document]:
        """Загружает содержимое MD файла."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Файл не найден: {self.file_path}")
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return [Document(
            page_content=content,
            metadata={'source': self.file_path}
        )]
