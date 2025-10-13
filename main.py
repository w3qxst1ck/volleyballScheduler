import asyncio
from datetime import datetime

import aiogram as io
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.database import async_engine
from database.tables import Base
from routers import admin, users, apsched, add_tournament, tournaments, pay_tournament, admin_tournament, libero_registration
from routers.middlewares import AdminMiddleware

from settings import settings


async def set_commands(bot: io.Bot):
    """Перечень команд для бота"""
    commands = [
        BotCommand(command="menu", description="👨🏻‍💻 Главное меню"),
        BotCommand(command="players", description="👥 Игроки"),
        BotCommand(command="help", description="❓ Инструкция и поддержка"),
        BotCommand(command="add_event", description="📌 Добавить событие"),
        BotCommand(command="add_tournament", description="🏆 Добавить турнир"),
        BotCommand(command="events", description="⚙️ Управление событиями"),
        BotCommand(command="levels", description="🏅 Присвоить уровень"),
    ]

    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def set_description(bot: io.Bot):
    """Описание бота до запуска"""
    await bot.set_my_description("🏐 Бот предоставляет функционал записи на волейбольные мероприятия\n\n"
                                 "Для запуска нажмите \"Начать\"")


async def start_bot() -> None:
    """Запуск бота"""
    bot = io.Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_commands(bot)
    await set_description(bot)

    storage = MemoryStorage()
    dispatcher = io.Dispatcher(storage=storage)

    # # SCHEDULER
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # оповещение для пользователей + удаление старых неактивных событий 9 утра
    scheduler.add_job(apsched.run_every_day, trigger="cron", year='*', month='*', day="*", hour=9, minute=0,
                      second=0, start_date=datetime.now(), kwargs={"bot": bot})
    # удаление команд не оплативших турнир за 4 дня в 4 утра
    scheduler.add_job(apsched.kick_from_tournaments_by_payments, trigger="cron", year='*', month='*', day="*", hour=4,
                      minute=0, second=0, start_date=datetime.now(), kwargs={"bot": bot})
    # проверка мероприятия на минимальное кол-во участников + перевод событий в неактивные в 01 минуту
    scheduler.add_job(apsched.run_every_hour, trigger="cron", year='*', month='*', day="*", hour="*", minute=1,
                      second=0, start_date=datetime.now(), kwargs={"bot": bot})
    # создание excel файла
    scheduler.add_job(apsched.create_players_excel, trigger="cron", year='*', month='*', day="*", hour="*", minute="*/10",
                      second=0, start_date=datetime.now())

    scheduler.start()

    dispatcher.include_routers(admin.router, users.router, add_tournament.router, tournaments.router, pay_tournament.router,
                               admin_tournament.router, libero_registration.router)
    # await init_models()

    # MIDDLEWARES
    dispatcher.message.middleware(AdminMiddleware())
    dispatcher.callback_query.middleware(AdminMiddleware())

    await dispatcher.start_polling(bot)


async def init_models():
    async with async_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(start_bot())
