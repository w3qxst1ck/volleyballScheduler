from aiogram import Router, types
from aiogram.filters import Command

from routers.middlewares import CheckPrivateMessageMiddleware, CheckIsAdminMiddleware
from settings import settings
from database import schemas
from database.orm import AsyncOrm

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(CheckIsAdminMiddleware(settings.admins))


@router.message(Command("start"))
async def start_handler(message: types.Message) -> None:
    """Start message"""
    user = schemas.UserAdd(
        tg_id="492-5-5533",
        username="kiril",
        firstname="Kirill",
        lastname="Avdeev"
    )
    await AsyncOrm.add_user(user)

    await message.answer("Hello!")


@router.message(Command("user"))
async def get_user_handler(message: types.Message) -> None:
    """User"""
    user = await AsyncOrm.get_user_by_id(1)
    await message.answer(f"{user.id} {user.username}")


@router.message(Command("users"))
async def get_users_handler(message: types.Message) -> None:
    """Users"""
    await AsyncOrm.get_users_with_events()