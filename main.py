import asyncio

import aiogram as io
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from routers import admin, users

from settings import settings


async def set_commands(bot: io.Bot):
    """Перечень команд для бота"""
    commands = [
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="help", description="Инструкция и поддержка"),
    ]

    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def set_description(bot: io.Bot):
    """Описание бота до запуска"""
    await bot.set_my_description("Бот предоставляет функционал управления подписками\n\nДля запуска нажмите /start")


async def start_bot() -> None:
    """Запуск бота"""
    bot = io.Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # await set_commands(bot)
    # await set_description(bot)

    storage = MemoryStorage()
    dispatcher = io.Dispatcher(storage=storage)

    dispatcher.include_routers(admin.router, users.router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    # database.create_db()
    asyncio.run(start_bot())
