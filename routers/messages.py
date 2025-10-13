from typing import List

from database.schemas import User, EventRel, Event, PaymentsEventsUsers, Payment, ReservedUser, Tournament, \
    TeamUsers, TournamentPayment
from routers.utils import convert_date, convert_time, convert_date_named_month, calculate_team_points
from settings import settings
import datetime


def main_menu_message() -> str:
    """Сообщение главного меню"""
    message = "<b>Главное меню</b>\n\n" \
              "🗓 <b>Все события</b> - в этом разделе вы можете записаться на тренировку или игровой сбор.\n" \
              "👤 <b>Мой профиль</b> - в этом разделе вы можете изменить Фамилию, Имя. Узнать Ваш уровень игры.\n" \
              "🏆 <b>Турниры</b> - в этом разделе вы можете записаться на подходящий для вас турнир.\n" \
              "🏐 <b>Мои события</b> - в этом разделе вы можете ознакомиться с событиями на которые вы записаны."
    return message


def user_profile_message(user: User) -> str:
    """Сообщение с профилем пользователя"""
    gender_ru = "Мужской" if user.gender == "male" else "Женский"
    user_gender = f"👥 Пол: " + gender_ru if user.gender else f"👥 Пол: не указан"
    user_lvl = f"🔝 Уровень: " + settings.levels[user.level] if user.level else f"🔝 Уровень: еще не определен"
    message = f"<b>Профиль</b>\n\n👤 {user.firstname} {user.lastname}\n{user_gender}\n{user_lvl}"

    return message


# карточка для чемпионатов
def tournament_card_for_user_message(event: Tournament, main_teams: list[TeamUsers], reserve_teams: list[TeamUsers],
                                     for_admin: bool = False, for_levels: bool = False) -> str:
    """Информация о чемпионате с его командами"""
    date = convert_date_named_month(event.date)
    time = convert_time(event.date)
    weekday = settings.weekdays[datetime.datetime.weekday(event.date)]

    # количество команд
    teams_count = len(main_teams)
    available_places = event.max_team_count - teams_count
    max_points = settings.tournament_points[event.level][0]

    # крайняя дата оплаты
    payment_days = event.date - datetime.timedelta(days=5)
    payment_date = convert_date_named_month(payment_days)
    payment_time = convert_time(payment_days)

    message = f"📅 <b>{date}, {time} ({weekday})</b>\n"
    message += f"🏆 <b>\"{event.type}\"</b> ({max_points})\n" \
               f"  • {event.title}\n" \
               f"  • <b>Максимальное кол-во баллов команды:</b> {settings.tournament_points[event.level][1]}\n" \
               f"💰 <b>Стоимость участия для команды:</b> {event.price} руб.\n" \
               f"❗ Оплатить участие необходимо до <b>{payment_date} {payment_time}</b>\n\n" \
               f"👥 <b>Количество команд:</b> {teams_count}/{event.max_team_count} (доступно {available_places} мест)\n" \
               f"👥 <b>Количество участников в команде:</b> {event.min_team_players}-{event.max_team_players}\n" \
               f"⚠️ <b>Минимальное количество команд:</b> {event.min_team_count}\n" \
               f"📍 <b>Адрес:</b> <a href='https://yandex.ru/navi/org/volleyball_city/9644230187/?ll=30.333934%2C59.993168&z=16'>{settings.address}</a>\n\n"

    if main_teams:
        message += "<b>Зарегистрированные команды:</b>\n"

        for count, team in enumerate(main_teams, start=1):
            # баллы команды
            team_points = calculate_team_points(team.users, team.team_libero_id)

            # убираем баллы при выставлении уровней
            if for_levels:
                message += f"<b>{count}.</b> \"{team.title}\"\n"
            else:
                message += f"<b>{count}.</b> \"{team.title}\" (баллов: {team_points})\n"

    if reserve_teams:
        message += "\n<b>Резервные команды:</b>\n"

        for count, team in enumerate(reserve_teams, start=len(main_teams)+1):
            # баллы команды
            team_points = calculate_team_points(team.users, team.team_libero_id)

            # убираем баллы при выставлении уровней
            if for_levels:
                message += f"<b>{count}.</b> \"{team.title}\"\n"
            else:
                message += f"<b>{count}.</b> \"{team.title}\" (баллов: {team_points})\n"

    # Приписка для админа
    if for_admin:
        if main_teams or reserve_teams:
            message += f"\nЧтобы удалить команду с турнира, нажмите кнопку с соответствующим названием команды"
        else:
            message += f"\nНа турнир еще не зарегистрировалась ни одна команда"

    # Приписка для уровней
    if for_levels:
        if main_teams or reserve_teams:
            message += f"\nЧтобы выставить уровень, нажмите кнопку с соответствующим названием команды участника"
        else:
            message += f"\nНа турнир не зарегистрировалась ни одна команда"

    return message


