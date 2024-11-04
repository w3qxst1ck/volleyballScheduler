from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from functools import wraps
from typing import Callable

from database.schemas import Event, User, EventRel
from routers.utils import convert_date


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
    keyboard.row(InlineKeyboardButton(text="🗓️ Мероприятия", callback_data=f"menu_events"))
    keyboard.row(InlineKeyboardButton(text="👤 Профиль", callback_data=f"menu_profile"))
    keyboard.row(InlineKeyboardButton(text="🏐 Мои мероприятия", callback_data=f"menu_my-events"))

    keyboard.adjust(2)
    return keyboard


@back_button("user-menu")
def events_keyboard_users(events: list[Event]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода пользователю"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        date = convert_date(event.date)
        keyboard.row(InlineKeyboardButton(text=f"{date} {event.title}", callback_data=f"user-event_{event.id}"))

    keyboard.adjust(1)
    return keyboard


@back_button("user-menu")
def user_profile_keyboard() -> InlineKeyboardBuilder:
    """Профиль пользователя"""
    keyboard = InlineKeyboardBuilder()
    return keyboard


@back_button("user-menu")
def user_events(events: list[Event]) -> InlineKeyboardBuilder:
    """Мероприятия куда пользователь зарегистрирован"""
    keyboard = InlineKeyboardBuilder()
    for event in events:
        date = convert_date(event.date)
        keyboard.row(InlineKeyboardButton(text=f"{date} {event.title}", callback_data=f"my-events_{event.id}"))

    keyboard.adjust(1)
    return keyboard


def event_card_keyboard(event_id: int, user_id: int, registered: bool) -> InlineKeyboardBuilder:
    """Зарегистрироваться и отменить регистрацию"""
    keyboard = InlineKeyboardBuilder()

    if registered:
        keyboard.row(InlineKeyboardButton(text=f"❌ Отменить регистрацию", callback_data=f"unreg-user_{event_id}_{user_id}"))
    else:
        keyboard.row(InlineKeyboardButton(text=f"✅ Зарегистрироваться", callback_data=f"reg-user_{event_id}_{user_id}"))

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"menu_my-events"))
    return keyboard


# ADMIN KEYBOARDS
def events_keyboard_admin(events: list[Event]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода админу"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        date = convert_date(event.date)
        keyboard.row(InlineKeyboardButton(text=f"{date} {event.title}", callback_data=f"admin-event_{event.id}"))

    keyboard.adjust(1)
    return keyboard


def event_card_keyboard_admin(event: EventRel) -> InlineKeyboardBuilder:
    """Выбор участника события"""
    keyboard = InlineKeyboardBuilder()

    if event.users_registered:
        for idx, user in enumerate(event.users_registered, start=1):
            keyboard.row(InlineKeyboardButton(text=f"{idx}", callback_data=f"admin-event-user_{event.id}_{user.id}"))
        keyboard.adjust(3)

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data="back-admin-events"))
    return keyboard


def yes_no_keyboard_for_admin_delete_user_from_event(event_id: int, user_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления участника с события"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"admin-event-user-delete_{event_id}_{user_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"admin-event_{event_id}"))
    keyboard.adjust(2)

    return keyboard


def cancel_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для отмены создания пользователя админом"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="button_cancel"))
    return keyboard