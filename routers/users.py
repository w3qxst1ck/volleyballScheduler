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
            await message.answer(ms.main_menu_message(), reply_markup=kb.menu_users_keyboard().as_markup())

    # новый пользователь
    else:
        await state.set_state(RegisterUserFSM.name)
        msg = await message.answer("Для записи на спортивные события необходимо зарегистрироваться\n\n"
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
        await message.answer(ms.main_menu_message(), reply_markup=kb.menu_users_keyboard().as_markup())

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
        await callback.answer(ms.main_menu_message(), reply_markup=kb.menu_users_keyboard().as_markup())

    else:
        await callback.message.edit_text(ms.main_menu_message(), reply_markup=kb.menu_users_keyboard().as_markup())


# ALL EVENTS
@router.callback_query(lambda callback: callback.data.split("_")[1] == "all-events")
async def user_events_dates_handler(callback: types.CallbackQuery) -> None:
    """Вывод дат с мероприятиями мероприятий"""
    events = await AsyncOrm.get_events(only_active=True, days_ahead=11) # берем мероприятия за ближайших 10 дней
    events_dates = [event.date for event in events]
    unique_dates = utils.get_unique_dates(events_dates)

    msg = "Даты с событиями:"
    if not events:
        msg = "В ближайшее время нет событий"

    await callback.message.edit_text(msg, reply_markup=kb.dates_keyboard(unique_dates).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "events-date")
async def user_events_dates_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятий в выбранную дату"""
    date_str = callback.data.split("_")[1]
    date = datetime.strptime(date_str, "%d.%m.%Y")
    converted_date = utils.convert_date_named_month(date)
    weekday = settings.settings.weekdays[datetime.weekday(date)]

    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))
    events = await AsyncOrm.get_events_for_date(date)
    reserved_events = await AsyncOrm.get_reserved_events_by_user_id(user.id)

    msg = f"События на <b>{converted_date} ({weekday})</b>:\n\n" \
          f"События, на которые вы уже записаны, помечены '✅️'\n" \
          f"События, на которые вы записаны в резерв, помечены '📝'"

    await callback.message.edit_text(
        msg,
        reply_markup=kb.events_keyboard(events, user, reserved_events).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "user-event")
async def user_event_handler(callback: types.CallbackQuery) -> None:
    """Вывод карточки мероприятия для пользователя"""

    event_id = int(callback.data.split("_")[1])
    user_tg_id = str(callback.from_user.id)

    user = await AsyncOrm.get_user_by_tg_id(user_tg_id)
    event_with_users = await AsyncOrm.get_event_with_users(event_id)

    payment = await AsyncOrm.get_payment_by_event_and_user(event_id, user.id)

    # check full Event or not
    full_event: bool = len(event_with_users.users_registered) == event_with_users.places

    # получаем пользователь в резерве события
    reserved_users = await AsyncOrm.get_reserved_users_by_event_id(event_id)

    msg = ms.event_card_for_user_message(event_with_users, payment, reserved_users)

    await callback.message.edit_text(
        msg,
        disable_web_page_preview=True,
        reply_markup=kb.event_card_keyboard(
            event_id,
            user.id,
            payment,
            f"events-date_{utils.convert_date(event_with_users.date)}",
            full_event,
        ).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "reg-user"
                       or callback.data.split("_")[0] == "reg-user-reserve")
async def register_user_on_event_or_reserve(callback: types.CallbackQuery) -> None:
    """Регистрация пользователя на событие или в резерв"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])
    # определение запись в основу или резерв
    to_reserve = callback.data.split("_")[0] == "reg-user-reserve"

    event_with_users = await AsyncOrm.get_event_with_users(event_id)
    user = await AsyncOrm.get_user_by_id(user_id)

    # если уровень соответствует
    if not user.level or user.level >= event_with_users.level:

        msg = ms.invoice_message_for_user(event_with_users, to_reserve=to_reserve)
        await callback.message.edit_text(
            msg,
            disable_web_page_preview=True,
            reply_markup=kb.payment_confirm_keyboard(user, event_with_users, to_reserve=to_reserve).as_markup()
        )

    # если уровень ниже
    else:
        payment = await AsyncOrm.get_payment_by_event_and_user(event_id, user.id)

        # получаем пользователей в резерве события
        reserved_users = await AsyncOrm.get_reserved_users_by_event_id(event_id)

        msg = ms.event_card_for_user_message(event_with_users, payment, reserved_users)
        await callback.message.edit_text("❗Вы не можете записаться на данное событие, "
                                         "так как ваш уровень ниже необходимого")
        await callback.message.answer(
            msg,
            disable_web_page_preview=True,
            reply_markup=kb.event_card_keyboard(
                event_id,
                user.id,
                payment,
                f"events-date_{utils.convert_date(event_with_users.date)}",
                full_event=to_reserve
            ).as_markup()
        )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "paid"
                       or callback.data.split("_")[0] == "paid-reserve")