# актуальная карточка для всех событий кроме чемпионатов
def event_card_for_user_message(event: EventRel, payment: Payment | None,
                                reserved_users: List[ReservedUser], admin: bool) -> str:
    """Информация о событии с его пользователями"""
    date = convert_date_named_month(event.date)
    time = convert_time(event.date)
    weekday = settings.weekdays[datetime.datetime.weekday(event.date)]

    user_registered_count = len(event.users_registered)

    message = f"📅 <b>{date}, {time} ({weekday})</b>\n"

    # пользователь еще не регистрировался
    if not payment:
        pass

    # пользователь ожидает подтверждения оплаты
    elif not payment.paid_confirm:
        message += "⏳ Ожидается подтверждение платежа от администратора\n\n"

    # проверка статуса регистрации на событие
    else:
        # пользователь зарегистрирован на событие
        if payment.user_id in [user.id for user in event.users_registered]:
            message += f"✅ <b>Вы записаны на событие \"{event.type}\"</b>\n\n"
        # пользователь зарегистрирован в резерв
        elif payment.user_id in [user.user.id for user in reserved_users]:
            message += f"📝 <b>Вы записаны в резерв на событие \"{event.type}\"</b>\n\n"

    message += f"🏐 <b>\"{event.type}\"</b>\n" \
               f"  • {event.title}\n" \
               f"  • <b>Минимальный уровень:</b> {settings.levels[event.level]}\n\n" \
               f"💰 <b>Стоимость участия:</b> {event.price} руб.\n" \
               f"👥 <b>Количество участников:</b> {user_registered_count}/{event.places} (доступно {event.places - user_registered_count} мест)\n" \
               f"⚠️ <b>Минимальное количество участников:</b> {event.min_user_count}\n" \
               f"📍 <b>Адрес:</b> <a href='https://yandex.ru/navi/org/volleyball_city/9644230187/?ll=30.333934%2C59.993168&z=16'>{settings.address}</a>\n\n"

    # если участники уже есть
    if event.users_registered:
        # сортировка по имени
        event.users_registered = sorted(event.users_registered, key=lambda user: user.firstname)

        message += "<b>Участники:</b>\n"
        for idx, user in enumerate(event.users_registered, 1):
            if admin:
                message += f"<b>{idx}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                           f"{f'({settings.levels[user.level]})' if user.level else ''}\n"
            else:
                message += f"<b>{idx}.</b> {user.firstname} {user.lastname} " \
                           f"{f'({settings.levels[user.level]})' if user.level else ''}\n"

    # если есть резерв
    if reserved_users:
        message += "\n<b>Резерв:</b>\n"

        for idx, reserve in enumerate(reserved_users, 1):
            if admin:
                message += f"<b>{idx}.</b> <a href='tg://user?id={reserve.user.tg_id}'>{reserve.user.firstname} {reserve.user.lastname}</a> " \
                           f"{f'({settings.levels[reserve.user.level]})' if reserve.user.level else ''}\n"
            else:
                message += f"<b>{idx}.</b> {reserve.user.firstname} {reserve.user.lastname} " \
                           f"{f'({settings.levels[reserve.user.level]})' if reserve.user.level else ''}\n"

    return message


# PAYMENTS
def invoice_message_for_user(event: Event, to_reserve: bool = False) -> str:
    """Сообщение о стоимости мероприятия"""
    message = ""

    # если идет запись в резерв
    if to_reserve:
        message += f"📝 После оплаты вы будете записаны в <b>резерв</b>, если кто-то из участников отменит запись, вы автоматически будете добавлены в список участников события\n\n"

    message += f"🗓 <b>Дата и время:</b> {convert_date(event.date)}, {convert_time(event.date)}\n"
    message += f"📅 <b>Событие:</b> {event.type}\n"
    message += f"💰 <b>Стоимость участия:</b> {event.price} руб.\n\n"
    message += f"Для записи на событие необходимо перевести {event.price} руб. на указанный номер телефона: <b>{settings.admin_phone} (Т-Банк)</b>\n\n"
    message += f"❗<b>ВАЖНО:</b> \n" \
               f"📩 После оплаты, пожалуйста, отправьте чек в Telegram на @Bagration178, указав следующие данные: фамилия, имя и Ваш игровой уровень!\n\n" \
               f"После завершения оплаты нажмите кнопку <b>\"Оплатил(а)\".</b>"
    return message


