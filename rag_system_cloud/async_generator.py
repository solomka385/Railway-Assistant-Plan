# async_generator.py
"""
Асинхронная обёртка для генерации LLM.
Позволяет обрабатывать несколько запросов параллельно без блокировки event loop.
"""
import asyncio
import logging
from typing import List, Optional, AsyncGenerator
import app_state

logger = logging.getLogger(__name__)


async def async_batch_generate(texts: List[str], max_new_tokens: int = 4096, temperature: float = 0.2) -> List[str]:
    """
    Асинхронная генерация ответов для батча текстов.
    Выполняет генерацию в отдельном потоке, чтобы не блокировать event loop.
    
    Args:
        texts: Список текстов для генерации
        max_new_tokens: Максимальное количество новых токенов
        temperature: Температура генерации
        
    Returns:
        Список сгенерированных текстов
    """
    if not texts or not isinstance(texts, list) or len(texts) == 0:
        return [""]
    
    def sync_generate():
        """Синхронная функция генерации, выполняемая в отдельном потоке."""
        try:
            logger.debug(f"[ASYNC_GENERATE] Начало sync_generate, количество текстов: {len(texts)}")
            logger.debug(f"[ASYNC_GENERATE] Длина первого текста: {len(texts[0]) if texts else 0}")
            
            results = app_state.pipe(
                texts,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                return_full_text=False,
                pad_token_id=app_state.tokenizer.eos_token_id,
                batch_size=1,
                truncation=True,
                do_sample=True
            )
            
            logger.debug(f"[ASYNC_GENERATE] Результаты от pipe: {type(results)}")
            
            outputs = []
            if results and isinstance(results, list):
                for i, result in enumerate(results):
                    logger.debug(f"[ASYNC_GENERATE] Обработка результата {i}: {type(result)}")
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get('generated_text', '').strip()
                        logger.debug(f"[ASYNC_GENERATE] Сгенерированный текст {i}: длина={len(generated_text)}, первые 100 символов={generated_text[:100]}")
                        if generated_text:
                            import re
                            cleaned_text = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', generated_text, flags=re.DOTALL)
                            outputs.append(cleaned_text.strip())
                        else:
                            logger.warning(f"[ASYNC_GENERATE] Пустой сгенерированный текст для результата {i}")
                            outputs.append("")
                    else:
                        logger.warning(f"[ASYNC_GENERATE] Некорректный формат результата {i}: {result}")
                        outputs.append("")
            else:
                logger.warning(f"[ASYNC_GENERATE] Некорректный формат результатов: {results}")
                outputs.append("")
            
            logger.debug(f"[ASYNC_GENERATE] Возврат {len(outputs)} результатов")
            return outputs
        except Exception as e:
            logger.error(f"[ASYNC_GENERATE] Ошибка в sync_generate: {e}", exc_info=True)
            return [""] * len(texts)
    
    try:
        # Выполняем генерацию в отдельном потоке
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, sync_generate)
        return results
    except Exception as e:
        logger.error(f"[ASYNC_GENERATE] Ошибка: {e}", exc_info=True)
        return [""] * len(texts)


async def async_generate_single(text: str, max_new_tokens: int = 4096, temperature: float = 0.2) -> str:
    """
    Асинхронная генерация ответа для одного текста.
    
    Args:
        text: Текст для генерации
        max_new_tokens: Максимальное количество новых токенов
        temperature: Температура генерации
        
    Returns:
        Сгенерированный текст
    """
    logger.debug(f"[ASYNC_GENERATE_SINGLE] Начало генерации, длина текста: {len(text)}")
    try:
        results = await async_batch_generate([text], max_new_tokens, temperature)
        logger.debug(f"[ASYNC_GENERATE_SINGLE] async_batch_generate завершён, тип results: {type(results)}")
        logger.debug(f"[ASYNC_GENERATE_SINGLE] Результаты: {results}")
        if results and len(results) > 0:
            logger.debug(f"[ASYNC_GENERATE_SINGLE] Длина результата: {len(results[0])}")
            result = results[0]
            logger.debug(f"[ASYNC_GENERATE_SINGLE] Возврат результата, длина: {len(result)}")
            return result
        else:
            logger.warning(f"[ASYNC_GENERATE_SINGLE] Пустой результат или None")
            return ""
    except Exception as e:
        logger.error(f"[ASYNC_GENERATE_SINGLE] Ошибка: {e}", exc_info=True)
        return ""


