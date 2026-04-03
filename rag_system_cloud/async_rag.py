# async_rag.py
"""
Асинхронная версия RAG-системы для параллельной обработки запросов.
"""
import json
import logging
import asyncio
from typing import Generator, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

import app_state
import session as session_mgr
import retrieval as retrieval
import response_processing as response_processing
import db
from config import ALLOWED_SUBDIVISIONS
from async_generator import get_llm_generator
import prompts

logger = logging.getLogger(__name__)


async def async_get_chat_response(question: str, session_id: str = None) -> AsyncGenerator[str, None]:
    """
    Асинхронный режим чата с использованием истории и всех документов.
    Использует настоящий стриминг токенов от LLM.
    """
    try:
        logger.info(f"[ASYNC_CHAT] Вопрос: {question}")
        session_id_local = session_mgr.get_or_create_session(session_id)
        history = session_mgr.get_session_history(session_id_local)
        # Используем меньше сообщений для контекста для ускорения
        formatted_history = session_mgr.format_history_for_prompt(history, max_messages=4)

        # Поиск документов (выполняется асинхронно)
        docs = []
        if app_state.retriever_all_docs:
            docs.extend(retrieval.enhanced_retriever(app_state.retriever_all_docs, question))
        else:
            if app_state.retriever_work_plan:
                docs.extend(retrieval.enhanced_retriever(app_state.retriever_work_plan, question))
            if app_state.retriever_subdivisions and len(docs) < 3:
                docs.extend(retrieval.enhanced_retriever(app_state.retriever_subdivisions, question))
            if app_state.retriever_technic and len(docs) < 3:
                docs.extend(retrieval.enhanced_retriever(app_state.retriever_technic, question))

        context = retrieval.format_docs(docs[:3])

        # Используем промт из prompts.py
        prompt = prompts.get_chat_prompt(context, formatted_history, question)

        logger.debug(f"[ASYNC_CHAT] Промпт (первые 1000 символов): {prompt[:1000]}...")

        if app_state.model:
            llm_gen = get_llm_generator()
            full_response = ""
            
            # Используем настоящий стриминг токенов
            async for token in llm_gen.generate_stream(prompt, session_id=session_id_local, max_new_tokens=4096, temperature=0.3):
                if token:
                    full_response += token
                    yield token
            
            # Сохраняем в историю только после завершения генерации
            if full_response:
                session_mgr.add_message_to_session(session_id_local, "user", question)
                session_mgr.add_message_to_session(session_id_local, "assistant", full_response)
        else:
            yield "Модель не загружена. Попробуйте позже."
    except Exception as e:
        logger.error(f"[ASYNC_CHAT] Ошибка: {e}", exc_info=True)
        yield f"Произошла ошибка: {str(e)}"