def invoice_message_for_team(tournament: Tournament, to_reserve: bool) -> str:
    """Сообщение о стоимости турнира"""
    message = ""

    # если идет запись в резерв
    if to_reserve:
        message += f"📝 После оплаты команда будет записана в <b>резерв</b>, если кто-то из команд отменит запись или не внесет оплату, ваша команда автоматически будет добавлена в список участников турнира\n\n"

    message += f"🗓 <b>Дата и время:</b> {convert_date(tournament.date)}, {convert_time(tournament.date)}\n"
    message += f"📅 <b>Турнир:</b> {tournament.type}\n"
    message += f"💰 <b>Стоимость участия команды:</b> {tournament.price} руб.\n\n"
    message += f"Для записи на турнир <b>капитану команды</b> необходимо перевести {tournament.price} руб. на указанный номер телефона: <b>{settings.admin_phone} (Т-Банк)</b>\n\n"
    message += f"❗<b>ВАЖНО:</b>\n" \
               f"📩 После оплаты, пожалуйста, отправьте чек в Telegram на @Bagration178, указав название вашей команды." \
               f"\n\nПосле завершения оплаты нажмите кнопку \"Оплатил(а)\"."
    return message


def event_levels_card_for_admin_message(event: EventRel) -> str:
    """Информация о событии для выставления уровней"""
    date = convert_date(event.date)
    time = convert_time(event.date)

    message = f"📅 <b>{date} {time}</b>\n\n" \
              f"<b>\"{event.type}\"</b>\n" \
              f"{event.title}\n\n" \

    if event.users_registered:
        # сортировка по имени
        event.users_registered = sorted(event.users_registered, key=lambda user: user.firstname)

        message += "Участники:\n"
        for idx, user in enumerate(event.users_registered, 1):
            message += f"<b>{idx}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                       f"{f'({settings.levels[user.level]})' if user.level else ''}\n"

        message += "\nЧтобы выставить уровень участника, нажмите кнопку с соответствующим номером участника"

    # если участников нет
    else:
        message += "<b>Участников нет</b>"

    return message


def notify_deleted_user_message(event: EventRel) -> str:
    """Оповещение пользователя о том, что его удалили из мероприятия"""
    date = convert_date(event.date)
    time = convert_time(event.date)
    message = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
              f"Администратор удалил вас из события <b>\"{date} {time} {event.title}\"</b>!\n\n" \
              f"Для уточнения деталей вы можете связаться с администратором @{settings.main_admin_url}"

    return message


def notify_set_level_message(level: int) -> str:
    """Сообщение для автоматического уведомления о присвоении уровня"""
    message = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
              f"Администратор присвоил вам уровень <b>{settings.levels[level]}</b>"

    return message


def notify_message(event: EventRel) -> str:
    """Сообщение для автоматического напоминания пользователю о событии"""
    event_date = convert_date(event.date)
    event_time = convert_time(event.date)
    message = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
              f"Напоминаем, что вы записались на событие <b>\"{event.title}\"</b>, " \
              f"которое пройдет <b>{event_date}</b> в <b>{event_time}</b>\n\n" \
              f"Если у вас не получится прийти, пожалуйста, сообщите об этом администратору @{settings.main_admin_url}"

    return message


def notify_tournament_message(tournament: Tournament) -> str:
    """Сообщение для автоматического напоминания пользователю о турнире"""
    event_date = convert_date(tournament.date)
    event_time = convert_time(tournament.date)
    message = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
              f"Напоминаем, что вы записались на турнир {tournament.type} <b>\"{tournament.title}\"</b>, " \
              f"который пройдет <b>{event_date}</b> в <b>{event_time}</b>\n\n" \
              f"Если у вас не получится прийти, пожалуйста, сообщите об этом администратору @{settings.main_admin_url}"

    return message


def notify_canceled_event(event: EventRel) -> str:
    """Сообщение об отмене мероприятия в связи с нехваткой участников"""
    event_date = convert_date(event.date)
    event_time = convert_time(event.date)
    message = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
              f"Событие <b>\"{event.title}\"</b>, запланированное <b>{event_date}</b> в <b>{event_time}</b>, " \
              f"<b>отменено</b> в связи с нехваткой участников\n\n" \
              f"По вопросу возврата оплаты обращайтесь к администратору @{settings.main_admin_url}"

    return message