async def register_paid_event(callback: types.CallbackQuery, bot: Bot) -> None:
    """Подтверждение оплаты от пользователя в основной состав события или резерв"""
    # определение запись в резерв или основу
    to_reserve = callback.data.split("_")[0] == "paid-reserve"
    user_id = int(callback.data.split("_")[1])
    event_id = int(callback.data.split("_")[2])

    user = await AsyncOrm.get_user_by_id(user_id)
    event = await AsyncOrm.get_event_by_id(event_id)

    # если мероприятие уже неактивно
    if not event.active:
        await callback.message.edit_text(
            "⚠️ Запись невозможна, так как данное событие уже недоступно\n\nВы можете посмотреть доступные"
            " события в главном меню /menu во вкладке \"🗓️ Все события\"",
        )
        return

    # создание платежа в БД
    await AsyncOrm.create_payments(user_id, event_id)

    # оповещение администратора
    event_date = utils.convert_date(event.date)
    event_time = utils.convert_time(event.date)

    if to_reserve:
        msg_to_admin = f"Пользователь <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                       f"оплатил <b>запись в резерв</b> события <b>{event.type}</b> \"{event.title}\" <b>{event_date} {event_time}</b> " \
                       f"на сумму <b>{event.price} руб.</b> \n\nПодтвердите или отклоните оплату"
    else:
        msg_to_admin = f"Пользователь <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                       f"оплатил <b>{event.type}</b> \"{event.title}\" <b>{event_date} {event_time}</b> " \
                       f"на сумму <b>{event.price} руб.</b> \n\nПодтвердите или отклоните оплату"

    # формирование клавиатуры для подтверждения оплаты в резерв или основу
    if to_reserve:
        reply_markup = kb.confirm_decline_keyboard(event_id, user_id, to_reserve=True)
    else:
        reply_markup = kb.confirm_decline_keyboard(event_id, user_id)

    await bot.send_message(
        settings.settings.main_admin_tg_id,
        msg_to_admin,
        reply_markup=reply_markup.as_markup()
    )

    # формирование текста ответу пользователю об ожидании подтверждения оплаты
    if to_reserve:
        answer_text = f"🔔 <b>Автоматическое уведомление</b>\n\n"\
                      f"Ваш платеж на сумму {event.price} руб. ожидает подтверждение администратором. "\
                      f"После подтверждения вам будет отправлено уведомление о записи <b>в резерв события</b>."
    else:
        answer_text = f"🔔 <b>Автоматическое уведомление</b>\n\n"\
                      f"Ваш платеж на сумму {event.price} руб. ожидает подтверждение администратором. "\
                      f"После подтверждения вам будет отправлено уведомление о записи на событие."

    await callback.message.edit_text(answer_text)

    msg = "⏳ <b>Дождитесь подтверждения оплаты от администратора</b>\n\n" \
          "Вы можете отслеживать статус оплаты во вкладке \"👨🏻‍💻 Главное меню\" в разделе \"🏐 Мои события\""

    await callback.message.answer(msg)
    await callback.message.answer(ms.main_menu_message(), reply_markup=kb.menu_users_keyboard().as_markup())


# USER ALREADY REGISTERED EVENTS
@router.callback_query(lambda callback: callback.data.split("_")[1] == "my-events")
async def user_event_registered_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятий куда пользователь уже зарегистрирован"""
    payments = await AsyncOrm.get_user_payments_with_events_and_users(str(callback.from_user.id))
    active_events = list(filter(lambda payment: payment.event.active == True, payments))

    # получение зарезервированных мероприятий
    if payments:
        user_id = payments[0].user_id
        reserved_events = await AsyncOrm.get_reserved_events_by_user_id(user_id)
    else:
        reserved_events = []

    if not active_events:
        msg = "Вы пока никуда не записаны\n\nВы можете это сделать во вкладке \n\"🗓️ Все события\""
    else:
        msg = "<b>События куда вы записались:</b>\n\n" \
              "✅ - оплаченные события\n" \
              "📝 - резерв на событие\n" \
              "⏳ - ожидается подтверждение оплаты от администратора"

    await callback.message.edit_text(msg, reply_markup=kb.user_events(active_events, reserved_events).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "my-events")
async def my_event_info_handler(callback: types.CallbackQuery) -> None:
    """Карточка события в Моих мероприятиях"""
    payment_id = int(callback.data.split("_")[1])

    payment = await AsyncOrm.get_payment_by_id(payment_id)
    event = await AsyncOrm.get_event_with_users(payment.event_id)
    reserved_users = await AsyncOrm.get_reserved_users_by_event_id(event.id)

    msg = ms.event_card_for_user_message(event, payment, reserved_users)

    # для кнопки отмены
    reserved_event = len(reserved_users) > 0

    await callback.message.edit_text(
        msg,
        disable_web_page_preview=True,
        reply_markup=kb.my_event_card_keyboard(payment, reserved_event).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "unreg-user")
async def unregister_form_my_event_handler(callback: types.CallbackQuery) -> None:
    """Отмена регистрации на событие в Моих мероприятиях"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    event = await AsyncOrm.get_event_by_id(event_id)
    payment = await AsyncOrm.get_payment_by_event_and_user(event_id, user_id)

    await callback.message.edit_text(
        f"<b>Вы действительно хотите отменить свою запись на событие \"{event.type}\" {utils.convert_date(event.date)} в {utils.convert_time(event.date)}?</b>",
        reply_markup=kb.yes_no_keyboard_for_unreg_from_event(event_id, user_id, payment.id).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "unreg-user-confirmed")
