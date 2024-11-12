import datetime

import aiogram
import pytz

from database.orm import AsyncOrm
import routers.messages as ms


async def run_every_day(bot: aiogram.Bot):
    """Запуск ежедневной проверки"""
    await update_events()
    await notify_users_about_events(bot)


async def update_events():
    """Изменение статуса прошедших событий"""
    events = await AsyncOrm.get_events()
    for event in events:
        if datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")).date() > event.date.date():
            await AsyncOrm.update_event_status(event.id)


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
