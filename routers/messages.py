from database.schemas import User, EventRel, Event, PaymentsEventsUsers, Payment
from routers.utils import convert_date, convert_time, convert_date_named_month
from settings import settings


def main_menu_message() -> str:
    """Сообщение главного меню"""
    message = "<b>Главное меню</b>\n\n" \
              "🗓 <b>Все события</b> - в этом разделе вы можете записаться на тренировку или игровой сбор.\n" \
              "👤 <b>Мой профиль</b> - в этом разделе вы можете изменить Фамилию, Имя. Узнать Ваш уровень игры.\n" \
              "🏐 <b>Мои события</b> - в этом разделе вы можете ознакомиться с событиями на которые вы записаны."
    return message


def user_profile_message(user: User) -> str:
    """Сообщение с профилем пользователя"""
    user_lvl = f"🔝 Уровень: " + settings.levels[user.level] if user.level else f"🔝 Уровень: еще не определен"
    message = f"<b>Профиль</b>\n\n👤 {user.firstname} {user.lastname}\n{user_lvl}"

    return message


# актуальная карточка
def event_card_for_user_message(event: EventRel, payment: Payment | None) -> str:
    """Информация о событии с его пользователями"""
    date = convert_date_named_month(event.date)
    time = convert_time(event.date)

    user_registered_count = len(event.users_registered)

    message = f"📅 <b>{date}, {time}</b>\n"

    # пользователь еще не регистрировался
    if not payment:
        pass

    # пользователь ожидает подтверждения оплаты
    elif not payment.paid_confirm:
        message += "⏳ Ожидается подтверждение платежа от администратора\n\n"

    # пользователь зарегистрирован на мероприятие
    else:
        message += f"✅ <b>Вы записаны на событие \"{event.type}\"</b>\n\n"

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
            message += f"<b>{idx}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                       f"{f'({settings.levels[user.level]})' if user.level else ''}\n"

        # message += "\nДля перехода в диалог с участником нажмите на его имя"

    return message


# PAYMENTS
def invoice_message_for_user(event: Event) -> str:
    """Сообщение о стоимости мероприятия"""
    message = f"🗓 <b>Дата и время:</b> {convert_date(event.date)}, {convert_time(event.date)}\n"
    message += f"📅 <b>Событие:</b> {event.type}\n"
    message += f"💰 <b>Стоимость участия:</b> {event.price} руб.\n\n"
    message += f"Для записи на событие необходимо перевести {event.price} руб. на указанный номер телефона: <b>{settings.admin_phone}</b>\n\n"
    message += f"❗<b>ВАЖНО:</b> \n" \
               f"В комментарии к оплате для подтверждения платежа укажите ваше имя (например, Иван Иванов), которое указано в вашем профиле.\n\n" \
               f"После завершения оплаты нажмите кнопку <b>\"Оплатил(а)\".</b>"
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
              f"Администратор присвоил вам уровень <b>\{settings.levels[level]}\</b>"

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


