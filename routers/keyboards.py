import datetime

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from functools import wraps
from typing import Callable, List

from database.schemas import Event, User, EventRel, PaymentsEventsUsers, Payment, ReservedEvent, Tournament, \
    TeamUsers, TournamentTeams, TournamentPayment, TournamentPaid
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
def events_keyboard(events: list[EventRel | Tournament],
                    user: User,
                    reserved_events: List[ReservedEvent],
                    ) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода пользователю"""
    keyboard = InlineKeyboardBuilder()

    # сортировка по времени
    sorted_events = sorted(events, key=lambda e: e.date)

    for event in sorted_events:

        # для турниров
        if type(event) == TournamentTeams:
            # делим пользователей на основных и резервных
            main_users_id = []
            reserve_users_id = []
            for team in event.teams:
                for team_user in team.users:
                    if team.reserve:
                        reserve_users_id.append(team_user.id)
                    else:
                        main_users_id.append(team_user.id)

            if user.id in main_users_id:
                registered = "✅️ "

            elif user.id in reserve_users_id:
                registered = "📝 "

            else:
                registered = ""

            time = event.date.time().strftime("%H:%M")

            keyboard.row(InlineKeyboardButton(text=f"{registered}{time} 🏆 {event.type}",
                                              callback_data=f"user-tournament_{event.id}"))

        # для всех событий кроме турниров
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
def user_profile_keyboard(has_gender: bool) -> InlineKeyboardBuilder:
    """Профиль пользователя"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="📝 Изменить имя", callback_data=f"update_user_profile")
    )
    if not has_gender:
        keyboard.row(
            InlineKeyboardButton(text="👥 Указать пол", callback_data=f"choose_gender")
        )
    return keyboard


def choose_gender_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура выбора пола"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Мужской", callback_data=f"update_gender|male"))
    keyboard.row(InlineKeyboardButton(text="Женский", callback_data=f"update_gender|female"))
    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"menu_profile"))

    return keyboard


def confirm_choose_gender_keyboard(gender: str) -> InlineKeyboardBuilder:
    """Клавиатура подтверждения выбора пола"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(text="Да", callback_data=f"confirm_update_gender|{gender}"),
        InlineKeyboardButton(text="Нет", callback_data=f"choose_gender")
    )

    return keyboard


@back_button("user-menu")
def user_events(events: list[PaymentsEventsUsers | Tournament],
                reserved_events: list[ReservedEvent]) -> InlineKeyboardBuilder:
    """Мероприятия куда пользователь зарегистрирован"""
    keyboard = InlineKeyboardBuilder()
    reserved_events_ids = [reserve.event.id for reserve in reserved_events]

    for event in events:
        # для турниров
        if type(event) == Tournament:
            date = convert_date(event.date)
            weekday = settings.weekdays[datetime.datetime.weekday(event.date)]

            keyboard.row(InlineKeyboardButton(
                text=f"🏆 {date} ({weekday}) {event.type}",
                callback_data=f"my-tournament_{event.id}")
            )

        # для остальных мероприятий
        else:
            date = convert_date(event.event.date)
            weekday = settings.weekdays[datetime.datetime.weekday(event.event.date)]

            if event.event.id in reserved_events_ids:
                status = "📝"
            elif event.paid_confirm:
                status = "✅️"
            else:
                status = "⏳"

            keyboard.row(InlineKeyboardButton(
                text=f"{status} {date} ({weekday}) {event.event.type}",
                callback_data=f"my-events_{event.id}")
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


def tournament_card_keyboard(tournament: Tournament, user_id: int, back_to: str, main_teams: list[TeamUsers],
                             reserve_teams: List[TeamUsers], wrong_level: bool = False) -> InlineKeyboardBuilder:
    """Зарегистрироваться на чемпионат"""
    keyboard = InlineKeyboardBuilder()
    user_already_has_team: bool = False

    # кнопки основных команд
    if main_teams:
        for team in main_teams:
            # Проверяем зарегистрирован ли пользователь
            registered = ""
            registered_users = [user.id for user in team.users]
            if user_id in registered_users:
                registered = "✅️ "
                user_already_has_team = True

            if back_to == "menu_my-events":
                keyboard.row(InlineKeyboardButton(text=f"{registered}{team.title}", callback_data=f"register-in-team_{team.team_id}_{tournament.id}_me"))
            else:
                keyboard.row(InlineKeyboardButton(text=f"{registered}{team.title}", callback_data=f"register-in-team_{team.team_id}_{tournament.id}_mm"))

    # кнопки резервных команд
    if reserve_teams:
        for team in reserve_teams:
            # Проверяем зарегистрирован ли пользователь
            registered = ""
            registered_users = [user.id for user in team.users]
            if user_id in registered_users:
                registered = "✅️ "
                user_already_has_team = True

            keyboard.row(InlineKeyboardButton(text=f"{registered}{team.title} (резерв)", callback_data=f"register-in-team_{team.team_id}_{tournament.id}"))

    # проверка не состоит ли участник в другой команде
    if not user_already_has_team:
        # если уровень не подходит записаться нельзя
        if not wrong_level:
        # проверка свободных мест для команд
            if len(main_teams) < tournament.max_team_count:
                keyboard.row(InlineKeyboardButton(text=f"✍️ Зарегистрировать команду", callback_data=f"register-new-team_{tournament.id}"))
            else:
                keyboard.row(InlineKeyboardButton(text=f"📝 Записать команду в резерв", callback_data=f"register-reserve-team_{tournament.id}"))
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


def payment_tournament_confirm_keyboard(team_id: int, tournament_id: int) -> InlineKeyboardBuilder:
    """Клавиатура с кнопкой подтверждения оплаты для турниров"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(
            text="Оплатил(а)", callback_data=f"t-paid_{team_id}_{tournament_id}")
    )

    keyboard.row(InlineKeyboardButton(text="🔙 назад", callback_data=f"register-in-team_{team_id}_{tournament_id}_mm"))

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