async def unregister_form_my_event_handler(callback: types.CallbackQuery, bot: Bot) -> None:
    """Подтверждение отмены регистрации на событие в Моих мероприятиях"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    await AsyncOrm.delete_user_from_event(event_id, user_id)
    await AsyncOrm.delete_payment(event_id, user_id)

    event = await AsyncOrm.get_event_by_id(event_id)
    # оповещение пользователя
    await callback.message.edit_text(f"🔔 <b>Автоматическое уведомление</b>\n\n"
                                     f"<b>Вы отменили запись на событие \"{event.type}\" {utils.convert_date(event.date)} в {utils.convert_time(event.date)}</b>")

    # возврат ко вкладке мои мероприятия
    events = await AsyncOrm.get_user_payments_with_events_and_users(str(callback.from_user.id))
    active_events = list(filter(lambda payment: payment.event.active == True, events))

    # получение зарезервированных мероприятий
    if events:
        user_id = events[0].user_id
        reserved_events = await AsyncOrm.get_reserved_events_by_user_id(user_id)
    else:
        reserved_events = []

    if not active_events:
        msg = "Вы пока никуда не записаны\n\nВы можете это сделать во вкладке \n\"🗓️ Все события\""
    else:
        msg = "<b>События куда вы записались:</b>\n\n" \
              "✅ - оплаченные события\n" \
              "📝 - резерв на событие\n" \
              "⏳ - ожидается подтверждение оплаты от администратора"

    await callback.message.answer(msg, reply_markup=kb.user_events(active_events, reserved_events).as_markup())

    # оповещение админа
    user = await AsyncOrm.get_user_by_id(user_id)
    admin_message = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                    f"Пользователь <b>{user.username} {user.lastname}</b> отменил запись на <b>{event.type}</b> {event.title} на " \
                    f"<b>{utils.convert_date(event.date)}</b> в <b>{utils.convert_time(event.date)}</b>"
    try:
        await bot.send_message(settings.settings.main_admin_tg_id, admin_message)
    except:
        pass


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
    msg = await callback.message.edit_text(
        "<b>Пожалуйста, отправьте сообщением вашу Фамилию, Имя (например, Иванов Иван).</b>",
        reply_markup=kb.cancel_update_profile_keyboard().as_markup()
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


@router.message(Command("test"))
async def help_handler(message: types.Message) -> None:
    """test message"""
    # user = await AsyncOrm.get_user_by_tg_id(str(message.from_user.id))
    # reserved_events = await AsyncOrm.get_reserved_events_by_user_id(user.id)
    # print(reserved_events)
    # for event in reserved_events:
    #     # await message.answer(f"{event.id} | {event.date} | {event.event.id} | {event.user.id}")
    #     await message.answer(f"{event.id} | {event.date} | {event.event.id}")

    reserved_users = await AsyncOrm.get_reserved_users_by_event_id(2)
    print(reserved_users)
    for reserve in reserved_users:
        await message.answer(f"{reserve.id} | {reserve.date} | {reserve.user.id}")


# HELP
@router.message(Command("help"))
async def help_handler(message: types.Message) -> None:
    """Help message"""
    msg = ms.get_help_message()
    await message.answer(msg)


@router.callback_query(lambda callback: callback.data == "button_update_cancel", UpdateUserFSM.name)
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel update profile"""
    await state.clear()

    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))

    message = ms.user_profile_message(user)
    await callback.message.edit_text(message, reply_markup=kb.user_profile_keyboard().as_markup())


# CANCEL BUTTON
@router.callback_query(lambda callback: callback.data == "button_cancel", StateFilter("*"))
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel FSM and delete last message"""
    await state.clear()
    await callback.message.answer("<b>Действие отменено</b> ❌")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass