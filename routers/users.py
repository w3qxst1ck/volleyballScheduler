from aiogram import Router, types
from aiogram.filters import Command

from routers.middlewares import CheckPrivateMessageMiddleware

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())


@router.message(Command("start"))
async def start_handler(message: types.Message) -> None:
    """Start message"""
    await message.answer("Hello!")