async def async_generate_stream(text: str, max_new_tokens: int = 4096, temperature: float = 0.2) -> AsyncGenerator[str, None]:
    """
    Асинхронная генерация ответа с настоящим стримингом токенов.
    
    Args:
        text: Текст для генерации
        max_new_tokens: Максимальное количество новых токенов
        temperature: Температура генерации
        
    Yields:
        Токены по мере их генерации
    """
    def sync_stream():
        """Синхронная функция стриминга, выполняемая в отдельном потоке."""
        try:
            # Токенизируем входной текст
            inputs = app_state.tokenizer(text, return_tensors="pt").to(app_state.model.device)
            
            # Генерируем с использованием stream=True
            from transformers import TextIteratorStreamer
            streamer = TextIteratorStreamer(
                app_state.tokenizer,
                skip_prompt=True,
                skip_special_tokens=True
            )
            
            # Запускаем генерацию в отдельном потоке
            import threading
            generation_kwargs = {
                "input_ids": inputs.input_ids,
                "attention_mask": inputs.attention_mask,
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "do_sample": True,
                "pad_token_id": app_state.tokenizer.eos_token_id,
                "streamer": streamer
            }
            
            def generate_in_thread():
                app_state.model.generate(**generation_kwargs)
            
            thread = threading.Thread(target=generate_in_thread)
            thread.start()
            
            # Читаем токены из стримера
            for new_text in streamer:
                if new_text:
                    # Удаляем служебные теги
                    import re
                    cleaned_text = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', new_text, flags=re.DOTALL)
                    if cleaned_text.strip():
                        yield cleaned_text
            
            thread.join()
        except Exception as e:
            logger.error(f"[ASYNC_STREAM] Ошибка в sync_stream: {e}", exc_info=True)
            yield ""
    
    try:
        # Создаем очередь для передачи токенов из синхронного кода в асинхронный
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        
        def stream_producer():
            """Продюсер, который помещает токены в очередь."""
            try:
                for token in sync_stream():
                    # Используем asyncio.run_coroutine_threadsafe для помещения в очередь
                    asyncio.run_coroutine_threadsafe(queue.put(token), loop)
                # Сигнал завершения
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            except Exception as e:
                logger.error(f"[ASYNC_STREAM] Ошибка в stream_producer: {e}", exc_info=True)
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
        
        # Запускаем продюсера в отдельном потоке
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = loop.run_in_executor(executor, stream_producer)
            
            # Читаем токены из очереди
            while True:
                token = await queue.get()
                if token is None:
                    break
                yield token
    except Exception as e:
        logger.error(f"[ASYNC_STREAM] Ошибка: {e}", exc_info=True)
        yield ""


