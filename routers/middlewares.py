from typing import Callable, Dict, Any, Awaitable, List

import asyncpg
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from settings import settings


class CheckIsAdminMiddleware(BaseMiddleware):
    """Проверка является ли пользователь админом"""
    def __init__(self, env_admins: List[str]):
        self.admins = env_admins

    def is_admin(self, tg_id) -> bool:
        if str(tg_id) not in self.admins:
            return False
        return True

    async def __call__(self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]) -> Any:

        # проверяем является ли пользователь админом
        if self.is_admin(data["event_from_user"].id):
            return await handler(event, data)

        # ответ для обычных пользователей
        await event.answer(
            "Эта функция доступна только администраторам",
            show_alert=True
        )
        return


class CheckPrivateMessageMiddleware(BaseMiddleware):
    """Проверка сообщения в лс, а не группу"""
    async def __call__(self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]) -> Any:

        # проверяем является ли пользователь админом
        if data["event_chat"].type == "private":
            return await handler(event, data)
        return


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        conn = await asyncpg.connect(
            user=settings.db.postgres_user,
            host=settings.db.postgres_host,
            password=settings.db.postgres_password,
            port=settings.db.postgres_port,
            database=settings.db.postgres_db
        )
        try:
            data["session"] = conn
            return await handler(event, data)
        finally:
            await conn.close()