def notify_deleted_event(event: EventRel) -> str:
    """Сообщение об удалении мероприятия администратором"""
    event_date = convert_date(event.date)
    event_time = convert_time(event.date)
    message = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
              f"Событие <b>\"{event.title}\"</b>, запланированное <b>{event_date}</b> в <b>{event_time}</b>, " \
              f"<b>отменено администратором</b>\n\n" \
              f"По вопросу возврата оплаты обращайтесь к администратору @{settings.main_admin_url}"

    return message


def get_help_message() -> str:
    """Сообщение для команды /help"""
    message = "<b>Возможности бота:</b>\n" \
              "• Позволяет зарегистрированным пользователям записываться на волейбольные события.\n" \
              "• Напоминает о приближающихся событиях.\n\n" \
              "<b>Инструкция по использованию:</b>\n" \
              "• Для перехода в главное меню отправьте команду \"👨🏻‍💻 Главное меню\".\n" \
              "• Во вкладке \"👤 Профиль\" вы можете посмотреть свои данные и уровень (❗ уровень пользователю присваивает администратор).\n" \
              "• Для записи на событие в главном меню нажмите кнопку \"🗓️Все события\", выберите подходящую дату и интересующее событие. " \
              "Для записи необходимо иметь уровень, не ниже требуемого, а также наличие свободных мест. " \
              "❗Обратите внимание, что окончательная запись на событие возможна только после подтверждения оплаты администратором. " \
              "В случае отмены записи менее чем за 4 часа до начала события, деньги не возвращаются. <a href='https://t.me/volleyballpiterchat/1710/1746'>Подробнее о правилах клуба</a>.\n" \
              "• Во вкладке \"🏐 Мои события\" вы можете отслеживать события, на которые подали заявку или записались.\n\n" \
              "<b>Контакт поддержки:</b> " \
              f"Если у вас есть вопросы или предложения, свяжитесь с нашей поддержкой через Telegram: @{settings.support_contact}."

    return message


def team_card(team: TeamUsers, user_already_in_team, user_already_has_another_team: bool, over_points: bool,
              over_players_count: bool, wrong_level: bool, payment: TournamentPayment | None, admin: bool) -> str:
    """
    Вывод карточки команды
    user_already_in_team: bool - пользователь уже в этой команде
    user_already_has_another_team: bool - пользователь уже в другой команде на этом турнире
    over_points: bool - количество баллов команды с пользователем превысит лимит
    over_players_count: bool - количество игроков команды с пользователем превысит лимит
    wrong_level: bool - неподходящий уровень для турнира
    """
    already_in_team = ""
    if user_already_in_team:
        already_in_team = "\n✅ Вы записаны в команду"
    elif user_already_has_another_team:
        already_in_team = "\n❗ Вы не можете записаться в команду, так как уже состоите в другой на этом турнире"
    elif over_points:
        already_in_team = "\n❗ Вы не можете записаться в команду, так как суммарное количество баллов команды будет превышать разрешенный лимит"
    elif over_players_count:
        already_in_team = "\n❗ Вы не можете записаться в команду, так как команда уже заполнена"
    elif wrong_level:
        already_in_team = "\n❗ Вы можете записаться в команду только в качестве либеро, так как у вас неподходящий уровень"

    # Статус оплаты
    paid = "\n❌ Участие не оплачено"
    if payment:
        if payment.paid_confirm:
            paid = "\n✅ Оплата подтверждена"
        else:
            paid = "\n⏳ Ожидается подтверждение платежа от администратора"

    # Скрываем статус оплаты для всех кроме участников команды
    if not user_already_in_team:
        paid = ""

    team_points = calculate_team_points(team.users, team.team_libero_id)
    message = f"<b>{team.title}</b>{paid}{already_in_team}\n\nКоличество баллов: <b>{team_points}</b>\nУчастники:\n"

    for count, user in enumerate(team.users, start=1):
        if admin:
            message += f"<b>{count}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> {settings.levels[user.level]}"
        else:
            message += f"<b>{count}.</b> {user.firstname} {user.lastname} {settings.levels[user.level]}"

        # пометка и капитан и либеро
        if user.id == team.team_leader_id and user.id == team.team_libero_id:
            message += " (капитан, либеро)"

        # пометка капитана
        elif user.id == team.team_leader_id:
            message += " (капитан)"

        # пометка либеро
        elif user.id == team.team_libero_id:
            message += " (либеро)"

        message += "\n"

    return message


