import datetime

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from functools import wraps
from typing import Callable, List

from database.schemas import Event, User, EventRel, PaymentsEventsUsers, Payment, ReservedEvent, Tournament, Team, \
    TeamUsers
from routers.utils import convert_date, convert_time, get_weekday_from_date
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
    keyboard.row(InlineKeyboardButton(text="🗓️ Все события", callback_data=f"menu_all-events"))
    keyboard.row(InlineKeyboardButton(text="👤 Мой профиль", callback_data=f"menu_profile"))
    keyboard.row(InlineKeyboardButton(text="🏐 Мои события", callback_data=f"menu_my-events"))

    keyboard.adjust(2)
    return keyboard


@back_button("all-events")
def events_keyboard(events: list[EventRel | Tournament], user: User, reserved_events: List[ReservedEvent]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода пользователю"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        # для чемпионатов
        if type(event) == Tournament:
            # TODO учесть где уже зареганы или в резерв
            time = event.date.time().strftime("%H:%M")

            keyboard.row(InlineKeyboardButton(text=f"{time} 🏁 {event.type}",
                                              callback_data=f"user-tournament_{event.id}"))

        elif type(event) == EventRel:
            time = event.date.time().strftime("%H:%M")

            registered = ""
            if user in event.users_registered:
                registered = "✅️" + " "

            reserved = ""
            if event.id in [reserve.event.id for reserve in reserved_events]:
                reserved = "📝" + " "

            keyboard.row(InlineKeyboardButton(text=f"{registered}{reserved}{time} {event.type}",
                                              callback_data=f"user-event_{event.id}"))

    keyboard.adjust(1)
    return keyboard


@back_button("user-menu")
def dates_keyboard(dates: dict[str:int]) -> InlineKeyboardBuilder:
    """Клавиатура со всеми датами мероприятий"""
    keyboard = InlineKeyboardBuilder()

    for key in dates.keys():
        weekday = get_weekday_from_date(key)
        count = dates[key]
        if count == 1:
            events = "мероприятие"
        elif count in [2, 3, 4]:
            events = "мероприятия"
        else:
            events = "мероприятий"

        keyboard.row(

            InlineKeyboardButton(text=f"{key} {weekday} ({count} {events})", callback_data=f"events-date_{key}"))

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
def user_events(payments: list[PaymentsEventsUsers], reserved_events: list[ReservedEvent]) -> InlineKeyboardBuilder:
    """Мероприятия куда пользователь зарегистрирован"""
    keyboard = InlineKeyboardBuilder()
    reserved_events_ids = [reserve.event.id for reserve in reserved_events]

    for payment in payments:
        date = convert_date(payment.event.date)
        weekday = settings.weekdays[datetime.datetime.weekday(payment.event.date)]

        if payment.event.id in reserved_events_ids:
            status = "📝"
        elif payment.paid_confirm:
            status = "✅️"
        else:
            status = "⏳"

        keyboard.row(InlineKeyboardButton(
            text=f"{status} {date} ({weekday}) {payment.event.type}",
            callback_data=f"my-events_{payment.id}")
        )

    keyboard.adjust(1)
    return keyboard


def my_event_card_keyboard(payment: Payment, reserved_event: bool = False) -> InlineKeyboardBuilder:
    """Клавиатура в моем мероприятии"""
    keyboard = InlineKeyboardBuilder()

    # если оплата подтверждена
    if payment.paid_confirm:
        if reserved_event:
            keyboard.row(
                InlineKeyboardButton(
                    text=f"❌ Отменить запись в резерв",
                    callback_data=f"unreg-user-reserve_{payment.event_id}_{payment.user_id}"))
        else:
            keyboard.row(
                InlineKeyboardButton(
                    text=f"❌ Отменить запись",
                    callback_data=f"unreg-user_{payment.event_id}_{payment.user_id}"
                )
            )

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"menu_my-events"))

    return keyboard


def tournament_card_keyboard(tournament_id: int, user_id: int, back_to: str, teams: list[TeamUsers]) -> InlineKeyboardBuilder:
    """Зарегистрироваться на чемпионат"""
    keyboard = InlineKeyboardBuilder()

    # Сортируем по названию команды
    ordered_teams = [team for team in sorted(teams, key=lambda x: x.title)]

    if ordered_teams:
        for team in ordered_teams:
            keyboard.row(InlineKeyboardButton(text=f"{team.title}", callback_data=f"register-in-team_{team.team_id}"))

    keyboard.row(InlineKeyboardButton(text=f"✍️ Зарегистрировать команду", callback_data=f"register-new-team_{tournament_id}"))
    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"{back_to}"))

    return keyboard


