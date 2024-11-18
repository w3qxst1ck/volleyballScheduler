from database.schemas import User, EventRel, Event, PaymentsEventsUsers, Payment
from routers.utils import convert_date, convert_time
from settings import settings


def user_profile_message(user: User) -> str:
    """Сообщение с профилем пользователя"""
    user_lvl = f"🔝 Уровень: " + settings.levels[user.level] if user.level else f"🔝 Уровень: еще не определен"
    message = f"Ваш профиль\n\n👤 {user.firstname} {user.lastname}\n{user_lvl}"

    return message


# актуальная карточка
def event_card_for_user_message(event: EventRel, payment: Payment | None) -> str:
    """Информация о событии с его пользователями"""
    date = convert_date(event.date)
    time = convert_time(event.date)

    user_registered_count = len(event.users_registered)

    message = f"📅 <b>{date}</b> <b>{time}</b>\n"

    # пользователь еще не регистрировался
    if not payment:
        pass

    # пользователь ожидает подтверждения оплаты
    elif not payment.paid_confirm:
        message += "⏳ Ожидается подтверждение платежа от администратора\n\n"

    # пользователь зарегистрирован на мероприятие
    else:
        message += "✅ Вы <b>зарегистрированы</b> на это мероприятие\n\n"

    message += f"<b>\"{event.type}\"</b>\n" \
               f"{event.title}\n" \
               f"Минимальный уровень: {settings.levels[event.level]}\n\n" \
               f"💰 Цена: <b>{event.price} руб.</b>\n\n" \
               f"👥 Участников: {user_registered_count}/{event.places} (<b>свободных мест {event.places - user_registered_count}</b>)\n" \
               f"⚠️ Мин. кол-во участников: <b>{event.min_user_count}</b>\n\n"

    # если участники уже есть
    if event.users_registered:
        # сортировка по имени
        event.users_registered = sorted(event.users_registered, key=lambda user: user.firstname)

        message += "Участники:\n"
        for idx, user in enumerate(event.users_registered, 1):
            message += f"<b>{idx}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                       f"{f'({settings.levels[user.level]})' if user.level else ''}\n"

        # message += "\nДля перехода в диалог с участником нажмите на его имя"

    return message


# PAYMENTS
def invoice_message_for_user(event: Event) -> str:
    """Сообщение о стоимости мероприятия"""
    message = f"Цена мероприятия <b>\"{event.title} {convert_date(event.date)} в {convert_time(event.date)}\"</b> - <b>{event.price} руб.</b>\n\n"
    message += f"Для записи необходимо выполнить оплату переводом <b>{event.price}</b> руб. по телефону: \n\n{settings.admin_phone}\n\n"
    message +=  f"❗<b>ВАЖНО: в комментарии к оплате для подтверждения платежа необходимо указать имя пользователя (например Иван Иванов), " \
               f"указанные в вашем профиле</b>\n\n" \
               f"После выполнения оплаты нажмите кнопку <b>\"Оплатил\"</b>"
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
    message = f"🔔 <i>Автоматическое уведомление</i>\n\n" \
              f"Администратор удалил вас из мероприятия <b>\"{date} {time} {event.title}\"</b>!\n\n" \
              f"Для уточнения деталей вы можете связаться с администратором @{settings.main_admin_url}"

    return message


def notify_set_level_message(level: int) -> str:
    """Сообщение для автоматического уведомления о присвоении уровня"""
    message = f"🔔 <i>Автоматическое уведомление</i>\n\n" \
              f"Администратор присвоил вам уровень <b>\{settings.levels[level]}\</b>"

    return message


def notify_message(event: EventRel) -> str:
    """Сообщение для автоматического напоминания пользователю о событии"""
    event_date = convert_date(event.date)
    event_time = convert_time(event.date)
    message = f"🔔 <i>Автоматическое уведомление</i>\n\n" \
              f"Напоминаем, что вы записались на мероприятие <b>\"{event.title}\"</b>, " \
              f"которое пройдет <b>{event_date}</b> в <b>{event_time}</b>\n\n" \
              f"Если у вас не получится прийти, пожалуйста, сообщите об этом администратору @{settings.main_admin_url}"

    return message


def notify_canceled_event(event: EventRel) -> str:
    """Сообщение об отмене мероприятия в связи с нехваткой участников"""
    event_date = convert_date(event.date)
    event_time = convert_time(event.date)
    message = f"🔔 <i>Автоматическое уведомление</i>\n\n" \
              f"Мероприятие <b>\"{event.title}\"</b>, запланированное <b>{event_date}</b> в <b>{event_time}</b>, " \
              f"<b>отменено</b> в связи с нехваткой участников\n\n" \
              f"По вопросу возврата оплаты обращайтесь к администратору @{settings.main_admin_url}"

    return message


def get_help_message() -> str:
    """Сообщение для команды /help"""
    message = "<b>Возможности бота:</b>\n" \
              "- Дает возможность зарегистрированным пользователям записаться на волейбольные мероприятия\n" \
              "- Напоминает пользователям о приближающихся событиях\n\n" \
              "<b>Инструкция использования:</b>\n" \
              "- Для перехода в главное меню отправьте команду \"👨🏻‍💻 Главное меню\"\n" \
              "- Во вкладке \"👤 Профиль\" вы можете посмотреть свои данные и уровень (❗ уровень пользователю присваивает администратор)\n" \
              "- Для записи на мероприятие в главном меню нажмите кнопку \"🗓️Все мероприятия\", далее выберите подходящую дату и интересующее вас мероприятие.\n" \
              "Для записи на мероприятие вы должны иметь уровень не ниже требуемого, также запись возможна только при наличии свободных мест.\n" \
              "❗Обращаем внимание, что окончательная запись на мероприятие происходит после подтверждения оплаты администратором\n" \
              "- Во вкладке \"🏐 Мои мероприятия\" вы можете отслеживать мероприятия, на которые подали заявку или записались\n\n" \
              "<b>Контакт поддержки:</b>\n" \
              f"Если у вас есть вопросы или предложения, свяжитесь с нашей поддержкой в телеграм: @{settings.main_admin_url}"

    return message