def message_for_team_leader(user: User, team: TeamUsers, tournament: Tournament, admin: bool) -> str:
    """Оповещение капитана о принятии игрока в команду"""
    converted_date = convert_date_named_month(tournament.date)
    if admin:
        message = f"<a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> ({settings.levels[user.level]}) " \
                  f"хочет присоединиться к вашей команде <b>{team.title}</b> на турнир \"{tournament.title}\" {converted_date}\n\n"\
                  f"Добавить игрока в команду?"
    else:
        message = f"{user.firstname} {user.lastname} ({settings.levels[user.level]}) " \
                  f"хочет присоединиться к вашей команде <b>{team.title}</b> на турнир \"{tournament.title}\" {converted_date}\n\n" \
                  f"Добавить игрока в команду?"

    return message


def message_for_team_leader_about_libero(user: User, team: TeamUsers, tournament: Tournament,
                                         already_have_libero: bool, over_points: bool, admin: bool,
                                         team_libero: User | None = None, wrong_level: bool = False) -> str:
    """Оповещение капитана о принятии либеро в команду"""
    converted_date = convert_date_named_month(tournament.date)

    # если либеро уже есть
    if already_have_libero:
        # Если перебор по очкам при замене либеро
        reason = ""
        if over_points:
            reason = ", так как суммарное количество баллов превысило допустимое для этого турнира"
        if wrong_level:
            reason = ", так как уровень игрока превышает допустимый на турнире"

        if wrong_level or over_points:
            if admin:
                message = f"<a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> ({settings.levels[user.level]}) " \
                          f"хочет присоединиться к вашей команде <b>{team.title}</b> в качестве <b>либеро</b> вместо игрока " \
                          f"<a href='tg://user?id={team_libero.tg_id}'>{team_libero.firstname} {team_libero.lastname}</a> ({settings.levels[team_libero.level]})" \
                          f" на турнир \"{tournament.title}\" {converted_date}\n\n❗Игрок <a href='tg://user?id={team_libero.tg_id}'>{team_libero.firstname} {team_libero.lastname}</a> ({settings.levels[team_libero.level]}) " \
                          f"будет исключен из команды{reason}" \
                          f"\n\nДобавить игрока в команду?"
            else:
                message = f"{user.firstname} {user.lastname} ({settings.levels[user.level]}) " \
                          f"хочет присоединиться к вашей команде <b>{team.title}</b> в качестве <b>либеро</b> вместо игрока " \
                          f"{team_libero.firstname} {team_libero.lastname} ({settings.levels[team_libero.level]})" \
                          f" на турнир \"{tournament.title}\" {converted_date}\n\n❗Игрок {team_libero.firstname} {team_libero.lastname} ({settings.levels[team_libero.level]}) " \
                          f"будет исключен из команды{reason}" \
                          f"\n\nДобавить игрока в команду?"

        # Нет перебора по очкам
        else:
            if admin:
                message = f"<a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> ({settings.levels[user.level]}) " \
                          f"хочет присоединиться к вашей команде <b>{team.title}</b> в качестве <b>либеро</b> вместо игрока " \
                          f"<a href='tg://user?id={team_libero.tg_id}'>{team_libero.firstname} {team_libero.lastname}</a> ({settings.levels[team_libero.level]})" \
                          f" на турнир \"{tournament.title}\" {converted_date}\n\nДобавить игрока в команду?"
            else:
                message = f"{user.firstname} {user.lastname} ({settings.levels[user.level]}) " \
                          f"хочет присоединиться к вашей команде <b>{team.title}</b> в качестве <b>либеро</b> вместо игрока " \
                          f"{team_libero.firstname} {team_libero.lastname} ({settings.levels[team_libero.level]})" \
                          f" на турнир \"{tournament.title}\" {converted_date}\n\nДобавить игрока в команду?"

    # если либеро еще нет
    else:
        if admin:
            message = f"<a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> ({settings.levels[user.level]}) " \
                      f"хочет присоединиться к вашей команде <b>{team.title}</b> в качестве <b>либеро</b> на турнир \"{tournament.title}\" {converted_date}\n\n" \
                      f"Добавить игрока в команду?"
        else:
            message = f"{user.firstname} {user.lastname} ({settings.levels[user.level]}) " \
                      f"хочет присоединиться к вашей команде <b>{team.title}</b> в качестве <b>либеро</b> на турнир \"{tournament.title}\" {converted_date}\n\n" \
                      f"Добавить игрока в команду?"

    return message