def admin_confirm_tournament_payment_keyboard(team_id: int, tournament_id: int) -> InlineKeyboardBuilder:
    """Клавиатура для подтверждения или отклонения платежа админом для турниров"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="Подтвердить ✅", callback_data=f"tournament-payment_ok_{team_id}_{tournament_id}"),
        InlineKeyboardButton(text="Отклонить ❌", callback_data=f"tournament-payment_cancel_{team_id}_{tournament_id}"),
    )
    return keyboard


# ADMIN KEYBOARDS
def events_keyboard_admin(events: list[Event | Tournament]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода админу"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        date = convert_date(event.date)
        time = convert_time(event.date)

        # турнир
        if type(event) == Tournament:
            keyboard.row(InlineKeyboardButton(text=f"🏆 {date} {time} {event.type}", callback_data=f"admin-tournament_{event.id}"))
        # тренировка
        else:
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


def tournament_card_admin_keyboard(main_teams: List[TeamUsers], reserve_teams: List[TeamUsers], tournament_id: int) -> InlineKeyboardBuilder:
    """Карточка турнира для администратора"""
    keyboard = InlineKeyboardBuilder()
    all_teams: List[TeamUsers] = main_teams + reserve_teams

    if all_teams:
        for idx, team in enumerate(all_teams, start=1):
            keyboard.row(InlineKeyboardButton(text=f"{team.title}", callback_data=f"admin-delete-team_{tournament_id}_{team.team_id}"))
        keyboard.adjust(3)

    keyboard.row(InlineKeyboardButton(text=f"🗑️ Удалить турнир", callback_data=f"admin-t-delete_{tournament_id}"))
    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data="back-admin-events"))
    return keyboard


def tournament_card_level_keyboard(main_teams: List[TeamUsers], reserve_teams: List[TeamUsers], tournament_id: int) -> InlineKeyboardBuilder:
    """Карточка турнира для уровней"""
    keyboard = InlineKeyboardBuilder()
    all_teams: List[TeamUsers] = main_teams + reserve_teams

    if all_teams:
        for idx, team in enumerate(all_teams, start=1):
            keyboard.row(InlineKeyboardButton(text=f"{team.title}", callback_data=f"admin-t-level-team_{tournament_id}_{team.team_id}"))
        keyboard.adjust(3)

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data="back-admin-levels"))
    return keyboard


def choose_player_for_level(users: List[User], tournament_id: int, team_id: int) -> InlineKeyboardBuilder:
    """Клавиатура с выбора участника команды для уровня"""
    keyboard = InlineKeyboardBuilder()

    for idx, user in enumerate(users, start=1):
        keyboard.row(InlineKeyboardButton(text=f"{idx}", callback_data=f"admin-t-level-user_{tournament_id}_{team_id}_{user.id}"))
    keyboard.adjust(3)

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"admin-t-levels_{tournament_id}"))
    return keyboard


def yes_no_keyboard_for_admin_delete_user_from_event(event_id: int, user_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления участника с события"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"admin-event-user-delete_{event_id}_{user_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"admin-event_{event_id}"))
    keyboard.adjust(2)

    return keyboard


def admin_confirmation_delete_team_keyboard(tournament_id: int, team_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления команды с турнира"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"delete-team-confirmed_{tournament_id}_{team_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"admin-tournament_{tournament_id}"))
    keyboard.adjust(2)

    return keyboard


def yes_no_keyboard_for_admin_delete_event(event_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления события"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"admin-event-delete-confirm_{event_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"admin-event_{event_id}"))
    keyboard.adjust(2)

    return keyboard


def admin_confirmation_delete_tournament_keyboard(tournament_id: int) -> InlineKeyboardBuilder:
    """Подтверждение удаления турнира"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"admin-t-delete-confirm_{tournament_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"admin-tournament_{tournament_id}"))
    keyboard.adjust(2)

    return keyboard


def back_to_admin_events() -> InlineKeyboardBuilder:
    """Назад к событиям для админа"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data="back-admin-events"))

    return keyboard


def events_levels_keyboard_admin(events: list[Event | Tournament]) -> InlineKeyboardBuilder:
    """Клавиатура с мероприятиями для вывода админу для выставления уровней"""
    keyboard = InlineKeyboardBuilder()

    for event in events:
        date = convert_date(event.date)

        # турниры
        if type(event) == Tournament:
            keyboard.row(InlineKeyboardButton(text=f"🏆 {date} {event.type}", callback_data=f"admin-t-levels_{event.id}"))
        # тренировки
        else:
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


def t_levels_keyboards(tournament_id: int, team_id: int, user_id: int) -> InlineKeyboardBuilder:
    """Инлайн клавиатура с уровнями для выставления пользователю на турнирах"""
    keyboard = InlineKeyboardBuilder()

    for k, v in settings.levels.items():
        keyboard.row(InlineKeyboardButton(text=f"{v}", callback_data=f"admin-add-t-level_{tournament_id}_{user_id}_{k}"))
    keyboard.adjust(2)

    keyboard.row(InlineKeyboardButton(text=f"🔙 назад", callback_data=f"admin-t-level-team_{tournament_id}_{team_id}"))

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


def back_to_tournament(tournament_id: int) -> InlineKeyboardBuilder:
    """Клавиатура для возвращения к карточке чемпионата"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Вернуться к турниру", callback_data=f"user-tournament_{tournament_id}"))

    return keyboard


def team_card_keyboard(tournament_id: int, team_id: int, user_already_in_team: bool,
                       user_already_has_another_team: bool, user_is_team_leader: bool,
                       over_points: bool, over_players_count: bool, wrong_level: bool,
                       payment: TournamentPayment | None,
                       back_to: str) -> InlineKeyboardBuilder:
    """
    Клавиатура карточки команды
    user_already_in_team: bool - пользователь уже в этой команде
    user_already_has_another_team: bool - пользователь уже в другой команде на этом турнире
    user_is_team_leader: bool - является ли пользователь капитаном команды
    over_points: bool - количество баллов команды с пользователем превысит лимит
    over_players_count: bool - количество игроков команды с пользователем превысит лимит
    wrong_level: bool - неподходящий уровень для турнира
    """
    keyboard = InlineKeyboardBuilder()

    if user_is_team_leader:
        if not payment:
            keyboard.row(InlineKeyboardButton(text="Внести оплату",
                                              callback_data=f"pay-for-team_{team_id}_{tournament_id}"))
        keyboard.row(
            InlineKeyboardButton(text="Выбрать либеро", callback_data=f"choose-libero_{team_id}_{tournament_id}"))

    # Если пользователь еще не в команде, у него нет другой команды
    if not user_already_in_team and not user_already_has_another_team and not over_points and not over_players_count:
        # если суммарное количество баллов не будет превышать лимит
        if not wrong_level:
            keyboard.row(InlineKeyboardButton(text="Записаться в команду",
                                              callback_data=f"reg-user-in-team_{team_id}_{tournament_id}"))
        # предлагаем стать либеро
        elif not over_players_count:
            keyboard.row(InlineKeyboardButton(text="Стать либеро команды",
                                              callback_data=f"reg-libero-in-team_{team_id}_{tournament_id}"))
    # Если уже зарегистрирован
    elif user_already_in_team:
        keyboard.row(InlineKeyboardButton(text="Выйти из команды",
                                          callback_data=f"leave-user-from-team_{team_id}_{tournament_id}"))

    keyboard.row(InlineKeyboardButton(text="🔙 назад", callback_data=back_to))

    return keyboard


