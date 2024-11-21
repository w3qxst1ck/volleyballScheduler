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
@router.callback_query(lambda callback: callback.data == "back-admin-events")
async def get_events_handler(message: types.Message | types.CallbackQuery) -> None:
    """Получение всех событий"""
    events = await AsyncOrm.get_events()

    if events:
        msg = "События"
    else:
        msg = "Событий пока нет"

    if type(message) == types.Message:
        await message.answer(msg, reply_markup=kb.events_keyboard_admin(events).as_markup())
    else:
        await message.message.edit_text(msg, reply_markup=kb.events_keyboard_admin(events).as_markup())


# ADMIN EVENT CARD
@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-event")
async def event_info_handler(callback: types.CallbackQuery) -> None:
    """Карточка события для админа"""
    event_id = int(callback.data.split("_")[1])
    event = await AsyncOrm.get_event_with_users(event_id)
    msg = ms.event_card_for_user_message(event, payment=None)
    msg += "\nЧтобы удалить участника с события, нажмите кнопку с соответствующим номером участника"

    await callback.message.edit_text(
        msg,
        reply_markup=kb.event_card_keyboard_admin(event).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-event-user")
async def event_info_handler(callback: types.CallbackQuery) -> None:
    """Предложение удалить пользователя в событии для админа"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    await callback.message.edit_text("Удалить пользователя с события?",
                                     reply_markup=kb.yes_no_keyboard_for_admin_delete_user_from_event(event_id, user_id).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-event-user-delete")
async def event_delete_user_handler(callback: types.CallbackQuery, bot: Bot) -> None:
    """Удаление пользователя в событии для админа"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    await AsyncOrm.delete_user_from_event(event_id, user_id)
    await AsyncOrm.delete_payment(event_id, user_id)
    event = await AsyncOrm.get_event_with_users(event_id)

    # оповещение пользователя об удалении
    user = await AsyncOrm.get_user_by_id(user_id)
    msg_for_user = ms.notify_deleted_user_message(event)
    await bot.send_message(user.tg_id, msg_for_user)

    await callback.message.edit_text("Пользователь удален с события ✅")

    # возврат к карточке мероприятия
    msg_for_admin = ms.event_card_for_user_message(event, payment=None)
    msg_for_admin += "\nЧтобы удалить участника с события, нажмите кнопку с соответствующим номером участника"
    await callback.message.answer(msg_for_admin, reply_markup=kb.event_card_keyboard_admin(event).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-event-delete")
async def event_delete_handler(callback: types.CallbackQuery) -> None:
    """Подтверждение удаления события админом"""
    event_id = int(callback.data.split("_")[1])

    event = await AsyncOrm.get_event_by_id(event_id)
    date = utils.convert_date(event.date)
    time = utils.convert_time(event.date)
    await callback.message.edit_text(
        f"Вы действительно хотите удалить мероприятие <b>{event.type} \"{event.title}\"</b> {date} в {time}?",
        reply_markup=kb.yes_no_keyboard_for_admin_delete_event(event_id).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-event-delete-confirm")
async def event_delete_confirmed_handler(callback: types.CallbackQuery) -> None:
    """Удаление события админом"""
    event_id = int(callback.data.split("_")[1])
    await AsyncOrm.delete_event(event_id)

    await callback.message.edit_text("Событие удалено ✅")

    events = await AsyncOrm.get_events()
    await callback.message.answer("События", reply_markup=kb.events_keyboard_admin(events).as_markup())


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
    """Сохранение places, выбор level"""
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
                                   "(например 8, 16 или 24)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если количество мест правильное
    await state.update_data(places=int(places_str))

    # удаление прошлого сообщения
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await state.set_state(AddEventFSM.min_count)

    msg = await message.answer(
        "Введите <b>минимальное</b> необходимое количество участников для мероприятия",
        reply_markup=kb.cancel_keyboard().as_markup()
    )
    await state.update_data(prev_mess=msg)


@router.message(AddEventFSM.min_count)
async def add_min_count_users_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение min_user_count, выбор level"""
    min_user_count_str = message.text
    data = await state.get_data()

    # неправильное количество мин людей
    if not utils.is_valid_places(min_user_count_str):
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass
        msg = await message.answer("Введено некорректное число\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 2, 4 или 8)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если количество мин людей правильное
    await state.update_data(min_user_count=int(min_user_count_str))

    # удаление прошлого сообщения
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await state.set_state(AddEventFSM.level)
    msg = await message.answer("Выберите минимальный уровень участников мероприятия",
                         reply_markup=kb.levels_keyboards().as_markup())
    await state.update_data(prev_mess=msg)


@router.callback_query(AddEventFSM.level, lambda callback: callback.data.split("_")[0] == "admin-add-event-level")
async def add_event_date_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Сохранение level, выбор price"""
    level = int(callback.data.split("_")[1])
    await state.update_data(level=level)
    await state.set_state(AddEventFSM.price)

    await callback.message.edit_text("Введите цифрой цену мероприятия", reply_markup=kb.cancel_keyboard().as_markup())


@router.message(AddEventFSM.price)
async def add_event_date_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение price, создание Event"""
    price_str = message.text
    data = await state.get_data()

    # неправильная цена
    if not utils.is_valid_price(price_str):
        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass
        msg = await message.answer("Введена некорректная цена\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 500, 1000 ил 1500)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # правильная цена
    date_time_str = f"{data['date']} в {data['time']}"
    date_time = datetime.strptime(f"{data['date']} {data['time']}", "%d.%m.%Y %H:%M")
    event = schemas.EventAdd(
        type=data["type"],
        title=data["title"],
        date=date_time,
        places=data["places"],
        min_user_count=data["min_user_count"],
        level=data["level"],
        price=int(price_str)
    )
    await AsyncOrm.add_event(event)

    # удаление сообщения
    try:
        await data["prev_mess"].delete()
    except TelegramBadRequest:
        pass

    await state.clear()
    await message.answer(f"Событие <b>\"{event.title}\"</b> <b>{date_time_str}</b> успешно создано ✅")


# SET LEVEL
@router.message(Command("levels"))
@router.callback_query(lambda callback: callback.data == "back-admin-levels")
async def choose_event_for_set_level_handler(message: types.Message) -> None:
    """Выбор мероприятия для назначения уровня пользователям"""
    events = await AsyncOrm.get_last_events()

    if events:
        msg = "Мероприятия за последние 3 дня"
    else:
        msg = "Прошедших мероприятий для присвоения уровня нет"

    if type(message) == types.Message:
        await message.answer(msg, reply_markup=kb.events_levels_keyboard_admin(events).as_markup())
    else:
        await message.message.edit_text(msg, reply_markup=kb.events_levels_keyboard_admin(events).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-event-levels")
async def event_levels_info_handler(callback: types.CallbackQuery) -> None:
    """Карточка события админа для выставления уровней"""
    event_id = int(callback.data.split("_")[1])
    event = await AsyncOrm.get_event_with_users(event_id)
    msg = ms.event_levels_card_for_admin_message(event)

    await callback.message.edit_text(
        msg,
        reply_markup=kb.event_levels_card_keyboard_admin(event).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-event-level-user")
async def event_level_choose_handler(callback: types.CallbackQuery) -> None:
    """Выбор уровня для конкретного участника"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])
    user = await AsyncOrm.get_user_by_id(user_id)

    if user.level:
        msg = f"Сейчас <b>{user.firstname} {user.lastname}</b> имеет уровень <b>{settings.levels[user.level]}</b>\n\n"
    else:
        msg = f"Сейчас <b>{user.firstname} {user.lastname} не имеет уровня</b>\n\n"

    msg += "Выберите уровень, который хотите установить пользователю"
    await callback.message.edit_text(msg, reply_markup=kb.event_levels_keyboards(event_id, user_id).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-add-user-level")
async def event_level_choose_handler(callback: types.CallbackQuery, bot: Bot) -> None:
    """Выбор уровня для конкретного участника"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])
    level = int(callback.data.split("_")[3])

    await AsyncOrm.set_level_for_user(user_id, level)

    event = await AsyncOrm.get_event_with_users(event_id)
    user = await AsyncOrm.get_user_by_id(user_id)

    # message to admin
    await callback.message.edit_text(f"Уровень пользователя <b>{user.firstname} {user.lastname}</b> обновлен на {settings.levels[level]}")

    # message to user
    user_msg = ms.notify_set_level_message(level)
    await bot.send_message(str(user.tg_id), user_msg)

    msg = ms.event_levels_card_for_admin_message(event)
    await callback.message.answer(msg, reply_markup=kb.event_levels_card_keyboard_admin(event).as_markup())


# PAYMENTS
@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-payment")
async def confirm_payment(callback: types.CallbackQuery, bot: Bot) -> None:
    """Подтверждение оплаты от админа"""
    confirm = callback.data.split("_")[1]

    event_id = int(callback.data.split("_")[2])
    user_id = int(callback.data.split("_")[3])

    event = await AsyncOrm.get_event_by_id(event_id)
    user = await AsyncOrm.get_user_by_id(user_id)

    event_date = utils.convert_date(event.date)
    event_time = utils.convert_time(event.date)

    answer_text = f"Пользователь <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                  f"оплатил <b>{event.type}</b> \"{event.title}\" <b>{event_date} {event_time}</b> " \
                  f"на сумму <b>{event.price} руб.</b>\n\n"

    # подтверждение оплаты
    if confirm == "ok":
        # подтверждение оплаты
        await AsyncOrm.update_payment_status(event_id, user_id)
        # создание записи в таблице event_users
        await AsyncOrm.add_user_to_event(event_id, user_id)

        # сообщение админу
        answer_ok = answer_text + "Оплата подтверждена ✅\nПользователь записан на мероприятие"
        await callback.message.edit_text(answer_ok)

        # сообщение пользователю
        date = utils.convert_date(event.date)
        time = utils.convert_time(event.date)
        msg = f"🔔 <i>Автоматическое уведомление</i>\n\nОплата прошла успешно ✅\nВы записаны на {event.type} \"{event.title} {date} в {time}\""
        await bot.send_message(user.tg_id, msg)

    # отклонение оплаты
    else:
        # сообщение админу
        answer_no = answer_text + "Оплата отклонена ❌\nОповещение направлено пользователю"
        await callback.message.edit_text(answer_no)

        # удаление записи из таблицы payments
        await AsyncOrm.delete_payment(event_id, user_id)

        # сообщение пользователю
        msg = f"🔔 <i>Автоматическое уведомление</i>\n\n❌ Администратор оплату не подтвердил\n" \
                       f"Вы можете связаться с администрацией канала @{settings.main_admin_url}"
        await bot.send_message(user.tg_id, msg)
