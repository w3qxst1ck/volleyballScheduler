from datetime import datetime

from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from routers.middlewares import CheckPrivateMessageMiddleware
from routers import keyboards as kb, messages as ms
from routers.fsm_states import RegisterUserFSM
from database import schemas
from database.orm import AsyncOrm
from routers import utils

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.callback_query.middleware.register(CheckPrivateMessageMiddleware())


# REGISTRATION
@router.message(Command("start"))
@router.message(Command("menu"))
async def start_handler(message: types.Message, state: FSMContext) -> None:
    """Start message, начало RegisterUserFsm"""
    tg_id = str(message.from_user.id)
    user = await AsyncOrm.get_user_by_tg_id(tg_id)

    # старый пользователь
    if user:
        # /start handler
        if message.text == "/start":
            await message.answer("Вы уже зарегистрированы!")

        # /menu handler
        else:
            await message.answer("Главное меню", reply_markup=kb.menu_users_keyboard().as_markup())

    # новый пользователь
    else:
        await state.set_state(RegisterUserFSM.name)
        msg = await message.answer("Для записи на спортивные мероприятия необходимо зарегистрироваться\n\n"
                                   "Отправьте сообщением свои <b>имя</b> и <b>фамилию</b> (например Иван Иванов)",
                                   reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)


@router.message(RegisterUserFSM.name)
async def add_user_handler(message: types.Message, state: FSMContext) -> None:
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

        await message.answer("Вы успешно зарегистрированы ✅")
        await message.answer("Главное меню", reply_markup=kb.menu_users_keyboard().as_markup())

    # ошибка введения данных
    except utils.FullnameException:
        msg = await message.answer(
            "Необходимо ввести <b>имя и фамилию через пробел</b> без знаков препинания, символов "
            "и цифр (например Иван Иванов)",
            reply_markup=kb.cancel_keyboard().as_markup()
        )

        data = await state.get_data()
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass

        await state.update_data(prev_mess=msg)


@router.callback_query(lambda callback: callback.data.split("_")[1] == "user-menu")
async def back_menu_handler(callback: types.CallbackQuery) -> None:
    """Главное меню пользователя"""
    await callback.message.edit_text("Выберите действие", reply_markup=kb.menu_users_keyboard().as_markup())


# USER EVENTS
@router.callback_query(lambda callback: callback.data == "menu_events")
async def user_events_dates_handler(callback: types.CallbackQuery) -> None:
    """Вывод дат с мероприятиями мероприятий"""
    # events = await AsyncOrm.get_events_with_users(only_active=True)

    events = await AsyncOrm.get_events(only_active=True)
    events_dates = [event.date for event in events]
    unique_dates = utils.get_unique_dates(events_dates)

    msg = "Выберите дату с мероприятием:" \
          # "Мероприятия, на которые вы зарегистрированы, помечены '✔️'"
    if not events:
        msg = "В ближайшее время нет мероприятий"

    await callback.message.edit_text(msg, reply_markup=kb.dates_keyboard(unique_dates).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "events-date")
async def user_events_dates_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятий в выбранную дату"""
    date_str = callback.data.split("_")[1]
    date = datetime.strptime(date_str, "%d.%m.%Y").date()

    events = await AsyncOrm.get_events_for_date(date, only_active=True)
    print(events)


@router.callback_query(lambda callback: callback.data.split("_")[0] == "user-event")
async def user_event_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятия для пользователя из общего списка 'Events'"""
    event_id = int(callback.data.split("_")[1])
    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))
    event_with_users = await AsyncOrm.get_event_with_users(event_id)

    # если зарегистрирован
    if user in event_with_users.users_registered:
        registered = True
    # не зарегистрирован
    else:
        registered = False

    msg = ms.event_card_message(event_with_users, registered)

    await callback.message.edit_text(
        msg,
        reply_markup=kb.event_card_keyboard(event_id, user.id, registered, "menu_events", "events").as_markup()
    )


# USER ALREADY REGISTERED EVENTS
@router.callback_query(lambda callback: callback.data.split("_")[1] == "my-events")
async def user_event_registered_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятий куда пользователь уже зарегистрирован"""
    user_with_events = await AsyncOrm.get_user_with_events(str(callback.from_user.id), only_active=True)

    if not user_with_events.events:
        msg = "Вы пока никуда не зарегистрировались\n\nВы можете это сделать во вкладке \n\"🗓️ Все мероприятия\""
    else:
        msg = "Вы являетесь участником следующих мероприятий:"

    await callback.message.edit_text(msg, reply_markup=kb.user_events(user_with_events.events).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "my-events")
async def event_info_handler(callback: types.CallbackQuery) -> None:
    """Карточка событий"""
    event_id = int(callback.data.split("_")[1])
    event = await AsyncOrm.get_event_with_users(event_id)

    # проверяем участвует ли пользователь уже в этом событии
    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))

    if user in event.users_registered:
        registered = True
    else:
        registered = False

    msg = ms.event_card_message(event, registered)

    await callback.message.edit_text(
        msg,
        reply_markup=kb.event_card_keyboard(event_id, user.id, registered, "menu_my-events", "my-events").as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] in ["unreg-user", "reg-user"])
async def reg_unreg_user_to_event_handler(callback: types.CallbackQuery) -> None:
    """Регистрация и удаление пользователя из события"""
    action = callback.data.split("_")[0]
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])
    from_ = callback.data.split("_")[3]

    if action == "reg-user":
        await AsyncOrm.add_user_to_event(event_id, user_id)
        registered_status = True
        await callback.message.edit_text("Вы зарегистрированы")

    else:
        await AsyncOrm.delete_user_from_event(event_id, user_id)
        registered_status = False
        await callback.message.edit_text("Регистрация на мероприятие отменена")

    event = await AsyncOrm.get_event_with_users(event_id)

    # при обращении из вкладки Мероприятия
    if from_ == "events":
        await callback.message.answer(
            ms.event_card_message(event, user_registered=registered_status),
            reply_markup=kb.event_card_keyboard(
                event_id, user_id, registered_status, "menu_events", "events"
            ).as_markup()
        )

    # при обращении из вкладки Мои мероприятия
    else:
        await callback.message.answer(
            ms.event_card_message(event, user_registered=registered_status),
            reply_markup=kb.event_card_keyboard(
                event_id, user_id, registered_status, "menu_my-events", "my-events"
            ).as_markup()
        )


# USER PROFILE
@router.callback_query(lambda callback: callback.data == "menu_profile")
async def main_menu_handler(callback: types.CallbackQuery) -> None:
    """Профиль пользователя"""
    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))

    message = ms.user_profile_message(user)
    await callback.message.edit_text(message, reply_markup=kb.user_profile_keyboard().as_markup())


# CANCEL BUTTON
@router.callback_query(lambda callback: callback.data == "button_cancel", StateFilter("*"))
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel FSM and delete last message"""
    await state.clear()
    await callback.message.answer("Действие отменено ❌")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass