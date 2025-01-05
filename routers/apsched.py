import datetime

import aiogram
import pytz

from database.orm import AsyncOrm
import routers.messages as ms
from settings import settings


async def run_every_hour(bot: aiogram.Bot) -> None:
    """Выполняется каждый час"""
    await update_events()
    await check_min_users_count(bot)


async def check_min_users_count(bot: aiogram.Bot):
    """Проверка мероприятий на кол-во зареганых людей"""
    active_events = await AsyncOrm.get_events(only_active=True)
    now = datetime.datetime.now(tz=pytz.timezone("Europe/Moscow"))

    for event in active_events:
        print(f"Время now + 2 hours: {now}")
        print(f"Время event.date with timezone: {event.date.astimezone(tz=pytz.timezone('Europe/Moscow'))}")
        if now + datetime.timedelta(hours=2) > event.date.astimezone(tz=pytz.timezone("Europe/Moscow")):
            event_with_users = await AsyncOrm.get_event_with_users(event.id)
            user_registered_count = len(event_with_users.users_registered)

            if event.min_user_count > user_registered_count:
                # переводим мероприятие в неактивные
                await AsyncOrm.update_event_status_to_false(event.id)

                # оповещаем пользователей
                msg = ms.notify_canceled_event(event_with_users)
                for user in event_with_users.users_registered:

                    await bot.send_message(user.tg_id, msg)


async def run_every_day(bot: aiogram.Bot):
    """Запуск ежедневной проверки"""
    await notify_users_about_events(bot)
    await delete_old_events()


async def update_events():
    """Изменение статуса прошедших событий"""
    events = await AsyncOrm.get_events()
    for event in events:
        if datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) > event.date.astimezone(tz=pytz.timezone("Europe/Moscow")):
            await AsyncOrm.update_event_status_to_false(event.id)


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
