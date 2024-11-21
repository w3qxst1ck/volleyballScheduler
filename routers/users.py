from datetime import datetime

from aiogram import Router, types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from routers.middlewares import CheckPrivateMessageMiddleware
from routers import keyboards as kb, messages as ms
from routers.fsm_states import RegisterUserFSM, UpdateUserFSM
from database import schemas
from database.orm import AsyncOrm
from routers import utils
import settings

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
    if type(callback) == types.Message:
        await callback.answer("Главное меню", reply_markup=kb.menu_users_keyboard().as_markup())

    else:
        await callback.message.edit_text("Главное меню", reply_markup=kb.menu_users_keyboard().as_markup())


# ALL EVENTS
@router.callback_query(lambda callback: callback.data.split("_")[1] == "all-events")
async def user_events_dates_handler(callback: types.CallbackQuery) -> None:
    """Вывод дат с мероприятиями мероприятий"""
    events = await AsyncOrm.get_events(only_active=True, days_ahead=11) # берем мероприятия за ближайших 10 дней
    events_dates = [event.date for event in events]
    unique_dates = utils.get_unique_dates(events_dates)

    msg = "Даты с мероприятиями:"
    if not events:
        msg = "В ближайшее время нет мероприятий"

    await callback.message.edit_text(msg, reply_markup=kb.dates_keyboard(unique_dates).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "events-date")
async def user_events_dates_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятий в выбранную дату"""
    date_str = callback.data.split("_")[1]
    date = datetime.strptime(date_str, "%d.%m.%Y").date()

    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))
    events = await AsyncOrm.get_events_for_date(date)

    await callback.message.edit_text(
        f"Мероприятия на <b>{date_str}</b>:\n\nМероприятия, на которые вы уже записаны, помечены '✔️'",
        reply_markup=kb.events_keyboard(events, user).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "user-event")
async def user_event_handler(callback: types.CallbackQuery) -> None:
    """Вывод карточки мероприятия для пользователя"""

    event_id = int(callback.data.split("_")[1])
    user_tg_id = str(callback.from_user.id)

    user = await AsyncOrm.get_user_by_tg_id(user_tg_id)
    event_with_users = await AsyncOrm.get_event_with_users(event_id)

    payment = await AsyncOrm.get_payment_by_event_and_user(event_id, user.id)

    msg = ms.event_card_for_user_message(event_with_users, payment)

    await callback.message.edit_text(
        msg,
        reply_markup=kb.event_card_keyboard(
            event_id,
            user.id,
            payment,
            f"events-date_{utils.convert_date(event_with_users.date)}",
        ).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "reg-user")
async def register_user_on_event(callback: types.CallbackQuery) -> None:
    """Регистрация пользователя на мероприятие"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    event_with_users = await AsyncOrm.get_event_with_users(event_id)
    user = await AsyncOrm.get_user_by_id(user_id)

    # если уровень соответствует
    if not user.level or user.level >= event_with_users.level:
        # если нет свободных мест
        if len(event_with_users.users_registered) >= event_with_users.places:
            payment = await AsyncOrm.get_payment_by_event_and_user(event_id, user.id)
            msg = ms.event_card_for_user_message(event_with_users, payment)
            await callback.message.edit_text("❗Вы не можете записаться на данное мероприятие, "
                                             "так как свободных мест нет")
            await callback.message.answer(msg, reply_markup=kb.event_card_keyboard(event_id, user.id, payment,
                f"events-date_{utils.convert_date(event_with_users.date)}").as_markup())

        # если места есть
        else:
            msg = ms.invoice_message_for_user(event_with_users)
            await callback.message.edit_text(msg, reply_markup=kb.payment_confirm_keyboard(user, event_with_users).as_markup())

    # если уровень ниже
    else:
        payment = await AsyncOrm.get_payment_by_event_and_user(event_id, user.id)
        msg = ms.event_card_for_user_message(event_with_users, payment)
        await callback.message.edit_text("❗Вы не можете записаться на данное мероприятие, "
                                         "так как ваш уровень ниже необходимого")
        await callback.message.answer(
            msg,
            reply_markup=kb.event_card_keyboard(
                event_id,
                user.id,
                payment,
                f"events-date_{utils.convert_date(event_with_users.date)}"
            ).as_markup()
        )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "paid")
async def register_paid_event(callback: types.CallbackQuery, bot: Bot) -> None:
    """Подтверждение оплаты от пользователя"""
    user_id = int(callback.data.split("_")[1])
    event_id = int(callback.data.split("_")[2])

    # создание платежа в БД
    await AsyncOrm.create_payments(user_id, event_id)

    # оповещение администратора
    user = await AsyncOrm.get_user_by_id(user_id)
    event = await AsyncOrm.get_event_by_id(event_id)

    event_date = utils.convert_date(event.date)
    event_time = utils.convert_time(event.date)

    msg_to_admin = f"Пользователь <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                   f"оплатил <b>{event.type}</b> \"{event.title}\" <b>{event_date} {event_time}</b> " \
                   f"на сумму <b>{event.price} руб.</b> \n\nПодтвердите или отклоните оплату"
    await bot.send_message(
        settings.settings.main_admin_tg_id,
        msg_to_admin,
        reply_markup=kb.confirm_decline_keyboard(event_id, user_id).as_markup()
    )

    await callback.message.edit_text(f"🔔 <i>Автоматическое уведомление</i>\n\n"
                                     f"Ваш платеж на сумму <b>{event.price}</b> руб. находится в обработке")

    msg = "Дождитесь подтверждения оплаты от администратора\n\n" \
          "Вы можете отслеживать статус оплаты во вкладке \"👨🏻‍💻 Главное меню\" в разделе \"🏐 Мои мероприятия\""

    await callback.message.answer(msg)
    await callback.message.answer("Главное меню", reply_markup=kb.menu_users_keyboard().as_markup())


