import datetime
from typing import Any, List

from aiogram import Router, types, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext

from database.schemas import TeamUsers, User, Tournament, TournamentTeams
from logger import logger
from routers.middlewares import CheckPrivateMessageMiddleware, DatabaseMiddleware
from routers import keyboards as kb, messages as ms
from routers.fsm_states import RegNewTeamFSM
from database.orm import AsyncOrm
from routers import utils
from routers.utils import convert_date, convert_time
from settings import settings

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.callback_query.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(DatabaseMiddleware())
router.callback_query.middleware.register(DatabaseMiddleware())


@router.callback_query(F.data.split("_")[0] == "pay-for-team")
async def payment_message(callback: types.CallbackQuery, session: Any) -> None:
    """Отправка сообщения об условиях оплаты"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])

    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)

    msg = ms.invoice_message_for_team(tournament, team.reserve)
    keyboard = kb.payment_tournament_confirm_keyboard(team_id, tournament_id)

    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.split("_")[0] == "t-paid")
async def paid_by_user(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Подтверждение оплаты пользователем"""
    tg_id = str(callback.from_user.id)
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    user: User = await AsyncOrm.get_user_by_tg_id(tg_id)

    # Создание платежа в БД
    await AsyncOrm.create_tournament_payment(team_id, tournament_id, session)

    # Сообщение пользователю
    msg = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
          f"Ваш платеж на сумму {tournament.price} руб. ожидает подтверждение администратором @{settings.main_admin_url}. " \
          f"После подтверждения вам будет отправлено уведомление об успешной оплате.\n\n" \
          f"⏳ <b>Дождитесь подтверждения оплаты от администратора</b>\n\n" \
          f"Вы можете отслеживать статус оплаты во вкладке \"👨🏻‍💻 Главное меню\" в разделе \"🏐 Мои события\""

    keyboard = kb.back_to_tournament(tournament_id)
    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())

    # Сообщение админу
    date = convert_date(tournament.date)
    time = convert_time(tournament.date)
    admin_msg = f"Капитан команды \"{team.title}\" <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                f"оплатил запись на турнир <b>{tournament.type}</b> \"{tournament.title}\" <b>{date} {time}</b> " \
                f"на сумму <b>{tournament.price} руб.</b> \n\nПодтвердите или отклоните оплату"
    keyboard = kb.admin_confirm_tournament_payment_keyboard(team_id, tournament_id)
    await bot.send_message(settings.main_admin_tg_id, admin_msg, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.split("_")[0] == "tournament-payment")
async def admin_confirm_payment(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Подтверждение или отклонение оплаты администратором"""
    confirmed = True if callback.data.split("_")[1] == "ok" else False
    team_id = int(callback.data.split("_")[2])
    tournament_id = int(callback.data.split("_")[3])

    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    team_lead: User = await AsyncOrm.get_user_by_id(team.team_leader_id)

    event_date = utils.convert_date(tournament.date)
    event_time = utils.convert_time(tournament.date)

    msg_to_admin = f"Капитан команды \"{team.title}\" <a href='tg://user?id={team_lead.tg_id}'>{team_lead.firstname} {team_lead.lastname}</a> " \
          f"оплатил запись на турнир <b>{tournament.type}</b> \"{tournament.title}\" <b>{event_date} {event_time}</b> " \
          f"на сумму <b>{tournament.price} руб.</b>\n\n"

    msg_to_captain = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                     f"Оплата за участие в турнире <b>{tournament.type}</b> \"{tournament.title}\" " \
                     f"<b>{event_date} {event_time}</b> на сумму {tournament.price} руб. для команды " \
                     f"\"{team.title}\"\n\n"

    keyboard = kb.back_to_tournament(tournament_id)

    # Если администратор подтвердил оплату
    if confirmed:
        # Обновляем статус платежа
        now_time = datetime.datetime.now()
        try:
            await AsyncOrm.update_tournament_payment_status(team_id, now_time, session)
            msg_to_admin += f"Оплата подтверждена ✅"
            msg_to_captain += f"Подтверждена ✅"

        except:
            msg_to_admin += f"❌ Ошибка, не удалось подтвердить платеж команде \"{team.title}\"."
            msg_to_captain += f"Не подтверждена ❌\nВы можете связаться с администрацией канала @{settings.main_admin_url}"

    # Оплата отклонена
    else:
        # удаляем платеж
        await AsyncOrm.delete_tournament_payment(team_id, session)

        msg_to_admin += "Оплата отклонена ❌\nОповещение направлено капитану команды"
        msg_to_captain += f"Не подтверждена ❌\nВы можете связаться с администрацией канала @{settings.main_admin_url}"

    # Сообщения для администратора
    await callback.message.edit_text(msg_to_admin)

    # Отправка сообщения капитану команды
    await bot.send_message(team_lead.tg_id, msg_to_captain, reply_markup=keyboard.as_markup())







