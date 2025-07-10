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
    time = convert_date(tournament.date)
    admin_msg = f"Капитан команды \"{team.title}\" <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                f"оплатил запись на турнир <b>{tournament.type}</b> \"{tournament.title}\" <b>{date} {time}</b> " \
                f"на сумму <b>{tournament.price} руб.</b> \n\nПодтвердите или отклоните оплату"
    keyboard = kb.admin_confirm_tournament_payment_keyboard(team_id, tournament_id)
    await bot.send_message(settings.main_admin_tg_id, admin_msg, reply_markup=keyboard.as_markup())