class AsyncLLMGenerator:
    """
    Класс для управления асинхронной генерацией LLM.
    Позволяет отслеживать активные запросы и управлять ими.
    """
    
    def __init__(self, max_concurrent: int = 5):
        """
        Инициализация генератора.
        
        Args:
            max_concurrent: Максимальное количество одновременных запросов
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = {}
        self.request_counter = 0
        
    async def generate(self, text: str, session_id: Optional[str] = None, 
                      max_new_tokens: int = 4096, temperature: float = 0.2) -> str:
        """
        Генерация ответа с ограничением количества одновременных запросов.
        
        Args:
            text: Текст для генерации
            session_id: ID сессии для логирования
            max_new_tokens: Максимальное количество новых токенов
            temperature: Температура генерации
            
        Returns:
            Сгенерированный текст
        """
        self.request_counter += 1
        request_id = f"req_{self.request_counter}"
        
        async with self.semaphore:
            self.active_requests[request_id] = {
                "session_id": session_id,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "start_time": asyncio.get_event_loop().time()
            }
            
            logger.info(f"[ASYNC_LLM] Запрос {request_id} (session={session_id}) начат. "
                       f"Активных запросов: {len(self.active_requests)}")
            
            try:
                logger.info(f"[ASYNC_LLM] Запрос {request_id}: вызов async_generate_single...")
                result = await async_generate_single(text, max_new_tokens, temperature)
                logger.info(f"[ASYNC_LLM] Запрос {request_id}: async_generate_single завершён, длина результата: {len(result)}")
                if not result:
                    logger.warning(f"[ASYNC_LLM] Запрос {request_id} вернул пустой результат!")
                return result
            except Exception as e:
                logger.error(f"[ASYNC_LLM] Ошибка при генерации запроса {request_id}: {e}", exc_info=True)
                return ""
            finally:
                duration = asyncio.get_event_loop().time() - self.active_requests[request_id]["start_time"]
                logger.info(f"[ASYNC_LLM] Запрос {request_id} завершен за {duration:.2f}с. "
                           f"Активных запросов: {len(self.active_requests) - 1}")
                del self.active_requests[request_id]
    
    async def generate_batch(self, texts: List[str], session_id: Optional[str] = None,
                           max_new_tokens: int = 4096, temperature: float = 0.2) -> List[str]:
        """
        Генерация ответов для батча текстов.
        
        Args:
            texts: Список текстов для генерации
            session_id: ID сессии для логирования
            max_new_tokens: Максимальное количество новых токенов
            temperature: Температура генерации
            
        Returns:
            Список сгенерированных текстов
        """
        self.request_counter += 1
        request_id = f"batch_{self.request_counter}"
        
        async with self.semaphore:
            self.active_requests[request_id] = {
                "session_id": session_id,
                "batch_size": len(texts),
                "start_time": asyncio.get_event_loop().time()
            }
            
            logger.info(f"[ASYNC_LLM] Батч {request_id} (session={session_id}, size={len(texts)}) начат. "
                       f"Активных запросов: {len(self.active_requests)}")
            
            try:
                results = await async_batch_generate(texts, max_new_tokens, temperature)
                return results
            finally:
                duration = asyncio.get_event_loop().time() - self.active_requests[request_id]["start_time"]
                logger.info(f"[ASYNC_LLM] Батч {request_id} завершен за {duration:.2f}с. "
                           f"Активных запросов: {len(self.active_requests) - 1}")
                del self.active_requests[request_id]
    
    async def generate_stream(self, text: str, session_id: Optional[str] = None,
                            max_new_tokens: int = 4096, temperature: float = 0.2) -> AsyncGenerator[str, None]:
        """
        Генерация ответа с настоящим стримингом токенов.
        
        Args:
            text: Текст для генерации
            session_id: ID сессии для логирования
            max_new_tokens: Максимальное количество новых токенов
            temperature: Температура генерации
            
        Yields:
            Токены по мере их генерации
        """
        self.request_counter += 1
        request_id = f"stream_{self.request_counter}"
        
        async with self.semaphore:
            self.active_requests[request_id] = {
                "session_id": session_id,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "start_time": asyncio.get_event_loop().time()
            }
            
            logger.info(f"[ASYNC_LLM] Стриминг {request_id} (session={session_id}) начат. "
                       f"Активных запросов: {len(self.active_requests)}")
            
            try:
                async for token in async_generate_stream(text, max_new_tokens, temperature):
                    yield token
            finally:
                duration = asyncio.get_event_loop().time() - self.active_requests[request_id]["start_time"]
                logger.info(f"[ASYNC_LLM] Стриминг {request_id} завершен за {duration:.2f}с. "
                           f"Активных запросов: {len(self.active_requests) - 1}")
                del self.active_requests[request_id]
    
    def get_active_requests(self) -> dict:
        """Возвращает информацию об активных запросах."""
        return self.active_requests.copy()


# Глобальный экземпляр генератора
_llm_generator = None


def get_llm_generator(max_concurrent: int = 5) -> AsyncLLMGenerator:
    """
    Возвращает глобальный экземпляр асинхронного генератора LLM.
    
    Args:
        max_concurrent: Максимальное количество одновременных запросов
        
    Returns:
        Экземпляр AsyncLLMGenerator
    """
    global _llm_generator
    if _llm_generator is None:
        _llm_generator = AsyncLLMGenerator(max_concurrent)
    return _llm_generator
