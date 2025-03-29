import datetime

import aiogram
import pytz

from database.orm import AsyncOrm
import routers.messages as ms
from routers import utils
from settings import settings
from routers.utils import write_excel_file


async def run_every_day(bot: aiogram.Bot):
    """Запуск ежедневной проверки"""
    await notify_users_about_events(bot)
    await delete_old_events()


async def run_every_hour(bot: aiogram.Bot) -> None:
    """Выполняется каждый час"""
    await update_events(bot)
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


async def update_events(bot: aiogram.Bot):
    """Изменение статуса прошедших событий"""
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


async def notify_users_about_events(bot: aiogram.Bot):
    """Напоминание пользователям о событии, на которое они записались (за день до события)"""
    events = await AsyncOrm.get_events_with_users()

    for event in events:
        if (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) + datetime.timedelta(days=1)).date() == event.date.date():
            for user in event.users_registered:
                try:
                    msg = ms.notify_message(event)
                    await bot.send_message(user.tg_id, msg)
                except:
                    pass


async def delete_old_events():
    """Удаление событий которые были более settings.expire_event_days дней назад"""
    await AsyncOrm.delete_old_events(settings.expire_event_days)


async def create_players_excel():
    """Создание файла с игроками"""
    users = await AsyncOrm.get_all_players_info()
    await write_excel_file(users)
