import datetime

import aiogram
import pytz

from database.orm import AsyncOrm


async def run_every_day_check():
    """Запуск ежедневной проверки"""
    await update_events()


async def update_events():
    """Изменение статуса прошедших событий"""
    events = await AsyncOrm.get_events()
    for event in events:
        if datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")).date() > event.date.date():
            await AsyncOrm.update_event_status(event.id)