async def _async_parallel_retrieve_docs(question: str, subdivisions: list = None, technics: list = None) -> dict:
    """
    Асинхронно выполняет поиск документов по всем векторным БД.
    """
    results = {
        "subdivisions": {"docs": [], "context": "", "sources": []},
        "technic": {"docs": [], "context": "", "sources": []},
        "employees": {"docs": [], "context": "", "sources": []},
        "work_plan": {"docs": [], "context": "", "sources": []},
        "subdivisions_examples": {"docs": [], "context": ""}
    }

    def retrieve_subdivisions():
        if app_state.retriever_subdivisions:
            search_query = f"{question}"
            docs = retrieval.enhanced_retriever(app_state.retriever_subdivisions, search_query)
            context, sources = retrieval.format_docs_with_sources(docs)
            return {"docs": docs, "context": context, "sources": sources}
        return {"docs": [], "context": "", "sources": []}
    
    def retrieve_technic():
        if app_state.retriever_technic:
            search_query = f"{'; '.join(subdivisions) if subdivisions else ''} {question}"
            docs = retrieval.enhanced_retriever(app_state.retriever_technic, search_query)
            context, sources = retrieval.format_docs_with_sources(docs)
            return {"docs": docs, "context": context, "sources": sources}
        return {"docs": [], "context": "", "sources": []}
    
    def retrieve_employees():
        if app_state.retriever_employees:
            search_query = f"{'; '.join(subdivisions) if subdivisions else ''} {'; '.join(technics) if technics else ''} {question}"
            # Убрали фильтрацию по подразделению, чтобы получить все релевантные документы
            # Фильтрация может привести к потере документов, если подразделение не найдено в метаданных
            docs = retrieval.enhanced_retriever(app_state.retriever_employees, search_query)
            context, sources = retrieval.format_docs_with_sources(docs)
            return {"docs": docs, "context": context, "sources": sources}
        return {"docs": [], "context": "", "sources": []}
    
    def retrieve_work_plan():
        if app_state.retriever_work_plan:
            search_query = f"{'; '.join(subdivisions) if subdivisions else ''} {'; '.join(technics) if technics else ''} {question}"
            docs = retrieval.enhanced_retriever(app_state.retriever_work_plan, search_query)
            context, sources = retrieval.format_docs_with_sources(docs)
            return {"docs": docs, "context": context, "sources": sources}
        return {"docs": [], "context": "", "sources": []}
    
    def retrieve_subdivisions_examples():
        if app_state.retriever_subdivisions_examples:
            docs = app_state.retriever_subdivisions_examples.invoke(question)
            context = retrieval.format_subdivisions_examples_for_prompt(docs) if docs else "Похожие примеры не найдены."
            return {"docs": docs, "context": context}
        return {"docs": [], "context": "База примеров подразделений не загружена."}
    
    # Асинхронное выполнение всех операций поиска
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            "subdivisions": loop.run_in_executor(executor, retrieve_subdivisions),
            "technic": loop.run_in_executor(executor, retrieve_technic),
            "employees": loop.run_in_executor(executor, retrieve_employees),
            "work_plan": loop.run_in_executor(executor, retrieve_work_plan),
            "subdivisions_examples": loop.run_in_executor(executor, retrieve_subdivisions_examples)
        }
        
        for key, future in futures.items():
            try:
                result = await future
                results[key] = result
            except Exception as e:
                logger.error(f"[ASYNC_PARALLEL] Ошибка при поиске {key}: {e}")
    
    return results