def choose_libero(team: TeamUsers, tournament_id: int) -> InlineKeyboardBuilder:
    """Клавиатура выбора либеро для капитана"""
    keyboard = InlineKeyboardBuilder()

    for idx, user in enumerate(team.users, start=1):
        if user.id == team.team_libero_id:
            continue
        keyboard.row(InlineKeyboardButton(text=f"{user.firstname} {user.lastname}", callback_data=f"choose-libero-user_{team.team_id}_{tournament_id}_{user.id}"))

    keyboard.row(InlineKeyboardButton(text="🔙 назад", callback_data=f"register-in-team_{team.team_id}_{tournament_id}_mm"))

    return keyboard


def choose_libero_accept(team_id: int, tournament_id: int, user_id: int) -> InlineKeyboardBuilder:
    """Клавиатура подтверждения выбора либеро"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"choose-liber-accept_{team_id}_{tournament_id}_{user_id}"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"choose-libero_{team_id}_{tournament_id}"))

    keyboard.adjust(2)

    return keyboard


def yes_no_leave_team_keyboard(user_is_team_leader: bool, team_id: int, tournament_id: int) -> InlineKeyboardBuilder:
    """Клавиатура подтверждения выхода из команды"""
    keyboard = InlineKeyboardBuilder()

    # Для капитана предлагаем удалить команду
    if user_is_team_leader:
        keyboard.row(InlineKeyboardButton(text="Да",
                                          callback_data=f"c-del-team_{team_id}_{tournament_id}"))
        keyboard.row(InlineKeyboardButton(text="Нет",
                                          callback_data=f"register-in-team_{team_id}_{tournament_id}_mm"))
    # Для обычных пользователей
    else:
        keyboard.row(InlineKeyboardButton(text="Да",
                                          callback_data=f"del-team_{team_id}_{tournament_id}"))
        keyboard.row(InlineKeyboardButton(text="Нет",
                                          callback_data=f"register-in-team_{team_id}_{tournament_id}_mm"))

    # keyboard.row(InlineKeyboardButton(text="🔙 назад", callback_data=f"user-tournament_{tournament_id}"))
    keyboard.adjust(2)
    return keyboard


def yes_no_accept_user_in_team_keyboard(team_id: int, user_id: int, tournament_id: int, for_libero: bool = False) -> InlineKeyboardBuilder:
    """Клавиатура подтверждения принятия игрока в команду"""
    keyboard = InlineKeyboardBuilder()

    # Для назначения либеро
    if for_libero:
        keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"accept-libero-in-team_{team_id}_{user_id}_{tournament_id}"))
        keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"refuse-libero-in-team_{team_id}_{user_id}_{tournament_id}"))

    # Для приема обычных игроков
    else:
        keyboard.row(InlineKeyboardButton(text="Да", callback_data=f"accept-user-in-team_{team_id}_{user_id}_{tournament_id}"))
        keyboard.row(InlineKeyboardButton(text="Нет", callback_data=f"refuse-user-in-team_{team_id}_{user_id}_{tournament_id}"))

    return keyboard


def back_and_choose_gender_keyboard(back_to: str) -> InlineKeyboardBuilder:
    """Клавиатура назад если пол еще не указан"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="👤 Мой профиль", callback_data=f"menu_profile"))
    keyboard.row(InlineKeyboardButton(text="🔙 назад", callback_data=f"{back_to}"))
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
