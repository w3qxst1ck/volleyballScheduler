import datetime

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from functools import wraps
from typing import Callable

from database.schemas import Event, User, EventRel, PaymentsEventsUsers, Payment
from routers.utils import convert_date
from settings import settings


def back_button(callback_data: str):
    """Добавление кнопки назад для клавиатур"""
    def wrapper(func: Callable):
        @wraps(func)
        def inner(*args, **kwargs):
            result = func(*args, **kwargs)
            result.row(InlineKeyboardButton(text="🔙 назад", callback_data=f"back_{callback_data}"))
            return result
        return inner
    return wrapper


# USERS KEYBOARDS
def menu_users_keyboard() -> InlineKeyboardBuilder:
    """Основное меню для пользователей"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🗓️ Все мероприятия", callback_data=f"menu_all-events"))
    keyboard.row(InlineKeyboardButton(text="👤 Профиль", callback_data=f"menu_profile"))
    keyboard.row(InlineKeyboardButton(text="🏐 Мои мероприятия", callback_data=f"menu_my-events"))

    keyboard.adjust(2)
    return keyboard


@back_button("all-events")
def events_keyboard(events: list[EventRel], user: User) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода пользователю"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        time = event.date.time().strftime("%H:%M")

        registered = ""
        if user in event.users_registered:
            registered = "✔️" + " "

        keyboard.row(InlineKeyboardButton(text=f"{registered}{time} {event.type}", callback_data=f"user-event_{event.id}"))

    keyboard.adjust(1)
    return keyboard


@back_button("user-menu")
def dates_keyboard(dates: dict[str:int]) -> InlineKeyboardBuilder:
    """Клавиатура со всеми датами мероприятий"""
    keyboard = InlineKeyboardBuilder()

    for key in dates.keys():
        count = dates[key]
        if count == 1:
            events = "мероприятие"
        elif count in [2, 3, 4]:
            events = "мероприятия"
        else:
            events = "мероприятий"

        keyboard.row(

            InlineKeyboardButton(text=f"{key} ({count} {events})", callback_data=f"events-date_{key}"))

    keyboard.adjust(1)
    return keyboard


@back_button("user-menu")
def user_profile_keyboard() -> InlineKeyboardBuilder:
    """Профиль пользователя"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="📝 Изменить имя", callback_data=f"update_user_profile")
    )
    return keyboard


@back_button("user-menu")
def user_events(payments: list[PaymentsEventsUsers]) -> InlineKeyboardBuilder:
    """Мероприятия куда пользователь зарегистрирован"""
    keyboard = InlineKeyboardBuilder()

    for payment in payments:
        date = convert_date(payment.event.date)
        status = "✅️" if payment.paid_confirm else "⏳"

        keyboard.row(InlineKeyboardButton(
            text=f"{status} {date} {payment.event.type}",
            callback_data=f"my-events_{payment.id}")
        )

    keyboard.adjust(1)
    return keyboard


def my_event_card_keyboard(payment: Payment) -> InlineKeyboardBuilder:
    """Клавиатура в моем мероприятии"""
    keyboard = InlineKeyboardBuilder()

    # если оплата подтверждена
    if payment.paid_confirm:
        keyboard.row(
            InlineKeyboardButton(
                text=f"❌ Отменить запись",
                callback_data=f"unreg-user_{payment.event_id}_{payment.user_id}"
            )
        )

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"menu_my-events"))

    return keyboard


def event_card_keyboard(event_id: int, user_id: int, payment: Payment | None, back_to: str) -> InlineKeyboardBuilder:
    """Зарегистрироваться и отменить регистрацию"""
    keyboard = InlineKeyboardBuilder()

    # пользователь еще не регистрировался
    if not payment:
        keyboard.row(InlineKeyboardButton(text=f"✅ Записаться", callback_data=f"reg-user_{event_id}_{user_id}"))

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"{back_to}"))

    return keyboard


def yes_no_keyboard_for_unreg_from_event(event_id: int, user_id: int, payment_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления с события в Моих мероприятиях"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"unreg-user-confirmed_{event_id}_{user_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"my-events_{payment_id}"))
    keyboard.adjust(2)

    return keyboard


