import datetime
from typing import Any

import aiogram
import asyncpg
import pytz

from database.orm import AsyncOrm
import routers.messages as ms
from database.schemas import Tournament, TeamUsers, User
from routers import utils
from settings import settings
from routers.utils import write_excel_file


async def run_every_day(bot: aiogram.Bot):
    """Запуск ежедневной проверки"""
    session = await asyncpg.connect(
        user=settings.db.postgres_user,
        host=settings.db.postgres_host,
        password=settings.db.postgres_password,
        port=settings.db.postgres_port,
        database=settings.db.postgres_db
    )

    await notify_users_about_events(bot, session)
    await delete_old_events(session)


async def run_every_hour(bot: aiogram.Bot) -> None:
    """Выполняется каждый час"""

    session = await asyncpg.connect(
        user=settings.db.postgres_user,
        host=settings.db.postgres_host,
        password=settings.db.postgres_password,
        port=settings.db.postgres_port,
        database=settings.db.postgres_db
    )

    await update_events(bot, session)
    # TODO проверку на минимальное кол-во команд для турниров
    await check_min_users_count(bot)


async def check_min_users_count(bot: aiogram.Bot):
    """Проверка мероприятий на кол-во зареганых людей"""
    active_events = await AsyncOrm.get_events(only_active=True)
    now = datetime.datetime.now(tz=pytz.timezone("Europe/Moscow"))

    for event in active_events:
        # now + datetime.timedelta(hours=2, seconds=10) - текущее время + 2 часа
        # event.date.astimezone(tz=pytz.timezone("Europe/Moscow")) - datetime.timedelta(hours=3) - перевод даты в текущее время по мск
        if now + datetime.timedelta(hours=2) > \
                event.date.astimezone(tz=pytz.timezone("Europe/Moscow")) - datetime.timedelta(hours=3):
            event_with_users = await AsyncOrm.get_event_with_users(event.id)
            user_registered_count = len(event_with_users.users_registered)

            if event.min_user_count > user_registered_count:
                # переводим мероприятие в неактивные
                await AsyncOrm.update_event_status_to_false(event.id)

                # оповещаем пользователей
                msg = ms.notify_canceled_event(event_with_users)
                for user in event_with_users.users_registered:

                    await bot.send_message(user.tg_id, msg)


async def update_events(bot: aiogram.Bot, session: Any):
    """Изменение статуса прошедших событий"""
    # Для обычных событий (тренировок, игр и тд.)
    events = await AsyncOrm.get_events()
    for event in events:
        # сравниваем текущее время + 1 ч с временем события
        # перевод события в неактивное через 1 ч после его начала
        if datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) - datetime.timedelta(hours=1) > \
                event.date.astimezone(tz=pytz.timezone("Europe/Moscow")) - datetime.timedelta(hours=3):
            await AsyncOrm.update_event_status_to_false(event.id)

            # отправляем администратору список людей резерва, для возвращения оплаты
            reserve_users = await AsyncOrm.get_reserved_users_by_event_id(event.id)
            if reserve_users:
                date = utils.convert_date(event.date)
                time = utils.convert_time(event.date)
                msg_for_admin = f"Необходимо вернуть деньги следующим <b>пользователям из резерва</b> " \
                      f"на событие {event.type} \"{event.title}\" {date} в {time}:\n\n"
                for user in reserve_users:
                    msg_for_admin += f"<a href='tg://user?id={user.user.tg_id}'>{user.user.firstname} {user.user.lastname}</a> - {event.price} руб.\n"

                # отправляем сообщение администратору
                try:
                    await bot.send_message(settings.main_admin_tg_id, msg_for_admin)
                except:
                    pass

    # Только для турниров
    tournaments: list[Tournament] = await AsyncOrm.get_all_tournaments(0, session)

    for tournament in tournaments:
        # сравниваем текущее время + 1 ч с временем события
        # перевод события в неактивное через 1 ч после его начала
        if datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) - datetime.timedelta(hours=1) > \
                tournament.date.astimezone(tz=pytz.timezone("Europe/Moscow")) - datetime.timedelta(hours=3):
            await AsyncOrm.update_tournament_status_to_false(tournament.id, session)

            # Получаем команды из резерва на этом турнире
            teams: list[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament.id, session)
            reserve_teams: list[TeamUsers] = []
            for team in teams:
                if team.reserve:
                    reserve_teams.append(team)

            # Отправляем админу список капитанов команд, которые были в резерве и не попали на турнир
            if reserve_teams:
                date = utils.convert_date(tournament.date)
                time = utils.convert_time(tournament.date)

                msg_for_admin = f"Необходимо вернуть деньги следующим капитанам <b>команд из резерва</b> " \
                      f"с турнира {tournament.type} \"{tournament.title}\" {date} в {time}:\n\n"

                for team in reserve_teams:
                    team_leader: User = await AsyncOrm.get_user_by_id(team.team_leader_id)
                    msg_for_admin += f"<a href='tg://user?id={team_leader.tg_id}'>{team_leader.firstname} {team_leader.lastname}</a>" \
                                     f"(команда <b>{team.title}</b>) - {tournament.price} руб.\n"

                # отправляем сообщение администратору
                try:
                    await bot.send_message(settings.main_admin_tg_id, msg_for_admin)
                except:
                    pass


async def notify_users_about_events(bot: aiogram.Bot, session: Any):
    """Напоминание пользователям о событии, на которое они записались (за день до события)"""
    # Для обычных событий
    events = await AsyncOrm.get_events_with_users()

    for event in events:
        if (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) + datetime.timedelta(days=1)).date() == event.date.date():
            for user in event.users_registered:
                try:
                    msg = ms.notify_message(event)
                    await bot.send_message(user.tg_id, msg)
                except:
                    pass

    # Для турниров
    tournaments: list[Tournament] = await AsyncOrm.get_all_tournaments(10, session)
    for tournament in tournaments:
        if (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) + datetime.timedelta(days=1)).date() == tournament.date.date():
            teams: list[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament.id, session)

            for team in teams:
                if not team.reserve:
                    for user in team.users:
                        try:
                            msg = ms.notify_tournament_message(tournament)
                            await bot.send_message(user.tg_id, msg)
                        except:
                            pass


async def delete_old_events(session: Any):
    """Удаление событий которые были более settings.expire_event_days дней назад"""
    # Удаление обычных событий
    await AsyncOrm.delete_old_events(settings.expire_event_days)

    # Удаление турниров и команд
    await AsyncOrm.delete_old_tournaments(settings.expire_event_days, session)


async def create_players_excel():
    """Создание файла с игроками"""
    users = await AsyncOrm.get_all_players_info()
    await write_excel_file(users)