# USER ALREADY REGISTERED EVENTS
@router.callback_query(lambda callback: callback.data.split("_")[1] == "my-events")
async def user_event_registered_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятий куда пользователь уже зарегистрирован"""
    payments = await AsyncOrm.get_user_payments_with_events_and_users(str(callback.from_user.id))
    active_events = list(filter(lambda payment: payment.event.active == True, payments))

    if not active_events:
        msg = "Вы пока никуда не записаны\n\nВы можете это сделать во вкладке \n\"🗓️ Все мероприятия\""
    else:
        msg = "Мероприятия куда вы записывались:\n\n✅ - оплаченные мероприятия\n⏳ - ожидается подтверждение оплаты от администратора"

    await callback.message.edit_text(msg, reply_markup=kb.user_events(active_events).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "my-events")
async def my_event_info_handler(callback: types.CallbackQuery) -> None:
    """Карточка события в Моих мероприятиях"""
    payment_id = int(callback.data.split("_")[1])

    payment = await AsyncOrm.get_payment_by_id(payment_id)
    event = await AsyncOrm.get_event_with_users(payment.event_id)

    msg = ms.event_card_for_user_message(event, payment)

    await callback.message.edit_text(msg, reply_markup=kb.my_event_card_keyboard(payment).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "unreg-user")
async def unregister_form_my_event_handler(callback: types.CallbackQuery) -> None:
    """Отмена регистрации на событие в Моих мероприятиях"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    event = await AsyncOrm.get_event_by_id(event_id)
    payment = await AsyncOrm.get_payment_by_event_and_user(event_id, user_id)

    await callback.message.edit_text(
        f"Вы действительно хотите отменить запись на мероприятие <b>{event.type} \"{event.title}\"</b>?",
        reply_markup=kb.yes_no_keyboard_for_unreg_from_event(event_id, user_id, payment.id).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "unreg-user-confirmed")
async def unregister_form_my_event_handler(callback: types.CallbackQuery) -> None:
    """Подтверждение отмены регистрации на событие в Моих мероприятиях"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    await AsyncOrm.delete_user_from_event(event_id, user_id)
    await AsyncOrm.delete_payment(event_id, user_id)

    event = await AsyncOrm.get_event_by_id(event_id)
    await callback.message.edit_text(f"🔔 <i>Автоматическое уведомление</i>\n\n"
                                     f"Вы отменили запись на мероприятие <b>{event.type} \"{event.title}\"</b>")

    # возврат ко вкладке мои мероприятия
    events = await AsyncOrm.get_user_payments_with_events_and_users(str(callback.from_user.id))

    if not events:
        msg = "Вы пока никуда не записаны\n\nВы можете это сделать во вкладке \n\"🗓️ Все мероприятия\""
    else:
        msg = "Мероприятия куда вы записывались:\n\n✅ - оплаченные мероприятия\n⏳ - ожидается подтверждение оплаты от администратора"

    await callback.message.answer(msg, reply_markup=kb.user_events(events).as_markup())


# USER PROFILE
@router.callback_query(lambda callback: callback.data == "menu_profile")
async def main_menu_handler(callback: types.CallbackQuery) -> None:
    """Профиль пользователя"""
    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))

    message = ms.user_profile_message(user)
    await callback.message.edit_text(message, reply_markup=kb.user_profile_keyboard().as_markup())


@router.callback_query(lambda callback: callback.data == "update_user_profile")
async def update_user_profile(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Изменение имени пользователя во вкладке Профиль"""

    await state.set_state(UpdateUserFSM.name)
    msg = await callback.message.answer(
        "Отправьте сообщением свои <b>имя</b> и <b>фамилию</b> (например Иван Иванов)",
        reply_markup=kb.cancel_keyboard().as_markup()
    )

    await state.update_data(prev_mess=msg)


@router.message(UpdateUserFSM.name)
async def update_user_handler(message: types.Message, state: FSMContext) -> None:
    """Изменение имени пользователя во вкладке Профиль"""

    fullname = message.text

    try:
        # validation
        firstname, lastname = await utils.get_firstname_lastname(fullname)
        tg_id = str(message.from_user.id)

        await AsyncOrm.update_user(tg_id, firstname, lastname)

        data = await state.get_data()

        try:
            await data["prev_mess"].delete()
        except TelegramBadRequest:
            pass

        await state.clear()

        user = await AsyncOrm.get_user_by_tg_id(tg_id)

        await message.answer("Данные успешно изменены ✅")

        msg = ms.user_profile_message(user)
        await message.answer(msg, reply_markup=kb.user_profile_keyboard().as_markup())

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


# HELP
@router.message(Command("help"))
async def help_handler(message: types.Message) -> None:
    """Help message"""
    msg = ms.get_help_message()
    await message.answer(msg)


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