async def async_get_rag_response_with_session(question: str, session_id: str = None) -> str:
    """
    Асинхронная версия основной функции режима "план".
    Выполняет четырёхступенчатый анализ параллельно с другими запросами.
    """
    try:
        logger.info(f"[ASYNC_MAIN] Запрос: {question}")
        session_id_local = session_mgr.get_or_create_session(session_id)
        history = session_mgr.get_session_history(session_id_local)
        # Используем меньше сообщений для контекста для ускорения
        formatted_history = session_mgr.format_history_for_prompt(history, max_messages=4)

        # Детекция намерения правки
        is_edit, edit_type = session_mgr.is_edit_request(question)
        logger.info(f"[ASYNC_MAIN] Детекция правки: is_edit={is_edit}, edit_type={edit_type}")

        prev_subdiv = session_mgr.get_last_subdivisions(session_id_local)
        prev_technics = session_mgr.get_last_technics(session_id_local)
        prev_employees = session_mgr.get_last_employees(session_id_local)
        prev_work_plan = session_mgr.get_last_work_plan(session_id_local)

        prev_subdiv_str = ";".join(sorted(prev_subdiv)) if prev_subdiv else ""
        prev_technics_str = ";".join(sorted(prev_technics)) if prev_technics else ""
        prev_employees_str = ";".join(sorted(prev_employees)) if prev_employees else ""
        prev_work_plan_str = prev_work_plan if prev_work_plan else ""

        final = {
            "status": "success",
            "subdivisions": {"list": [], "analysis": "", "sources": []},
            "technics": {"list": [], "analysis": "", "sources": []},
            "employees": {"list": [], "analysis": "", "sources": []},
            "work_plan": {"plan": "", "analysis": "", "sources": []},
            "session_id": session_id_local
        }

        # Подготовка общего контекста
        examples_text = retrieval.format_examples_for_prompt(app_state.accidents_examples, limit=5)
        allowed_subdivisions_str = "\n".join([f"{k} - {v}" for k, v in ALLOWED_SUBDIVISIONS.items()])

        llm_gen = get_llm_generator()

        # --- Шаг 1: Подразделения ---
        logger.info("[ASYNC_MAIN] Шаг 1: подразделения")
        if not app_state.retriever_subdivisions:
            final["status"] = "partial_success"
            final["subdivisions"]["analysis"] = "Векторная БД для подразделений не инициализирована"
        else:
            step1_results = await _async_parallel_retrieve_docs(question)
            context_subdivisions = step1_results["subdivisions"]["context"]
            sources_subdivisions = step1_results["subdivisions"]["sources"]
            subdivisions_examples_context = step1_results["subdivisions_examples"]["context"]

            # Используем промт из prompts.py
            prompt_sub = prompts.get_subdivisions_prompt(
                context_users=context_subdivisions,
                examples_text=examples_text,
                subdivisions_examples_context=subdivisions_examples_context,
                formatted_history=formatted_history,
                prev_subdiv_str=prev_subdiv_str,
                question=question,
                allowed_subdivisions_str=allowed_subdivisions_str,
                is_edit=is_edit,
                edit_type=edit_type
            )
            
            resp_sub = await llm_gen.generate(prompt_sub, session_id=session_id_local, max_new_tokens=512, temperature=0.2)
            logger.info(f"[ASYNC_MAIN] Ответ модели (подразделения): {resp_sub[:500]}")
            sub_data = response_processing.process_model_response(resp_sub, question, sources_subdivisions, session_id_local)

            logger.info(f"[ASYNC_MAIN] Шаг 1 результат: {sub_data}")
            final["subdivisions"]["list"] = sub_data.get("subdivisions", [])
            final["subdivisions"]["analysis"] = sub_data.get("analysis", "")
            final["subdivisions"]["sources"] = sub_data.get("sources", [])
            if sub_data.get("status") != "success":
                final["status"] = "partial_success"

        # --- Шаг 2: Техника ---
        logger.info("[ASYNC_MAIN] Шаг 2: техника")
        if not app_state.retriever_technic:
            final["status"] = "partial_success"
            final["technics"]["analysis"] = "Векторная БД для техники не инициализирована"
        else:
            subdivisions = final["subdivisions"]["list"]
            step2_results = await _async_parallel_retrieve_docs(question, subdivisions=subdivisions)
            context_tech = step2_results["technic"]["context"]
            sources_tech = step2_results["technic"]["sources"]
            subdivisions_str = "; ".join(subdivisions)
            
            # Используем промт из prompts.py
            prompt_tech = prompts.get_technics_prompt(
                context_tech=context_tech,
                examples_text=examples_text,
                formatted_history=formatted_history,
                prev_technics_str=prev_technics_str,
                question=question,
                subdivisions_str=subdivisions_str,
                is_edit=is_edit,
                edit_type=edit_type
            )
            
            resp_tech = await llm_gen.generate(prompt_tech, session_id=session_id_local, max_new_tokens=512, temperature=0.2)
            logger.info(f"[ASYNC_MAIN] Ответ модели (техника): {resp_tech[:1000]}")
            technics = response_processing.extract_technics_from_model_response(resp_tech)
            logger.info(f"[ASYNC_MAIN] Извлечённая техника: {technics}")
            final["technics"]["list"] = technics
            final["technics"]["sources"] = sources_tech
            if not technics:
                final["technics"]["analysis"] = "Техника не требуется или не найдена."
            final["technics"]["status"] = "success"

        # --- Шаг 3: Сотрудники ---
        logger.info("[ASYNC_MAIN] Шаг 3: сотрудники")
        if not app_state.retriever_employees:
            final["status"] = "partial_success"
            final["employees"]["analysis"] = "Векторная БД для сотрудников не инициализирована"
        else:
            subdivisions = final["subdivisions"]["list"]
            technics = final["technics"]["list"]
            step3_results = await _async_parallel_retrieve_docs(question, subdivisions=subdivisions, technics=technics)
            context_emp = step3_results["employees"]["context"]
            sources_emp = step3_results["employees"]["sources"]
            subdivisions_str = "; ".join(subdivisions)
            technics_str = "; ".join(technics)
            
            # Используем промт из prompts.py
            prompt_emp = prompts.get_employees_prompt(
                context_emp=context_emp,
                examples_text=examples_text,
                formatted_history=formatted_history,
                prev_employees_str=prev_employees_str,
                question=question,
                subdivisions_str=subdivisions_str,
                technics_str=technics_str,
                is_edit=is_edit,
                edit_type=edit_type
            )
            
            logger.info(f"[ASYNC_MAIN] Длина промта для сотрудников: {len(prompt_emp)} символов")
            logger.debug(f"[ASYNC_MAIN] Промт для сотрудников (первые 500 символов): {prompt_emp[:500]}")
            
            logger.info(f"[ASYNC_MAIN] Начало генерации ответа для сотрудников...")
            resp_emp = await llm_gen.generate(prompt_emp, session_id=session_id_local, max_new_tokens=512, temperature=0.2)
            logger.info(f"[ASYNC_MAIN] Ответ модели (сотрудники) получен, длина: {len(resp_emp)}")
            logger.info(f"[ASYNC_MAIN] Ответ модели (сотрудники): {resp_emp[:1000]}")
            
            logger.info(f"[ASYNC_MAIN] Начало извлечения сотрудников из ответа модели...")
            employees = response_processing.extract_employees_from_model_response(resp_emp)
            logger.info(f"[ASYNC_MAIN] Извлечённые сотрудники: {employees}")
            
            final["employees"]["list"] = employees
            final["employees"]["sources"] = sources_emp
            if not employees:
                final["employees"]["analysis"] = "Сотрудники не требуются или не найдены."
            final["employees"]["status"] = "success"
            logger.info(f"[ASYNC_MAIN] Шаг 3 (сотрудники) завершён успешно")

        # --- Шаг 4: План работ ---
        logger.info("[ASYNC_MAIN] Шаг 4: план работ")
        if not app_state.retriever_work_plan:
            final["status"] = "partial_success"
            final["work_plan"]["analysis"] = "Векторная БД для планов работ не инициализирована"
        else:
            subdivisions = final["subdivisions"]["list"]
            technics = final["technics"]["list"]
            employees = final["employees"]["list"]
            step4_results = await _async_parallel_retrieve_docs(question, subdivisions=subdivisions, technics=technics)
            context_plan = step4_results["work_plan"]["context"]
            sources_plan = step4_results["work_plan"]["sources"]
            subdivisions_str = "; ".join(final["subdivisions"]["list"])
            technics_str = "; ".join(final["technics"]["list"])
            employees_str = "; ".join(final["employees"]["list"])

            # Используем промт из prompts.py
            prompt_plan = prompts.get_work_plan_prompt(
                context_plan=context_plan,
                examples_text=examples_text,
                formatted_history=formatted_history,
                prev_work_plan_str=prev_work_plan_str,
                question=question,
                subdivisions_str=subdivisions_str,
                technics_str=technics_str,
                employees_str=employees_str,
                is_edit=is_edit,
                edit_type=edit_type
            )
            
            logger.info(f"[ASYNC_MAIN] Начало генерации ответа для плана работ...")
            resp_plan = await llm_gen.generate(prompt_plan, session_id=session_id_local, max_new_tokens=1024, temperature=0.2)
            logger.info(f"[ASYNC_MAIN] Ответ модели (план работ) получен, длина: {len(resp_plan)}")
            logger.info(f"[ASYNC_MAIN] Ответ модели (план работ): {resp_plan[:2000]}")
            
            logger.info(f"[ASYNC_MAIN] Начало извлечения плана работ из ответа модели...")
            work_plan = response_processing.extract_work_plan_from_model_response(resp_plan)
            logger.info(f"[ASYNC_MAIN] План работ извлечён, длина: {len(work_plan)}")
            
            # Валидация плана работ
            validated_plan, warnings = response_processing.validate_work_plan(
                work_plan,
                final["subdivisions"]["list"],
                final["technics"]["list"],
                final["employees"]["list"]
            )
            
            if warnings:
                logger.warning(f"[ASYNC_MAIN] Предупреждения при валидации плана: {warnings}")
            
            final["work_plan"]["plan"] = validated_plan
            final["work_plan"]["sources"] = sources_plan
            if not validated_plan:
                final["work_plan"]["analysis"] = "Не удалось сформировать план."
            else:
                final["work_plan"]["analysis"] = "План сформирован и валидирован."
            final["work_plan"]["status"] = "success"

        # --- Обрезка источников до топ-3 ---
        final["subdivisions"]["sources"] = final["subdivisions"]["sources"][:1]
        final["technics"]["sources"] = final["technics"]["sources"][:1]
        final["employees"]["sources"] = final["employees"]["sources"][:1]
        final["work_plan"]["sources"] = final["work_plan"]["sources"][:1]

        # --- Сохранение в БД PostgreSQL ---
        conn = db.get_pg_connection()
        if conn:
            try:
                # Откатываем любую незавершенную транзакцию и сбрасываем состояние
                try:
                    conn.rollback()
                except:
                    pass
                
                # Проверяем, что соединение не в режиме только для чтения
                cur = conn.cursor()
                cur.execute("SHOW transaction_read_only")
                read_only = cur.fetchone()[0]
                
                if read_only == 'on':
                    logger.warning("Соединение в режиме только для чтения, переподключаемся к мастеру...")
                    cur.close()
                    db.return_pg_connection(conn)
                    
                    # Переинициализируем пул с мастером
                    try:
                        db.init_pg_pool()
                        conn = db.get_pg_connection()
                        if not conn:
                            logger.error("Не удалось переподключиться к мастеру")
                        else:
                            cur = conn.cursor()
                            # Повторно проверяем режим только для чтения
                            cur.execute("SHOW transaction_read_only")
                            read_only = cur.fetchone()[0]
                            if read_only == 'on':
                                logger.error("После переподключения хост всё ещё в режиме read-only!")
                                cur.close()
                                db.return_pg_connection(conn)
                                conn = None
                    except Exception as e:
                        logger.error(f"Ошибка переподключения: {e}")
                        conn = None
                
                if conn:
                    if final["subdivisions"]["list"]:
                        cur.execute(
                            """INSERT INTO knowledge_base (question, answer, category)
                               VALUES (%s, %s, %s)
                               ON CONFLICT (question, category) DO UPDATE
                               SET answer = %s, usage_count = knowledge_base.usage_count + 1""",
                            [question, "; ".join(final["subdivisions"]["list"]), 'subdivisions', "; ".join(final["subdivisions"]["list"])]
                        )
                    if final["technics"]["list"]:
                        cur.execute(
                            """INSERT INTO knowledge_base (question, answer, category)
                               VALUES (%s, %s, %s)
                               ON CONFLICT (question, category) DO UPDATE
                               SET answer = %s, usage_count = knowledge_base.usage_count + 1""",
                            [question, "; ".join(final["technics"]["list"]), 'technics', "; ".join(final["technics"]["list"])]
                        )
                    if final["employees"]["list"]:
                        cur.execute(
                            """INSERT INTO knowledge_base (question, answer, category)
                               VALUES (%s, %s, %s)
                               ON CONFLICT (question, category) DO UPDATE
                               SET answer = %s, usage_count = knowledge_base.usage_count + 1""",
                            [question, "; ".join(final["employees"]["list"]), 'employees', "; ".join(final["employees"]["list"])]
                        )
                    if final["work_plan"]["plan"]:
                        cur.execute(
                            """INSERT INTO knowledge_base (question, answer, category)
                               VALUES (%s, %s, %s)
                               ON CONFLICT (question, category) DO UPDATE
                               SET answer = %s, usage_count = knowledge_base.usage_count + 1""",
                            [question, final["work_plan"]["plan"], 'work_plan', final["work_plan"]["plan"]]
                        )
                    conn.commit()
                    cur.close()
            except Exception as e:
                logger.error(f"Ошибка сохранения в knowledge_base: {e}")
                try:
                    conn.rollback()
                except:
                    pass
            finally:
                if conn:
                    db.return_pg_connection(conn)

        # Сохраняем сообщения в таблицу messages для отображения в чате
        # Сохраняем сообщение пользователя (неблокирующее)
        try:
            db.save_message_to_db(session_id_local, "user", question, "plan", [], [])
            logger.info(f"[ASYNC_MAIN] Сообщение пользователя сохранено в БД")
        except Exception as e:
            logger.error(f"[ASYNC_MAIN] Ошибка сохранения сообщения пользователя: {e}")
        
        # Формируем и сохраняем ответ бота
        answer_parts = []
        if final["technics"]["list"]:
            tech_list = "\n".join([f"- {t}" for t in final["technics"]["list"]])
            answer_parts.append(f"Необходимая техника:\n{tech_list}")
        if final["subdivisions"]["list"]:
            sub_list = "\n".join([f"- {s}" for s in final["subdivisions"]["list"]])
            answer_parts.append(f"Необходимые подразделения:\n{sub_list}")
        if final["employees"]["list"]:
            emp_list = "\n".join([f"- {e}" for e in final["employees"]["list"]])
            answer_parts.append(f"Необходимые сотрудники:\n{emp_list}")
        if final["work_plan"]["plan"]:
            answer_parts.append(f"План работ:\n{final['work_plan']['plan']}")
        
        bot_answer = "\n\n".join(answer_parts)
        
        # Собираем источники
        sources_list = []
        for source in final["subdivisions"]["sources"][:1]:
            sources_list.append({
                "document_id": source.get("document_id"),
                "source_file": source.get("source_file"),
                "content_preview": source.get("content_preview", "")[:200]
            })
        
        # Сохраняем ответ бота (неблокирующее)
        try:
            db.save_message_to_db(
                session_id_local,
                "bot",
                bot_answer,
                "plan",
                sources_list,
                final["employees"]["list"]
            )
            logger.info(f"[ASYNC_MAIN] Ответ бота сохранен в БД")
        except Exception as e:
            logger.error(f"[ASYNC_MAIN] Ошибка сохранения ответа бота: {e}")

        # Сохраняем сообщение пользователя
        session_mgr.add_message_to_session(session_id_local, "user", question)
        
        # Сохраняем ответ ассистента со структурированными данными
        hist_response = f"Подразделения: {'; '.join(final['subdivisions']['list'])}\nТехника: {'; '.join(final['technics']['list'])}\nСотрудники: {'; '.join(final['employees']['list'])}\nПлан работ: {final['work_plan']['plan'][:200]}..."
        structured_data = {
            "subdivisions": final['subdivisions']['list'],
            "technics": final['technics']['list'],
            "employees": final['employees']['list'],
            "work_plan": final['work_plan']['plan']
        }
        session_mgr.add_message_to_session(session_id_local, "assistant", hist_response, structured_data)

        logger.info(f"[ASYNC_MAIN] Формирование JSON ответа...")
        json_response = json.dumps(final, ensure_ascii=False, indent=2)
        logger.info(f"[ASYNC_MAIN] JSON ответ сформирован, длина: {len(json_response)}")
        return json_response

    except Exception as e:
        logger.error(f"[ASYNC_MAIN] Необработанная ошибка: {e}", exc_info=True)
        logger.error(f"[ASYNC_MAIN] Тип ошибки: {type(e).__name__}")
        error_resp = {
            "status": "error",
            "subdivisions": {"list": [], "analysis": f"Ошибка при обработке вопроса: {str(e)}", "sources": []},
            "technics": {"list": [], "analysis": "", "sources": []},
            "employees": {"list": [], "analysis": "", "sources": []},
            "work_plan": {"plan": "", "analysis": "", "sources": []},
            "session_id": session_id_local if 'session_id_local' in locals() else session_id
        }
        return json.dumps(error_resp, ensure_ascii=False, indent=2)
