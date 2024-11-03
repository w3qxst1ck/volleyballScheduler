from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from routers.middlewares import CheckPrivateMessageMiddleware
from routers import keyboards as kb
from routers.fsm_states import RegisterUserFSM
from database import schemas
from database.orm import AsyncOrm
from routers import utils

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())


@router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext) -> None:
    """Start message, начало RegisterUserFsm"""
    tg_id = str(message.from_user.id)
    user = await AsyncOrm.get_user_by_tg_id(tg_id)

    # пользователь уже зарегистрирован
    if user:
        await message.answer("Вы уже зарегистрированы!")

    # новый пользователь
    else:
        await state.set_state(RegisterUserFSM.name)
        msg = await message.answer("Для записи на спортивные мероприятия необходимо зарегистрироваться\n\n"
                                   "Отправьте сообщением свои <b>имя</b> и <b>фамилию</b> (например Иван Иванов)",
                                   reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)


@router.message(RegisterUserFSM.name)
async def start_handler(message: types.Message, state: FSMContext) -> None:
    """Регистрация нового пользователя"""
    fullname = message.text

    try:
        # validation
        firstname, lastname = await utils.get_firstname_lastname(fullname)
        tg_id = str(message.from_user.id)
        username = message.from_user.username if message.from_user.username else ""

        user = schemas.UserAdd(
            tg_id=tg_id,
            username=username,
            firstname=firstname,
            lastname=lastname
        )
        await AsyncOrm.add_user(user)

        data = await state.get_data()
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass
        await state.clear()

        await message.answer("Вы успешно зарегистрированы!")

    # ошибка введения данных
    except utils.FullnameException:
        msg = await message.answer("Необходимо ввести <b>имя и фамилию через пробел</b> без знаков препинания, символов "
                                   "и цифр (например Иван Иванов)",
                                   reply_markup=kb.cancel_keyboard().as_markup())

        data = await state.get_data()
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass

        await state.update_data(prev_mess=msg)


# CANCEL BUTTON
@router.callback_query(lambda callback: callback.data == "cancel", StateFilter("*"))
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel FSM and delete last message"""
    await state.clear()
    await callback.message.answer("Действие отменено ❌")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass