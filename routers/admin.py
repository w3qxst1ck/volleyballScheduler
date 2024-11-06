from datetime import datetime

from aiogram import Router, types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import schemas
from database.orm import AsyncOrm
from routers.middlewares import CheckPrivateMessageMiddleware, CheckIsAdminMiddleware
from settings import settings
from routers.fsm_states import AddEventFSM
from routers import keyboards as kb
from routers import utils
from routers import messages as ms

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(CheckIsAdminMiddleware(settings.admins))


# GET EVENTS
@router.message(Command("events"))
@router.callback_query(lambda callback:callback.data == "back-admin-events")
async def get_events_handler(message: types.Message | types.CallbackQuery) -> None:
    """Получение всех событий"""
    events = await AsyncOrm.get_events()

    if type(message) == types.Message:
        await message.answer("События", reply_markup=kb.events_keyboard_admin(events).as_markup())
    else:
        await message.message.edit_text("События", reply_markup=kb.events_keyboard_admin(events).as_markup())


@router.callback_query(lambda callback: callback.data != "cancel" and callback.data.split("_")[0] == "admin-event")
async def event_info_handler(callback: types.CallbackQuery) -> None:
    """Карточка события для админа"""
    event_id = int(callback.data.split("_")[1])
    event = await AsyncOrm.get_event_with_users(event_id)
    msg = ms.event_card_for_admin_message(event)

    await callback.message.edit_text(msg, reply_markup=kb.event_card_keyboard_admin(event).as_markup())


@router.callback_query(lambda callback: callback.data != "cancel" and callback.data.split("_")[0] == "admin-event-user")
async def event_info_handler(callback: types.CallbackQuery) -> None:
    """Предложение удалить пользователя в событии для админа"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    await callback.message.edit_text("Удалить пользователя с события?",
                                     reply_markup=kb.yes_no_keyboard_for_admin_delete_user_from_event(event_id, user_id).as_markup())


@router.callback_query(lambda callback: callback.data != "cancel" and callback.data.split("_")[0] == "admin-event-user-delete")
async def event_info_handler(callback: types.CallbackQuery, bot: Bot) -> None:
    """Удаление пользователя в событии для админа"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    await AsyncOrm.delete_user_from_event(event_id, user_id)
    event = await AsyncOrm.get_event_with_users(event_id)

    # оповещение пользователя об удалении
    user = await AsyncOrm.get_user_by_id(user_id)
    msg_for_user = ms.notify_deleted_user_message(event)
    await bot.send_message(user.tg_id, msg_for_user)

    await callback.message.edit_text("Пользователь удален с события ✅")

    msg_for_admin = ms.event_card_for_admin_message(event)
    await callback.message.answer(msg_for_admin, reply_markup=kb.event_card_keyboard_admin(event).as_markup())


# ADD EVENT
@router.message(Command("add_event"))
async def add_event_start_handler(message: types.Message, state: FSMContext) -> None:
    """Добавление события, начало AddEventFSM"""
    msg = await message.answer("Отправьте тип события (например соревнование, тренировка, турнир)",
                               reply_markup=kb.cancel_keyboard().as_markup())

    await state.set_state(AddEventFSM.type)
    await state.update_data(prev_mess=msg)


@router.message(AddEventFSM.type)
async def add_event_type_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение type, выбор title"""
    type = message.text
    await state.update_data(type=type)

    msg = await message.answer("Отправьте описание события, не указывая дату",
                               reply_markup=kb.cancel_keyboard().as_markup())

    # удаление прошлого сообщения
    data = await state.get_data()
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await state.set_state(AddEventFSM.title)
    await state.update_data(prev_mess=msg)


@router.message(AddEventFSM.title)
async def add_event_title_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение title, выбор date"""
    title = message.text
    await state.update_data(title=title)

    msg = await message.answer("Введите дату в формате <b>ДД.ММ.ГГГГ</b> (например 25.07.2025)",
                               reply_markup=kb.cancel_keyboard().as_markup())

    # удаление прошлого сообщения
    data = await state.get_data()
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await state.set_state(AddEventFSM.date)
    await state.update_data(prev_mess=msg)


@router.message(AddEventFSM.date)
async def add_event_date_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение date, выбор time"""
    date = message.text
    data = await state.get_data()

    # если ввели неправильную дату
    if not utils.is_valid_date(date):
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass
        msg = await message.answer("Указан неверный формат даты\n\n"
                                   "Необходимо указать дату в формате <b>ДД.ММ.ГГГГ</b> без букв "
                                   "\"д\", \"м\" и \"г\" (например 25.07.2025)\n"
                                   "Дата не может быть раньше сегодняшней",
                                   reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если дата правильная
    await state.update_data(date=date)

    msg = await message.answer("Введите время в формате <b>ММ:ЧЧ</b> (например 09:00)",
                               reply_markup=kb.cancel_keyboard().as_markup())

    # удаление прошлого сообщения
    data = await state.get_data()
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await state.set_state(AddEventFSM.time)
    await state.update_data(prev_mess=msg)


@router.message(AddEventFSM.time)
async def add_event_date_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение time, выбор places"""
    time = message.text
    data = await state.get_data()

    # неправильное время
    if not utils.is_valid_time(time):
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass
        msg = await message.answer("Указан неверный формат времени\n\n"
                                   "Необходимо указать время в формате <b>ЧЧ:ММ</b> без букв \"м\" и \"ч\" "
                                   "(например 09:00 или 13:00)",
                                   reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если время правильное
    await state.update_data(time=time)

    msg = await message.answer("Введите количество мест <b>цифрой</b>",
                               reply_markup=kb.cancel_keyboard().as_markup())

    # удаление прошлого сообщения
    data = await state.get_data()
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await state.set_state(AddEventFSM.places)
    await state.update_data(prev_mess=msg)


@router.message(AddEventFSM.places)
async def add_event_date_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение time, выбор places"""
    places_str = message.text
    data = await state.get_data()

    # неправильное количество мест
    if not utils.is_valid_places(places_str):
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass
        msg = await message.answer("Введено некорректное число\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 8, 16 ил 24)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если количество мест правильное, то создаем event
    date_time_str = f"{data['date']} {data['time']}"
    date_time = datetime.strptime(date_time_str, "%d.%m.%Y %H:%M")
    event = schemas.EventAdd(
        type=data["type"],
        title=data["title"],
        date=date_time,
        places=int(places_str)
    )
    await AsyncOrm.add_event(event)

    # удаление прошлого сообщения
    data = await state.get_data()
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await message.answer(f"Событие <b>\"{event.title}\"</b> в <b>{date_time_str}</b> успешно создано ✅")


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

#
# @router.message(Command("user"))
# async def get_user_handler(message: types.Message) -> None:
#     """User"""
#     user = await AsyncOrm.get_user_by_id(1)
#     await message.answer(f"{user.id} {user.username}")
#
#
# @router.message(Command("users"))
# async def get_users_handler(message: types.Message) -> None:
#     """Users"""
#     await AsyncOrm.get_users_with_events()
#
#
# @router.message(Command("event"))
# async def add_event_handler(message: types.Message) -> None:
#     """Users"""
#     date_time_str = "30.10.2025 08:00"
#     date_time = datetime.strptime(date_time_str, "%d.%m.%Y %H:%M")
#     event1 = schemas.EventAdd(
#         type="Соревнования",
#         title="Городской турнир",
#         date=date_time,
#         places=18
#     )
#     event2 = schemas.EventAdd(type="Тренировка", title="Обычная тренировка", date=date_time, places=12)
#     event3 = schemas.EventAdd(type="Турнир", title="Сульский турнир", date=date_time, places=24)
#
#     await AsyncOrm.add_event(event1)
#     await AsyncOrm.add_event(event2)
#     await AsyncOrm.add_event(event3)
#
#
# @router.message(Command("events"))
# async def add_event_handler(message: types.Message) -> None:
#     """Users"""
#     await AsyncOrm.get_events_with_users()
#
#
# @router.message(Command("add"))
# async def add_user_to_event_handler(message: types.Message) -> None:
#     """Users"""
#     await AsyncOrm.add_user_to_event(3, 2)

# SELECT e.id, e.type, e.title, e.date, e.places, e.active, users.id
# FROM events AS e
# JOIN events_users ON events_users.event_id = e.id
# JOIN users ON events_users.user_id = users.id
# WHERE e.active = true
# ORDER BY e.id;
