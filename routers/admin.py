from aiogram import Router, types
from aiogram.filters import Command

from routers.middlewares import CheckPrivateMessageMiddleware, CheckIsAdminMiddleware
from settings import settings

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(CheckIsAdminMiddleware(settings.admins))


@router.message(Command("start"))
async def start_handler(message: types.Message) -> None:
    """Start message"""
    await message.answer("Hello!")
