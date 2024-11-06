from database.schemas import User, EventRel
from routers.utils import convert_date, convert_time
from settings import settings

def user_profile_message(user: User) -> str:
    """Сообщение с профилем пользователя"""
    user_lvl = "🔝 Уровень:" + user.level if user.level else "🔝 Уровень: уровень еще не определен"
    message = f"Ваш профиль\n\n👤 {user.firstname} {user.lastname}\n{user_lvl}"

    return message


def event_card_message(event: EventRel, user_registered: bool) -> str:
    """Информация о событии с его пользователями"""
    date = convert_date(event.date)
    user_registered_count = len(event.users_registered)

    message = f"<b>📅 {date}</b>\n\n" \
              f"<b>\"{event.title}\"</b>\n" \
              f"{event.type}\n" \
              f"👥Участников: {user_registered_count}/{event.places} (<b>свободных мест {event.places - user_registered_count}</b>)\n\n"
    if user_registered:
        message += "✅ Вы <b>зарегистрированы</b> на это мероприятие"
    else:
        message += "❌ Вы еще <b>не зарегистрированы</b> на это мероприятие"
    return message


def event_card_for_admin_message(event: EventRel) -> str:
    """Информация о событии для админа"""
    date = convert_date(event.date)
    user_registered_count = len(event.users_registered)
    message = f"<b>📅 {date}</b>\n\n" \
              f"<b>\"{event.title}\"</b>\n" \
              f"{event.type}\n" \
              f"👥Участников: {user_registered_count}/{event.places} (<b>свободных мест {event.places - user_registered_count}</b>)\n\n"

    if event.users_registered:
        message += "Участники:\n"
        for idx, user in enumerate(event.users_registered, 1):
            message += f"<b>{idx}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> <b>{'уровень ' + user.level if user.level else ''}</b>\n"

        message += "\nДля перехода в диалог с участником нажмите на его имя\n" \
                   "Чтобы удалить участника с события нажмите кнопку с соответствующим номером участника"
    # если участников нет
    else:
        message += "<b>Участников пока нет</b>"

    return message


def notify_message(event: EventRel) -> str:
    """Сообщение для автоматического напоминания пользователю о событии"""
    event_date = convert_date(event.date)
    event_time = convert_time(event.date)
    message = f"🔔 <i>Автоматическое уведомление</i>\n\n" \
              f"Напоминаем, что вы записались на мероприятие <b>\"{event.title}\"</b>, " \
              f"которое пройдет <b>{event_date}</b> в <b>{event_time}</b>\n\n" \
              f"Если у вас не получится прийти, пожалуйста, сообщите об этом администратору @{settings.main_admin}"

    return message


