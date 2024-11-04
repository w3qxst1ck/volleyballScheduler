from database.schemas import User, EventRel
from routers.utils import convert_date


def user_profile_message(user: User) -> str:
    """Сообщение с профилем пользователя"""
    user_lvl = "🔝 Уровень:" + user.level if user.level else "🔝 Уровень: уровень еще не определен"
    message = f"Ваш профиль\n\n👤 {user.firstname} {user.lastname}\n{user_lvl}"

    return message


def event_card_message(event: EventRel, user_registered: bool) -> str:
    """Информация о событии с его пользователями"""
    date = convert_date(event.date)
    user_registered_count = len(event.users_registered)

    message = f"<b>{date}</b>\n\n<b>{event.title}</b>\n{event.type}\nЗарег-но:👥 {user_registered_count}/{event.places}\n\n"
    if user_registered:
        message += "✅ Вы <b>зарегистрированы</b> на это мероприятие"
    else:
        message += "❌ Вы еще <b>не зарегистрированы</b> на это мероприятие"
    return message