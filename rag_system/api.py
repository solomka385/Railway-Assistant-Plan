# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from contextlib import asynccontextmanager
import json
import os
import sys
import re
import asyncio
from typing import Optional, Dict, List

from config import (
    DOCS_FOLDER_SUBDIVISIONS, DOCS_FOLDER_TECHNIC,
    DOCS_FOLDER_WORK_PLAN, DOCS_FOLDER_ALL_DOCS,
    DOCS_FOLDER_EMPLOYEES
)

import app_state
import logging
logging.basicConfig(level=logging.DEBUG, force=True)
if not app_state.init_system():
    print("Критическая ошибка инициализации системы. Завершение.")
    sys.exit(1)

import async_rag
from ingestion import reindex_documents
from app_state import get_system_status
from task_queue import get_task_queue, init_task_queue, shutdown_task_queue
import marts_db
from db import init_pg_pool
from async_generator import get_llm_generator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    await init_task_queue()
    if not init_pg_pool():
        logger.error("Не удалось инициализировать пул соединений PostgreSQL")
    logger.info("API запущен, очередь задач инициализирована")
    yield
    # Shutdown
    await shutdown_task_queue()
    logger.info("API остановлен, очередь задач очищена")


app = FastAPI(
    title="RAG Railway API",
    description="API для анализа железнодорожных аварий с поддержкой двух режимов работы",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Вопрос пользователя")
    session_id: Optional[str] = Field(None, pattern=r'^[a-f0-9-]{36}$', description="UUID сессии")
    mode: str = Field("chat", pattern=r'^(chat|plan)$', description="Режим работы: chat или plan")
    
    @field_validator('question')
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        """Проверка на потенциальные инъекции и очистка вопроса."""
        dangerous_patterns = [
            '<script',
            'javascript:',
            'onerror=',
            'onload=',
            'onclick=',
            'onmouseover=',
            'onfocus=',
            'onblur=',
            'eval(',
            'document.cookie',
            'window.location',
            'alert('
        ]
        question_lower = v.lower()
        if any(pattern in question_lower for pattern in dangerous_patterns):
            raise ValueError('Вопрос содержит недопустимые символы или паттерны')
        return v.strip()

class QueryResponse(BaseModel):
    answer: str
    session_id: Optional[str] = None
    status: str = "success"
    subdivisions: Optional[dict] = None
    technics: Optional[dict] = None
    employees: Optional[dict] = None
    work_plan: Optional[dict] = None
    mode: str = "chat"

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    vector_db_ready: bool
    gpu_available: bool
    examples_loaded: bool

class ReindexResponse(BaseModel):
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

class TaskListResponse(BaseModel):
    tasks: Dict[str, TaskStatusResponse]
    queue_size: int
    running_count: int

class GeoTag(BaseModel):
    lat: float
    lon: float

class MartsDataRequest(BaseModel):
    geo_tags: List[GeoTag]
    subdivisions: Optional[List[str]] = None
    positions: Optional[List[str]] = None
    equipment: Optional[List[str]] = None

class MartsDataResponse(BaseModel):
    status: str
    stations: List[Dict]
    equipment: Dict[str, List[Dict]]
    staff: Dict[str, List[Dict]]
    responsibles: Dict[str, List[Dict]]

def safe_json_dumps(obj, **kwargs):
    """Безопасная сериализация JSON с обработкой некорректных символов."""
    def default(o):
        if isinstance(o, (str,)):
            # Заменяем некорректные escape-последовательности
            return o.replace('\\', '\\\\')
        return str(o)
    
    try:
        return json.dumps(obj, default=default, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка сериализации JSON: {e}")
        # В случае ошибки возвращаем упрощенный JSON
        return json.dumps({"error": "JSON serialization error", "type": "error"})


def normalize_response_structure(response_data, mode="plan"):
    """Нормализует структуру ответа от RAG-модели к единому формату."""
    if mode == "chat":
        return {
            "status": "success",
            "session_id": response_data.get("session_id", ""),
            "mode": mode,
            "subdivisions": {"list": [], "analysis": "", "sources": []},
            "technics": {"list": [], "analysis": "", "sources": []},
            "employees": {"list": [], "analysis": "", "sources": []},
            "work_plan": {"plan": "", "analysis": "", "sources": []}
        }
    
    normalized = {
        "status": response_data.get("status", "error"),
        "session_id": response_data.get("session_id", ""),
        "mode": mode,
        "subdivisions": response_data.get("subdivisions", {"list": [], "analysis": "", "sources": []}),
        "technics": response_data.get("technics", {"list": [], "analysis": "", "sources": []}),
        "employees": response_data.get("employees", {"list": [], "analysis": "", "sources": []}),
        "work_plan": response_data.get("work_plan", {"plan": "", "analysis": "", "sources": []})
    }
    
    # Преобразование, если данные пришли в старом формате
    if isinstance(normalized["subdivisions"], list):
        normalized["subdivisions"] = {"list": normalized["subdivisions"], "analysis": "", "sources": []}
    if isinstance(normalized["technics"], list):
        normalized["technics"] = {"list": normalized["technics"], "analysis": "", "sources": []}
    if isinstance(normalized["employees"], list):
        normalized["employees"] = {"list": normalized["employees"], "analysis": "", "sources": []}
    if isinstance(normalized["work_plan"], str):
        normalized["work_plan"] = {"plan": normalized["work_plan"], "analysis": "", "sources": []}
    
    if normalized["status"] == "error" and (normalized["subdivisions"]["list"] or normalized["technics"]["list"] or normalized["employees"]["list"] or normalized["work_plan"]["plan"]):
        normalized["status"] = "partial_success"
    
    return normalized

async def generate_streaming_response(question: str, session_id: str = None, mode: str = "chat"):
    """Асинхронная генерация потокового ответа с настоящим стримингом токенов."""
    try:
        logger.info(f"[ASYNC_STREAM] Начало обработки: question={question[:50]}..., session_id={session_id}, mode={mode}")
        
        if mode == "plan":
            # Для режима plan сначала получаем полный ответ (так как нужна структура)
            logger.info(f"[ASYNC_STREAM] Вызов async_get_rag_response_with_session...")
            raw_response = await async_rag.async_get_rag_response_with_session(question, session_id)
            logger.info(f"[ASYNC_STREAM] Получен raw_response длиной: {len(raw_response)}")
            response_data = json.loads(raw_response)
            logger.info(f"[ASYNC_STREAM] Response data: {json.dumps(response_data, ensure_ascii=False)}")
            normalized_data = normalize_response_structure(response_data, mode)
            logger.info(f"[ASYNC_STREAM] Normalized data: {json.dumps(normalized_data, ensure_ascii=False)}")
            
            answer_parts = []
            if normalized_data["status"] in ["success", "partial_success"]:
                # Сначала техника
                if normalized_data["technics"]["list"]:
                    tech_list = "\n".join([f"- {t}" for t in normalized_data["technics"]["list"]])
                    answer_parts.append(f"Необходимая техника:\n{tech_list}")
                # Затем подразделения
                if normalized_data["subdivisions"]["list"]:
                    sub_list = "\n".join([f"- {s}" for s in normalized_data["subdivisions"]["list"]])
                    answer_parts.append(f"Необходимые подразделения:\n{sub_list}")
                # Затем сотрудники
                if normalized_data["employees"]["list"]:
                    emp_list = "\n".join([f"- {e}" for e in normalized_data["employees"]["list"]])
                    answer_parts.append(f"Необходимые сотрудники:\n{emp_list}")
                # План работ
                if normalized_data["work_plan"]["plan"]:
                    answer_parts.append(f"План работ:\n{normalized_data['work_plan']['plan']}")
            else:
                error_message = normalized_data["subdivisions"]["analysis"] or "Произошла ошибка при обработке запроса"
                answer_parts.append(f"⚠️ {error_message}")
            
            if not isinstance(normalized_data["technics"].get("list"), list):
                normalized_data["technics"]["list"] = []
            if not isinstance(normalized_data["employees"].get("list"), list):
                normalized_data["employees"]["list"] = []
            full_answer = "\n\n".join(answer_parts)
            
            logger.info(f"[ASYNC_STREAM] Начало отправки ответа клиенту, длина: {len(full_answer)}")
            
            # Отправляем ответ по токенам (настоящий стриминг)
            for char in full_answer:
                yield f"data: {safe_json_dumps({'chunk': char, 'type': 'content'}, ensure_ascii=False)}\n\n"
            
            logger.info(f"[ASYNC_STREAM] Отправка текста завершена, отправка final_data")
            
            final_data = {
                'chunk': '',
                'type': 'complete',
                'session_id': normalized_data['session_id'],
                'status': normalized_data['status'],
                'subdivisions': normalized_data['subdivisions'],
                'technics': normalized_data['technics'],
                'employees': normalized_data['employees'],
                'work_plan': normalized_data['work_plan'],
                'sources': {
                    'subdivisions': normalized_data['subdivisions'].get('sources', []),
                    'technics': normalized_data['technics'].get('sources', []),
                    'employees': normalized_data['employees'].get('sources', []),
                    'work_plan': normalized_data['work_plan'].get('sources', [])
                }
            }
            yield f"data: {safe_json_dumps(final_data, ensure_ascii=False)}\n\n"
            logger.info(f"[ASYNC_STREAM] final_data отправлен")
        else:
            # Для режима chat используем настоящий стриминг токенов от LLM
            logger.info(f"[ASYNC_STREAM] Режим chat, начало стриминга токенов")
            response_generator = async_rag.async_get_chat_response(question, session_id)
            full_response = ""
            async for token in response_generator:
                full_response += token
                # Отправляем каждый токен сразу клиенту
                yield f"data: {safe_json_dumps({'chunk': token, 'type': 'content'}, ensure_ascii=False)}\n\n"
            
            logger.info(f"[ASYNC_STREAM] Стриминг токенов завершен, отправка final_data")
            
            final_data = {
                'chunk': '',
                'type': 'complete',
                'session_id': session_id,
                'status': 'success',
                'subdivisions': {"list": [], "analysis": "", "sources": []},
                'technics': {"list": [], "analysis": "", "sources": []},
                'employees': {"list": [], "analysis": "", "sources": []},
                'work_plan': {"plan": "", "analysis": "", "sources": []}
            }
            yield f"data: {safe_json_dumps(final_data, ensure_ascii=False)}\n\n"
            logger.info(f"[ASYNC_STREAM] final_data отправлен (chat mode)")
    except Exception as e:
        logger.error(f"[ASYNC_STREAM] Ошибка: {e}", exc_info=True)
        yield f"data: {json.dumps({'chunk': f'Ошибка: {str(e)}', 'type': 'error'})}\n\n"

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Асинхронный endpoint для обработки запросов."""
    logger.info(f"[ASYNC_API] Начало обработки запроса: {request.question}")
    try:
        logger.info(f"[ASYNC_API] Запрос: {request.question}, session_id: {request.session_id}, mode: {request.mode}")
        if request.mode == "chat":
            response_text = ""
            async for chunk in async_rag.async_get_chat_response(request.question, request.session_id):
                response_text += chunk
            return QueryResponse(
                answer=response_text,
                session_id=request.session_id,
                status="success",
                subdivisions={"list": [], "analysis": "", "sources": []},
                technics={"list": [], "analysis": "", "sources": []},
                employees={"list": [], "analysis": "", "sources": []},
                work_plan={"plan": "", "analysis": "", "sources": []},
                mode=request.mode
            )
        else:
            raw_response = await async_rag.async_get_rag_response_with_session(request.question, request.session_id)
            logger.info(f"[ASYNC_API] Сырой ответ: {raw_response[:500]}...")
            response_data = json.loads(raw_response)
            normalized_data = normalize_response_structure(response_data, request.mode)
            subdivisions = normalized_data["subdivisions"]
            technics = normalized_data["technics"]
            employees = normalized_data["employees"]
            work_plan = normalized_data["work_plan"]
            status = normalized_data["status"]
            session_id = normalized_data["session_id"]
            answer = ""
            if status in ["success", "partial_success"]:
                if request.mode == "plan":
                    if technics["list"]:
                        tech_list = "\n".join([f"- {t}" for t in technics["list"]])
                        answer += f"Необходимая техника:\n{tech_list}\n\n"
                    if subdivisions["list"]:
                        sub_list = "\n".join([f"- {s}" for s in subdivisions["list"]])
                        answer += f"Необходимые подразделения:\n{sub_list}\n\n"
                    if employees["list"]:
                        emp_list = "\n".join([f"- {e}" for e in employees["list"]])
                        answer += f"Необходимые сотрудники:\n{emp_list}\n\n"
                    if work_plan["plan"]:
                        answer += f"План работ:\n{work_plan['plan']}"
                else:
                    answer = response_data.get('answer', '')
            else:
                error_message = subdivisions["analysis"] or "Произошла ошибка при обработке запроса"
                answer = f"⚠️ {error_message}"
            return QueryResponse(
                answer=answer,
                session_id=session_id,
                status=status,
                subdivisions=subdivisions if request.mode == "plan" else {"list": [], "analysis": "", "sources": []},
                technics=technics if request.mode == "plan" else {"list": [], "analysis": "", "sources": []},
                employees=employees if request.mode == "plan" else {"list": [], "analysis": "", "sources": []},
                work_plan=work_plan if request.mode == "plan" else {"plan": "", "analysis": "", "sources": []},
                mode=request.mode
            )
    except json.JSONDecodeError as e:
        logger.error(f"[ASYNC_API] Ошибка парсинга JSON: {e}")
        return QueryResponse(answer="⚠️ Ошибка обработки ответа от модели.", status="error", mode=request.mode)
    except Exception as e:
        logger.error(f"[ASYNC_API] Необработанная ошибка: {e}")
        return QueryResponse(answer=f"⚠️ Внутренняя ошибка сервера: {str(e)}", status="error", mode=request.mode)

@app.post("/ask-stream")
async def ask_question_stream(request: QueryRequest):
    return StreamingResponse(
        generate_streaming_response(request.question, request.session_id, request.mode),
        media_type="text/plain"
    )

@app.get("/active-requests")
async def get_active_requests():
    """Возвращает информацию об активных запросах к LLM."""
    llm_gen = get_llm_generator()
    active = llm_gen.get_active_requests()
    return {
        "active_count": len(active),
        "max_concurrent": llm_gen.max_concurrent,
        "requests": active
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    status = app_state.get_system_status()
    return HealthResponse(
        status="OK",
        model_loaded=status["model_loaded"],
        vector_db_ready=status["vector_db_ready"],
        gpu_available=status["gpu_available"],
        examples_loaded=status.get("examples_loaded", False)
    )

@app.post("/reindex", response_model=ReindexResponse)
async def reindex_docs():
    """Запускает переиндексацию документов в фоновом режиме через очередь задач."""
    try:
        queue = get_task_queue()
        task_id = queue.add_task(reindex_documents)
        return ReindexResponse(
            status="success",
            message=f"Задача переиндексации добавлена в очередь. ID задачи: {task_id}"
        )
    except Exception as e:
        return ReindexResponse(status="error", message=f"Ошибка добавления задачи: {str(e)}")

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Возвращает статус задачи по её ID."""
    queue = get_task_queue()
    task_info = queue.get_task_status(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return TaskStatusResponse(**task_info)

@app.get("/tasks", response_model=TaskListResponse)
async def get_all_tasks():
    """Возвращает информацию о всех задачах."""
    queue = get_task_queue()
    tasks = queue.get_all_tasks()
    return TaskListResponse(
        tasks={tid: TaskStatusResponse(**tinfo) for tid, tinfo in tasks.items()},
        queue_size=queue.get_queue_size(),
        running_count=queue.get_running_count()
    )

@app.post("/marts-data", response_model=MartsDataResponse)
async def get_marts_data(request: MartsDataRequest):
    """
    Получает данные из витрин (equipment_mart, staff_mart, station_responsibles)
    на основе геометок и фильтров по подразделениям, должностям и технике.
    """
    try:
        # Преобразуем GeoTag в словари
        geo_tags_dict = [{"lat": tag.lat, "lon": tag.lon} for tag in request.geo_tags]
        
        # Получаем данные из витрин
        marts_data = marts_db.get_marts_data_by_geo(
            geo_tags=geo_tags_dict,
            subdivisions=request.subdivisions,
            positions=request.positions,
            equipment=request.equipment
        )
        
        return MartsDataResponse(
            status="success",
            stations=marts_data["stations"],
            equipment=marts_data["equipment"],
            staff=marts_data["staff"],
            responsibles=marts_data["responsibles"]
        )
    except Exception as e:
        logger.error(f"Ошибка при получении данных из витрин: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных из витрин: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "RAG Railway API v2.1 (Async)",
        "version": "2.1.0",
        "endpoints": {
            "POST /ask": "Задать вопрос с поддержкой сессий и режимов (асинхронно)",
            "POST /ask-stream": "Потоковый вопрос (асинхронно)",
            "GET /health": "Проверить статус системы",
            "GET /active-requests": "Получить информацию об активных запросах к LLM",
            "POST /reindex": "Переиндексировать документы (фоновая задача)",
            "GET /tasks": "Получить список всех задач",
            "GET /tasks/{task_id}": "Получить статус задачи по ID",
            "POST /marts-data": "Получить данные из витрин по геометкам"
        },
        "modes": {
            "plan": "Полный анализ с подразделениями, техникой, сотрудниками и планом работ",
            "chat": "Простой чат с использованием истории"
        },
        "parallel_processing": {
            "enabled": True,
            "max_concurrent_requests": 5,
            "description": "Система поддерживает параллельную обработку запросов от нескольких пользователей"
        }
    }

@app.get("/download/{filename}")
async def download_document(filename: str):
    safe_filename = os.path.basename(filename)
    for folder in [DOCS_FOLDER_SUBDIVISIONS, DOCS_FOLDER_TECHNIC, DOCS_FOLDER_WORK_PLAN, DOCS_FOLDER_ALL_DOCS, DOCS_FOLDER_EMPLOYEES]:
        file_path = os.path.join(folder, safe_filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(
                file_path,
                media_type='application/octet-stream',
                filename=safe_filename
            )
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")