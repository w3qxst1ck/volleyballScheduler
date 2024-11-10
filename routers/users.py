from datetime import datetime

from aiogram import Router, types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from routers.middlewares import CheckPrivateMessageMiddleware
from routers import keyboards as kb, messages as ms
from routers.fsm_states import RegisterUserFSM
from database import schemas
from database.orm import AsyncOrm
from routers import utils
import settings

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.callback_query.middleware.register(CheckPrivateMessageMiddleware())


# REGISTRATION
@router.message(Command("start"))
# @router.message(Command("menu"))
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


@router.message(Command("menu"))
@router.callback_query(lambda callback: callback.data.split("_")[1] == "user-menu")
async def back_menu_handler(callback: types.CallbackQuery) -> None:
    """Главное меню пользователя"""
    if type(callback) == types.Message:
        await callback.answer("Главное меню", reply_markup=kb.menu_users_keyboard().as_markup())

    else:
        await callback.message.edit_text("Главное меню", reply_markup=kb.menu_users_keyboard().as_markup())


# USER EVENTS
@router.callback_query(lambda callback: callback.data.split("_")[1] == "all-events")
async def user_events_dates_handler(callback: types.CallbackQuery) -> None:
    """Вывод дат с мероприятиями мероприятий"""
    # events = await AsyncOrm.get_events_with_users(only_active=True)

    events = await AsyncOrm.get_events(only_active=True)
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
        f"Мероприятия на <b>{date_str}</b>:\n\nМероприятия, на которые вы уже зарегистрированы, помечены '✔️'",
        reply_markup=kb.events_keyboard(events, user).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "user-event")
async def user_event_handler(callback: types.CallbackQuery) -> None:
    """Вывод карточки мероприятия для пользователя"""

    event_id = int(callback.data.split("_")[1])

    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))
    event_with_users = await AsyncOrm.get_event_with_users(event_id)

    # если зарегистрирован
    if user in event_with_users.users_registered:
        registered = True
    # не зарегистрирован
    else:
        registered = False

    msg = ms.event_card_for_user_message(event_with_users, registered)

    await callback.message.edit_text(
        msg,
        reply_markup=kb.event_card_keyboard(
            event_id,
            user.id,
            registered,
            f"events-date_{utils.convert_date(event_with_users.date)}",
            "events"
        ).as_markup()
    )


@router.callback_query(lambda callback: callback.data.split("_")[0] == "reg-user")
async def register_user_on_event(callback: types.CallbackQuery) -> None:
    """Регистрация пользователя на мероприятие"""
    event_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    # TODO сделать проверку на уровень

    event = await AsyncOrm.get_event_by_id(event_id)
    user = await AsyncOrm.get_user_by_id(user_id)

    msg = ms.invoice_message_for_user(event)

    await callback.message.edit_text(msg, reply_markup=kb.payment_confirm_keyboard(user, event).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "paid")
async def register_paid_event(callback: types.CallbackQuery, bot: Bot) -> None:
    """Подтверждение оплаты от пользователя"""
    user_id = int(callback.data.split("_")[1])
    event_id = int(callback.data.split("_")[2])

    # создание платежа в БД
    await AsyncOrm.create_payments(user_id, event_id)

    msg = "Дождитесь подтверждения оплаты от администратора\n\n" \
              "Вы можете отслеживать статус оплаты во вкладке \"🏐 Мои мероприятия\""

    # оповещение администратора
    user = await AsyncOrm.get_user_by_id(user_id)
    event = await AsyncOrm.get_event_by_id(event_id)

    msg_to_admin = f"Пользователь <b>{user.firstname} {user.lastname}</b> оплатил \"{event.type} {event.title}\" " \
                   f"на сумму {event.price} руб. \n\nПодтвердите или отклоните оплату"
    await bot.send_message(
        settings.settings.admins[0],
        msg_to_admin,
        reply_markup=kb.confirm_decline_keyboard(event_id, user_id).as_markup()
    )

    # TODO что делать с теми кому оплату не подтвердили
    # TODO если админ подтвердил сделать запись в таблице EventsUsers
    # TODO как часто чистить оплаты

    await callback.message.edit_text(msg, reply_markup=kb.main_keyboard_or_my_events().as_markup())



# USER ALREADY REGISTERED EVENTS
@router.callback_query(lambda callback: callback.data.split("_")[1] == "my-events")
async def user_event_registered_handler(callback: types.CallbackQuery) -> None:
    """Вывод мероприятий куда пользователь уже зарегистрирован"""
    events = await AsyncOrm.get_payments_with_events_and_users(str(callback.from_user.id))
    if not events:
        msg = "Вы пока никуда не зарегистрировались\n\nВы можете это сделать во вкладке \n\"🗓️ Все мероприятия\""
    else:
        msg = "Мероприятия куда вы записывались:\n\n✅ - оплаченные мероприятия\n⏳ - ожидается подтверждение оплаты от администратора"

    await callback.message.edit_text(msg, reply_markup=kb.user_events(events).as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "my-events")
async def my_event_info_handler(callback: types.CallbackQuery) -> None:
    """Карточка события в Моих мероприятиях"""
    payment_id = int(callback.data.split("_")[1])

    payment = await AsyncOrm.get_payment_by_id(payment_id)
    event = await AsyncOrm.get_event_with_users(payment.event_id)

    msg = ms.my_event_card_for_user_message(payment, event)

    await callback.message.edit_text(msg, reply_markup=kb.my_event_card_keyboard(
        paid_confirmed=payment.paid_confirm,
        event_id=event.id,
        user_id=payment.user_id
    ).as_markup())


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