from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command

from routers.middlewares import CheckPrivateMessageMiddleware, CheckIsAdminMiddleware
from settings import settings
from database import schemas
from database.orm import AsyncOrm

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(CheckIsAdminMiddleware(settings.admins))

#
# @router.message(Command("start"))
# async def start_handler(message: types.Message) -> None:
#     """Start message"""
#     user1 = schemas.UserAdd(
#         tg_id="492-5-5533",
#         username="kiril",
#         firstname="Kirill",
#         lastname="Avdeev"
#     )
#     user2 = schemas.UserAdd(tg_id="492-5-393", username="alexandr", firstname="alex", lastname="Smehnov")
#     user3 = schemas.UserAdd(tg_id="492-5-401", username="lexey", firstname="lex", lastname="pon")
#     await AsyncOrm.add_user(user1)
#     await AsyncOrm.add_user(user2)
#     await AsyncOrm.add_user(user3)
#
#     await message.answer("Hello!")


@router.message(Command("user"))
async def get_user_handler(message: types.Message) -> None:
    """User"""
    user = await AsyncOrm.get_user_by_id(1)
    await message.answer(f"{user.id} {user.username}")


@router.message(Command("users"))
async def get_users_handler(message: types.Message) -> None:
    """Users"""
    await AsyncOrm.get_users_with_events()


@router.message(Command("event"))
async def add_event_handler(message: types.Message) -> None:
    """Users"""
    date_time_str = "30.10.2025 08:00"
    date_time = datetime.strptime(date_time_str, "%d.%m.%Y %H:%M")
    event1 = schemas.EventAdd(
        type="Соревнования",
        title="Городской турнир",
        date=date_time,
        places=18
    )
    event2 = schemas.EventAdd(type="Тренировка", title="Обычная тренировка", date=date_time, places=12)
    event3 = schemas.EventAdd(type="Турнир", title="Сульский турнир", date=date_time, places=24)

    await AsyncOrm.add_event(event1)
    await AsyncOrm.add_event(event2)
    await AsyncOrm.add_event(event3)


@router.message(Command("events"))
async def add_event_handler(message: types.Message) -> None:
    """Users"""
    await AsyncOrm.get_events_with_users()


@router.message(Command("add"))
async def add_user_to_event_handler(message: types.Message) -> None:
    """Users"""
    await AsyncOrm.add_user_to_event(3, 2)