def event_card_keyboard(event_id: int,
                        user_id: int,
                        payment: Payment | None,
                        back_to: str,
                        full_event: bool) -> InlineKeyboardBuilder:
    """Зарегистрироваться и отменить регистрацию"""
    keyboard = InlineKeyboardBuilder()

    # пользователь еще не регистрировался
    if not payment:
        # если все места заняты, предлагаем в резерв
        if full_event:
            keyboard.row(InlineKeyboardButton(text=f"📝 Записаться в резерв", callback_data=f"reg-user-reserve_{event_id}_{user_id}"))
        # свободные места есть
        else:
            keyboard.row(InlineKeyboardButton(text=f"✅ Записаться", callback_data=f"reg-user_{event_id}_{user_id}"))

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"{back_to}"))
    return keyboard


def yes_no_keyboard_for_unreg_from_event(event_id: int, user_id: int, payment_id: int, reserved_event: bool = False) -> InlineKeyboardBuilder:
    """Подтверждение удаления с события в Моих мероприятиях"""
    keyboard = InlineKeyboardBuilder()

    if reserved_event:
        keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"unreg-user-confirmed-reserve_{event_id}_{user_id}"))
    else:
        keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"unreg-user-confirmed_{event_id}_{user_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"my-events_{payment_id}"))
    keyboard.adjust(2)

    return keyboard


# PAYMENTS
def payment_confirm_keyboard(user: User, event: Event, to_reserve: bool = False) -> InlineKeyboardBuilder:
    """Клавиатура с кнопкой подтверждения оплаты"""
    keyboard = InlineKeyboardBuilder()
    if to_reserve:
        keyboard.row(InlineKeyboardButton(
            text="Оплатил(а)", callback_data=f"paid-reserve_{user.id}_{event.id}"
        ))
    else:
        keyboard.row(
            InlineKeyboardButton(
                text="Оплатил(а)", callback_data=f"paid_{user.id}_{event.id}")
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


def confirm_decline_keyboard(event_id: int, user_id: int, to_reserve: bool = False) -> InlineKeyboardBuilder:
    """Клавиатура для подтверждения или отклонения платежа админом"""
    keyboard = InlineKeyboardBuilder()
    if to_reserve:
        keyboard.row(
            InlineKeyboardButton(text="Подтвердить ✅", callback_data=f"admin-payment-reserve_ok_{event_id}_{user_id}"),
            InlineKeyboardButton(text="Отклонить ❌", callback_data=f"admin-payment-reserve_cancel_{event_id}_{user_id}"),
        )
    else:
        keyboard.row(
            InlineKeyboardButton(text="Подтвердить ✅", callback_data=f"admin-payment_ok_{event_id}_{user_id}"),
            InlineKeyboardButton(text="Отклонить ❌", callback_data=f"admin-payment_cancel_{event_id}_{user_id}"), )
    return keyboard


# ADMIN KEYBOARDS
def events_keyboard_admin(events: list[Event]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода админу"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        date = convert_date(event.date)
        time = convert_time(event.date)
        keyboard.row(InlineKeyboardButton(text=f"{date} {time} {event.type}", callback_data=f"admin-event_{event.id}"))

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


def tournament_levels_keyboards() -> InlineKeyboardBuilder:
    """Клавиатура уровня турниров"""
    keyboard = InlineKeyboardBuilder()

    for k, v in settings.tournament_points.items():
        keyboard.row(InlineKeyboardButton(text=f"{v[0]}", callback_data=f"admin-add-tournament-level_{k}"))
    keyboard.adjust(2)

    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="button_cancel"))

    return keyboard


def cancel_update_profile_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для отмены редактирования профиля"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="button_update_cancel"))
    return keyboard


def cancel_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для отмены создания пользователя админом"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="button_cancel"))
    return keyboard


def back_keyboard(back_to: str) -> InlineKeyboardBuilder:
    """Клавиатура назад"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔙 назад", callback_data=f"{back_to}"))
    return keyboard