# PAYMENTS
def payment_confirm_keyboard(user: User, event: Event) -> InlineKeyboardBuilder:
    """Клавиатура с кнопкой подтверждения оплаты"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="Оплатил", callback_data=f"paid_{user.id}_{event.id}"),
    )

    keyboard.row(InlineKeyboardButton(text="🔙 назад", callback_data=f"user-event_{event.id}"))

    return keyboard


def main_keyboard_or_my_events() -> InlineKeyboardBuilder:
    """Клавиатура для возвращения в Главное меню или в Мои мероприятия"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="Главное меню", callback_data=f"back_user-menu"),
        InlineKeyboardButton(
            text="🏐 Мои мероприятия", callback_data=f"menu_my-events"),
    )

    keyboard.adjust(2)

    return keyboard


def confirm_decline_keyboard(event_id: int, user_id: int) -> InlineKeyboardBuilder:
    """Клавиатура для подтверждения или отклонения платежа админом"""
    """Клавиатура с кнопкой подтверждения оплаты для админа"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="Подтвердить ✅", callback_data=f"admin-payment_ok_{event_id}_{user_id}"),
        InlineKeyboardButton(
            text="Отклонить ❌", callback_data=f"admin-payment_cancel_{event_id}_{user_id}"),
    )
    return keyboard


# ADMIN KEYBOARDS
def events_keyboard_admin(events: list[Event]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода админу"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        date = convert_date(event.date)
        keyboard.row(InlineKeyboardButton(text=f"{date} {event.type}", callback_data=f"admin-event_{event.id}"))

    keyboard.adjust(1)
    return keyboard


def event_card_keyboard_admin(event: EventRel) -> InlineKeyboardBuilder:
    """Выбор участника события для удаления"""
    keyboard = InlineKeyboardBuilder()

    if event.users_registered:
        for idx, user in enumerate(event.users_registered, start=1):
            keyboard.row(InlineKeyboardButton(text=f"{idx}", callback_data=f"admin-event-user_{event.id}_{user.id}"))
        keyboard.adjust(3)

    keyboard.row(InlineKeyboardButton(text=f"🗑️ Удалить мероприятие", callback_data=f"admin-event-delete_{event.id}"))
    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data="back-admin-events"))
    return keyboard


def yes_no_keyboard_for_admin_delete_user_from_event(event_id: int, user_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления участника с события"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"admin-event-user-delete_{event_id}_{user_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"admin-event_{event_id}"))
    keyboard.adjust(2)

    return keyboard


def yes_no_keyboard_for_admin_delete_event(event_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления события"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"admin-event-delete-confirm_{event_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"admin-event_{event_id}"))
    keyboard.adjust(2)

    return keyboard


def events_levels_keyboard_admin(events: list[Event]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода админу для выставления уровней"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        date = convert_date(event.date)
        keyboard.row(InlineKeyboardButton(text=f"{date} {event.type}", callback_data=f"admin-event-levels_{event.id}"))

    keyboard.adjust(1)
    return keyboard


def event_levels_card_keyboard_admin(event: EventRel) -> InlineKeyboardBuilder:
    """Выбор участника события для выставления уровня"""
    keyboard = InlineKeyboardBuilder()

    if event.users_registered:
        for idx, user in enumerate(event.users_registered, start=1):
            keyboard.row(InlineKeyboardButton(text=f"{idx}", callback_data=f"admin-event-level-user_{event.id}_{user.id}"))
        keyboard.adjust(3)

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data="back-admin-levels"))
    return keyboard


def event_levels_keyboards(event_id: int, user_id: int) -> InlineKeyboardBuilder:
    """Инлайн клавиатура с уровнями для выставления пользователю"""
    keyboard = InlineKeyboardBuilder()

    for k, v in settings.levels.items():
        keyboard.row(InlineKeyboardButton(text=f"{v}", callback_data=f"admin-add-user-level_{event_id}_{user_id}_{k}"))
    keyboard.adjust(2)

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"admin-event-levels_{event_id}"))

    return keyboard


def levels_keyboards() -> InlineKeyboardBuilder:
    """Инлайн клавиатура с уровнями"""
    keyboard = InlineKeyboardBuilder()

    for k, v in settings.levels.items():
        keyboard.row(InlineKeyboardButton(text=f"{v}", callback_data=f"admin-add-event-level_{k}"))
    keyboard.adjust(2)

    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="button_cancel"))

    return keyboard


def cancel_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для отмены создания пользователя админом"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="button_cancel"))
    return keyboard