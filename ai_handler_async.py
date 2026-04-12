import asyncio
import logging

try:
    # Reuse existing synchronous implementation to avoid duplication
    from ai_handler import ask_ai as ask_ai_sync
except Exception as e:
    ask_ai_sync = None
    logging.getLogger(__name__).warning("Не удалось импортировать sync ai_handler: %s", e)


async def ask_ai_async(user_question: str) -> str:
    """
    Async wrapper that runs the existing synchronous `ask_ai` in a threadpool.
    Use this as a drop-in async replacement while keeping legacy `ai_handler.py`.
    """
    if ask_ai_sync is None:
        return "AI недоступен (импорт failed)."
    return await asyncio.to_thread(ask_ai_sync, user_question)
